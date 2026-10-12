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
