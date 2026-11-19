import { useState } from 'react'
import { PhotoIcon, VideoIcon } from './Icons'
import PhotoAnalyzer from './PhotoAnalyzer'
import VideoAnalyzer from './VideoAnalyzer'

const TABS = [
  { id: 'photo', label: 'Photo', Icon: PhotoIcon },
  { id: 'video', label: 'Dashcam video', Icon: VideoIcon },
]

export default function Analyzer() {
  const [tab, setTab] = useState('photo')

  const onKey = (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    const i = TABS.findIndex((t) => t.id === tab)
    const next = TABS[(i + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length]
    setTab(next.id)
    document.getElementById(`tab-${next.id}`)?.focus()
  }

  return (
    <div className="analyzer">
      <div className="tabs" role="tablist" aria-label="What do you want to analyse?" onKeyDown={onKey}>
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            id={`tab-${id}`}
            role="tab"
            type="button"
            aria-selected={tab === id}
            aria-controls={`panel-${id}`}
            tabIndex={tab === id ? 0 : -1}
            className="tab"
            onClick={() => setTab(id)}
          >
            <Icon /> {label}
          </button>
        ))}
      </div>
      {/* Both stay mounted so switching tabs keeps your results */}
      <div id="panel-photo" role="tabpanel" aria-labelledby="tab-photo" hidden={tab !== 'photo'}>
        <PhotoAnalyzer />
      </div>
      <div id="panel-video" role="tabpanel" aria-labelledby="tab-video" hidden={tab !== 'video'}>
        <VideoAnalyzer />
      </div>
    </div>
  )
}
