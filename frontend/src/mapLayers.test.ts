import { describe, expect, it } from 'vitest'
import { routeLayerPosition } from './mapLayers'

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
