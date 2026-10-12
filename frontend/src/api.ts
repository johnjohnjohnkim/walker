// Thin wrappers around the backend JSON API. All paths are relative, so the
// Vite dev proxy (or a production reverse proxy) decides where they go.

export type LngLat = [number, number]

export interface GraphInfo {
  area: string | null
  nodes: number
  edges: number
  built_at: string | null
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  graph: GraphInfo | null
  detail?: string
}

export interface RouteEndpoint {
  requested: LngLat
  snapped: LngLat
  snap_distance_m: number
}

export interface RouteResponse {
  algorithm: string
  route: {
    coordinates: LngLat[]
    distance_m: number
    duration_s: number
    nodes: number
  }
  origin: RouteEndpoint
  destination: RouteEndpoint
  metrics: SearchMetrics
  trace: TracePayload | null
}

/** What the search cost to run (see backend/algorithms/metrics.py). */
export interface SearchMetrics {
  // Median time of the algorithm alone over `timing_runs` clean runs.
  wall_ms: number
  cpu_ms: number
  timing_runs: number
  peak_memory_bytes: number
  visited: number
  discovered: number
  frontier_pushes: number
  peak_frontier: number
  path_nodes: number
  optimal_distance_m: number
  is_shortest: boolean
  extra_distance_m: number
  extra_distance_pct: number
}

/**
 * Every event of the search, compactly (see backend/routing/views.py).
 * `events` holds three numbers per event: code (0 discover, 1 visit,
 * 2 discover backward, 3 visit backward), node index into `coordinates`,
 * and parent index (-1 for none).
 */
export interface TracePayload {
  coordinates: LngLat[]
  events: number[]
  count: number
  truncated: boolean
}

export interface AlgorithmInfo {
  id: string
  name: string
  description: string
  guarantee: 'shortest' | 'fewest_edges' | 'any'
  uses_lengths: boolean
  bidirectional: boolean
  implemented: boolean
}

/** An error the backend explained, with a message fit to show the user. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string | undefined

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function errorFrom(response: Response): Promise<ApiError> {
  // Error bodies are JSON with an `error` message, but a proxy or crash can
  // return anything, so fall back to a generic message.
  try {
    const body = await response.json()
    if (body && typeof body.error === 'string') {
      return new ApiError(body.error, response.status, body.code)
    }
  } catch {
    // Not JSON.
  }
  return new ApiError(`The server could not be reached (HTTP ${response.status}).`, response.status)
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/health', { signal })
  // 503 still carries a JSON body explaining what is wrong.
  if (!response.ok && response.status !== 503) {
    throw new Error(`Health check failed with HTTP ${response.status}`)
  }
  return response.json()
}

export async function fetchRoute(
  origin: LngLat,
  destination: LngLat,
  algorithm: string,
  signal?: AbortSignal,
  { trace = true }: { trace?: boolean } = {},
): Promise<RouteResponse> {
  const response = await fetch('/api/route', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin: { lon: origin[0], lat: origin[1] },
      destination: { lon: destination[0], lat: destination[1] },
      algorithm,
      trace,
    }),
    signal,
  })
  if (!response.ok) throw await errorFrom(response)
  return response.json()
}

export async function fetchAlgorithms(signal?: AbortSignal): Promise<AlgorithmInfo[]> {
  const response = await fetch('/api/algorithms', { signal })
  if (!response.ok) throw await errorFrom(response)
  const body: { algorithms: AlgorithmInfo[] } = await response.json()
  return body.algorithms
}

export interface Place {
  name: string
  address: string
  lon: number
  lat: number
}

export async function fetchPlaces(query: string, signal?: AbortSignal): Promise<Place[]> {
  const response = await fetch(`/api/geocode?${new URLSearchParams({ q: query })}`, { signal })
  if (!response.ok) throw await errorFrom(response)
  const body: { results: Place[] } = await response.json()
  return body.results
}
