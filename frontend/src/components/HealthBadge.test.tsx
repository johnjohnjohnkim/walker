import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { HealthBadge } from './HealthBadge'

function respond(body: unknown, status = 200) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })))
}

describe('HealthBadge', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the graph size when the backend is ready', async () => {
    respond({ status: 'ok', graph: { area: 'downtown', nodes: 16139, edges: 43914, built_at: null } })

    render(<HealthBadge />)

    expect(await screen.findByText('backend: ok · 16,139 nodes')).toBeInTheDocument()
  })

  it('shows no graph when the backend has not loaded one', async () => {
    respond({ status: 'degraded', graph: null, detail: 'No graph file' }, 503)

    render(<HealthBadge />)

    const badge = await screen.findByText('backend: no graph')
    expect(badge).toHaveAttribute('title', 'No graph file')
  })

  it('shows down when the backend returns an error status', async () => {
    // What the Vite proxy returns when Django isn't running.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 502 })))

    render(<HealthBadge />)

    expect(await screen.findByText('backend: down')).toBeInTheDocument()
  })

  it('shows down when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network error')))

    render(<HealthBadge />)

    expect(await screen.findByText('backend: down')).toBeInTheDocument()
  })
})
