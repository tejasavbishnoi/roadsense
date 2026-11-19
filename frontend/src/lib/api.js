export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function getJson(path, timeoutMs = 15000) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(`${API_URL}${path}`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    return await res.json()
  } finally {
    clearTimeout(timer)
  }
}

export const getHealth = () => getJson('/health')
export const getModelCard = () => getJson('/model')

/**
 * Upload with progress. Uses XMLHttpRequest because fetch can't report upload progress.
 * onProgress receives { phase: 'uploading' | 'processing', percent }
 */
function upload(path, file, onProgress) {
  let xhr
  const promise = new Promise((resolve, reject) => {
    xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_URL}${path}`)
    xhr.responseType = 'json'
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.({ phase: 'uploading', percent: Math.round((e.loaded / e.total) * 100) })
    }
    xhr.upload.onload = () => onProgress?.({ phase: 'processing', percent: 100 })
    xhr.onload = () => {
      const body = xhr.response
      if (xhr.status >= 200 && xhr.status < 300) return resolve(body)
      const detail = body && typeof body.detail === 'string' ? body.detail : null
      reject(new Error(detail || messageForStatus(xhr.status)))
    }
    xhr.onerror = () =>
      reject(new Error('Could not reach the RoadSense API. It may be waking up — try again in a minute.'))
    xhr.onabort = () => reject(Object.assign(new Error('Cancelled'), { cancelled: true }))
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
  return { promise, cancel: () => xhr?.abort() }
}

function messageForStatus(status) {
  if (status === 413) return 'That file is too large.'
  if (status === 415) return 'That file type isn’t supported.'
  if (status === 503) return 'The model isn’t loaded on the server yet.'
  return `The server returned an error (${status}).`
}

// The API returns every detection down to a low confidence; the UI filters locally.
export const analyzeImage = (file, onProgress) => upload('/predict/image?conf=0.25', file, onProgress)
export const analyzeVideo = (file, onProgress) => upload('/predict/video?conf=0.25&sample_fps=2', file, onProgress)
