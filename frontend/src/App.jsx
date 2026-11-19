import Analyzer from './components/Analyzer'
import Header from './components/Header'
import HowItWorks from './components/HowItWorks'
import ModelCard from './components/ModelCard'
import { CLASS_ORDER, classInfo } from './lib/classes'

export default function App() {
  return (
    <>
      <a className="skip" href="#analyze">Skip to the analyser</a>
      <Header />
      <main id="top">
        <section id="analyze" className="hero">
          <div className="hero__copy">
            <h1>Spot potholes and cracks from a single road photo.</h1>
            <p className="lede">
              Upload a photo or a dashcam clip. RoadSense marks every pothole and crack it finds and rates the road from Good to Critical.
            </p>
            <ul className="legend" aria-label="Damage types RoadSense detects">
              {CLASS_ORDER.map((k) => {
                const c = classInfo(k)
                return (
                  <li key={k} title={c.about}>
                    <i style={{ borderColor: c.color }} />
                    {c.name}
                  </li>
                )
              })}
            </ul>
          </div>
          <Analyzer />
        </section>

        <div className="lane" aria-hidden="true" />
        <HowItWorks />
        <div className="lane" aria-hidden="true" />
        <ModelCard />
      </main>
      <footer className="footer">
        <div className="footer__inner">
          <p>
            Built by <a href="https://github.com/tejasavbishnoi">Tejasav Bishnoi</a>. Source code on{' '}
            <a href="https://github.com/tejasavbishnoi/roadsense">GitHub</a>.
          </p>
          <p className="fineprint">
            Trained on RDD2022 by Arya et al., released under CC BY-SA 4.0. Results are estimates from a machine learning model and
            aren’t a substitute for an engineering survey.
          </p>
        </div>
      </footer>
    </>
  )
}
