import { useCallback, useEffect, useMemo, useReducer, useState } from 'react'
import { type AlgorithmInfo, ApiError, fetchAlgorithms, fetchRoute, type LngLat, type Place } from './api'
import { HealthBadge } from './components/HealthBadge'
import { MetricsCard } from './components/MetricsCard'
import { MapView } from './components/MapView'
import { PlaybackBar } from './components/PlaybackBar'
import { RoutePanel } from './components/RoutePanel'
import { type Endpoint, initialRouteState, routeReducer } from './routeState'
import { decodeTrace } from './trace'
import { usePlayback } from './usePlayback'

// Shown until the backend's list arrives, or if it can't be fetched.
const FALLBACK_ALGORITHMS: AlgorithmInfo[] = [
  {
    id: 'dijkstra',
    name: 'Dijkstra',
    description: 'Explores outward in order of walking distance. Always finds the shortest route.',
    guarantee: 'shortest',
    uses_lengths: true,
    bidirectional: false,
    implemented: true,
  },
]

export default function App() {
  const [state, dispatch] = useReducer(routeReducer, initialRouteState)
  const [algorithms, setAlgorithms] = useState<AlgorithmInfo[]>(FALLBACK_ALGORITHMS)
  // Where the map should move to after a search result is picked. A new
  // object each time, so picking the same place twice still moves the map.
  const [focus, setFocus] = useState<{ point: LngLat } | null>(null)
  const { algorithm, origin, destination, status, requestId } = state

  useEffect(() => {
    const controller = new AbortController()
    fetchAlgorithms(controller.signal)
      .then(setAlgorithms)
      .catch(() => {
        // Keep the fallback list; routing with Dijkstra still works.
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (status !== 'loading' || origin === null || destination === null) return
    const controller = new AbortController()
    fetchRoute(origin, destination, algorithm, controller.signal)
      .then((route) => dispatch({ type: 'routeLoaded', requestId, route }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof ApiError ? error.message : 'Could not reach the server.'
        dispatch({ type: 'routeFailed', requestId, error: message })
      })
    return () => controller.abort()
  }, [algorithm, origin, destination, status, requestId])

  // Decoded once per route; the animation then only moves `playback.step`.
  const trace = useMemo(() => (state.route?.trace ? decodeTrace(state.route.trace) : null), [state.route])
  const playback = usePlayback(trace?.steps ?? 0, trace)
  const algorithmName = algorithms.find((a) => a.id === state.route?.algorithm)?.name ?? state.route?.algorithm ?? ''

  const handleMapClick = useCallback((point: LngLat) => dispatch({ type: 'mapClicked', point }), [])
  const handleClear = useCallback(() => dispatch({ type: 'cleared' }), [])
  const handlePlaceSelect = useCallback((which: Endpoint, place: Place) => {
    const point: LngLat = [place.lon, place.lat]
    dispatch({ type: 'pointChosen', which, point, label: place.name })
    setFocus({ point })
  }, [])
  const handleAlgorithmChange = useCallback(
    (id: string) => dispatch({ type: 'algorithmChanged', algorithm: id }),
    [],
  )

  return (
    <div className="app">
      <MapView
        origin={origin}
        destination={destination}
        route={state.route?.route.coordinates ?? null}
        trace={trace}
        traceStep={playback.step}
        routeVisible={trace === null || playback.finished}
        focus={focus}
        showBothPoints={status === 'error'}
        onMapClick={handleMapClick}
      />
      <div className="sidebar">
        <RoutePanel
          state={state}
          algorithms={algorithms}
          onAlgorithmChange={handleAlgorithmChange}
          onPlaceSelect={handlePlaceSelect}
          onClear={handleClear}
        />
        {state.status === 'done' && state.route && (
          <MetricsCard
            metrics={state.route.metrics}
            algorithmName={algorithmName}
            distanceM={state.route.route.distance_m}
          />
        )}
      </div>
      {trace && <PlaybackBar trace={trace} playback={playback} algorithmName={algorithmName} />}
      <HealthBadge />
    </div>
  )
}
