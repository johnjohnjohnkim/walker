import { memo } from 'react'
import type { AlgorithmInfo, Place } from '../api'
import { formatDistance, formatDuration } from '../format'
import type { Endpoint, RouteState } from '../routeState'
import { AlgorithmPicker } from './AlgorithmPicker'
import { SearchBox } from './SearchBox'

interface Props {
  state: RouteState
  algorithms: AlgorithmInfo[]
  onAlgorithmChange: (id: string) => void
  onPlaceSelect: (which: Endpoint, place: Place) => void
  onClear: () => void
}

function message(state: RouteState): string {
  if (state.origin === null) return 'Search for a place or click the map to choose a starting point.'
  if (state.destination === null) return 'Now choose a destination.'
  if (state.status === 'loading') return 'Finding a walking route…'
  return ''
}

// Memoized: the animation re-renders App every frame, but this panel's
// props only change when the route state does.
export const RoutePanel = memo(function RoutePanel({
  state,
  algorithms,
  onAlgorithmChange,
  onPlaceSelect,
  onClear,
}: Props) {
  const { route, error } = state
  const hint = message(state)

  return (
    <section className="panel" aria-label="Directions">
      <h1 className="panel__title">Walker</h1>

      <div className="panel__searches">
        <SearchBox
          label="Starting point"
          placeholder="Choose starting point"
          value={state.originLabel}
          marker="origin"
          onSelect={(place) => onPlaceSelect('origin', place)}
        />
        <SearchBox
          label="Destination"
          placeholder="Choose destination"
          value={state.destinationLabel}
          marker="destination"
          onSelect={(place) => onPlaceSelect('destination', place)}
        />
      </div>

      <AlgorithmPicker algorithms={algorithms} selected={state.algorithm} onSelect={onAlgorithmChange} />

      {hint && <p className="panel__hint">{hint}</p>}

      {state.status === 'done' && route && (
        <div className="panel__summary">
          <span className="panel__duration">{formatDuration(route.route.duration_s)}</span>
          <span className="panel__distance">{formatDistance(route.route.distance_m)}</span>
          <p className="panel__meta">
            {algorithms.find((a) => a.id === route.algorithm)?.name ?? route.algorithm} explored {route.metrics.visited.toLocaleString('en-US')} intersections
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
})
