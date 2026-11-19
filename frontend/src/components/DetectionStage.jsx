import { classInfo } from '../lib/classes'

/** The photo with detection boxes positioned in percentages over it. */
export default function DetectionStage({ src, alt, detections, showLabels, active, onActive }) {
  return (
    <div className="stage">
      <div className="stage__frame">
        <img src={src} alt={alt} draggable="false" />
        {detections.map((d, i) => {
          const [x1, y1, x2, y2] = d.box
          const { color, name } = classInfo(d.label)
          const dim = active !== null && active !== i
          return (
            <button
              type="button"
              key={i}
              className={`box${active === i ? ' box--active' : ''}${dim ? ' box--dim' : ''}`}
              style={{
                left: `${x1 * 100}%`,
                top: `${y1 * 100}%`,
                width: `${(x2 - x1) * 100}%`,
                height: `${(y2 - y1) * 100}%`,
                '--c': color,
              }}
              onMouseEnter={() => onActive(i)}
              onMouseLeave={() => onActive(null)}
              onFocus={() => onActive(i)}
              onBlur={() => onActive(null)}
              aria-label={`${name}, ${Math.round(d.confidence * 100)}% confidence`}
            >
              {(showLabels || active === i) && (
                <span className={`box__tag${y1 < 0.06 ? ' box__tag--inside' : ''}`}>
                  {name} {Math.round(d.confidence * 100)}%
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
