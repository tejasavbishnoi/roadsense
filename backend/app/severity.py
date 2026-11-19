"""
Road condition score.

Each detection contributes `weight(class) * confidence * size_factor`.
Potholes are the most dangerous for riders, alligator cracking means the
surface is failing structurally, single cracks are early-stage damage.
The total is squashed into 0-100 so many small cracks can't produce an
unbounded score.

Keep this file in sync with frontend/src/lib/severity.js.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

CLASS_WEIGHTS = {
    "pothole": 1.0,
    "alligator_crack": 0.7,
    "transverse_crack": 0.4,
    "longitudinal_crack": 0.35,
}
DEFAULT_WEIGHT = 0.4
SCALE = 1.5

LEVELS = [  # (upper bound, label)
    (15, "Good"),
    (40, "Fair"),
    (70, "Poor"),
    (101, "Critical"),
]


def size_factor(area_ratio: float) -> float:
    """0.5 for a tiny box, up to 2.0 for a box covering >=7.5% of the frame."""
    return 0.5 + min(max(area_ratio, 0.0) * 20.0, 1.5)


def damage_load(detections: Iterable[dict]) -> float:
    return sum(
        CLASS_WEIGHTS.get(d["label"], DEFAULT_WEIGHT) * d["confidence"] * size_factor(d["area_ratio"])
        for d in detections
    )


def score(detections: Iterable[dict]) -> int:
    return round(100 * (1 - math.exp(-damage_load(detections) / SCALE)))


def level(value: int) -> str:
    for upper, name in LEVELS:
        if value < upper:
            return name
    return LEVELS[-1][1]


def assess(detections: list[dict], min_conf: float) -> dict:
    kept = [d for d in detections if d["confidence"] >= min_conf]
    s = score(kept)
    counts: dict[str, int] = {}
    for d in kept:
        counts[d["label"]] = counts.get(d["label"], 0) + 1
    return {"score": s, "level": level(s), "counts": counts, "total": len(kept)}
