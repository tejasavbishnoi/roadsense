import { useRef, useState } from 'react'
import { UploadIcon } from './Icons'

export default function Dropzone({ accept, maxMb, title, hint, onFile }) {
  const input = useRef(null)
  const [over, setOver] = useState(false)
  const [error, setError] = useState('')

  const take = (file) => {
    if (!file) return
    const okType = accept.split(',').some((t) => {
      t = t.trim()
      return t.endsWith('/*') ? file.type.startsWith(t.slice(0, -1)) : file.type === t || file.name.toLowerCase().endsWith(t)
    })
    if (!okType) return setError('That file type isn’t supported here.')
    if (file.size > maxMb * 1024 * 1024) return setError(`That file is larger than ${maxMb} MB. Try a shorter clip or a smaller photo.`)
    setError('')
    onFile(file)
  }

  return (
    <div
      className={`dropzone${over ? ' dropzone--over' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        take(e.dataTransfer.files?.[0])
      }}
    >
      <div className="dropzone__lane" aria-hidden="true" />
      <UploadIcon width={28} height={28} />
      <p className="dropzone__title">{title}</p>
      <button type="button" className="btn btn--primary" onClick={() => input.current?.click()}>
        Choose a file
      </button>
      <p className="dropzone__hint">{hint}</p>
      {error && (
        <p className="dropzone__error" role="alert">
          {error}
        </p>
      )}
      <input
        ref={input}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => {
          take(e.target.files?.[0])
          e.target.value = ''
        }}
      />
    </div>
  )
}
