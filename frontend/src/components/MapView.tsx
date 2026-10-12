import 'maplibre-gl/dist/maplibre-gl.css'
import * as maplibregl from 'maplibre-gl'
import { useEffect, useRef } from 'react'
import { INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE_URL } from '../config'

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
    })
    map.addControl(new maplibregl.NavigationControl(), 'bottom-right')

    return () => map.remove()
  }, [])

  return <div ref={containerRef} className="map" data-testid="map" />
}
