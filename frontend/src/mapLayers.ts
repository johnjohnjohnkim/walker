import type { ExpressionSpecification } from 'maplibre-gl'

/**
 * The layer id to insert route layers before: the first label layer above the
 * last 3D building layer. Route lines then sit on top of buildings (which
 * would otherwise hide them) but under street names, which stay readable.
 */
export function routeLayerPosition(layers: { id: string; type: string }[]): string | undefined {
  let lastExtrusion = -1
  layers.forEach((layer, i) => {
    if (layer.type === 'fill-extrusion') lastExtrusion = i
  })
  return layers.find((layer, i) => i > lastExtrusion && layer.type === 'symbol')?.id
}

// The forward search in purple, the backward one (bidirectional) in orange,
// each going from light (explored early) to dark (explored late), so the
// order of exploration shows even in a still picture.
export function exploredColor(steps: number): ExpressionSpecification {
  const last = Math.max(steps, 1)
  return [
    'match',
    ['get', 'side'],
    'backward',
    ['interpolate', ['linear'], ['get', 't'], 0, '#fdd663', last, '#c5221f'],
    ['interpolate', ['linear'], ['get', 't'], 0, '#d7aefb', last, '#5b1f99'],
  ]
}

