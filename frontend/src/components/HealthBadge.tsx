import { useEffect, useState } from 'react'
import { fetchHealth } from '../api'

type Status = 'checking' | 'ok' | 'down'

export function HealthBadge() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal)
      .then((body) => setStatus(body.status === 'ok' ? 'ok' : 'down'))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setStatus('down')
      })
    return () => controller.abort()
  }, [])

  return (
    <div className={`health-badge health-badge--${status}`} role="status">
      backend: {status}
    </div>
  )
}
