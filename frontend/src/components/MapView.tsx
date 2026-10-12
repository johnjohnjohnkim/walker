import 'maplibre-gl/dist/maplibre-gl.css'
import type { Feature, FeatureCollection, LineString } from 'geojson'
import * as maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import type { LngLat } from '../api'
import { INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE_URL } from '../config'
import { exploredColor, routeLayerPosition } from '../mapLayers'
import { type DecodedTrace, EDGE_FEATURE, VISIT_FEATURE } from '../trace'

interface Props {
  origin: LngLat | null
  destination: LngLat | null
  route: LngLat[] | null
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

function originElement(): HTMLElement {
  const el = document.createElement('div')
  el.className = 'origin-marker'
  return el
}

/** Draws the map, the two chosen points and the route. Holds no route state itself. */
export function MapView({
  origin,
  destination,
  route,
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
    map.on('click', (event) => onClickRef.current([event.lngLat.lng, event.lngLat.lat]))
    // 'style.load' fires once the style is parsed, without waiting for every
    // tile like 'load' does, so a route can be drawn while tiles still stream in.
    map.once('style.load', () => {
      const firstSymbol = routeLayerPosition(map.getStyle().layers)
      map.addSource(EDGES_SOURCE, { type: 'geojson', data: emptyLine() })
      map.addSource(VISITS_SOURCE, { type: 'geojson', data: emptyLine() })
      map.addLayer(
        {
          id: EDGES_LAYER,
          type: 'line',
          source: EDGES_SOURCE,
          layout: { 'line-cap': 'round' },
          paint: { 'line-color': exploredColor(1), 'line-width': 1.5, 'line-opacity': whenShown(0.55) },
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
            'circle-opacity': whenShown(0.8),
          },
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
          paint: { 'line-color': '#1967d2', 'line-width': 9 },
        },
        firstSymbol,
      )
      map.addLayer(
        {
          id: 'route-line',
          type: 'line',
          source: ROUTE_SOURCE,
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': '#4285f4', 'line-width': 6 },
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
    syncMarker(mapRef.current, originMarker, origin, () => new maplibregl.Marker({ element: originElement() }))
  }, [origin])

  useEffect(() => {
    syncMarker(mapRef.current, destinationMarker, destination, () => new maplibregl.Marker({ color: '#ea4335' }))
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
  // source, unlike filters or data-driven paint changes, so the cost per
  // frame stays small however big the trace is.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded || !trace) return
    const target = Math.min(traceStep, trace.steps)
    const from = shownRef.current
    if (target === 0 && from > 0) {
      map.removeFeatureState({ source: EDGES_SOURCE })
      map.removeFeatureState({ source: VISITS_SOURCE })
    } else {
      const [lo, hi, shown] = target > from ? [from, target, true] : [target, from, false]
      for (let t = lo; t < hi; t++) {
        const kind = trace.featureOf[t]
        if (kind === EDGE_FEATURE) map.setFeatureState({ source: EDGES_SOURCE, id: t }, { shown })
        else if (kind === VISIT_FEATURE) map.setFeatureState({ source: VISITS_SOURCE, id: t }, { shown })
      }
    }
    shownRef.current = target
  }, [trace, traceStep, styleLoaded])

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

function emptyLine(): FeatureCollection {
  return { type: 'FeatureCollection', features: [] }
}
