import { CLASS_ORDER, classInfo } from '../lib/classes'

export default function ClassBreakdown({ counts, note }) {
  const max = Math.max(1, ...Object.values(counts))
  return (
    <div className="breakdown">
      <ul>
        {CLASS_ORDER.map((key) => {
          const { name, color } = classInfo(key)
          const n = counts[key] || 0
          return (
            <li key={key} className={n === 0 ? 'is-zero' : ''}>
              <span className="breakdown__name">
                <i style={{ background: color }} />
                {name}
              </span>
              <span className="breakdown__bar" aria-hidden="true">
                <span style={{ width: `${(n / max) * 100}%`, background: color }} />
              </span>
              <span className="breakdown__n">{n}</span>
            </li>
          )
        })}
      </ul>
      {note && <p className="fineprint">{note}</p>}
    </div>
  )
}
