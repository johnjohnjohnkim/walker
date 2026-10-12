import { describe, expect, it } from 'vitest'
import { formatDistance, formatDuration } from './format'

describe('formatDistance', () => {
  it.each([
    [0, '0 m'],
    [850.4, '850 m'],
    [999.4, '999 m'],
    [1000, '1.0 km'],
    [2223.7, '2.2 km'],
  ])('%d m -> %s', (metres, expected) => {
    expect(formatDistance(metres)).toBe(expected)
  })
})

describe('formatDuration', () => {
  it.each([
    [0, '1 min'],
    [89, '1 min'],
    [1588, '26 min'],
    [3600, '1 hr'],
    [3900, '1 hr 5 min'],
  ])('%d s -> %s', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected)
  })
})
