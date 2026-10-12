import { describe, expect, it } from 'vitest'
import type { TracePayload } from './api'
import { decodeTrace, visitsUpTo } from './trace'

// Discover 0, visit 0, discover 1 from 0, discover 2 backward (root),
// visit 2 backward, discover 1 backward from 2.
const PAYLOAD: TracePayload = {
  coordinates: [
    [-79.38, 43.65],
    [-79.37, 43.65],
    [-79.36, 43.65],
  ],
  events: [0, 0, -1, 1, 0, -1, 0, 1, 0, 2, 2, -1, 3, 2, -1, 2, 1, 2],
  count: 6,
  truncated: false,
}

describe('decodeTrace', () => {
  it('turns discoveries into lines from the parent and visits into dots', () => {
    const decoded = decodeTrace(PAYLOAD)

    expect(decoded.steps).toBe(6)
    expect(decoded.edges.features.map((f) => [f.properties.t, f.properties.side, f.geometry.coordinates])).toEqual([
      [2, 'forward', [[-79.38, 43.65], [-79.37, 43.65]]],
      [5, 'backward', [[-79.36, 43.65], [-79.37, 43.65]]],
    ])
    expect(decoded.visits.features.map((f) => [f.properties.t, f.properties.side])).toEqual([
      [1, 'forward'],
      [4, 'backward'],
    ])
    expect(decoded.visited).toBe(2)
  })

  it('draws nothing for the starting points themselves', () => {
    const decoded = decodeTrace(PAYLOAD)

    // Events 0 and 3 are the roots (no parent): no line for them.
    expect(decoded.edges.features.map((f) => f.properties.t)).not.toContain(0)
    expect(decoded.edges.features.map((f) => f.properties.t)).not.toContain(3)
  })

  it('handles an empty trace', () => {
    const decoded = decodeTrace({ coordinates: [], events: [], count: 0, truncated: false })

    expect(decoded.steps).toBe(0)
    expect(decoded.visits.features).toEqual([])
  })
})

describe('visitsUpTo', () => {
  it('counts visits among the first n events', () => {
    const decoded = decodeTrace(PAYLOAD)

    expect([0, 1, 2, 4, 5, 6].map((n) => visitsUpTo(decoded, n))).toEqual([0, 0, 1, 1, 2, 2])
  })
})
