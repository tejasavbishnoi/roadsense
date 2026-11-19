"""RoadSense API - road damage detection for images and dashcam videos."""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from . import config, severity
from .detector import Detector, ModelNotReady

VERSION = "1.0.0"

# BGR colours for annotated video frames (match the frontend palette)
COLORS = {
    "pothole": (77, 77, 239),
    "alligator_crack": (22, 115, 249),
    "transverse_crack": (21, 204, 250),
    "longitudinal_crack": (212, 182, 6),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    detector = Detector()
    detector.load()
    app.state.detector = detector
    yield


app = FastAPI(
    title="RoadSense API",
    version=VERSION,
    description="Detects potholes and cracks in road images and dashcam videos and scores road condition.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_detector() -> Detector:
    return app.state.detector


def _require_ready(detector: Detector) -> None:
    if not detector.ready:
        raise HTTPException(status_code=503, detail=detector.error or "Model is not loaded yet")


async def _read_limited(file: UploadFile, max_mb: float) -> bytes:
    data = await file.read()
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large (max {max_mb:.0f} MB)")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    return data


# --------------------------------------------------------------------------- #
@app.get("/")
def root():
    return {"name": "RoadSense API", "version": VERSION, "docs": "/docs"}


@app.get("/health")
def health(detector: Detector = Depends(get_detector)):
    return {
        "status": "ok" if detector.ready else "degraded",
        "model_loaded": detector.ready,
        "classes": detector.names,
        "detail": detector.error,
        "version": VERSION,
    }


@app.get("/model")
def model_card(detector: Detector = Depends(get_detector)):
    """Evaluation results produced by training/evaluate.py."""
    card = {"available": False, "classes": detector.names}
    if config.METRICS_PATH.exists():
        card = {"available": True, **json.loads(config.METRICS_PATH.read_text())}
    card["severity_weights"] = severity.CLASS_WEIGHTS
    return card


@app.post("/predict/image")
async def predict_image(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0, description="confidence used for the condition score"),
    detector: Detector = Depends(get_detector),
):
    _require_ready(detector)
    data = await _read_limited(file, config.MAX_IMAGE_MB)
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=415, detail="Unsupported image. Use JPG, PNG or WebP.")
    arr = np.asarray(img)

    t0 = time.perf_counter()
    try:
        detections = (await run_in_threadpool(detector.predict, [arr]))[0]
    except ModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "filename": file.filename,
        "width": img.width,
        "height": img.height,
        "inference_ms": round(elapsed, 1),
        "detections": detections,
        "summary": severity.assess(detections, conf),
    }


def _annotate(frame_bgr: np.ndarray, detections: list[dict], min_conf: float, width: int = 640) -> str:
    h, w = frame_bgr.shape[:2]
    scale = width / w
    img = cv2.resize(frame_bgr, (width, int(h * scale)))
    for d in detections:
        if d["confidence"] < min_conf:
            continue
        x1, y1, x2, y2 = d["box"]
        p1 = (int(x1 * img.shape[1]), int(y1 * img.shape[0]))
        p2 = (int(x2 * img.shape[1]), int(y2 * img.shape[0]))
        color = COLORS.get(d["label"], (255, 255, 255))
        cv2.rectangle(img, p1, p2, color, 2)
        text = f"{d['label'].replace('_', ' ')} {d['confidence']:.0%}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(img, (p1[0], p1[1] - th - 6), (p1[0] + tw + 6, p1[1]), color, -1)
        cv2.putText(img, text, (p1[0] + 3, p1[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (15, 15, 15), 1, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode() if ok else ""


@app.post("/predict/video")
async def predict_video(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0),
    sample_fps: float = Query(config.VIDEO_SAMPLE_FPS, gt=0.0, le=10.0),
    detector: Detector = Depends(get_detector),
):
    _require_ready(detector)
    data = await _read_limited(file, config.MAX_VIDEO_MB)
    suffix = os.path.splitext(file.filename or "")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        return await run_in_threadpool(_process_video, path, conf, sample_fps, detector, file.filename)
    finally:
        os.unlink(path)


def _process_video(path: str, conf: float, sample_fps: float, detector: Detector, filename: str | None):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise HTTPException(status_code=415, detail="Could not read video. Use MP4, MOV or WebM.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if total_frames else 0.0
    step = max(1, round(fps / sample_fps))
    max_frames = int(config.MAX_VIDEO_SECONDS * fps)

    t0 = time.perf_counter()
    timeline, frames_bgr = [], []
    batch_rgb, batch_meta = [], []

    def flush():
        if not batch_rgb:
            return
        for (idx, bgr), dets in zip(batch_meta, detector.predict(batch_rgb)):
            s = severity.assess(dets, conf)
            timeline.append({"t": round(idx / fps, 2), "score": s["score"], "level": s["level"],
                             "counts": s["counts"], "total": s["total"]})
            frames_bgr.append((s["score"], idx, bgr, dets))
        batch_rgb.clear()
        batch_meta.clear()

    idx = 0
    try:
        while idx < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                small = frame if frame.shape[1] <= 1280 else cv2.resize(
                    frame, (1280, int(frame.shape[0] * 1280 / frame.shape[1])))
                batch_rgb.append(small[..., ::-1].copy())
                batch_meta.append((idx, small))
                if len(batch_rgb) == 8:
                    flush()
            idx += 1
        flush()
    except ModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        cap.release()

    if not timeline:
        raise HTTPException(status_code=422, detail="No frames could be decoded from this video.")

    scores = [p["score"] for p in timeline]
    totals: dict[str, int] = {}
    for p in timeline:
        for k, v in p["counts"].items():
            totals[k] = totals.get(k, 0) + v

    worst = sorted(frames_bgr, key=lambda f: f[0], reverse=True)[:4]
    worst_frames = [
        {"t": round(i / fps, 2), "score": s, "level": severity.level(s), "image": _annotate(bgr, dets, conf)}
        for s, i, bgr, dets in sorted(worst, key=lambda f: f[1])
        if s > 0
    ]
    avg = round(sum(scores) / len(scores))
    damaged = sum(1 for s in scores if s >= 15)
    return {
        "filename": filename,
        "duration_s": round(min(duration, config.MAX_VIDEO_SECONDS) if duration else timeline[-1]["t"], 2),
        "truncated": duration > config.MAX_VIDEO_SECONDS,
        "fps": round(fps, 2),
        "frames_analyzed": len(timeline),
        "processing_ms": round((time.perf_counter() - t0) * 1000, 1),
        "summary": {
            "average_score": avg,
            "peak_score": max(scores),
            "level": severity.level(avg),
            "damaged_frame_ratio": round(damaged / len(scores), 3),
            "detections_by_class": totals,
        },
        "timeline": timeline,
        "worst_frames": worst_frames,
    }
