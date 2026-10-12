// What the user has picked on the map and what the backend returned.
// Kept as a pure reducer so the click logic can be tested without a map.

import type { LngLat, RouteResponse } from './api'

export type RouteState = {
  algorithm: string
  origin: LngLat | null
  destination: LngLat | null
  status: 'idle' | 'loading' | 'done' | 'error'
  route: RouteResponse | null
  error: string | null
  // Increments with every request so late responses for an old pair of
  // points can be recognised and ignored.
  requestId: number
}

export type RouteAction =
  | { type: 'mapClicked'; point: LngLat }
  | { type: 'cleared' }
  | { type: 'algorithmChanged'; algorithm: string }
  | { type: 'routeLoaded'; requestId: number; route: RouteResponse }
  | { type: 'routeFailed'; requestId: number; error: string }

export const initialRouteState: RouteState = {
  algorithm: 'dijkstra',
  origin: null,
  destination: null,
  status: 'idle',
  route: null,
  error: null,
  requestId: 0,
}

export function routeReducer(state: RouteState, action: RouteAction): RouteState {
  switch (action.type) {
    case 'mapClicked':
      // First click sets the origin, second the destination, and a third
      // starts over with a new origin.
      // Starting over gets a new requestId too, so an answer for the old pair
      // of points that is already on its way is recognised as stale.
      if (state.origin === null || state.destination !== null) {
        return {
          ...initialRouteState,
          algorithm: state.algorithm,
          origin: action.point,
          requestId: state.requestId + 1,
        }
      }
      return {
        ...state,
        destination: action.point,
        status: 'loading',
        route: null,
        error: null,
        requestId: state.requestId + 1,
      }
    case 'cleared':
      return { ...initialRouteState, algorithm: state.algorithm, requestId: state.requestId + 1 }
    case 'algorithmChanged':
      if (action.algorithm === state.algorithm) return state
      // With both points chosen, switching algorithm re-runs the search.
      if (state.origin !== null && state.destination !== null) {
        return {
          ...state,
          algorithm: action.algorithm,
          status: 'loading',
          route: null,
          error: null,
          requestId: state.requestId + 1,
        }
      }
      return { ...state, algorithm: action.algorithm }
    case 'routeLoaded':
      if (action.requestId !== state.requestId || state.status !== 'loading') return state
      return { ...state, status: 'done', route: action.route, error: null }
    case 'routeFailed':
      if (action.requestId !== state.requestId || state.status !== 'loading') return state
      return { ...state, status: 'error', route: null, error: action.error }
  }
}
