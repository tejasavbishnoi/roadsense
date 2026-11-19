import { useEffect, useState } from 'react'
import { getModelCard } from '../lib/api'
import { classInfo } from '../lib/classes'

const pct = (v) => (v == null ? 'n/a' : `${(v * 100).toFixed(1)}%`)

export default function ModelCard() {
  const [card, setCard] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    getModelCard().then(setCard).catch(() => setFailed(true))
  }, [])

  return (
    <section id="model" className="section">
      <div className="section__head">
        <h2>Model card</h2>
        <p>How well the current model does on test photos it never saw during training.</p>
      </div>

      {!card && !failed && <p className="muted">Loading evaluation results…</p>}
      {failed && <p className="empty">The API isn’t reachable right now, so the scores can’t be shown. Refresh in a minute.</p>}
      {card && !card.available && (
        <p className="empty">
          This model hasn’t been evaluated yet. Run <code>training/evaluate.py</code> and its scores will appear here.
        </p>
      )}
      {card?.available && <CardBody card={card} />}
    </section>
  )
}

function CardBody({ card }) {
  const o = card.overall
  const train = card.dataset?.splits?.train?._images
  const test = card.dataset?.splits?.test?._images
  const figures = [
    { value: pct(o.map50), label: 'mAP@50', help: 'Average precision when a box must overlap the true damage by at least half' },
    { value: pct(o.map50_95), label: 'mAP@50–95', help: 'The same, averaged over stricter overlap thresholds' },
    { value: pct(o.precision), label: 'Precision', help: 'Of the boxes it draws, how many are real damage' },
    { value: pct(o.recall), label: 'Recall', help: 'Of the real damage, how much it finds' },
  ]
  return (
    <div className="card">
      <dl className="figures">
        {figures.map((f) => (
          <div key={f.label} title={f.help}>
            <dt>{f.label}</dt>
            <dd>{f.value}</dd>
          </div>
        ))}
      </dl>

      <div className="card__grid">
        <div>
          <h3>By damage type</h3>
          <table className="table">
            <thead>
              <tr><th scope="col">Damage</th><th scope="col">AP@50</th><th scope="col">Precision</th><th scope="col">Recall</th></tr>
            </thead>
            <tbody>
              {card.per_class.map((c) => {
                const info = classInfo(c.name)
                return (
                  <tr key={c.name}>
                    <th scope="row"><i style={{ background: info.color }} />{info.name}</th>
                    <td>
                      <span className="meter"><span style={{ width: `${c.ap50 * 100}%`, background: info.color }} /></span>
                      {pct(c.ap50)}
                    </td>
                    <td>{pct(c.precision)}</td>
                    <td>{pct(c.recall)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div>
          <h3>Where it struggles</h3>
          <table className="table">
            <thead><tr><th scope="col">Condition</th><th scope="col">Recall</th><th scope="col">Instances</th></tr></thead>
            <tbody>
              {Object.entries(card.analysis?.by_lighting ?? {}).map(([k, v]) => (
                <tr key={k}><th scope="row">{k[0].toUpperCase() + k.slice(1)} photos</th><td>{pct(v.recall)}</td><td>{v.instances}</td></tr>
              ))}
              {Object.entries(card.analysis?.by_size ?? {}).map(([k, v]) => (
                <tr key={k}><th scope="row">{k[0].toUpperCase() + k.slice(1)} defects</th><td>{pct(v.recall)}</td><td>{v.instances}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="fineprint card__meta">
        {card.architecture} fine-tuned on {train ? `${train.toLocaleString()} images` : 'RDD2022'}
        {card.dataset?.countries ? ` from ${card.dataset.countries.join(', ')}` : ''}, tested on {test ? `${test.toLocaleString()} held-out images` : 'a held-out split'}.
        {card.speed_ms?.inference ? ` Inference takes about ${Math.round(card.speed_ms.inference)} ms per image on the evaluation machine.` : ''} Evaluated {card.date}.
      </p>
    </div>
  )
}
