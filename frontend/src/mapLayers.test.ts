import { describe, expect, it } from 'vitest'
import { exploredColor, routeLayerPosition } from './mapLayers'

describe('routeLayerPosition', () => {
  it('goes under the first label layer after the roads', () => {
    const layers = [
      { id: 'water', type: 'fill', 'source-layer': 'water' },
      { id: 'roads', type: 'line', 'source-layer': 'transportation' },
      { id: 'street-names', type: 'symbol', 'source-layer': 'transportation_name' },
    ]
    expect(routeLayerPosition(layers)).toBe('street-names')
  })

  it('goes above roads drawn after the first labels', () => {
    const layers = [
      { id: 'water', type: 'fill', 'source-layer': 'water' },
      { id: 'water-names', type: 'symbol', 'source-layer': 'water_name' },
      { id: 'roads', type: 'line', 'source-layer': 'transportation' },
      { id: 'street-names', type: 'symbol', 'source-layer': 'transportation_name' },
    ]
    expect(routeLayerPosition(layers)).toBe('street-names')
  })

  it('stays under street names even if boundaries are drawn after them', () => {
    // The dark style's order: road names, then more lines (boundaries), then places.
    const layers = [
      { id: 'roads', type: 'line', 'source-layer': 'transportation' },
      { id: 'street-names', type: 'symbol', 'source-layer': 'transportation_name' },
      { id: 'boundary', type: 'line', 'source-layer': 'boundary' },
      { id: 'places', type: 'symbol', 'source-layer': 'place' },
    ]
    expect(routeLayerPosition(layers)).toBe('street-names')
  })

  it('goes above 3D buildings even when labels come before them', () => {
    const layers = [
      { id: 'roads', type: 'line', 'source-layer': 'transportation' },
      { id: 'water-names', type: 'symbol', 'source-layer': 'water_name' },
      { id: 'building-3d', type: 'fill-extrusion', 'source-layer': 'building' },
      { id: 'street-names', type: 'symbol', 'source-layer': 'transportation_name' },
    ]
    expect(routeLayerPosition(layers)).toBe('street-names')
  })

  it('goes on top when there are no labels above the buildings', () => {
    expect(routeLayerPosition([{ id: 'building-3d', type: 'fill-extrusion' }])).toBeUndefined()
  })
})

describe('exploredColor', () => {
  it('fades each side from grey to white over the whole search', () => {
    const expression = exploredColor(500) as unknown[]
    expect(expression[0]).toBe('match')
    expect(expression[4]).toEqual(['interpolate', ['linear'], ['get', 't'], 0, '#6e737b', 500, '#ffffff'])
  })

  it('never uses an empty range', () => {
    expect((exploredColor(0) as unknown[])[4]).toContain(1)
  })
})
