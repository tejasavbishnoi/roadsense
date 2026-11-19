import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE_DIR / "weights" / "best.pt"))
METRICS_PATH = Path(os.getenv("METRICS_PATH", BASE_DIR / "weights" / "metrics.json"))

# Comma-separated list, e.g. "https://roadsense.vercel.app,http://localhost:5173"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

# The API always detects down to this confidence; the frontend filters above it
# so the confidence slider feels instant without re-running the model.
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.10"))
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "640"))

MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "10"))
MAX_VIDEO_MB = float(os.getenv("MAX_VIDEO_MB", "60"))
MAX_VIDEO_SECONDS = float(os.getenv("MAX_VIDEO_SECONDS", "60"))
VIDEO_SAMPLE_FPS = float(os.getenv("VIDEO_SAMPLE_FPS", "2"))
