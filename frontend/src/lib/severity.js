// Mirror of backend/app/severity.py so the confidence slider updates instantly.
export const CLASS_WEIGHTS = {
  pothole: 1.0,
  alligator_crack: 0.7,
  transverse_crack: 0.4,
  longitudinal_crack: 0.35,
}
const DEFAULT_WEIGHT = 0.4
const SCALE = 1.5

export const LEVELS = [
  { max: 15, name: 'Good', advice: 'No meaningful damage. Routine inspection is enough.' },
  { max: 40, name: 'Fair', advice: 'Early cracking. Seal cracks before the monsoon to stop water getting in.' },
  { max: 70, name: 'Poor', advice: 'Visible damage that affects riders. Schedule a repair.' },
  { max: 101, name: 'Critical', advice: 'Dangerous for two-wheelers. Repair urgently and mark the hazard.' },
]

const sizeFactor = (area) => 0.5 + Math.min(Math.max(area, 0) * 20, 1.5)

export function score(detections) {
  const load = detections.reduce(
    (sum, d) => sum + (CLASS_WEIGHTS[d.label] ?? DEFAULT_WEIGHT) * d.confidence * sizeFactor(d.area_ratio),
    0,
  )
  return Math.round(100 * (1 - Math.exp(-load / SCALE)))
}

export const levelFor = (value) => LEVELS.find((l) => value < l.max) ?? LEVELS[LEVELS.length - 1]

export function assess(detections, minConf) {
  const kept = detections.filter((d) => d.confidence >= minConf)
  const s = score(kept)
  const counts = {}
  for (const d of kept) counts[d.label] = (counts[d.label] || 0) + 1
  return { score: s, level: levelFor(s), counts, total: kept.length, kept }
}
