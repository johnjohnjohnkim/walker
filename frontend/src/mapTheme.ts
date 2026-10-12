// Map colours for the Night survey theme. The interface's colours live in
// index.css; these are the ones MapLibre paints.

// Western University purple, reserved for the route.
export const ROUTE = '#4f2683'
// A thin white edge keeps the purple readable against the black map.
export const ROUTE_CASING = '#ffffff'

// Other algorithms' routes in the comparison.
// Lighter than the dark map's own road greys, so it doesn't read as a road.
export const ALTERNATIVE = '#8a8a8a'
export const ALTERNATIVE_CASING = '#000000'

// Dotted line from a requested point to where the route starts.
export const SNAP_LINE = '#bdbdbd'

// The exploration fades from grey (explored early) to white (explored late).
// The backward half of a bidirectional search is a warm white, so the two
// halves stay distinguishable without adding a hue.
export const EXPLORED_FORWARD: [string, string] = ['#6e737b', '#ffffff']
export const EXPLORED_BACKWARD: [string, string] = ['#7d6f60', '#fff1e0']

// How strongly the explored network shows while the search plays, and once
// the route is on screen (dimmed so the route stands out).
export const EXPLORED_OPACITY = { playing: { edges: 0.55, visits: 0.8 }, done: { edges: 0.28, visits: 0.4 } }
