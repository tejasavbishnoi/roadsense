"""Check the ONNX deployment path.

    cd backend
    python scripts/check_onnx.py path/to/road.jpg

Runs three things on one photo:
  1. Ultralytics + best.pt     (the original PyTorch model)
  2. Ultralytics + best.onnx   (reference: official pre/post-processing)
  3. RoadSense  + best.onnx    (our NumPy/ONNX Runtime code used in production)

(2) and (3) must match exactly: that proves our letterbox and decoding are correct.
(1) can differ slightly in confidence because PyTorch pads images only to a multiple
of 32 (e.g. 640x448), while the exported ONNX model always takes a 640x640 square.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.detector import Detector, to_detections  # noqa: E402

img = np.asarray(ImageOps.exif_transpose(Image.open(sys.argv[1])).convert("RGB"))
h, w = img.shape[:2]
weights = ROOT / "weights"
CONF = 0.25


def ultralytics_run(path: Path) -> list[dict]:
    from ultralytics import YOLO

    model = YOLO(str(path), task="detect")
    res = model.predict(np.ascontiguousarray(img[..., ::-1]), conf=0.1, imgsz=640, verbose=False)[0]
    names = [model.names[i] for i in sorted(model.names)]
    b = res.boxes
    raw = [(*map(float, xyxy), float(c), int(k)) for xyxy, c, k in
           zip(b.xyxy.cpu().numpy(), b.conf.cpu().numpy(), b.cls.cpu().numpy())]
    return to_detections(raw, names, w, h)


def ours(path: Path) -> list[dict]:
    d = Detector(path)
    d.load()
    if not d.ready:
        sys.exit(f"{path.name}: {d.error}")
    return d.predict([img])[0]


def show(title: str, dets: list[dict]) -> list[dict]:
    dets = [x for x in dets if x["confidence"] >= CONF]
    print(f"\n{title}: {len(dets)} detections")
    for x in dets:
        print(f"  {x['label']:20s} {x['confidence']:.2f}  {x['box']}")
    return dets


def same(a: list[dict], b: list[dict], conf_tol: float, box_tol: float) -> bool:
    a = sorted(a, key=lambda x: x["box"])
    b = sorted(b, key=lambda x: x["box"])
    return len(a) == len(b) and all(
        p["label"] == q["label"] and abs(p["confidence"] - q["confidence"]) <= conf_tol
        and max(abs(u - v) for u, v in zip(p["box"], q["box"])) <= box_tol
        for p, q in zip(a, b))


pt = show("1. Ultralytics + best.pt (PyTorch)", ultralytics_run(weights / "best.pt"))
ref = show("2. Ultralytics + best.onnx (reference)", ultralytics_run(weights / "best.onnx"))
mine = show("3. RoadSense + best.onnx (production code)", ours(weights / "best.onnx"))

print()
if same(ref, mine, 0.01, 0.005):
    print("MATCH: production ONNX code gives the same results as Ultralytics on the same model")
else:
    print("DIFFERENT: production code doesn't match the reference. Send this output to Claude")
