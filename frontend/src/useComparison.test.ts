import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { LngLat } from './api'
import { useComparison } from './useComparison'

const A: LngLat = [-79.38, 43.65]
const B: LngLat = [-79.39, 43.66]
const C: LngLat = [-79.4, 43.64]

function route(algorithm: string) {
  return { algorithm, route: { coordinates: [], distance_m: 1, duration_s: 1, nodes: 1 }, metrics: {}, trace: null }
}

describe('useComparison', () => {
  let resolvers: Record<string, (r: Response) => void>
  let bodies: Record<string, unknown>[]

  beforeEach(() => {
    resolvers = {}
    bodies = []
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init: RequestInit) => {
        const body = JSON.parse(init.body as string)
        bodies.push(body)
        return new Promise<Response>((resolve) => {
          resolvers[body.algorithm] = resolve
        })
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does nothing until enabled', () => {
    const { result } = renderHook(() => useComparison(A, B, ['dijkstra'], false))

    expect(result.current).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('runs the algorithms one after another, without traces', async () => {
    const { result } = renderHook(() => useComparison(A, B, ['dijkstra', 'bfs'], true))

    expect(result.current).toEqual({ dijkstra: { status: 'loading' }, bfs: { status: 'loading' } })
    // Only the first is running: searches side by side would spoil each other's timings.
    expect(bodies.map((b) => [b.algorithm, b.trace])).toEqual([['dijkstra', false]])

    await act(async () => resolvers.dijkstra(new Response(JSON.stringify(route('dijkstra')))))

    expect(result.current?.dijkstra).toMatchObject({ status: 'done' })
    expect(result.current?.bfs).toEqual({ status: 'loading' })
    expect(bodies.map((b) => b.algorithm)).toEqual(['dijkstra', 'bfs'])

    await act(async () => resolvers.bfs(new Response(JSON.stringify(route('bfs')))))

    expect(result.current?.bfs).toMatchObject({ status: 'done' })
  })

  it('records errors per algorithm', async () => {
    const { result } = renderHook(() => useComparison(A, B, ['dfs'], true))

    await act(async () =>
      resolvers.dfs(new Response(JSON.stringify({ error: 'The dfs implementation failed.' }), { status: 500 })),
    )

    expect(result.current?.dfs).toEqual({ status: 'error', message: 'The dfs implementation failed.' })
  })

  it('drops results when a point changes, even ones that arrive late', async () => {
    const { result, rerender } = renderHook(({ dest }) => useComparison(A, dest, ['dijkstra'], true), {
      initialProps: { dest: B },
    })
    const lateResolve = resolvers.dijkstra

    rerender({ dest: C })
    await act(async () => lateResolve(new Response(JSON.stringify(route('dijkstra')))))

    expect(result.current).toEqual({ dijkstra: { status: 'loading' } })
  })

  it('keeps the same object between renders when nothing changed', () => {
    const { result, rerender } = renderHook(() => useComparison(A, B, ['dijkstra'], true))
    const first = result.current

    rerender()

    expect(result.current).toBe(first)
  })
})
