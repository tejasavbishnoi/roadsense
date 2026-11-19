"""
Train a RoadSense detector with Ultralytics YOLO and log everything to MLflow.

Experiments are defined as presets so every run on your resume is
reproducible and comparable in the MLflow UI:

    python train.py --preset baseline      # small model, default settings
    python train.py --preset improved      # bigger model + road-specific augmentation
    python train.py --preset improved --model yolo11s.pt --name yolo11s_compare

Then:  mlflow ui --backend-store-uri ./mlruns   ->  http://127.0.0.1:5000
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

PRESETS = {
    # Plain transfer learning: the number every later run must beat.
    "baseline": dict(model="yolo26n.pt", epochs=30, imgsz=640, batch=32,
                     mosaic=1.0, mixup=0.0, degrees=0.0, hsv_v=0.4, fliplr=0.5),
    # Road-specific choices:
    #  - bigger model (cracks are thin, small objects)
    #  - stronger brightness jitter (shadows, evening light)
    #  - mild rotation (phone held at an angle) and mixup for robustness
    #  - longer training with cosine LR and early stopping
    "improved": dict(model="yolo26s.pt", epochs=80, imgsz=640, batch=16,
                     mosaic=1.0, mixup=0.1, degrees=5.0, hsv_v=0.6, fliplr=0.5,
                     cos_lr=True, patience=20, close_mosaic=10),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=PRESETS, default="baseline")
    ap.add_argument("--data", default="../datasets/roadsense/data.yaml")
    ap.add_argument("--model", help="override preset model, e.g. yolo11s.pt")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--imgsz", type=int)
    ap.add_argument("--batch", type=int)
    ap.add_argument("--name", help="run name (default: preset name)")
    ap.add_argument("--device", default=None, help="0 for GPU, cpu, or mps (Apple Silicon)")
    ap.add_argument("--export-to", default="../backend/weights",
                    help="copy best.pt here when training finishes")
    args = ap.parse_args()

    cfg = dict(PRESETS[args.preset])
    for key in ("model", "epochs", "imgsz", "batch"):
        if getattr(args, key) is not None:
            cfg[key] = getattr(args, key)
    run_name = args.name or args.preset

    # MLflow: Ultralytics has a built-in callback; we just switch it on and point it at ./mlruns
    os.environ.setdefault("MLFLOW_TRACKING_URI", f"file:{Path('mlruns').resolve()}")
    os.environ.setdefault("MLFLOW_EXPERIMENT_NAME", "roadsense")
    os.environ["MLFLOW_RUN"] = run_name
    from ultralytics import YOLO, settings

    settings.update({"mlflow": True})

    model_name = cfg.pop("model")
    print(f"Training {model_name} | preset={args.preset} | {cfg}")
    model = YOLO(model_name)
    results = model.train(
        data=args.data,
        project="runs",
        name=run_name,
        exist_ok=True,
        seed=42,
        device=args.device,
        plots=True,
        **cfg,
    )

    save_dir = Path(results.save_dir) if results is not None else Path("runs") / run_name
    best = save_dir / "weights" / "best.pt"
    summary = {
        "run": run_name,
        "preset": args.preset,
        "model": model_name,
        "config": cfg,
        "metrics": {k: float(v) for k, v in (results.results_dict if results else {}).items()},
        "weights": str(best),
    }
    (save_dir / "run_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary["metrics"], indent=2))

    if args.export_to and best.exists():
        dest = Path(args.export_to)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best, dest / "best.pt")
        print(f"Copied {best} -> {dest / 'best.pt'}")
        print("Next: python evaluate.py --weights", dest / "best.pt")


if __name__ == "__main__":
    main()
