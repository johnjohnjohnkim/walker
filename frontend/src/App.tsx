import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { type AlgorithmInfo, ApiError, fetchAlgorithms, fetchRoute, type LngLat, type Place } from './api'
import { ComparisonTable } from './components/ComparisonTable'
import { HealthBadge } from './components/HealthBadge'
import { MetricsCard } from './components/MetricsCard'
import { MapView } from './components/MapView'
import { PlaybackBar } from './components/PlaybackBar'
import { RoutePanel } from './components/RoutePanel'
import { type Endpoint, initialRouteState, routeReducer } from './routeState'
import { decodeTrace } from './trace'
import { useComparison } from './useComparison'
import { usePlayback } from './usePlayback'

// A snapped point closer than this to where it was asked for needs no
// connector line.
const SNAP_LINE_MIN_M = 5

const NO_LINES: never[] = []

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
  // The answer (route, grey alternatives, snap lines) appears only once the
  // search has played out.
  const routeVisible = state.status === 'done' && (trace === null || playback.finished)
  const algorithmName = algorithms.find((a) => a.id === state.route?.algorithm)?.name ?? state.route?.algorithm ?? ''

  // Comparison: every implemented algorithm for the current two points.
  // The pair of points the comparison was asked for; it switches off by
  // itself as soon as either point changes.
  const [comparedPoints, setComparedPoints] = useState<string | null>(null)
  const pointsKey = origin && destination ? `${origin.join(',')}|${destination.join(',')}` : null
  const comparing = comparedPoints !== null && comparedPoints === pointsKey
  const compareButtonRef = useRef<HTMLButtonElement>(null)
  const implementedIds = useMemo(() => algorithms.filter((a) => a.implemented).map((a) => a.id), [algorithms])
  const comparison = useComparison(origin, destination, implementedIds, comparing)
  const alternatives = useMemo(() => {
    if (!comparison) return []
    return Object.entries(comparison).flatMap(([id, entry]) =>
      id !== state.route?.algorithm && entry.status === 'done' ? [entry.route.route.coordinates] : [],
    )
  }, [comparison, state.route])

  const snapLines = useMemo(() => {
    const route = state.route
    if (!route) return []
    return [route.origin, route.destination]
      .filter((end) => end.snap_distance_m >= SNAP_LINE_MIN_M)
      .map((end): [LngLat, LngLat] => [end.requested, end.snapped])
  }, [state.route])

  const handleMapClick = useCallback((point: LngLat) => dispatch({ type: 'mapClicked', point }), [])
  const handleClear = useCallback(() => {
    dispatch({ type: 'cleared' })
    setComparedPoints(null)
  }, [])
  const handleSwap = useCallback(() => dispatch({ type: 'swapped' }), [])
  const handleCompare = useCallback(
    () => setComparedPoints((current) => (current === pointsKey ? null : pointsKey)),
    [pointsKey],
  )
  const handleCloseComparison = useCallback(() => {
    setComparedPoints(null)
    // The close button disappears with the table; keep keyboard focus nearby.
    compareButtonRef.current?.focus()
  }, [])
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
        alternatives={routeVisible ? alternatives : NO_LINES}
        snapLines={routeVisible ? snapLines : NO_LINES}
        trace={trace}
        traceStep={playback.step}
        routeVisible={routeVisible}
        focus={focus}
        showBothPoints={status === 'error'}
        onMapClick={handleMapClick}
      />
      <div className={`sidebar${comparing ? ' sidebar--comparing' : ''}`}>
        <RoutePanel
          state={state}
          algorithms={algorithms}
          onAlgorithmChange={handleAlgorithmChange}
          onPlaceSelect={handlePlaceSelect}
          onSwap={handleSwap}
          comparing={comparing}
          onCompare={handleCompare}
          onClear={handleClear}
          compareButtonRef={compareButtonRef}
        />
        <div className="sidebar__cards">
          {comparison && (
            <ComparisonTable
              algorithms={algorithms}
              entries={comparison}
              selected={state.algorithm}
              onSelect={handleAlgorithmChange}
              onClose={handleCloseComparison}
            />
          )}
          {state.status === 'done' && state.route && (
            <MetricsCard
              metrics={state.route.metrics}
              algorithmName={algorithmName}
              distanceM={state.route.route.distance_m}
            />
          )}
        </div>
      </div>
      {trace && state.route && (
        <PlaybackBar
          trace={trace}
          playback={playback}
          algorithmName={algorithmName}
          totalVisited={state.route.metrics.visited}
        />
      )}
      <HealthBadge />
    </div>
  )
}
