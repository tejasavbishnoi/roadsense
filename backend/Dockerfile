# RoadSense API - works locally and on Hugging Face Spaces (Docker SDK)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces run as uid 1000
RUN useradd -m -u 1000 app
WORKDIR /home/app/api

# CPU-only PyTorch keeps the image ~1.5 GB smaller than the default CUDA build
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY --chown=app requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app app ./app
COPY --chown=app weights ./weights

USER app
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health')"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
