import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SearchBox } from './SearchBox'

const CN_TOWER = { name: 'CN Tower', address: '290 Bremner Boulevard, Toronto', lon: -79.3871, lat: 43.6426 }
const UNION = { name: 'Union Station', address: '65 Front Street West, Toronto', lon: -79.3806, lat: 43.6453 }

function respond(body: unknown, status = 200) {
  // A fresh Response per call: a body can only be read once.
  const mock = vi.fn(async (_url: string, _init?: RequestInit) => new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', mock)
  return mock
}

function setup(onSelect = vi.fn(), value = '') {
  render(<SearchBox label="Starting point" placeholder="Choose" value={value} marker="origin" onSelect={onSelect} />)
  return { input: screen.getByRole('combobox', { name: 'Starting point' }), onSelect }
}

async function type(input: HTMLElement, text: string) {
  fireEvent.focus(input)
  fireEvent.change(input, { target: { value: text } })
  // Let the debounce timer fire and the fetch resolve.
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300)
  })
}

describe('SearchBox', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('suggests places after a pause in typing', async () => {
    const fetchMock = respond({ results: [CN_TOWER, UNION] })
    const { input } = setup()

    fireEvent.focus(input)
    fireEvent.change(input, { target: { value: 'c' } })
    fireEvent.change(input, { target: { value: 'cn' } })
    fireEvent.change(input, { target: { value: 'cn to' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300)
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/geocode?q=cn+to')
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual([
      'CN Tower290 Bremner Boulevard, Toronto',
      'Union Station65 Front Street West, Toronto',
    ])
  })

  it('does not search for a single character', async () => {
    const fetchMock = respond({ results: [] })
    const { input } = setup()

    await type(input, 'c')

    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('picks a suggestion with the mouse', async () => {
    respond({ results: [CN_TOWER, UNION] })
    const { input, onSelect } = setup()
    await type(input, 'station')

    fireEvent.mouseDown(screen.getByText('Union Station'))

    expect(onSelect).toHaveBeenCalledWith(UNION)
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('picks a suggestion with the keyboard', async () => {
    respond({ results: [CN_TOWER, UNION] })
    const { input, onSelect } = setup()
    await type(input, 'cn')

    fireEvent.keyDown(input, { key: 'ArrowDown' })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(onSelect).toHaveBeenCalledWith(UNION)
  })

  it('wraps around with the arrow keys', async () => {
    respond({ results: [CN_TOWER, UNION] })
    const { input } = setup()
    await type(input, 'cn')

    fireEvent.keyDown(input, { key: 'ArrowUp' })

    expect(screen.getByRole('option', { name: /Union Station/ })).toHaveAttribute('aria-selected', 'true')
  })

  it('closes on Escape and shows the chosen value again', async () => {
    respond({ results: [CN_TOWER] })
    const { input } = setup(vi.fn(), 'CN Tower')
    await type(input, 'somewhere')

    fireEvent.keyDown(input, { key: 'Escape' })

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(input).toHaveValue('CN Tower')
  })

  it('says when nothing matches', async () => {
    respond({ results: [] })
    const { input } = setup()

    await type(input, 'zzzz')

    expect(screen.getByText('No places found on the map.')).toBeInTheDocument()
  })

  it('shows the server message when search is unavailable', async () => {
    respond({ error: 'Place search is unavailable right now. You can still click the map.', code: 'geocoder_unavailable' }, 503)
    const { input } = setup()

    await type(input, 'cn')

    expect(screen.getByText(/You can still click the map/)).toBeInTheDocument()
  })

  it('cancels the previous search when typing continues', async () => {
    const fetchMock = respond({ results: [CN_TOWER] })
    const { input } = setup()
    await type(input, 'cn')

    fireEvent.change(input, { target: { value: 'cn tower' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300)
    })

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect((fetchMock.mock.calls[0][1] as RequestInit).signal!.aborted).toBe(true)
  })
})

describe('SearchBox with changing text', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('never picks a result for text the user has since changed', async () => {
    respond({ results: [UNION] })
    const { input, onSelect } = setup()
    await type(input, 'union')

    // Keep typing and press Enter before the next search runs.
    fireEvent.change(input, { target: { value: 'union station hotel' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(onSelect).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('keeps editing after leaving and quickly coming back', async () => {
    respond({ results: [CN_TOWER] })
    const { input } = setup(vi.fn(), 'Union Station')
    await type(input, 'cn')

    fireEvent.blur(input)
    fireEvent.focus(input)
    fireEvent.change(input, { target: { value: 'cn tow' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300)
    })

    expect(input).toHaveValue('cn tow')
    expect(screen.getByRole('listbox')).toBeInTheDocument()
  })

  it('announces how many suggestions there are', async () => {
    respond({ results: [CN_TOWER, UNION] })
    const { input } = setup()

    await type(input, 'cn')

    expect(screen.getByRole('status')).toHaveTextContent('2 suggestions')
  })
})
