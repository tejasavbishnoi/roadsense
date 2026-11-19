import { classInfo } from './classes'

function download(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const baseName = (name = 'road') => name.replace(/\.[^.]+$/, '')

/** Draw the kept detections onto the original image and download it as PNG. */
export async function downloadAnnotated(imageUrl, detections, filename) {
  const img = new Image()
  img.src = imageUrl
  await img.decode()
  const canvas = document.createElement('canvas')
  canvas.width = img.naturalWidth
  canvas.height = img.naturalHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, 0, 0)
  const line = Math.max(2, Math.round(canvas.width / 400))
  const font = Math.max(12, Math.round(canvas.width / 70))
  ctx.font = `600 ${font}px Barlow, sans-serif`
  ctx.textBaseline = 'top'
  for (const d of detections) {
    const { color, name } = classInfo(d.label)
    const [x1, y1, x2, y2] = d.box
    const x = x1 * canvas.width
    const y = y1 * canvas.height
    const w = (x2 - x1) * canvas.width
    const h = (y2 - y1) * canvas.height
    ctx.lineWidth = line
    ctx.strokeStyle = color
    ctx.strokeRect(x, y, w, h)
    const text = `${name} ${Math.round(d.confidence * 100)}%`
    const tw = ctx.measureText(text).width + font * 0.6
    const th = font * 1.35
    const ty = y - th < 0 ? y : y - th
    ctx.fillStyle = color
    ctx.fillRect(x - line / 2, ty, tw, th)
    ctx.fillStyle = '#16191D'
    ctx.fillText(text, x + font * 0.3, ty + font * 0.18)
  }
  const blob = await new Promise((r) => canvas.toBlob(r, 'image/png'))
  download(blob, `${baseName(filename)}-roadsense.png`)
}

export function downloadReport(result, summary, minConf, filename) {
  const report = {
    generated_by: 'RoadSense',
    generated_at: new Date().toISOString(),
    file: filename,
    confidence_threshold: minConf,
    condition: { score: summary.score, level: summary.level.name, counts: summary.counts },
    detections: result.detections ? summary.kept : undefined,
    image: result.width ? { width: result.width, height: result.height } : undefined,
    inference_ms: result.inference_ms ?? result.processing_ms,
    timeline: result.timeline,
  }
  download(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }), `${baseName(filename)}-report.json`)
}
