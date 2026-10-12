import { describe, expect, it } from 'vitest'
import { exploredColor, routeLayerPosition } from './mapLayers'

describe('routeLayerPosition', () => {
  it('goes under the first label layer', () => {
    const layers = [
      { id: 'water', type: 'fill' },
      { id: 'roads', type: 'line' },
      { id: 'street-names', type: 'symbol' },
    ]
    expect(routeLayerPosition(layers)).toBe('street-names')
  })

  it('goes above 3D buildings even when labels come before them', () => {
    const layers = [
      { id: 'roads', type: 'line' },
      { id: 'water-names', type: 'symbol' },
      { id: 'building-3d', type: 'fill-extrusion' },
      { id: 'street-names', type: 'symbol' },
    ]
    expect(routeLayerPosition(layers)).toBe('street-names')
  })

  it('goes on top when there are no labels above the buildings', () => {
    expect(routeLayerPosition([{ id: 'building-3d', type: 'fill-extrusion' }])).toBeUndefined()
  })
})

describe('exploredColor', () => {
  it('fades each side from light to dark over the whole search', () => {
    const expression = exploredColor(500) as unknown[]
    expect(expression[0]).toBe('match')
    expect(expression[4]).toEqual(['interpolate', ['linear'], ['get', 't'], 0, '#d7aefb', 500, '#5b1f99'])
  })

  it('never uses an empty range', () => {
    expect((exploredColor(0) as unknown[])[4]).toContain(1)
  })
})
