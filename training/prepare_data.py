"""
Prepare the RoadSense dataset.

1. Downloads RDD2022 country subsets (default: India) from the official
   CRDDC'2022 S3 bucket.
2. Converts Pascal VOC XML annotations to YOLO format, keeping the 4 main
   damage classes (D00, D10, D20, D40) and dropping everything else.
3. Splits into train / val / test using *block* splitting: RDD images are
   consecutive dashcam frames, so a random split would put near-identical
   frames in train and test and inflate the scores. We group every
   BLOCK_SIZE consecutive frames and split by group instead.
4. Optionally merges your own labelled data (a Roboflow "YOLOv8" export)
   and keeps a separate `pune_test` split to measure real-world transfer.
5. Writes data.yaml + dataset_stats.json.

Usage:
    python prepare_data.py --countries India --out ../datasets/roadsense
    python prepare_data.py --countries India Czech --extra ./pune_roboflow_export
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

BASE_URL = (
    "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/"
    "Country_Specific_Data_CRDDC2022/RDD2022_{country}.zip"
)
# Official mirror: the full RDD2022 release on Figshare (article 21431547, ~13 GB)
FIGSHARE_FULL_URL = "https://ndownloader.figshare.com/files/38030910"

# RDD code -> (class id, name). Order matters: it defines the model's class ids.
CLASS_MAP = {
    "D00": (0, "longitudinal_crack"),
    "D10": (1, "transverse_crack"),
    "D20": (2, "alligator_crack"),
    "D40": (3, "pothole"),
}
CLASS_NAMES = [name for _, name in sorted(CLASS_MAP.values())]
BLOCK_SIZE = 50
SPLITS = {"train": 0.8, "val": 0.1, "test": 0.1}


def _fetch(url: str, dest: Path) -> None:
    """Download with a progress line. Writes to a .part file so a failed download never looks complete."""
    print(f"[download] {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (RoadSense dataset prep)"})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done, last = 0, -1
        while chunk := resp.read(1 << 22):  # 4 MB
            out.write(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else -1
            if pct != last:
                last = pct
                size = f"{done / 1e9:.2f} GB" + (f" / {total / 1e9:.2f} GB" if total else "")
                print(f"\r  {pct:3d}%  {size}" if total else f"\r  {size}", end="", flush=True)
    print()
    tmp.rename(dest)


def _extract_nested(extract_dir: Path) -> None:
    # Country zips sometimes contain another zip inside.
    for inner in list(extract_dir.rglob("*.zip")):
        with zipfile.ZipFile(inner) as zf:
            zf.extractall(inner.parent)


def download(country: str, cache: Path) -> Path:
    """Get one RDD2022 country subset. Tries the per-country zip on the official
    S3 bucket first; if that's refused, falls back to the full dataset on
    Figshare (13 GB) and extracts only this country from it."""
    cache.mkdir(parents=True, exist_ok=True)
    extract_dir = cache / f"RDD2022_{country}"
    if extract_dir.exists() and any(extract_dir.rglob("*.xml")):
        print(f"[skip] {country} already extracted")
        return extract_dir

    zip_path = cache / f"RDD2022_{country}.zip"
    if not zip_path.exists():
        try:
            _fetch(BASE_URL.format(country=country), zip_path)
        except Exception as exc:  # noqa: BLE001 - any network failure -> mirror
            print(f"[warn] official download failed ({exc}); using the Figshare mirror instead")

    if zip_path.exists():
        print(f"[extract] {zip_path.name}")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
    else:
        full = cache / "RDD2022_full.zip"
        if not full.exists():
            _fetch(FIGSHARE_FULL_URL, full)
        print(f"[extract] {country} from {full.name} (only this country's files)")
        with zipfile.ZipFile(full) as zf:
            members = [m for m in zf.namelist()
                       if country.lower() in [p.lower() for p in Path(m).parts]
                       or Path(m).name.lower() == f"rdd2022_{country.lower()}.zip"]
            if not members:
                raise SystemExit(f"Could not find '{country}' inside {full.name}")
            zf.extractall(extract_dir, members=members)
    _extract_nested(extract_dir)

    if not any(extract_dir.rglob("*.xml")):
        raise SystemExit(f"No annotations found for {country} in {extract_dir}")
    return extract_dir


def parse_voc(xml_path: Path) -> tuple[int, int, list[tuple[int, float, float, float, float]]]:
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    w = float(size.findtext("width"))
    h = float(size.findtext("height"))
    boxes = []
    for obj in root.iter("object"):
        code = (obj.findtext("name") or "").strip()
        if code not in CLASS_MAP:
            continue
        bb = obj.find("bndbox")
        x1, y1 = float(bb.findtext("xmin")), float(bb.findtext("ymin"))
        x2, y2 = float(bb.findtext("xmax")), float(bb.findtext("ymax"))
        x1, x2 = max(0.0, min(x1, x2)), min(w, max(x1, x2))
        y1, y2 = max(0.0, min(y1, y2)), min(h, max(y1, y2))
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue  # degenerate box
        cls_id = CLASS_MAP[code][0]
        boxes.append((cls_id, (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h))
    return int(w), int(h), boxes


def collect_rdd(extract_dir: Path, country: str) -> list[dict]:
    items = []
    for xml_path in sorted(extract_dir.rglob("*.xml")):
        if "train" not in [p.lower() for p in xml_path.parts]:
            continue  # the official test split has no labels
        img_dir = xml_path.parent.parent.parent / "images"
        img = img_dir / f"{xml_path.stem}.jpg"
        if not img.exists():
            continue
        _, _, boxes = parse_voc(xml_path)
        items.append({"image": img, "boxes": boxes, "source": country})
    print(f"[rdd] {country}: {len(items)} labelled images")
    return items


def block_split(items: list[dict], seed: int) -> dict[str, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for i, item in enumerate(items):
        groups[(item["source"], i // BLOCK_SIZE)].append(item)
    keys = list(groups)
    random.Random(seed).shuffle(keys)
    n = len(keys)
    n_train = int(n * SPLITS["train"])
    n_val = int(n * SPLITS["val"])
    parts = {
        "train": keys[:n_train],
        "val": keys[n_train : n_train + n_val],
        "test": keys[n_train + n_val :],
    }
    return {split: [it for k in ks for it in groups[k]] for split, ks in parts.items()}


def collect_extra(extra_dir: Path) -> dict[str, list[dict]]:
    """Read a Roboflow YOLO export (train/valid/test folders). Class names in its
    data.yaml must match CLASS_NAMES (or RDD codes) - we remap by name."""
    import yaml  # ultralytics already depends on PyYAML

    meta = yaml.safe_load((extra_dir / "data.yaml").read_text())
    names = meta["names"]
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    lookup = {n: i for i, n in enumerate(CLASS_NAMES)}
    lookup.update({code: cid for code, (cid, _) in CLASS_MAP.items()})
    remap = {i: lookup.get(str(n).strip().lower().replace(" ", "_"), lookup.get(str(n))) for i, n in enumerate(names)}
    unknown = [names[i] for i, v in remap.items() if v is None]
    if unknown:
        print(f"[extra] ignoring unknown classes: {unknown}")

    out: dict[str, list[dict]] = {"train": [], "val": [], "pune_test": []}
    folder_to_split = {"train": "train", "valid": "val", "val": "val", "test": "pune_test"}
    for folder, split in folder_to_split.items():
        img_dir = extra_dir / folder / "images"
        if not img_dir.exists():
            continue
        for img in sorted(img_dir.iterdir()):
            if img.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            label = extra_dir / folder / "labels" / f"{img.stem}.txt"
            boxes = []
            if label.exists():
                for line in label.read_text().splitlines():
                    parts = line.split()
                    if len(parts) != 5:
                        continue
                    cid = remap.get(int(parts[0]))
                    if cid is not None:
                        boxes.append((cid, *map(float, parts[1:])))
            out[split].append({"image": img, "boxes": boxes, "source": "pune"})
    print(f"[extra] " + ", ".join(f"{k}={len(v)}" for k, v in out.items()))
    return out


def write_split(items: list[dict], out: Path, split: str) -> Counter:
    img_dir, lbl_dir = out / split / "images", out / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    for item in items:
        name = f"{item['source']}_{item['image'].stem}"
        shutil.copy2(item["image"], img_dir / f"{name}{item['image'].suffix.lower()}")
        lines = [f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}" for c, x, y, w, h in item["boxes"]]
        (lbl_dir / f"{name}.txt").write_text("\n".join(lines))
        counts.update(CLASS_NAMES[c] for c, *_ in item["boxes"])
    counts["_images"] = len(items)
    counts["_background_images"] = sum(1 for it in items if not it["boxes"])
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--countries", nargs="+", default=["India"],
                    help="RDD2022 subsets: India Japan Czech United_States China_MotorBike Norway")
    ap.add_argument("--out", type=Path, default=Path("../datasets/roadsense"))
    ap.add_argument("--cache", type=Path, default=Path("../datasets/_downloads"))
    ap.add_argument("--extra", type=Path, default=None, help="Roboflow YOLO export of your own photos")
    ap.add_argument("--max-background-ratio", type=float, default=0.15,
                    help="Keep at most this fraction of images with no damage (they teach 'clean road').")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    items: list[dict] = []
    for country in args.countries:
        items += collect_rdd(download(country, args.cache), country)

    # Limit pure-background images so the model isn't dominated by empty roads.
    rng = random.Random(args.seed)
    damaged = [it for it in items if it["boxes"]]
    background = [it for it in items if not it["boxes"]]
    keep_bg = int(len(damaged) * args.max_background_ratio)
    rng.shuffle(background)
    items = sorted(damaged + background[:keep_bg], key=lambda it: (it["source"], it["image"].name))
    print(f"[filter] {len(damaged)} damaged + {min(keep_bg, len(background))} background images")

    splits = block_split(items, args.seed)
    if args.extra:
        extra = collect_extra(args.extra)
        splits["train"] += extra["train"]
        splits["val"] += extra["val"]
        if extra["pune_test"]:
            splits["pune_test"] = extra["pune_test"]

    if args.out.exists():
        shutil.rmtree(args.out)
    stats = {split: dict(write_split(its, args.out, split)) for split, its in splits.items()}

    data_yaml = [
        f"path: {args.out.resolve()}",
        "train: train/images",
        "val: val/images",
        "test: test/images",
        "names:",
        *[f"  {i}: {n}" for i, n in enumerate(CLASS_NAMES)],
    ]
    (args.out / "data.yaml").write_text("\n".join(data_yaml) + "\n")
    if "pune_test" in splits:
        pune_yaml = [l if not l.startswith("test:") else "test: pune_test/images" for l in data_yaml]
        (args.out / "data_pune.yaml").write_text("\n".join(pune_yaml) + "\n")
    (args.out / "dataset_stats.json").write_text(json.dumps(
        {"countries": args.countries, "classes": CLASS_NAMES, "splits": stats}, indent=2))

    print("\nDataset ready:")
    for split, s in stats.items():
        per_class = ", ".join(f"{n}={s.get(n, 0)}" for n in CLASS_NAMES)
        print(f"  {split:10s} images={s['_images']:5d} | {per_class}")
    print(f"\n-> {args.out / 'data.yaml'}")


if __name__ == "__main__":
    main()
