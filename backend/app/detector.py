"""Thin wrapper around an Ultralytics YOLO model."""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from . import config


class ModelNotReady(RuntimeError):
    pass


class Detector:
    def __init__(self, weights: Path = config.MODEL_PATH):
        self.weights = Path(weights)
        self._model = None
        self._lock = threading.Lock()
        self.error: str | None = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    @property
    def names(self) -> list[str]:
        if not self.ready:
            return []
        n = self._model.names
        return [n[i] for i in sorted(n)] if isinstance(n, dict) else list(n)

    def load(self) -> None:
        if not self.weights.exists():
            self.error = f"No model weights at {self.weights}. Train one (see training/) and copy best.pt there."
            return
        try:
            from ultralytics import YOLO  # heavy import, keep it lazy

            self._model = YOLO(str(self.weights))
            # warm-up so the first real request isn't slow
            self._model.predict(np.zeros((config.IMAGE_SIZE, config.IMAGE_SIZE, 3), np.uint8), verbose=False)
            self.error = None
        except Exception as exc:  # pragma: no cover - depends on weights file
            self._model = None
            self.error = f"Failed to load model: {exc}"

    def predict(self, images: list[np.ndarray]) -> list[list[dict]]:
        """images: list of RGB uint8 arrays -> detections per image (boxes normalised to 0-1)."""
        if not self.ready:
            raise ModelNotReady(self.error or "Model not loaded")
        # Ultralytics expects BGR for numpy input
        bgr = [np.ascontiguousarray(img[..., ::-1]) for img in images]
        with self._lock:
            results = self._model.predict(bgr, conf=config.MIN_CONFIDENCE, imgsz=config.IMAGE_SIZE, verbose=False)
        names = self.names
        out = []
        for img, res in zip(images, results):
            h, w = img.shape[:2]
            dets = []
            boxes = res.boxes
            xyxy = boxes.xyxy.cpu().numpy() if len(boxes) else np.zeros((0, 4))
            confs = boxes.conf.cpu().numpy() if len(boxes) else np.zeros(0)
            classes = boxes.cls.cpu().numpy().astype(int) if len(boxes) else np.zeros(0, int)
            for (x1, y1, x2, y2), c, k in zip(xyxy, confs, classes):
                bw, bh = (x2 - x1) / w, (y2 - y1) / h
                dets.append({
                    "label": names[k] if k < len(names) else str(k),
                    "confidence": round(float(c), 4),
                    "box": [round(float(x1 / w), 5), round(float(y1 / h), 5),
                            round(float(x2 / w), 5), round(float(y2 / h), 5)],
                    "area_ratio": round(float(bw * bh), 6),
                })
            dets.sort(key=lambda d: d["confidence"], reverse=True)
            out.append(dets)
        return out
