import 'maplibre-gl/dist/maplibre-gl.css'
import type { Feature, FeatureCollection, LineString } from 'geojson'
import * as maplibregl from 'maplibre-gl'
// MapLibre works out its worker's address at run time, which the production
// build can't see, so the worker file would be left out. Importing it as a
// URL makes Vite ship it, and MapLibre is told where it is.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState } from 'react'
import type { LngLat } from '../api'
import { INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE_URL } from '../config'
import { exploredColor, routeLayerPosition, type StyleLayer } from '../mapLayers'
import {
  ALTERNATIVE,
  ALTERNATIVE_CASING,
  EXPLORED_OPACITY,
  ROUTE,
  ROUTE_CASING,
  SNAP_LINE,
} from '../mapTheme'
import { type DecodedTrace, EDGE_FEATURE, VISIT_FEATURE } from '../trace'

interface Props {
  origin: LngLat | null
  destination: LngLat | null
  route: LngLat[] | null
  // Other algorithms' routes for the same points, drawn in grey.
  alternatives: LngLat[][]
  // Dashed lines from where each point was asked for to where the route
  // actually starts or ends (the nearest walkable street).
  snapLines: [LngLat, LngLat][]
  // The search's exploration, revealed up to `traceStep` events.
  trace: DecodedTrace | null
  traceStep: number
  routeVisible: boolean
  // Pan here when it changes (after a search result is picked).
  focus: { point: LngLat } | null
  // True when both points are set but no route will arrive (it failed), so
  // the map shows both markers itself.
  showBothPoints: boolean
  onMapClick: (point: LngLat) => void
}

const ROUTE_SOURCE = 'route'
// Wait this long after the route appears (or hides) before dimming (or
// restoring) the explored network.
const DIM_DELAY_MS = 300

// Feature-state updates per frame when catching up after a big jump.
const MAX_STATE_CHANGES_PER_FRAME = 20_000

const ALTERNATIVES_SOURCE = 'alternatives'
const SNAP_SOURCE = 'snap-lines'
const EDGES_SOURCE = 'explored-edges'
const VISITS_SOURCE = 'explored-visits'
const EDGES_LAYER = 'explored-edges'
const VISITS_LAYER = 'explored-visits'

/** An opacity that is `opacity` for features marked shown, and 0 otherwise. */
function whenShown(opacity: number): maplibregl.ExpressionSpecification {
  return ['case', ['boolean', ['feature-state', 'shown'], false], opacity, 0]
}

// Leave room for the directions panel on the left when zooming to a route.
const FIT_PADDING = { top: 80, bottom: 80, left: 420, right: 80 }

function markerElement(className: string): HTMLElement {
  const el = document.createElement('div')
  el.className = className
  return el
}

maplibregl.setWorkerUrl(workerUrl)

/** Draws the map, the two chosen points and the route. Holds no route state itself. */
export function MapView({
  origin,
  destination,
  route,
  alternatives,
  snapLines,
  trace,
  traceStep,
  routeVisible,
  focus,
  showBothPoints,
  onMapClick,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const originMarker = useRef<maplibregl.Marker | null>(null)
  const destinationMarker = useRef<maplibregl.Marker | null>(null)
  const onClickRef = useRef(onMapClick)
  const [styleLoaded, setStyleLoaded] = useState(false)

  // Keep the latest callback without re-registering map listeners.
  useEffect(() => {
    onClickRef.current = onMapClick
  }, [onMapClick])

  useEffect(() => {
    if (!containerRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      attributionControl: { customAttribution: 'Search by <a href="https://photon.komoot.io">Photon</a>' },
    })
    map.addControl(new maplibregl.NavigationControl(), 'bottom-right')
    // The dark style refers to a pattern image it doesn't ship; give MapLibre
    // a transparent stand-in instead of a console warning.
    map.setMissingStyleImageResolver((id) => {
      if (!map.hasImage(id)) map.addImage(id, { width: 1, height: 1, data: new Uint8Array(4) })
    })
    map.on('click', (event) => onClickRef.current([event.lngLat.lng, event.lngLat.lat]))
    // 'style.load' fires once the style is parsed, without waiting for every
    // tile like 'load' does, so a route can be drawn while tiles still stream in.
    map.once('style.load', () => {
      const firstSymbol = routeLayerPosition(map.getStyle().layers as StyleLayer[])
      map.addSource(EDGES_SOURCE, { type: 'geojson', data: emptyLine() })
      map.addSource(VISITS_SOURCE, { type: 'geojson', data: emptyLine() })
      map.addLayer(
        {
          id: EDGES_LAYER,
          type: 'line',
          source: EDGES_SOURCE,
          layout: { 'line-cap': 'round' },
          paint: { 'line-color': exploredColor(1), 'line-width': 1.5, 'line-opacity': whenShown(EXPLORED_OPACITY.playing.edges) },
        },
        firstSymbol,
      )
      map.addLayer(
        {
          id: VISITS_LAYER,
          type: 'circle',
          source: VISITS_SOURCE,
          paint: {
            'circle-color': exploredColor(1),
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 1, 16, 3],
            'circle-opacity': whenShown(EXPLORED_OPACITY.playing.visits),
          },
        },
        firstSymbol,
      )
      map.addSource(ALTERNATIVES_SOURCE, { type: 'geojson', data: emptyLine() })
      map.addLayer(
        {
          id: 'alternatives-casing',
          type: 'line',
          source: ALTERNATIVES_SOURCE,
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': ALTERNATIVE_CASING, 'line-width': 8 },
        },
        firstSymbol,
      )
      map.addLayer(
        {
          id: 'alternatives-line',
          type: 'line',
          source: ALTERNATIVES_SOURCE,
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': ALTERNATIVE, 'line-width': 5 },
        },
        firstSymbol,
      )
      map.addSource(SNAP_SOURCE, { type: 'geojson', data: emptyLine() })
      map.addLayer(
        {
          id: 'snap-lines',
          type: 'line',
          source: SNAP_SOURCE,
          layout: { 'line-cap': 'round' },
          paint: { 'line-color': SNAP_LINE, 'line-width': 2, 'line-dasharray': [0.5, 2] },
        },
        firstSymbol,
      )
      map.addSource(ROUTE_SOURCE, { type: 'geojson', data: emptyLine() })
      map.addLayer(
        {
          id: 'route-casing',
          type: 'line',
          source: ROUTE_SOURCE,
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': ROUTE_CASING, 'line-width': 10 },
        },
        firstSymbol,
      )
      map.addLayer(
        {
          id: 'route-line',
          type: 'line',
          source: ROUTE_SOURCE,
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': ROUTE, 'line-width': 6 },
        },
        firstSymbol,
      )
      setStyleLoaded(true)
    })
    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
      originMarker.current = null
      destinationMarker.current = null
      setStyleLoaded(false)
    }
  }, [])

  useEffect(() => {
    syncMarker(mapRef.current, originMarker, origin, () => new maplibregl.Marker({ element: markerElement('origin-marker') }))
  }, [origin])

  useEffect(() => {
    syncMarker(mapRef.current, destinationMarker, destination, () => new maplibregl.Marker({ element: markerElement('destination-marker') }))
  }, [destination])

  // Read inside the focus effect without re-running it when the points change.
  const bothPointsRef = useRef(false)
  useEffect(() => {
    bothPointsRef.current = origin !== null && destination !== null
  }, [origin, destination])

  useEffect(() => {
    // A route on its way will fit the view to itself, so only pan for the
    // first point.
    const map = mapRef.current
    if (!map || !focus || bothPointsRef.current) return
    map.easeTo({ center: focus.point, zoom: Math.max(map.getZoom(), 15) })
  }, [focus])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !showBothPoints || !origin || !destination) return
    const bounds = new maplibregl.LngLatBounds(origin, origin).extend(destination)
    map.fitBounds(bounds, { padding: fitPadding(map), maxZoom: 16 })
  }, [showBothPoints, origin, destination])

  // How many events are currently shown on the map.
  const shownRef = useRef(0)

  // A new trace: hand all its features to the map once, all hidden.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded) return
    map.removeFeatureState({ source: EDGES_SOURCE })
    map.removeFeatureState({ source: VISITS_SOURCE })
    shownRef.current = 0
    map.getSource<maplibregl.GeoJSONSource>(EDGES_SOURCE)?.setData(trace ? trace.edges : emptyLine())
    map.getSource<maplibregl.GeoJSONSource>(VISITS_SOURCE)?.setData(trace ? trace.visits : emptyLine())
    if (trace) {
      map.setPaintProperty(EDGES_LAYER, 'line-color', exploredColor(trace.steps))
      map.setPaintProperty(VISITS_LAYER, 'circle-color', exploredColor(trace.steps))
    }
  }, [trace, styleLoaded])

  // Each animation step flips the "shown" state of just the features that
  // appeared (or, scrubbing back, disappeared) since the last step. Feature
  // state changes are applied on the main thread without re-tiling the
  // source, unlike filters or data-driven paint changes. A big jump (Skip,
  // or scrubbing far) is spread over several frames, at most
  // MAX_STATE_CHANGES_PER_FRAME changes each, so the page never freezes.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded || !trace) return
    const target = Math.min(traceStep, trace.steps)
    if (target === 0 && shownRef.current > 0) {
      map.removeFeatureState({ source: EDGES_SOURCE })
      map.removeFeatureState({ source: VISITS_SOURCE })
      shownRef.current = 0
      return
    }

    let frame = 0
    const work = () => {
      const from = shownRef.current
      const forward = target > from
      const to = forward
        ? Math.min(target, from + MAX_STATE_CHANGES_PER_FRAME)
        : Math.max(target, from - MAX_STATE_CHANGES_PER_FRAME)
      const [lo, hi] = forward ? [from, to] : [to, from]
      for (let t = lo; t < hi; t++) {
        const kind = trace.featureOf[t]
        if (kind === EDGE_FEATURE) map.setFeatureState({ source: EDGES_SOURCE, id: t }, { shown: forward })
        else if (kind === VISIT_FEATURE) map.setFeatureState({ source: VISITS_SOURCE, id: t }, { shown: forward })
      }
      shownRef.current = to
      if (to !== target) frame = requestAnimationFrame(work)
    }
    work()
    return () => cancelAnimationFrame(frame)
  }, [trace, traceStep, styleLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded) return
    map.getSource<maplibregl.GeoJSONSource>(ALTERNATIVES_SOURCE)?.setData(lines(alternatives))
  }, [alternatives, styleLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded) return
    map.getSource<maplibregl.GeoJSONSource>(SNAP_SOURCE)?.setData(lines(snapLines))
  }, [snapLines, styleLoaded])

  // Once the route is on screen, dim the explored network behind it. (This
  // re-evaluates the layers once, which is fine for an occasional switch,
  // unlike the per-frame updates above.)
  // Applied after a short pause, so dragging the scrubber back and forth
  // across the end doesn't re-evaluate the layers on every crossing.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded) return
    const opacity = routeVisible && route ? EXPLORED_OPACITY.done : EXPLORED_OPACITY.playing
    const timer = setTimeout(() => {
      map.setPaintProperty(EDGES_LAYER, 'line-opacity', whenShown(opacity.edges))
      map.setPaintProperty(VISITS_LAYER, 'circle-opacity', whenShown(opacity.visits))
    }, DIM_DELAY_MS)
    return () => clearTimeout(timer)
  }, [routeVisible, route, styleLoaded])

  // The route line appears once the exploration has played out.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded) return
    const source = map.getSource<maplibregl.GeoJSONSource>(ROUTE_SOURCE)
    source?.setData(route && routeVisible ? line(route) : emptyLine())
  }, [route, routeVisible, styleLoaded])

  // When a new route arrives, frame everything the search will cover, which
  // for Dijkstra or DFS can reach well beyond the route itself.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !route || route.length < 2) return
    const bounds = route.reduce((b, point) => b.extend(point), new maplibregl.LngLatBounds(route[0], route[0]))
    for (const visit of trace?.visits.features ?? []) bounds.extend(visit.geometry.coordinates as LngLat)
    map.fitBounds(bounds, { padding: fitPadding(map), maxZoom: 17 })
  }, [route, trace])

  return <div ref={containerRef} className="map" data-testid="map" />
}

function syncMarker(
  map: maplibregl.Map | null,
  ref: React.RefObject<maplibregl.Marker | null>,
  point: LngLat | null,
  create: () => maplibregl.Marker,
) {
  if (!map) return
  if (point === null) {
    ref.current?.remove()
    ref.current = null
    return
  }
  if (!ref.current) ref.current = create().setLngLat(point).addTo(map)
  else ref.current.setLngLat(point)
}

function fitPadding(map: maplibregl.Map) {
  // On a narrow screen the panel sits on top of the map, not beside it.
  const narrow = map.getContainer().clientWidth < 700
  return narrow ? { top: 200, bottom: 40, left: 40, right: 40 } : FIT_PADDING
}

function line(coordinates: LngLat[]): Feature<LineString> {
  return { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates } }
}

function lines(lineList: LngLat[][]): FeatureCollection {
  return { type: 'FeatureCollection', features: lineList.filter((l) => l.length > 1).map(line) }
}

function emptyLine(): FeatureCollection {
  return { type: 'FeatureCollection', features: [] }
}
