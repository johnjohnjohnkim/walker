import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { HealthBadge } from './HealthBadge'

describe('HealthBadge', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows ok when the backend responds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }), { status: 200 })),
    )

    render(<HealthBadge />)

    expect(await screen.findByText('backend: ok')).toBeInTheDocument()
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
