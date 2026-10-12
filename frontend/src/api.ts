// Thin wrappers around the backend JSON API. All paths are relative, so the
// Vite dev proxy (or a production reverse proxy) decides where they go.

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

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/health', { signal })
  // 503 still carries a JSON body explaining what is wrong.
  if (!response.ok && response.status !== 503) {
    throw new Error(`Health check failed with HTTP ${response.status}`)
  }
  return response.json()
}
