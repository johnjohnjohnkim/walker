import type { ExpressionSpecification } from 'maplibre-gl'
import { EXPLORED_BACKWARD, EXPLORED_FORWARD } from './mapTheme'

export interface StyleLayer {
  id: string
  type: string
  'source-layer'?: string
}

// Map layers a route must never be hidden under.
function covers(layer: StyleLayer): boolean {
  return (
    layer.type === 'fill-extrusion' ||
    layer['source-layer'] === 'transportation' ||
    layer['source-layer'] === 'building'
  )
}

/**
 * The layer id to insert route layers before: the first label layer after
 * the style's last road or building layer. The route then sits on top of
 * everything it could be hidden by (some styles draw roads after their first
 * labels, others draw 3D buildings last) but under the street names and
 * place labels that follow, which stay readable.
 */
export function routeLayerPosition(layers: StyleLayer[]): string | undefined {
  let lastCovering = -1
  layers.forEach((layer, i) => {
    if (covers(layer)) lastCovering = i
  })
  return layers.find((layer, i) => i > lastCovering && layer.type === 'symbol')?.id
}

// Each half of the search fades from grey (explored early) to white
// (explored late), so the order of exploration shows even in a still
// picture. The backward half of a bidirectional search is warmer.
export function exploredColor(steps: number): ExpressionSpecification {
  const last = Math.max(steps, 1)
  return [
    'match',
    ['get', 'side'],
    'backward',
    ['interpolate', ['linear'], ['get', 't'], 0, EXPLORED_BACKWARD[0], last, EXPLORED_BACKWARD[1]],
    ['interpolate', ['linear'], ['get', 't'], 0, EXPLORED_FORWARD[0], last, EXPLORED_FORWARD[1]],
  ]
}

