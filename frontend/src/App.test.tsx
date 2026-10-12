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

function routeBody(distance: number) {
  return {
    algorithm: 'dijkstra',
    route: { coordinates: [[-79.38, 43.65], [-79.39, 43.66]], distance_m: distance, duration_s: distance / 1.4, nodes: 2 },
    origin: { requested: [0, 0], snapped: [0, 0], snap_distance_m: 1 },
    destination: { requested: [0, 0], snapped: [0, 0], snap_distance_m: 1 },
    search: { visited: 10, discovered: 12 },
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
    expect(screen.getByText('Now click to choose a destination.')).toBeInTheDocument()
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
})
