import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = BASE_DIR / "weights"


def resolve_model_path() -> Path:
    """MODEL_PATH if set; otherwise prefer the lightweight ONNX export, then the PyTorch file."""
    if os.getenv("MODEL_PATH"):
        return Path(os.environ["MODEL_PATH"])
    onnx = WEIGHTS_DIR / "best.onnx"
    return onnx if onnx.exists() else WEIGHTS_DIR / "best.pt"


METRICS_PATH = Path(os.getenv("METRICS_PATH", WEIGHTS_DIR / "metrics.json"))

# Comma-separated list, e.g. "https://roadsense.vercel.app,http://localhost:5173"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

# The API always detects down to this confidence; the frontend filters above it
# so the confidence slider feels instant without re-running the model.
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.10"))
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "640"))
ONNX_THREADS = int(os.getenv("ONNX_THREADS", "2"))

MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "10"))
MAX_VIDEO_MB = float(os.getenv("MAX_VIDEO_MB", "60"))
MAX_VIDEO_SECONDS = float(os.getenv("MAX_VIDEO_SECONDS", "60"))
VIDEO_SAMPLE_FPS = float(os.getenv("VIDEO_SAMPLE_FPS", "2"))
