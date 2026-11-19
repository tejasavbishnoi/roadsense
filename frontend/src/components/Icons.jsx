const base = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }

export const UploadIcon = (p) => (
  <svg {...base} {...p}><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
)
export const PhotoIcon = (p) => (
  <svg {...base} {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><circle cx="9" cy="10" r="1.6" /><path d="M21 16l-5-5-8 8" /></svg>
)
export const VideoIcon = (p) => (
  <svg {...base} {...p}><rect x="3" y="6" width="13" height="12" rx="2" /><path d="M16 10.5l5-3v9l-5-3" /></svg>
)
export const DownloadIcon = (p) => (
  <svg {...base} {...p}><path d="M12 4v12M7 11l5 5 5-5" /><path d="M5 20h14" /></svg>
)
export const FileIcon = (p) => (
  <svg {...base} {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></svg>
)
export const ResetIcon = (p) => (
  <svg {...base} {...p}><path d="M4 12a8 8 0 1 0 2.4-5.7L4 8.5" /><path d="M4 4v4.5h4.5" /></svg>
)
export const GitHubIcon = (p) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...p}>
    <path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2z" />
  </svg>
)
export const Logo = () => (
  <svg width="26" height="30" viewBox="0 0 32 36" aria-hidden="true">
    <path d="M5 34V16a11 11 0 0 1 22 0v18z" fill="#fff" stroke="#1F2328" strokeWidth="2.4" />
    <path d="M6.2 16a9.8 9.8 0 0 1 19.6 0z" fill="#F5B800" />
    <line x1="5" y1="16" x2="27" y2="16" stroke="#1F2328" strokeWidth="2" />
    <rect x="10" y="21" width="12" height="2.6" rx="1.3" fill="#1F2328" />
    <rect x="10" y="27" width="8" height="2.6" rx="1.3" fill="#1F2328" />
  </svg>
)
