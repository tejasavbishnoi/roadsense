"""ONNX post-processing: letterbox maths and both output formats."""

import numpy as np

from app.detector import decode, letterbox, to_detections


def to_letterbox(box, r, pad):
    x1, y1, x2, y2 = (v * r for v in box)
    return x1 + pad[0], y1 + pad[1], x2 + pad[0], y2 + pad[1]


def test_letterbox_shape_and_padding():
    out, r, pad = letterbox(np.zeros((375, 533, 3), np.uint8), 640)
    assert out.shape == (640, 640, 3)
    assert pad[0] == 0 and pad[1] > 0
    assert abs(r - 640 / 533) < 1e-6


def test_end_to_end_output_maps_back_to_original_pixels():
    _, r, pad = letterbox(np.zeros((375, 533, 3), np.uint8), 640)
    out = np.zeros((1, 300, 6), np.float32)
    out[0, 0] = [*to_letterbox((100, 50, 200, 150), r, pad), 0.9, 3]
    out[0, 1] = [0, 0, 10, 10, 0.05, 1]  # below threshold
    dets = decode(out, 0.1, r, pad, 533, 375)
    assert len(dets) == 1
    x1, y1, x2, y2, score, cls = dets[0]
    assert cls == 3 and abs(score - 0.9) < 1e-6
    assert max(abs(a - b) for a, b in zip((x1, y1, x2, y2), (100, 50, 200, 150))) < 0.5


def test_classic_output_applies_nms():
    _, r, pad = letterbox(np.zeros((480, 640, 3), np.uint8), 640)
    x1, y1, x2, y2 = to_letterbox((100, 100, 200, 200), r, pad)
    out = np.zeros((1, 8, 8400), np.float32)
    for i, (dx, s) in enumerate([(0, 0.8), (3, 0.7), (300, 0.6)]):  # two overlapping + one separate
        out[0, :4, i] = [(x1 + x2) / 2 + dx, (y1 + y2) / 2, x2 - x1, y2 - y1]
        out[0, 4 + 3, i] = s
    dets = decode(out, 0.1, r, pad, 640, 480)
    assert len(dets) == 2


def test_to_detections_normalises():
    d = to_detections([(64, 48, 128, 96, 0.5, 3)], ["a", "b", "c", "pothole"], 640, 480)[0]
    assert d["label"] == "pothole"
    assert d["box"] == [0.1, 0.1, 0.2, 0.2]
    assert abs(d["area_ratio"] - 0.01) < 1e-9
