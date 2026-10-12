import 'maplibre-gl/dist/maplibre-gl.css'
import type { Feature, FeatureCollection, LineString } from 'geojson'
import * as maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import type { LngLat } from '../api'
import { INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE_URL } from '../config'
import { routeLayerPosition } from '../mapLayers'

interface Props {
  origin: LngLat | null
  destination: LngLat | null
  route: LngLat[] | null
  onMapClick: (point: LngLat) => void
}

const ROUTE_SOURCE = 'route'

// Leave room for the directions panel on the left when zooming to a route.
const FIT_PADDING = { top: 80, bottom: 80, left: 420, right: 80 }

function originElement(): HTMLElement {
  const el = document.createElement('div')
  el.className = 'origin-marker'
  return el
}

/** Draws the map, the two chosen points and the route. Holds no route state itself. */
export function MapView({ origin, destination, route, onMapClick }: Props) {
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
    })
    map.addControl(new maplibregl.NavigationControl(), 'bottom-right')
    map.on('click', (event) => onClickRef.current([event.lngLat.lng, event.lngLat.lat]))
    // 'style.load' fires once the style is parsed, without waiting for every
    // tile like 'load' does, so a route can be drawn while tiles still stream in.
    map.once('style.load', () => {
      const firstSymbol = routeLayerPosition(map.getStyle().layers)
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

  useEffect(() => {
    const map = mapRef.current
    if (!map || !styleLoaded) return
    const source = map.getSource<maplibregl.GeoJSONSource>(ROUTE_SOURCE)
    source?.setData(route ? line(route) : emptyLine())

    if (route && route.length > 1) {
      const bounds = route.reduce(
        (b, point) => b.extend(point),
        new maplibregl.LngLatBounds(route[0], route[0]),
      )
      map.fitBounds(bounds, { padding: fitPadding(map), maxZoom: 17 })
    }
  }, [route, styleLoaded])

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
