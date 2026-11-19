import { LEVEL_COLORS } from '../lib/classes'

/**
 * The road condition score drawn as an Indian highway milestone:
 * a white stone whose coloured cap shows the condition level.
 */
export default function Milestone({ score, level, caption = 'Road condition', size = 'lg' }) {
  const color = LEVEL_COLORS[level] ?? '#8A94A0'
  return (
    <figure className={`milestone milestone--${size}`} aria-label={`${caption}: ${level}, ${score} out of 100`}>
      <svg viewBox="0 0 120 150" role="img" aria-hidden="true">
        <path d="M6 146V58a54 54 0 0 1 108 0v88z" fill="#fff" stroke="#1F2328" strokeWidth="4" strokeLinejoin="round" />
        <path d="M8 58a52 52 0 0 1 104 0z" fill={color} className="milestone__cap" />
        <line x1="6" y1="58" x2="114" y2="58" stroke="#1F2328" strokeWidth="3" />
        <text x="60" y="44" textAnchor="middle" className="milestone__level">
          {level}
        </text>
        <text x="60" y="112" textAnchor="middle" className="milestone__score">
          {score}
        </text>
        <text x="60" y="134" textAnchor="middle" className="milestone__unit">
          of 100
        </text>
      </svg>
      <figcaption>{caption}</figcaption>
    </figure>
  )
}
