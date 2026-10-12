import { useCallback, useEffect, useRef, useState } from 'react'

// At 1x, a whole search plays in this long, however many steps it has, so a
// small search isn't over in a blink and a huge one doesn't take minutes.
export const BASE_DURATION_S = 8

export const SPEEDS = [0.5, 1, 2, 4] as const

export interface Playback {
  // How many events are shown, from 0 to `steps`.
  step: number
  playing: boolean
  speed: number
  finished: boolean
  toggle: () => void
  seek: (step: number) => void
  skipToEnd: () => void
  setSpeed: (speed: number) => void
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
}

/**
 * Plays `steps` events over time. Starts from the beginning and plays
 * whenever `key` changes (a new search arrived). For people who have asked
 * their system for less motion, a new search is shown finished instead, and
 * they can press play to watch it.
 */
export function usePlayback(steps: number, key: unknown): Playback {
  const reduceMotion = prefersReducedMotion()
  const [step, setStep] = useState(reduceMotion ? steps : 0)
  const [playing, setPlaying] = useState(steps > 0 && !reduceMotion)
  const [speed, setSpeed] = useState(1)
  // The exact (fractional) position, read by the animation loop and moved by
  // seek and skip. `step` is its whole-number copy for rendering.
  const stepRef = useRef(0)

  // A new search: start over and play. Done while rendering, React's
  // recommended way to reset state when an input changes.
  const [currentKey, setCurrentKey] = useState(key)
  if (key !== currentKey) {
    setCurrentKey(key)
    setStep(reduceMotion ? steps : 0)
    setPlaying(steps > 0 && !reduceMotion)
  }
  useEffect(() => {
    stepRef.current = reduceMotion ? steps : 0
    // Only when a new search arrives; reduceMotion and steps come with it.
  }, [key]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!playing) return
    let frame = 0
    let last = performance.now()
    const perSecond = (steps / BASE_DURATION_S) * speed

    const tick = (now: number) => {
      const next = Math.min(steps, stepRef.current + ((now - last) / 1000) * perSecond)
      last = now
      stepRef.current = next
      setStep(Math.floor(next))
      if (next >= steps) {
        setPlaying(false)
        return
      }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, speed, steps])

  const seek = useCallback(
    (target: number) => {
      const clamped = Math.max(0, Math.min(steps, Math.round(target)))
      stepRef.current = clamped
      setStep(clamped)
    },
    [steps],
  )

  const toggle = useCallback(() => {
    // Pressing play at the end starts again from the beginning.
    if (!playing && stepRef.current >= steps) {
      stepRef.current = 0
      setStep(0)
    }
    setPlaying(!playing)
  }, [playing, steps])

  const skipToEnd = useCallback(() => {
    stepRef.current = steps
    setStep(steps)
    setPlaying(false)
  }, [steps])

  return { step, playing, speed, finished: step >= steps, toggle, seek, skipToEnd, setSpeed }
}
