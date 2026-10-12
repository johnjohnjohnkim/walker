import { memo, useEffect, useState } from 'react'
import { fetchHealth, type HealthResponse } from '../api'

type State = { kind: 'checking' } | { kind: 'down' } | { kind: 'up'; health: HealthResponse }

function label(state: State): string {
  if (state.kind === 'checking') return 'backend: checking'
  if (state.kind === 'down') return 'backend: down'
  const { health } = state
  if (health.status !== 'ok' || !health.graph) return 'backend: no graph'
  return `backend: ok · ${health.graph.nodes.toLocaleString('en-US')} nodes`
}

function tone(state: State): 'checking' | 'ok' | 'down' {
  if (state.kind === 'checking') return 'checking'
  return state.kind === 'up' && state.health.status === 'ok' ? 'ok' : 'down'
}

export const HealthBadge = memo(function HealthBadge() {
  const [state, setState] = useState<State>({ kind: 'checking' })

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal)
      .then((health) => setState({ kind: 'up', health }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({ kind: 'down' })
      })
    return () => controller.abort()
  }, [])

  const detail = state.kind === 'up' ? state.health.detail : undefined

  return (
    <div className={`health-badge health-badge--${tone(state)}`} role="status" title={detail}>
      {label(state)}
    </div>
  )
})
