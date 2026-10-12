import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { decodeTrace } from '../trace'
import type { Playback } from '../usePlayback'
import { PlaybackBar } from './PlaybackBar'

// Discover 0, visit 0, discover 1, visit 1: two visits in the sample.
const trace = decodeTrace({
  coordinates: [
    [0, 0],
    [1, 0],
  ],
  events: [0, 0, -1, 1, 0, -1, 0, 1, 0, 1, 1, -1],
  count: 4,
  stride: 3,
  total: 12,
  truncated: false,
})

function playback(step: number): Playback {
  const noop = () => {}
  return { step, playing: true, speed: 1, finished: step >= 4, toggle: noop, seek: noop, skipToEnd: noop, setSpeed: noop }
}

describe('PlaybackBar', () => {
  it('scales a sampled trace up to the real number explored', () => {
    render(<PlaybackBar trace={trace} playback={playback(2)} algorithmName="Dijkstra" totalVisited={6} />)

    // One of the sample's two visits shown = half of the real 6.
    expect(screen.getByText(/Dijkstra: 3 \/ 6 explored/)).toBeInTheDocument()
    expect(screen.getByText(/showing every 3rd step/)).toBeInTheDocument()
  })

  it('shows the exact total at the end', () => {
    render(<PlaybackBar trace={trace} playback={playback(4)} algorithmName="Dijkstra" totalVisited={6} />)

    expect(screen.getByText(/Dijkstra: 6 \/ 6 explored/)).toBeInTheDocument()
  })
})
