// What the user has picked (by clicking the map or searching) and what the
// backend returned. Kept as a pure reducer so the logic can be tested
// without a map.

import type { LngLat, RouteResponse } from './api'

export type Endpoint = 'origin' | 'destination'

export type RouteState = {
  algorithm: string
  origin: LngLat | null
  destination: LngLat | null
  // What the search boxes show for each point: a place name, or
  // "Dropped pin" for a map click.
  originLabel: string
  destinationLabel: string
  status: 'idle' | 'loading' | 'done' | 'error'
  route: RouteResponse | null
  error: string | null
  // Increments with every request so late responses for an old pair of
  // points can be recognised and ignored.
  requestId: number
}

export type RouteAction =
  | { type: 'mapClicked'; point: LngLat }
  | { type: 'pointChosen'; which: Endpoint; point: LngLat; label: string }
  | { type: 'cleared' }
  | { type: 'swapped' }
  | { type: 'algorithmChanged'; algorithm: string }
  | { type: 'routeLoaded'; requestId: number; route: RouteResponse }
  | { type: 'routeFailed'; requestId: number; error: string }

export const DROPPED_PIN = 'Dropped pin'

export const initialRouteState: RouteState = {
  algorithm: 'dijkstra',
  origin: null,
  destination: null,
  originLabel: '',
  destinationLabel: '',
  status: 'idle',
  route: null,
  error: null,
  requestId: 0,
}

/** Start a new search if both points are set, otherwise wait for the other one. */
function withPoints(state: RouteState, changes: Partial<RouteState>): RouteState {
  const next = { ...state, ...changes, route: null, error: null, requestId: state.requestId + 1 }
  const ready = next.origin !== null && next.destination !== null
  return { ...next, status: ready ? 'loading' : 'idle' }
}

export function routeReducer(state: RouteState, action: RouteAction): RouteState {
  switch (action.type) {
    case 'mapClicked':
      // First click sets the origin, second the destination, and a third
      // starts over with a new origin. Every change gets a new requestId,
      // so an answer for an earlier pair of points is recognised as stale.
      if (state.origin === null) {
        return withPoints(state, { origin: action.point, originLabel: DROPPED_PIN })
      }
      if (state.destination === null) {
        return withPoints(state, { destination: action.point, destinationLabel: DROPPED_PIN })
      }
      return withPoints(state, {
        origin: action.point,
        originLabel: DROPPED_PIN,
        destination: null,
        destinationLabel: '',
      })
    case 'pointChosen':
      // A search result replaces just that end; the other end is kept.
      return action.which === 'origin'
        ? withPoints(state, { origin: action.point, originLabel: action.label })
        : withPoints(state, { destination: action.point, destinationLabel: action.label })
    case 'swapped':
      if (state.origin === null && state.destination === null) return state
      return withPoints(state, {
        origin: state.destination,
        destination: state.origin,
        originLabel: state.destinationLabel,
        destinationLabel: state.originLabel,
      })
    case 'cleared':
      return { ...initialRouteState, algorithm: state.algorithm, requestId: state.requestId + 1 }
    case 'algorithmChanged':
      if (action.algorithm === state.algorithm) return state
      // With both points chosen, switching algorithm re-runs the search.
      return withPoints(state, { algorithm: action.algorithm })
    case 'routeLoaded':
      if (action.requestId !== state.requestId || state.status !== 'loading') return state
      return { ...state, status: 'done', route: action.route, error: null }
    case 'routeFailed':
      if (action.requestId !== state.requestId || state.status !== 'loading') return state
      return { ...state, status: 'error', route: null, error: action.error }
  }
}
