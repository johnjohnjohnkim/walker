import { useCallback, useEffect, useReducer, useState } from 'react'
import { type AlgorithmInfo, ApiError, fetchAlgorithms, fetchRoute, type LngLat } from './api'
import { HealthBadge } from './components/HealthBadge'
import { MapView } from './components/MapView'
import { RoutePanel } from './components/RoutePanel'
import { initialRouteState, routeReducer } from './routeState'

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

  const handleMapClick = useCallback((point: LngLat) => dispatch({ type: 'mapClicked', point }), [])
  const handleClear = useCallback(() => dispatch({ type: 'cleared' }), [])
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
        onMapClick={handleMapClick}
      />
      <RoutePanel
        state={state}
        algorithms={algorithms}
        onAlgorithmChange={handleAlgorithmChange}
        onClear={handleClear}
      />
      <HealthBadge />
    </div>
  )
}
