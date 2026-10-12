import type { AlgorithmInfo } from '../api'
import { formatDistance, formatDuration } from '../format'
import type { RouteState } from '../routeState'
import { AlgorithmPicker } from './AlgorithmPicker'

interface Props {
  state: RouteState
  algorithms: AlgorithmInfo[]
  onAlgorithmChange: (id: string) => void
  onClear: () => void
}

function message(state: RouteState): string {
  if (state.origin === null) return 'Click the map to choose a starting point.'
  if (state.destination === null) return 'Now click to choose a destination.'
  if (state.status === 'loading') return 'Finding a walking route…'
  return ''
}

export function RoutePanel({ state, algorithms, onAlgorithmChange, onClear }: Props) {
  const { route, error } = state
  const hint = message(state)

  return (
    <section className="panel" aria-label="Directions">
      <h1 className="panel__title">Walker</h1>

      <AlgorithmPicker algorithms={algorithms} selected={state.algorithm} onSelect={onAlgorithmChange} />

      {hint && <p className="panel__hint">{hint}</p>}

      {state.status === 'done' && route && (
        <div className="panel__summary">
          <span className="panel__duration">{formatDuration(route.route.duration_s)}</span>
          <span className="panel__distance">{formatDistance(route.route.distance_m)}</span>
          <p className="panel__meta">
            {algorithms.find((a) => a.id === route.algorithm)?.name ?? route.algorithm} explored {route.search.visited.toLocaleString('en-US')} intersections
          </p>
        </div>
      )}

      {state.status === 'error' && error && (
        <p className="panel__error" role="alert">
          {error}
        </p>
      )}

      {state.origin !== null && (
        <button type="button" className="panel__clear" onClick={onClear}>
          Clear
        </button>
      )}
    </section>
  )
}
