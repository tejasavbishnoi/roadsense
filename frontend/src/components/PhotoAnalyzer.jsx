import { useEffect, useMemo, useRef, useState } from 'react'
import { analyzeImage } from '../lib/api'
import { classInfo } from '../lib/classes'
import { downloadAnnotated, downloadReport } from '../lib/exporters'
import { assess } from '../lib/severity'
import ClassBreakdown from './ClassBreakdown'
import DetectionStage from './DetectionStage'
import Dropzone from './Dropzone'
import { DownloadIcon, FileIcon, ResetIcon } from './Icons'
import Milestone from './Milestone'
import Progress from './Progress'

export default function PhotoAnalyzer() {
  const [file, setFile] = useState(null)
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(null)
  const [conf, setConf] = useState(0.25)
  // On phones the labels crowd the photo, so start with them off (tap a box to see it)
  const [showLabels, setShowLabels] = useState(() => typeof window === 'undefined' || window.innerWidth > 640)
  const [active, setActive] = useState(null)
  const job = useRef(null)

  useEffect(() => () => url && URL.revokeObjectURL(url), [url])

  const run = async (f) => {
    setFile(f)
    setUrl(URL.createObjectURL(f))
    setResult(null)
    setError('')
    setActive(null)
    setProgress({ phase: 'uploading', percent: 0 })
    job.current = analyzeImage(f, setProgress)
    try {
      setResult(await job.current.promise)
    } catch (e) {
      if (!e.cancelled) setError(e.message)
      else reset()
    } finally {
      setProgress(null)
    }
  }

  const reset = () => {
    job.current?.cancel()
    setFile(null)
    setUrl('')
    setResult(null)
    setError('')
    setProgress(null)
  }

  const summary = useMemo(() => (result ? assess(result.detections, conf) : null), [result, conf])

  if (!file) {
    return (
      <Dropzone
        accept="image/jpeg,image/png,image/webp"
        maxMb={10}
        title="Drop a road photo here"
        hint="JPG, PNG or WebP, up to 10 MB. Photos taken from a car or bike at road level work best."
        onFile={run}
      />
    )
  }

  return (
    <div className="workspace">
      <div className="workspace__main">
        {summary ? (
          <DetectionStage
            src={url}
            alt={`Road photo ${file.name} with detected damage`}
            detections={summary.kept}
            showLabels={showLabels}
            active={active}
            onActive={setActive}
          />
        ) : (
          <div className="stage stage--waiting">
            <div className="stage__frame">
              <img src={url} alt="Uploaded road photo" />
            </div>
            {progress && <Progress progress={progress} processingText="Looking for potholes and cracks…" onCancel={reset} />}
          </div>
        )}
        <div className="workspace__bar">
          <span className="filename" title={file.name}>
            {file.name}
          </span>
          {result && <span className="muted">{result.width}×{result.height} px, analysed in {Math.round(result.inference_ms)} ms</span>}
          <button type="button" className="btn btn--ghost" onClick={reset}>
            <ResetIcon /> Analyse another photo
          </button>
        </div>
      </div>

      <aside className="panel" aria-label="Results">
        {error && (
          <div className="alert" role="alert">
            <p>{error}</p>
            <button type="button" className="btn" onClick={() => run(file)}>
              Try again
            </button>
          </div>
        )}
        {!summary && !error && <PanelSkeleton />}
        {summary && (
          <>
            <div className="verdict">
              <Milestone score={summary.score} level={summary.level.name} />
              <div>
                <p className="verdict__count">
                  {summary.total === 0
                    ? 'No damage found'
                    : `${summary.total} ${summary.total === 1 ? 'defect' : 'defects'} found`}
                </p>
                <p className="verdict__advice">{summary.level.advice}</p>
              </div>
            </div>

            <ClassBreakdown counts={summary.counts} />

            <div className="controls">
              <label className="slider">
                <span>
                  Minimum confidence <strong>{Math.round(conf * 100)}%</strong>
                </span>
                <input
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                  value={conf}
                  onChange={(e) => setConf(Number(e.target.value))}
                />
                <span className="fineprint">Lower finds more damage but adds false alarms.</span>
              </label>
              <label className="toggle">
                <input type="checkbox" checked={showLabels} onChange={(e) => setShowLabels(e.target.checked)} />
                <span>Show labels on the photo</span>
              </label>
            </div>

            {summary.kept.length > 0 && (
              <ol className="detlist" aria-label="Detections">
                {summary.kept.map((d, i) => {
                  const { name, color } = classInfo(d.label)
                  return (
                    <li
                      key={i}
                      className={active === i ? 'is-active' : ''}
                      onMouseEnter={() => setActive(i)}
                      onMouseLeave={() => setActive(null)}
                    >
                      <i style={{ background: color }} />
                      <span>{name}</span>
                      <span className="muted" title="Share of the photo this defect covers">{(d.area_ratio * 100).toFixed(1)}%</span>
                      <strong>{Math.round(d.confidence * 100)}%</strong>
                    </li>
                  )
                })}
              </ol>
            )}

            <div className="actions">
              <button type="button" className="btn btn--primary" onClick={() => downloadAnnotated(url, summary.kept, file.name)}>
                <DownloadIcon /> Download marked photo
              </button>
              <button type="button" className="btn" onClick={() => downloadReport(result, summary, conf, file.name)}>
                <FileIcon /> Export report
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  )
}

function PanelSkeleton() {
  return (
    <div className="skeleton" aria-hidden="true">
      <div className="skeleton__stone" />
      <div className="skeleton__line" />
      <div className="skeleton__line skeleton__line--short" />
      <div className="skeleton__line" />
    </div>
  )
}
