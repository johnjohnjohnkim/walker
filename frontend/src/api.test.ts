import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fetchRoute } from './api'

function respond(body: string, status: number) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(body, { status }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('fetchRoute', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts lon/lat objects and the algorithm', async () => {
    const fetchMock = respond(JSON.stringify({ algorithm: 'dijkstra' }), 200)

    await fetchRoute([-79.38, 43.65], [-79.39, 43.66], 'dijkstra')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/route')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({
      origin: { lon: -79.38, lat: 43.65 },
      destination: { lon: -79.39, lat: 43.66 },
      algorithm: 'dijkstra',
    })
  })

  it('turns a JSON error into an ApiError with the server message', async () => {
    respond(JSON.stringify({ error: 'The destination is too far.', code: 'outside_coverage' }), 422)

    const error = await fetchRoute([0, 0], [0, 0], 'dijkstra').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ message: 'The destination is too far.', status: 422, code: 'outside_coverage' })
  })

  it('falls back to a generic message for a non-JSON error', async () => {
    respond('<html>Bad gateway</html>', 502)

    const error = await fetchRoute([0, 0], [0, 0], 'dijkstra').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).message).toContain('HTTP 502')
  })
})
