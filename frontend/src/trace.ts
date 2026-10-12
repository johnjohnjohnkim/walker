// Turns a search trace from the backend into map features that can be
// revealed step by step. Each feature carries `t`, the index of the event
// that created it, so the map shows step n by filtering on t <= n.

import type { Feature, FeatureCollection, LineString, Point } from 'geojson'
import type { TracePayload } from './api'

export const DISCOVER = 0
export const VISIT = 1
export const DISCOVER_BACKWARD = 2
export const VISIT_BACKWARD = 3

export type Side = 'forward' | 'backward'

// Which map source holds the feature made by each event.
export const NO_FEATURE = 0
export const EDGE_FEATURE = 1
export const VISIT_FEATURE = 2

export interface DecodedTrace {
  // Each discovery: a line from the parent to the newly reached node.
  edges: FeatureCollection<LineString, { t: number; side: Side }>
  // Each visit: a dot where the node was explored.
  visits: FeatureCollection<Point, { t: number; side: Side }>
  steps: number
  visited: number
  truncated: boolean
  // featureOf[t]: which source (if any) has the feature for event t. That
  // feature's id is t, so the map can show or hide it by id.
  featureOf: Uint8Array
}

export function decodeTrace(trace: TracePayload): DecodedTrace {
  const { coordinates, events } = trace
  const edges: Feature<LineString, { t: number; side: Side }>[] = []
  const visits: Feature<Point, { t: number; side: Side }>[] = []
  const featureOf = new Uint8Array(trace.count)

  for (let t = 0; t < trace.count; t++) {
    const code = events[3 * t]
    const node = coordinates[events[3 * t + 1]]
    const parentIndex = events[3 * t + 2]
    const side: Side = code === DISCOVER_BACKWARD || code === VISIT_BACKWARD ? 'backward' : 'forward'

    if (code === VISIT || code === VISIT_BACKWARD) {
      featureOf[t] = VISIT_FEATURE
      visits.push({ type: 'Feature', id: t, properties: { t, side }, geometry: { type: 'Point', coordinates: node } })
    } else if (parentIndex >= 0) {
      // A straight line: drawing each street's real curve would make the
      // trace several times larger, and the route itself is drawn exactly.
      featureOf[t] = EDGE_FEATURE
      const parent = coordinates[parentIndex]
      edges.push({
        type: 'Feature',
        id: t,
        properties: { t, side },
        geometry: { type: 'LineString', coordinates: [parent, node] },
      })
    }
  }

  return {
    edges: { type: 'FeatureCollection', features: edges },
    visits: { type: 'FeatureCollection', features: visits },
    steps: trace.count,
    visited: visits.length,
    truncated: trace.truncated,
    featureOf,
  }
}

/** How many visits happen in the first `step` events, for the progress label. */
export function visitsUpTo(decoded: DecodedTrace, step: number): number {
  // Visits are in event order, so binary-search the last one at or before step.
  const features = decoded.visits.features
  let lo = 0
  let hi = features.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (features[mid].properties.t < step) lo = mid + 1
    else hi = mid
  }
  return lo
}
