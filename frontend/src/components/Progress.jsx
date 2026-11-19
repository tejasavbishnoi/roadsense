export default function Progress({ progress, processingText, onCancel }) {
  const uploading = progress?.phase === 'uploading'
  return (
    <div className="progress" role="status" aria-live="polite">
      <div className="progress__road" aria-hidden="true">
        <span
          className={`progress__fill${uploading ? '' : ' progress__fill--busy'}`}
          style={uploading ? { width: `${progress.percent}%` } : undefined}
        />
      </div>
      <p>{uploading ? `Uploading… ${progress.percent}%` : processingText}</p>
      {onCancel && (
        <button type="button" className="btn btn--ghost" onClick={onCancel}>
          Cancel
        </button>
      )}
    </div>
  )
}
