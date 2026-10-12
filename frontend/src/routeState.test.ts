import { describe, expect, it } from 'vitest'
import type { LngLat, RouteResponse } from './api'
import { initialRouteState, routeReducer, type RouteState } from './routeState'

const A: LngLat = [-79.38, 43.65]
const B: LngLat = [-79.39, 43.66]
const C: LngLat = [-79.4, 43.64]

const fakeRoute = { algorithm: 'dijkstra' } as RouteResponse

function click(state: RouteState, point: LngLat) {
  return routeReducer(state, { type: 'mapClicked', point })
}

describe('routeReducer', () => {
  it('sets the origin on the first click', () => {
    const state = click(initialRouteState, A)

    expect(state.origin).toEqual(A)
    expect(state.destination).toBeNull()
    expect(state.status).toBe('idle')
  })

  it('sets the destination and starts loading on the second click', () => {
    const state = click(click(initialRouteState, A), B)

    expect(state.destination).toEqual(B)
    expect(state.status).toBe('loading')
    expect(state.requestId).toBe(2)
  })

  it('starts over with a new origin on the third click', () => {
    const state = click(click(click(initialRouteState, A), B), C)

    expect(state.origin).toEqual(C)
    expect(state.destination).toBeNull()
    expect(state.route).toBeNull()
    expect(state.status).toBe('idle')
  })

  it('stores the route for the current request', () => {
    const loading = click(click(initialRouteState, A), B)

    const state = routeReducer(loading, { type: 'routeLoaded', requestId: loading.requestId, route: fakeRoute })

    expect(state.status).toBe('done')
    expect(state.route).toBe(fakeRoute)
  })

  it('ignores a late response for an earlier pair of points', () => {
    const first = click(click(initialRouteState, A), B)
    const second = click(click(click(first, C), A), B)

    const state = routeReducer(second, { type: 'routeLoaded', requestId: first.requestId, route: fakeRoute })

    expect(state).toBe(second)
  })

  it('records an error', () => {
    const loading = click(click(initialRouteState, A), B)

    const state = routeReducer(loading, { type: 'routeFailed', requestId: loading.requestId, error: 'Too far' })

    expect(state.status).toBe('error')
    expect(state.error).toBe('Too far')
  })

  it('clears everything and invalidates the request in flight', () => {
    const loading = click(click(initialRouteState, A), B)

    const cleared = routeReducer(loading, { type: 'cleared' })
    const late = routeReducer(cleared, { type: 'routeLoaded', requestId: loading.requestId, route: fakeRoute })

    expect(cleared.origin).toBeNull()
    expect(cleared.status).toBe('idle')
    expect(late).toBe(cleared)
  })

  it('ignores the answer for a request abandoned by starting over', () => {
    const loading = click(click(initialRouteState, A), B)
    const restarted = click(loading, C)

    const state = routeReducer(restarted, { type: 'routeLoaded', requestId: loading.requestId, route: fakeRoute })

    expect(state).toBe(restarted)
    expect(state.route).toBeNull()
  })

  it('re-runs the search when the algorithm changes with both points set', () => {
    const done = routeReducer(click(click(initialRouteState, A), B), {
      type: 'routeLoaded',
      requestId: 2,
      route: fakeRoute,
    })

    const state = routeReducer(done, { type: 'algorithmChanged', algorithm: 'bfs' })

    expect(state.algorithm).toBe('bfs')
    expect(state.status).toBe('loading')
    expect(state.route).toBeNull()
    expect(state.requestId).toBe(done.requestId + 1)
  })

  it('just records the algorithm before both points are set', () => {
    const state = routeReducer(click(initialRouteState, A), { type: 'algorithmChanged', algorithm: 'bfs' })

    expect(state.algorithm).toBe('bfs')
    expect(state.status).toBe('idle')
  })

  it('keeps the algorithm when starting over or clearing', () => {
    const picked = routeReducer(initialRouteState, { type: 'algorithmChanged', algorithm: 'bfs' })

    expect(click(click(click(picked, A), B), C).algorithm).toBe('bfs')
    expect(routeReducer(picked, { type: 'cleared' }).algorithm).toBe('bfs')
  })

  it('ignores picking the algorithm already selected', () => {
    expect(routeReducer(initialRouteState, { type: 'algorithmChanged', algorithm: 'dijkstra' })).toBe(initialRouteState)
  })

  it('swaps the two ends and searches again', () => {
    const chosen = routeReducer(click(initialRouteState, A), {
      type: 'pointChosen',
      which: 'destination',
      point: B,
      label: 'Union Station',
    })

    const swapped = routeReducer(chosen, { type: 'swapped' })

    expect(swapped.origin).toEqual(B)
    expect(swapped.originLabel).toBe('Union Station')
    expect(swapped.destination).toEqual(A)
    expect(swapped.destinationLabel).toBe('Dropped pin')
    expect(swapped.status).toBe('loading')
    expect(swapped.requestId).toBe(chosen.requestId + 1)
  })

  it('swaps a lone point to the other end', () => {
    const swapped = routeReducer(click(initialRouteState, A), { type: 'swapped' })

    expect(swapped.origin).toBeNull()
    expect(swapped.destination).toEqual(A)
    expect(swapped.status).toBe('idle')
  })
})
