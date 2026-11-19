import { useEffect, useState } from 'react'
import { getHealth } from '../lib/api'
import { GitHubIcon, Logo } from './Icons'

const REPO = 'https://github.com/tejasavbishnoi/roadsense'

const STATUS = {
  checking: { text: 'Connecting to model…', tone: 'muted' },
  online: { text: 'Model online', tone: 'good' },
  nomodel: { text: 'API up, no model loaded', tone: 'warn' },
  offline: { text: 'API waking up', tone: 'warn' },
}

export default function Header() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let alive = true
    const check = () =>
      getHealth()
        .then((h) => alive && setStatus(h.model_loaded ? 'online' : 'nomodel'))
        .catch(() => alive && setStatus('offline'))
    check()
    const id = setInterval(check, 45000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  const s = STATUS[status]
  return (
    <header className="header">
      <div className="header__inner">
        <a href="#top" className="brand">
          <Logo />
          <span>RoadSense</span>
        </a>
        <nav className="nav" aria-label="Main">
          <a href="#analyze">Analyze</a>
          <a href="#how">How it works</a>
          <a href="#model">Model</a>
        </nav>
        <div className="header__right">
          <span className={`status status--${s.tone}`} role="status" title={status === 'offline' ? 'The free server sleeps when idle. The first request can take up to a minute.' : undefined}>
            <span className="status__dot" />
            {s.text}
          </span>
          <a className="icon-link" href={REPO} target="_blank" rel="noreferrer" aria-label="Source code on GitHub">
            <GitHubIcon />
          </a>
        </div>
      </div>
    </header>
  )
}
