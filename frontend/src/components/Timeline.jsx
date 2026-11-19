import { useState } from 'react'
import { LEVEL_COLORS } from '../lib/classes'

const W = 720
const H = 180
const PAD = { l: 34, r: 12, t: 12, b: 26 }
const BANDS = [
  { from: 0, to: 15, level: 'Good' },
  { from: 15, to: 40, level: 'Fair' },
  { from: 40, to: 70, level: 'Poor' },
  { from: 70, to: 100, level: 'Critical' },
]

/** Condition score along the length of the video. Click to jump the video there. */
export default function Timeline({ points, duration, current, onSeek }) {
  const [hover, setHover] = useState(null)
  const end = Math.max(duration || 0, points[points.length - 1]?.t || 1)
  const x = (t) => PAD.l + (t / end) * (W - PAD.l - PAD.r)
  const y = (s) => PAD.t + (1 - s / 100) * (H - PAD.t - PAD.b)
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.score).toFixed(1)}`).join(' ')
  const area = `${line} L${x(points[points.length - 1].t)},${y(0)} L${x(points[0].t)},${y(0)} Z`
  const tickStep = [1, 2, 5, 10, 15, 30].find((s) => end / s <= 8) ?? 60
  const ticks = Array.from({ length: Math.floor(end / tickStep) + 1 }, (_, i) => i * tickStep)

  const pick = (e) => {
    const box = e.currentTarget.getBoundingClientRect()
    const t = ((e.clientX - box.left) / box.width * W - PAD.l) / (W - PAD.l - PAD.r) * end
    let best = points[0]
    for (const p of points) if (Math.abs(p.t - t) < Math.abs(best.t - t)) best = p
    return best
  }

  return (
    <div className="timeline">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Road condition score over the video"
        onMouseMove={(e) => setHover(pick(e))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => onSeek(pick(e).t)}
      >
        {BANDS.map((b) => (
          <g key={b.level}>
            <rect x={PAD.l} y={y(b.to)} width={W - PAD.l - PAD.r} height={y(b.from) - y(b.to)} fill={LEVEL_COLORS[b.level]} opacity="0.07" />
            <text x={PAD.l - 6} y={y(b.from) - 3} textAnchor="end" className="timeline__axis">{b.from}</text>
          </g>
        ))}
        {ticks.map((t) => (
          <text key={t} x={x(t)} y={H - 8} textAnchor="middle" className="timeline__axis">
            {Math.round(t)}s
          </text>
        ))}
        <path d={area} fill="#F5B800" opacity="0.18" />
        <path d={line} fill="none" stroke="#1F2328" strokeWidth="2" strokeLinejoin="round" />
        {points.map((p) => (
          <circle key={p.t} cx={x(p.t)} cy={y(p.score)} r={p.score >= 40 ? 3.5 : 2} fill={p.score >= 40 ? LEVEL_COLORS[p.level] : '#1F2328'} />
        ))}
        {current != null && <line x1={x(current)} x2={x(current)} y1={PAD.t} y2={H - PAD.b} stroke="#1F2328" strokeDasharray="4 4" />}
        {hover && (
          <g>
            <line x1={x(hover.t)} x2={x(hover.t)} y1={PAD.t} y2={H - PAD.b} stroke="#5B636E" />
            <circle cx={x(hover.t)} cy={y(hover.score)} r="5" fill="#fff" stroke="#1F2328" strokeWidth="2" />
          </g>
        )}
      </svg>
      <p className="fineprint timeline__readout" aria-live="polite">
        {hover
          ? `${hover.t.toFixed(1)}s: ${hover.level}, score ${hover.score}, ${hover.total} ${hover.total === 1 ? 'defect' : 'defects'}. Click to jump there.`
          : 'Hover the chart to inspect a moment. Click to jump the video there.'}
      </p>
    </div>
  )
}
