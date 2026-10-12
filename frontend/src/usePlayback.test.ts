import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BASE_DURATION_S, usePlayback } from './usePlayback'

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

describe('usePlayback', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance', 'setTimeout'] })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('plays a whole search in the base duration at 1x', async () => {
    const { result } = renderHook(() => usePlayback(1000, 'search-1'))
    expect(result.current.playing).toBe(true)

    await advance((BASE_DURATION_S * 1000) / 2)
    expect(result.current.step).toBeGreaterThan(400)
    expect(result.current.step).toBeLessThan(600)

    await advance((BASE_DURATION_S * 1000) / 2 + 100)
    expect(result.current.step).toBe(1000)
    expect(result.current.finished).toBe(true)
    expect(result.current.playing).toBe(false)
  })

  it('goes faster at higher speed', async () => {
    const { result } = renderHook(() => usePlayback(1000, 'search-1'))
    act(() => result.current.setSpeed(4))

    await advance((BASE_DURATION_S * 1000) / 4 + 100)

    expect(result.current.finished).toBe(true)
  })

  it('pauses, seeks and skips', async () => {
    const { result } = renderHook(() => usePlayback(1000, 'search-1'))
    act(() => result.current.toggle())
    expect(result.current.playing).toBe(false)

    act(() => result.current.seek(250.4))
    expect(result.current.step).toBe(250)
    await advance(2000)
    expect(result.current.step).toBe(250)

    act(() => result.current.skipToEnd())
    expect(result.current.step).toBe(1000)
  })

  it('replays from the start when play is pressed at the end', async () => {
    const { result } = renderHook(() => usePlayback(1000, 'search-1'))
    act(() => result.current.skipToEnd())

    act(() => result.current.toggle())

    expect(result.current.step).toBe(0)
    expect(result.current.playing).toBe(true)
  })

  it('starts over when a new search arrives', async () => {
    const { result, rerender } = renderHook(({ key }) => usePlayback(1000, key), { initialProps: { key: 'a' } })
    act(() => result.current.skipToEnd())

    rerender({ key: 'b' })

    expect(result.current.step).toBe(0)
    expect(result.current.playing).toBe(true)
  })

  it('does nothing without a trace', () => {
    const { result } = renderHook(() => usePlayback(0, null))

    expect(result.current.playing).toBe(false)
    expect(result.current.finished).toBe(true)
  })
})

describe('usePlayback with reduced motion', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', (query: string) => ({ matches: query.includes('reduce'), media: query }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a new search finished instead of animating it', () => {
    const { result, rerender } = renderHook(({ key }) => usePlayback(1000, key), { initialProps: { key: 'a' } })
    expect(result.current.step).toBe(1000)
    expect(result.current.playing).toBe(false)

    rerender({ key: 'b' })

    expect(result.current.step).toBe(1000)
    expect(result.current.playing).toBe(false)
  })

  it('still plays when asked', () => {
    const { result } = renderHook(() => usePlayback(1000, 'a'))

    act(() => result.current.toggle())

    expect(result.current.step).toBe(0)
    expect(result.current.playing).toBe(true)
  })
})
