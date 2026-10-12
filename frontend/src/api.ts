// Thin wrappers around the backend JSON API. All paths are relative, so the
// Vite dev proxy (or a production reverse proxy) decides where they go.

export interface HealthResponse {
  status: string
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/health', { signal })
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`)
  }
  return response.json()
}
