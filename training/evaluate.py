"""
Evaluate a trained RoadSense model honestly.

Produces:
  * standard detection metrics on the held-out test split
    (mAP@50, mAP@50-95, precision, recall - overall and per class)
  * error analysis that goes beyond one number:
      - recall by lighting (dark / normal / bright images)
      - recall by object size (small / medium / large boxes)
      - a gallery of the worst images (ground truth in green, predictions in red)
  * backend/weights/metrics.json  -> shown on the website's "Model card"
  * results/report.md             -> paste the tables into the README

Usage:
    python evaluate.py --weights ../backend/weights/best.pt
    python evaluate.py --weights ../backend/weights/best.pt --data ../datasets/roadsense/data_pune.yaml --tag pune
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import cv2
import numpy as np
import yaml

IOU_MATCH = 0.5
SIZE_BUCKETS = {"small": (0, 32**2), "medium": (32**2, 96**2), "large": (96**2, float("inf"))}


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """IoU between boxes a (N,4) and b (M,4) in xyxy -> (N,M)."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-9)


def load_gt(label_path: Path, w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    boxes, classes = [], []
    if label_path.exists():
        for line in label_path.read_text().splitlines():
            p = line.split()
            if len(p) != 5:
                continue
            c, x, y, bw, bh = int(p[0]), *map(float, p[1:])
            boxes.append([(x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h])
            classes.append(c)
    return np.array(boxes, dtype=float).reshape(-1, 4), np.array(classes, dtype=int)


def match(gt_b, gt_c, pr_b, pr_c) -> tuple[np.ndarray, np.ndarray]:
    """Greedy same-class matching. Returns (gt_matched mask, pred_matched mask)."""
    gt_hit = np.zeros(len(gt_b), bool)
    pr_hit = np.zeros(len(pr_b), bool)
    ious = iou(pr_b, gt_b)
    for pi in range(len(pr_b)):  # preds are sorted by confidence already
        if len(gt_b) == 0:
            break
        cand = np.where((gt_c == pr_c[pi]) & ~gt_hit)[0]
        if len(cand) == 0:
            continue
        best = cand[np.argmax(ious[pi, cand])]
        if ious[pi, best] >= IOU_MATCH:
            gt_hit[best] = True
            pr_hit[pi] = True
    return gt_hit, pr_hit


def draw(img, gt_b, gt_c, pr_b, pr_c, pr_s, names):
    out = img.copy()
    for (x1, y1, x2, y2), c in zip(gt_b.astype(int), gt_c):
        cv2.rectangle(out, (x1, y1), (x2, y2), (60, 200, 60), 2)
        cv2.putText(out, f"GT {names[c]}", (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 200, 60), 1)
    for (x1, y1, x2, y2), c, s in zip(pr_b.astype(int), pr_c, pr_s):
        cv2.rectangle(out, (x1, y1), (x2, y2), (40, 40, 230), 2)
        cv2.putText(out, f"{names[c]} {s:.2f}", (x1, y2 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 230), 1)
    return out


def architecture(model) -> str:
    """Base model the weights were fine-tuned from, e.g. 'yolo26s'."""
    ckpt = getattr(model, "ckpt", None) or {}
    base = (ckpt.get("train_args") or {}).get("model") if isinstance(ckpt, dict) else None
    return Path(str(base)).stem if base else "YOLO"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", default="../backend/weights/best.pt")
    ap.add_argument("--data", default="../datasets/roadsense/data.yaml")
    ap.add_argument("--conf", type=float, default=0.25, help="confidence used for error analysis")
    ap.add_argument("--tag", default="test", help="name for this evaluation (e.g. test, pune)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--card", default="../backend/weights/metrics.json",
                    help="model card JSON served by the API ('' to skip)")
    ap.add_argument("--worst", type=int, default=12)
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.weights)
    names = model.names if isinstance(model.names, list) else [model.names[i] for i in sorted(model.names)]
    data_cfg = yaml.safe_load(Path(args.data).read_text())
    root = Path(data_cfg["path"])
    test_images = root / data_cfg["test"]

    # ---- 1. Standard metrics -------------------------------------------------
    m = model.val(data=args.data, split="test", plots=True, project=args.out, name=f"val_{args.tag}", exist_ok=True)
    box = m.box
    per_class = []
    for i, cls_idx in enumerate(box.ap_class_index):
        per_class.append({
            "name": names[int(cls_idx)],
            "precision": round(float(box.p[i]), 4),
            "recall": round(float(box.r[i]), 4),
            "ap50": round(float(box.ap50[i]), 4),
            "ap50_95": round(float(box.ap[i]), 4),
        })
    overall = {
        "map50": round(float(box.map50), 4),
        "map50_95": round(float(box.map), 4),
        "precision": round(float(box.mp), 4),
        "recall": round(float(box.mr), 4),
    }

    # ---- 2. Error analysis ---------------------------------------------------
    img_paths = sorted(p for p in test_images.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    records = []
    size_tot = {k: [0, 0] for k in SIZE_BUCKETS}  # [hits, total]
    for res in model.predict([str(p) for p in img_paths], conf=args.conf, stream=True, verbose=False):
        path = Path(res.path)
        img = res.orig_img
        h, w = img.shape[:2]
        gt_b, gt_c = load_gt(root / data_cfg["test"].replace("images", "labels") / f"{path.stem}.txt", w, h)
        pr_b = res.boxes.xyxy.cpu().numpy()
        pr_c = res.boxes.cls.cpu().numpy().astype(int)
        pr_s = res.boxes.conf.cpu().numpy()
        gt_hit, pr_hit = match(gt_b, gt_c, pr_b, pr_c)
        brightness = float(cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 2].mean())
        for b, hit in zip(gt_b, gt_hit):
            area = (b[2] - b[0]) * (b[3] - b[1])
            for k, (lo, hi) in SIZE_BUCKETS.items():
                if lo <= area < hi:
                    size_tot[k][0] += int(hit)
                    size_tot[k][1] += 1
        records.append({
            "path": path, "brightness": brightness,
            "gt": len(gt_b), "tp": int(gt_hit.sum()), "fp": int((~pr_hit).sum()),
            "fn": int((~gt_hit).sum()), "draw": (gt_b, gt_c, pr_b, pr_c, pr_s),
        })

    # lighting buckets by tertile so each bucket has the same number of images
    lights = np.array([r["brightness"] for r in records])
    t1, t2 = np.percentile(lights, [33.3, 66.6]) if len(lights) else (0, 0)
    light_tot = {"dark": [0, 0], "normal": [0, 0], "bright": [0, 0]}
    for r in records:
        k = "dark" if r["brightness"] < t1 else "normal" if r["brightness"] < t2 else "bright"
        light_tot[k][0] += r["tp"]
        light_tot[k][1] += r["gt"]

    def rate(d):
        return {k: {"recall": round(h / t, 4) if t else None, "instances": t} for k, (h, t) in d.items()}

    analysis = {"by_lighting": rate(light_tot), "by_size": rate(size_tot)}

    out = Path(args.out) / args.tag
    gallery = out / "worst_images"
    gallery.mkdir(parents=True, exist_ok=True)
    worst = sorted(records, key=lambda r: (r["fn"] + r["fp"]), reverse=True)[: args.worst]
    for i, r in enumerate(worst):
        img = cv2.imread(str(r["path"]))
        cv2.imwrite(str(gallery / f"{i:02d}_{r['path'].stem}.jpg"), draw(img, *r["draw"], names))

    # ---- 3. Write report + model card ----------------------------------------
    stats_file = root / "dataset_stats.json"
    dataset = json.loads(stats_file.read_text()) if stats_file.exists() else {}
    card = {
        "model": Path(args.weights).name,
        "architecture": architecture(model),
        "evaluated_on": args.tag,
        "date": date.today().isoformat(),
        "classes": names,
        "overall": overall,
        "per_class": per_class,
        "analysis": analysis,
        "speed_ms": {k: round(float(v), 2) for k, v in m.speed.items()},
        "dataset": dataset,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(card, indent=2))
    if args.card and args.tag == "test":
        Path(args.card).parent.mkdir(parents=True, exist_ok=True)
        Path(args.card).write_text(json.dumps(card, indent=2))

    lines = [
        f"## RoadSense evaluation ({args.tag})",
        "",
        "| Metric | Value |", "|---|---|",
        *[f"| {k} | {v:.3f} |" for k, v in overall.items()],
        "",
        "| Class | Precision | Recall | AP@50 | AP@50-95 |", "|---|---|---|---|---|",
        *[f"| {c['name']} | {c['precision']:.3f} | {c['recall']:.3f} | {c['ap50']:.3f} | {c['ap50_95']:.3f} |" for c in per_class],
        "",
        f"Error analysis at conf={args.conf}, IoU={IOU_MATCH}",
        "",
        "| Slice | Recall | Instances |", "|---|---|---|",
        *[f"| lighting: {k} | {v['recall']} | {v['instances']} |" for k, v in analysis["by_lighting"].items()],
        *[f"| size: {k} | {v['recall']} | {v['instances']} |" for k, v in analysis["by_size"].items()],
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWorst images -> {gallery}")


if __name__ == "__main__":
    main()
