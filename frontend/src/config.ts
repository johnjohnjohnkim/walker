// Map settings. The tile provider is swappable through VITE_MAP_STYLE_URL,
// so moving from OpenFreeMap to MapTiler is a config change, not a code change.

export const MAP_STYLE_URL: string =
  import.meta.env.VITE_MAP_STYLE_URL || 'https://tiles.openfreemap.org/styles/dark'

// Downtown Toronto, roughly King and Bay.
export const INITIAL_CENTER: [number, number] = [-79.3832, 43.6487]
export const INITIAL_ZOOM = 14
