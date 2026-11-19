# RoadSense API

FastAPI service that serves the RoadSense YOLO model.

| Endpoint | What it does |
|---|---|
| `GET /health` | Is the model loaded? Which classes? |
| `GET /model` | Model card: test metrics, per-class AP, error analysis |
| `POST /predict/image` | Upload a road photo → detections + condition score |
| `POST /predict/video` | Upload a dashcam clip (≤60 s) → per-frame timeline + worst frames |

Interactive docs at `/docs`.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The model is loaded from `weights/best.onnx` if it exists (ONNX Runtime, no PyTorch needed), otherwise `weights/best.pt` (override with `MODEL_PATH`). Production installs only `requirements-deploy.txt`.
Model card data comes from `weights/metrics.json`, written by `training/evaluate.py`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests use a fake detector, so they run without PyTorch or trained weights.

## Configuration

| Variable | Default | |
|---|---|---|
| `ALLOWED_ORIGINS` | `*` | comma-separated frontend URLs for CORS |
| `MODEL_PATH` | `weights/best.pt` | |
| `MIN_CONFIDENCE` | `0.10` | lowest confidence returned (frontend filters above this) |
| `MAX_VIDEO_SECONDS` | `60` | longer videos are truncated |
| `VIDEO_SAMPLE_FPS` | `2` | frames analysed per second of video |
