import { useCallback, useEffect, useReducer } from 'react'
import { ApiError, fetchRoute, type LngLat } from './api'
import { HealthBadge } from './components/HealthBadge'
import { MapView } from './components/MapView'
import { RoutePanel } from './components/RoutePanel'
import { initialRouteState, routeReducer } from './routeState'

const ALGORITHM = 'dijkstra'

export default function App() {
  const [state, dispatch] = useReducer(routeReducer, initialRouteState)
  const { origin, destination, status, requestId } = state

  useEffect(() => {
    if (status !== 'loading' || origin === null || destination === null) return
    const controller = new AbortController()
    fetchRoute(origin, destination, ALGORITHM, controller.signal)
      .then((route) => dispatch({ type: 'routeLoaded', requestId, route }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof ApiError ? error.message : 'Could not reach the server.'
        dispatch({ type: 'routeFailed', requestId, error: message })
      })
    return () => controller.abort()
  }, [origin, destination, status, requestId])

  const handleMapClick = useCallback((point: LngLat) => dispatch({ type: 'mapClicked', point }), [])
  const handleClear = useCallback(() => dispatch({ type: 'cleared' }), [])

  return (
    <div className="app">
      <MapView
        origin={origin}
        destination={destination}
        route={state.route?.route.coordinates ?? null}
        onMapClick={handleMapClick}
      />
      <RoutePanel state={state} onClear={handleClear} />
      <HealthBadge />
    </div>
  )
}
