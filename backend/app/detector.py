"""Model wrapper with two backends.

* ``best.onnx`` -> ONNX Runtime + NumPy only (no PyTorch). Used in production:
  it needs ~150 MB of RAM, so it fits free hosting tiers.
* ``best.pt``   -> Ultralytics/PyTorch. Handy during development.

Both return the same detections: label, confidence, box normalised to 0-1, area ratio.
"""

from __future__ import annotations

import ast
import threading
from pathlib import Path

import cv2
import numpy as np

from . import config

DEFAULT_NAMES = ["longitudinal_crack", "transverse_crack", "alligator_crack", "pothole"]


class ModelNotReady(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Pre/post-processing for the ONNX backend (mirrors Ultralytics' letterbox)
# --------------------------------------------------------------------------- #
def letterbox(img: np.ndarray, size: int) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize keeping aspect ratio and pad to size x size with grey (114), centred."""
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nw, nh = round(w * r), round(h * r)
    pad_w, pad_h = (size - nw) / 2, (size - nh) / 2
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR) if (nw, nh) != (w, h) else img
    top, bottom = round(pad_h - 0.1), round(pad_h + 0.1)
    left, right = round(pad_w - 0.1), round(pad_w + 0.1)
    out = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return out, r, (left, top)


def decode(output: np.ndarray, conf: float, ratio: float, pad: tuple[float, float],
           orig_w: int, orig_h: int, iou: float = 0.7) -> list[tuple[float, float, float, float, float, int]]:
    """Turn raw ONNX output into (x1, y1, x2, y2, score, cls) in original-image pixels.

    Handles both export styles:
      * end-to-end / NMS-free (YOLO26 default): shape (1, N, 6) = x1, y1, x2, y2, score, cls
      * classic: shape (1, 4 + num_classes, anchors) = cx, cy, w, h, class scores -> needs NMS
    """
    out = np.asarray(output)[0]
    if out.ndim != 2:
        raise ValueError(f"Unexpected ONNX output shape {np.asarray(output).shape}")

    if out.shape[-1] == 6 and out.shape[0] != 6:  # end-to-end
        boxes, scores, classes = out[:, :4], out[:, 4], out[:, 5].astype(int)
        keep = scores >= conf
        boxes, scores, classes = boxes[keep], scores[keep], classes[keep]
    else:  # classic, (4 + nc, anchors)
        if out.shape[0] > out.shape[1]:
            out = out.T
        cxcywh, cls_scores = out[:4].T, out[4:].T
        classes = cls_scores.argmax(1)
        scores = cls_scores.max(1)
        keep = scores >= conf
        cxcywh, scores, classes = cxcywh[keep], scores[keep], classes[keep]
        boxes = np.empty_like(cxcywh)
        boxes[:, 0] = cxcywh[:, 0] - cxcywh[:, 2] / 2
        boxes[:, 1] = cxcywh[:, 1] - cxcywh[:, 3] / 2
        boxes[:, 2] = cxcywh[:, 0] + cxcywh[:, 2] / 2
        boxes[:, 3] = cxcywh[:, 1] + cxcywh[:, 3] / 2
        if len(boxes):
            # class-aware NMS: offset boxes per class so different classes never suppress each other
            offset = classes[:, None] * 4096.0
            xywh = np.concatenate([boxes[:, :2] + offset, boxes[:, 2:] - boxes[:, :2]], 1)
            idx = cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(), conf, iou)
            idx = np.array(idx).reshape(-1)
            boxes, scores, classes = boxes[idx], scores[idx], classes[idx]

    # undo letterbox
    boxes = boxes.astype(np.float32).copy()
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad[0]) / ratio
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad[1]) / ratio
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, orig_w)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, orig_h)
    return [(float(b[0]), float(b[1]), float(b[2]), float(b[3]), float(s), int(c))
            for b, s, c in zip(boxes, scores, classes) if b[2] - b[0] > 1 and b[3] - b[1] > 1]


def to_detections(raw, names: list[str], w: int, h: int) -> list[dict]:
    dets = []
    for x1, y1, x2, y2, score, k in raw:
        dets.append({
            "label": names[k] if 0 <= k < len(names) else str(k),
            "confidence": round(score, 4),
            "box": [round(x1 / w, 5), round(y1 / h, 5), round(x2 / w, 5), round(y2 / h, 5)],
            "area_ratio": round(((x2 - x1) / w) * ((y2 - y1) / h), 6),
        })
    dets.sort(key=lambda d: d["confidence"], reverse=True)
    return dets


# --------------------------------------------------------------------------- #
class Detector:
    def __init__(self, weights: Path | None = None):
        self.weights = Path(weights) if weights else config.resolve_model_path()
        self._backend: str | None = None
        self._session = None  # onnxruntime session
        self._model = None  # ultralytics model
        self._names: list[str] = []
        self._imgsz = config.IMAGE_SIZE
        self._lock = threading.Lock()
        self.error: str | None = None

    @property
    def ready(self) -> bool:
        return self._backend is not None

    @property
    def backend(self) -> str | None:
        return self._backend

    @property
    def names(self) -> list[str]:
        return list(self._names)

    def load(self) -> None:
        if not self.weights.exists():
            self.error = (f"No model weights at {self.weights}. Train one (see training/) and put "
                          "best.onnx (or best.pt) in backend/weights/.")
            return
        try:
            if self.weights.suffix == ".onnx":
                self._load_onnx()
            else:
                self._load_ultralytics()
            self.predict([np.zeros((self._imgsz, self._imgsz, 3), np.uint8)])  # warm-up
            self.error = None
        except Exception as exc:  # pragma: no cover - depends on weights file
            self._backend = None
            self.error = f"Failed to load model: {exc}"

    def _load_onnx(self) -> None:
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = config.ONNX_THREADS
        self._session = ort.InferenceSession(str(self.weights), opts, providers=["CPUExecutionProvider"])
        meta = self._session.get_modelmeta().custom_metadata_map or {}
        names = meta.get("names")
        if names:
            parsed = ast.literal_eval(names)
            self._names = [parsed[i] for i in sorted(parsed)] if isinstance(parsed, dict) else list(parsed)
        else:
            self._names = DEFAULT_NAMES
        shape = self._session.get_inputs()[0].shape  # [1, 3, H, W] (may be symbolic)
        if isinstance(shape[-1], int):
            self._imgsz = shape[-1]
        self._backend = "onnx"

    def _load_ultralytics(self) -> None:
        from ultralytics import YOLO  # heavy import, keep it lazy

        self._model = YOLO(str(self.weights))
        n = self._model.names
        self._names = [n[i] for i in sorted(n)] if isinstance(n, dict) else list(n)
        self._backend = "pytorch"

    def predict(self, images: list[np.ndarray]) -> list[list[dict]]:
        """images: list of RGB uint8 arrays -> detections per image (boxes normalised to 0-1)."""
        if not self.ready:
            raise ModelNotReady(self.error or "Model not loaded")
        if self._backend == "onnx":
            return [self._predict_onnx(img) for img in images]
        return self._predict_ultralytics(images)

    def _predict_onnx(self, img: np.ndarray) -> list[dict]:
        h, w = img.shape[:2]
        lb, ratio, pad = letterbox(img, self._imgsz)  # RGB in, RGB out
        x = (lb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        with self._lock:
            out = self._session.run(None, {self._session.get_inputs()[0].name: x})[0]
        return to_detections(decode(out, config.MIN_CONFIDENCE, ratio, pad, w, h), self._names, w, h)

    def _predict_ultralytics(self, images: list[np.ndarray]) -> list[list[dict]]:
        bgr = [np.ascontiguousarray(img[..., ::-1]) for img in images]  # Ultralytics wants BGR arrays
        with self._lock:
            results = self._model.predict(bgr, conf=config.MIN_CONFIDENCE, imgsz=self._imgsz, verbose=False)
        out = []
        for img, res in zip(images, results):
            h, w = img.shape[:2]
            b = res.boxes
            raw = [(*map(float, xyxy), float(c), int(k)) for xyxy, c, k in
                   zip(b.xyxy.cpu().numpy(), b.conf.cpu().numpy(), b.cls.cpu().numpy())] if len(b) else []
            out.append(to_detections(raw, self._names, w, h))
        return out
