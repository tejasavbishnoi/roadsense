const STEPS = [
  {
    title: 'Collect and label',
    body: 'Thousands of Indian road photos from the RDD2022 dataset, plus my own photos of Pune roads labelled box by box. Frames from the same drive are kept together when splitting, so test images are never near-copies of training images.',
  },
  {
    title: 'Train',
    body: 'A YOLO detector pretrained on everyday objects is fine-tuned to spot four kinds of damage. Every experiment, from the small baseline to the final model, is tracked in MLflow.',
  },
  {
    title: 'Evaluate honestly',
    body: 'Scored on photos the model never saw, with mAP, precision and recall for each damage type, and checked on dark photos and on small cracks, where detectors usually struggle.',
  },
  {
    title: 'Score and serve',
    body: 'A FastAPI service runs the model and turns each detection into a 0–100 condition score. Potholes and large defects count for more than hairline cracks.',
  },
]

export default function HowItWorks() {
  return (
    <section id="how" className="section">
      <div className="section__head">
        <h2>How RoadSense works</h2>
        <p>The full machine learning pipeline behind every result, from raw photos to a live API.</p>
      </div>
      <ol className="route">
        {STEPS.map((s, i) => (
          <li key={s.title} className="route__stop">
            <span className="route__km" aria-hidden="true">{i + 1}</span>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </li>
        ))}
      </ol>
      <p className="stack">
        <span>Python</span><span>PyTorch</span><span>Ultralytics YOLO</span><span>OpenCV</span><span>MLflow</span>
        <span>FastAPI</span><span>React</span><span>Docker</span><span>GitHub Actions</span>
      </p>
    </section>
  )
}
