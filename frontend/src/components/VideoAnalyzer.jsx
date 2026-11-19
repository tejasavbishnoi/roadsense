import { useEffect, useRef, useState } from 'react'
import { analyzeVideo } from '../lib/api'
import { downloadReport } from '../lib/exporters'
import { levelFor } from '../lib/severity'
import ClassBreakdown from './ClassBreakdown'
import Dropzone from './Dropzone'
import { FileIcon, ResetIcon } from './Icons'
import Milestone from './Milestone'
import Progress from './Progress'
import Timeline from './Timeline'

export default function VideoAnalyzer() {
  const [file, setFile] = useState(null)
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(null)
  const [time, setTime] = useState(null)
  const video = useRef(null)
  const job = useRef(null)

  useEffect(() => () => url && URL.revokeObjectURL(url), [url])

  const run = async (f) => {
    setFile(f)
    setUrl(URL.createObjectURL(f))
    setResult(null)
    setError('')
    setProgress({ phase: 'uploading', percent: 0 })
    job.current = analyzeVideo(f, setProgress)
    try {
      setResult(await job.current.promise)
    } catch (e) {
      if (!e.cancelled) setError(e.message)
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
    setTime(null)
  }

  const seek = (t) => {
    if (!video.current) return
    video.current.currentTime = t
    video.current.pause()
    video.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  if (!file) {
    return (
      <Dropzone
        accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"
        maxMb={60}
        title="Drop a dashcam or phone clip here"
        hint="MP4, MOV or WebM, up to 60 MB. The first 60 seconds are analysed at 2 frames per second."
        onFile={run}
      />
    )
  }

  const s = result?.summary
  return (
    <div className="workspace workspace--video">
      <div className="workspace__main">
        <div className="stage stage--video">
          <video ref={video} src={url} controls playsInline onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)} />
          {progress && (
            <Progress progress={progress} processingText="Checking every half second of road. Longer clips take up to a minute…" onCancel={reset} />
          )}
        </div>
        <div className="workspace__bar">
          <span className="filename" title={file.name}>{file.name}</span>
          {result && (
            <span className="muted">
              {result.frames_analyzed} frames analysed in {(result.processing_ms / 1000).toFixed(1)} s
              {result.truncated ? ', first 60 s only' : ''}
            </span>
          )}
          <button type="button" className="btn btn--ghost" onClick={reset}>
            <ResetIcon /> Analyse another clip
          </button>
        </div>

        {result && (
          <section className="video-detail">
            <h3>Condition along the route</h3>
            <Timeline points={result.timeline} duration={result.duration_s} current={time} onSeek={seek} />
            {result.worst_frames.length > 0 && (
              <>
                <h3>Worst stretches</h3>
                <div className="frames">
                  {result.worst_frames.map((f) => (
                    <button type="button" key={f.t} className="frame" onClick={() => seek(f.t)}>
                      <img src={f.image} alt={`Frame at ${f.t} seconds, ${f.level}`} loading="lazy" />
                      <span>
                        <strong>{f.t.toFixed(1)}s</strong> {f.level}, score {f.score}
                      </span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </section>
        )}
      </div>

      <aside className="panel" aria-label="Results">
        {error && (
          <div className="alert" role="alert">
            <p>{error}</p>
            <button type="button" className="btn" onClick={() => run(file)}>Try again</button>
          </div>
        )}
        {s && (
          <>
            <div className="verdict">
              <Milestone score={s.average_score} level={s.level} caption="Average condition" />
              <div>
                <p className="verdict__count">{Math.round(s.damaged_frame_ratio * 100)}% of the route shows damage</p>
                <p className="verdict__advice">
                  Worst moment scored <strong>{s.peak_score}</strong> ({levelFor(s.peak_score).name}). {levelFor(s.average_score).advice}
                </p>
              </div>
            </div>
            <ClassBreakdown
              counts={s.detections_by_class}
              note="Counted across all analysed frames, so one pothole seen in three frames counts three times."
            />
            <div className="actions">
              <button
                type="button"
                className="btn"
                onClick={() =>
                  downloadReport(
                    { ...result, worst_frames: undefined },
                    { score: s.average_score, level: levelFor(s.average_score), counts: s.detections_by_class, kept: [] },
                    0.25,
                    file.name,
                  )
                }
              >
                <FileIcon /> Export route report
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  )
}
