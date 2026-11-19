"""API tests with a fake detector, so CI doesn't need PyTorch or trained weights."""

import io

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, get_detector


class FakeDetector:
    ready = True
    error = None
    names = ["longitudinal_crack", "transverse_crack", "alligator_crack", "pothole"]

    def predict(self, images):
        return [[
            {"label": "pothole", "confidence": 0.91, "box": [0.1, 0.5, 0.3, 0.7], "area_ratio": 0.04},
            {"label": "transverse_crack", "confidence": 0.15, "box": [0.5, 0.5, 0.9, 0.55], "area_ratio": 0.02},
        ] for _ in images]


class NotReadyDetector:
    ready = False
    error = "No model weights"
    names = []


@pytest.fixture
def client():
    app.dependency_overrides[get_detector] = lambda: FakeDetector()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def png_bytes(w=320, h=240):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (90, 90, 90)).save(buf, format="PNG")
    return buf.getvalue()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["model_loaded"] is True


def test_model_card(client):
    r = client.get("/model")
    assert r.status_code == 200
    assert "severity_weights" in r.json()


def test_predict_image(client):
    r = client.post("/predict/image?conf=0.25", files={"file": ("road.png", png_bytes(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["width"] == 320 and body["height"] == 240
    assert len(body["detections"]) == 2
    # low-confidence crack is returned but not counted in the summary
    assert body["summary"]["counts"] == {"pothole": 1}
    assert body["summary"]["score"] > 0


def test_rejects_non_image(client):
    r = client.post("/predict/image", files={"file": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 415


def test_model_not_ready():
    app.dependency_overrides[get_detector] = lambda: NotReadyDetector()
    with TestClient(app) as c:
        r = c.post("/predict/image", files={"file": ("road.png", png_bytes(), "image/png")})
    app.dependency_overrides.clear()
    assert r.status_code == 503


def test_predict_video(client, tmp_path):
    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (160, 120))
    for i in range(30):  # 3 seconds
        writer.write(np.full((120, 160, 3), i * 5, np.uint8))
    writer.release()
    r = client.post("/predict/video?sample_fps=2", files={"file": ("clip.avi", path.read_bytes(), "video/x-msvideo")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["frames_analyzed"] == 6
    assert body["summary"]["peak_score"] > 0
    assert body["worst_frames"][0]["image"].startswith("data:image/jpeg;base64,")
