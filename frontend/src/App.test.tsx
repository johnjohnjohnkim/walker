import { act, fireEvent, render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { LngLat } from './api'
import App from './App'

// MapLibre needs WebGL, which jsdom lacks. Replace the map with buttons that
// "click" fixed points.
vi.mock('./components/MapView', () => ({
  MapView: ({ onMapClick }: { onMapClick: (p: LngLat) => void }) => (
    <div>
      <button onClick={() => onMapClick([-79.38, 43.65])}>A</button>
      <button onClick={() => onMapClick([-79.39, 43.66])}>B</button>
      <button onClick={() => onMapClick([-79.4, 43.64])}>C</button>
    </div>
  ),
}))

const ALGORITHMS = [
  { id: 'dijkstra', name: 'Dijkstra', description: 'd', guarantee: 'shortest', uses_lengths: true, bidirectional: false, implemented: true },
  { id: 'bfs', name: 'BFS', description: 'b', guarantee: 'fewest_edges', uses_lengths: false, bidirectional: false, implemented: true },
  { id: 'dfs', name: 'DFS', description: 'x', guarantee: 'any', uses_lengths: false, bidirectional: false, implemented: false },
]

function routeBody(distance: number) {
  return {
    algorithm: 'dijkstra',
    route: { coordinates: [[-79.38, 43.65], [-79.39, 43.66]], distance_m: distance, duration_s: distance / 1.4, nodes: 2 },
    origin: { requested: [0, 0], snapped: [0, 0], snap_distance_m: 1 },
    destination: { requested: [0, 0], snapped: [0, 0], snap_distance_m: 1 },
    metrics: {
      wall_ms: 1.5,
      cpu_ms: 1.4,
      timing_runs: 5,
      peak_memory_bytes: 2048,
      visited: 10,
      discovered: 12,
      frontier_pushes: 13,
      peak_frontier: 4,
      path_nodes: 2,
      optimal_distance_m: distance,
      is_shortest: true,
      extra_distance_m: 0,
      extra_distance_pct: 0,
    },
    trace: null,
  }
}

describe('App', () => {
  let resolvers: Array<(r: Response) => void>
  let signals: AbortSignal[]

  beforeEach(() => {
    resolvers = []
    signals = []
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url === '/api/health') return Promise.resolve(new Response('{"status":"ok","graph":null}'))
        if (url === '/api/algorithms') return Promise.resolve(new Response(JSON.stringify({ algorithms: ALGORITHMS })))
        signals.push(init!.signal!)
        return new Promise<Response>((resolve) => resolvers.push(resolve))
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the route once both points are chosen', async () => {
    render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))
    expect(screen.getByText('Finding a walking route…')).toBeInTheDocument()

    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(2000)))))

    expect(screen.getByText('2.0 km')).toBeInTheDocument()
  })

  it('cancels the request and ignores its answer after starting over', async () => {
    render(<App />)
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))
    const firstSignal = signals.at(-1)!
    const firstResolve = resolvers.at(-1)!

    fireEvent.click(screen.getByText('C')) // starts over: new origin

    expect(firstSignal.aborted).toBe(true)
    await act(async () => firstResolve(new Response(JSON.stringify(routeBody(2000)))))
    expect(screen.queryByText('2.0 km')).not.toBeInTheDocument()
    expect(screen.getByText('Now choose a destination.')).toBeInTheDocument()
  })

  it('shows the server error message', async () => {
    render(<App />)
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))

    await act(async () =>
      resolvers.at(-1)!(
        new Response(JSON.stringify({ error: 'The destination is too far.', code: 'outside_coverage' }), {
          status: 422,
        }),
      ),
    )

    expect(screen.getByRole('alert')).toHaveTextContent('The destination is too far.')
  })

  it('re-runs the search with the newly picked algorithm', async () => {
    render(<App />)
    const bfs = await screen.findByRole('radio', { name: 'BFS' })
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))
    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(2000)))))

    fireEvent.click(bfs)

    const fetchMock = vi.mocked(fetch)
    const lastRoute = fetchMock.mock.calls.filter(([url]) => url === '/api/route').at(-1)!
    expect(JSON.parse(lastRoute[1]!.body as string).algorithm).toBe('bfs')
    expect(screen.getByText('Finding a walking route…')).toBeInTheDocument()
  })

  it('disables algorithms that are not implemented', async () => {
    render(<App />)

    expect(await screen.findByRole('radio', { name: 'DFS' })).toBeDisabled()
    expect(screen.getByRole('radio', { name: 'Dijkstra' })).toHaveAttribute('aria-checked', 'true')
  })

  it('swaps the two points and searches again', async () => {
    render(<App />)
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))
    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(2000)))))

    fireEvent.click(screen.getByRole('button', { name: 'Swap starting point and destination' }))

    const routeCalls = vi.mocked(fetch).mock.calls.filter(([url]) => url === '/api/route')
    const last = JSON.parse(routeCalls.at(-1)![1]!.body as string)
    expect(last.origin).toEqual({ lon: -79.39, lat: 43.66 })
    expect(last.destination).toEqual({ lon: -79.38, lat: 43.65 })
  })

  it('compares every implemented algorithm on request', async () => {
    render(<App />)
    await screen.findByRole('radio', { name: 'BFS' })
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))
    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(2000)))))

    fireEvent.click(screen.getByRole('button', { name: 'Compare algorithms' }))
    // Answer the comparison's requests as they come, one at a time.
    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(2000)))))

    const compared = vi
      .mocked(fetch)
      .mock.calls.filter(([url]) => url === '/api/route')
      .map(([, init]) => JSON.parse(init!.body as string))
      .filter((body) => body.trace === false)
      .map((body) => body.algorithm)
    expect(compared).toEqual(['dijkstra', 'bfs'])
    expect(screen.getByRole('region', { name: 'Algorithm comparison' })).toBeInTheDocument()
  })

  it('turns the comparison off when the points change', async () => {
    render(<App />)
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))
    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(2000)))))
    fireEvent.click(screen.getByRole('button', { name: 'Compare algorithms' }))
    expect(screen.getByRole('region', { name: 'Algorithm comparison' })).toBeInTheDocument()

    fireEvent.click(screen.getByText('C')) // starts over
    fireEvent.click(screen.getByText('A')) // new destination
    const routeCallsBefore = vi.mocked(fetch).mock.calls.filter(([url]) => url === '/api/route').length
    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(1500)))))

    expect(screen.queryByRole('region', { name: 'Algorithm comparison' })).not.toBeInTheDocument()
    const routeCallsAfter = vi.mocked(fetch).mock.calls.filter(([url]) => url === '/api/route').length
    expect(routeCallsAfter).toBe(routeCallsBefore) // no surprise comparison requests
  })

  it('returns focus to the compare button when the table is closed', async () => {
    render(<App />)
    fireEvent.click(screen.getByText('A'))
    fireEvent.click(screen.getByText('B'))
    await act(async () => resolvers.at(-1)!(new Response(JSON.stringify(routeBody(2000)))))
    fireEvent.click(screen.getByRole('button', { name: 'Compare algorithms' }))

    fireEvent.click(screen.getByRole('button', { name: 'Close comparison' }))

    expect(screen.getByRole('button', { name: 'Compare algorithms' })).toHaveFocus()
  })
})
