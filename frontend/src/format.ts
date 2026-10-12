// Distance and time in the style Google Maps uses: "850 m", "2.2 km", "26 min", "1 hr 5 min".

export function formatDistance(metres: number): string {
  if (metres < 1000) return `${Math.round(metres)} m`
  return `${(metres / 1000).toFixed(1)} km`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60))
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? `${hours} hr` : `${hours} hr ${rest} min`
}

/** Milliseconds, keeping a useful number of digits: "0.042 ms", "3.8 ms", "142 ms". */
export function formatMs(ms: number): string {
  if (ms < 1) return `${ms.toFixed(3)} ms`
  if (ms < 10) return `${ms.toFixed(1)} ms`
  return `${Math.round(ms)} ms`
}

/** Bytes in decimal units, as the labels say: "512 B", "2.7 KB", "2.7 MB". */
export function formatBytes(bytes: number): string {
  if (bytes < 1000) return `${bytes} B`
  if (bytes < 1_000_000) return `${(bytes / 1000).toFixed(1)} KB`
  return `${(bytes / 1_000_000).toFixed(1)} MB`
}

export function formatCount(n: number): string {
  return n.toLocaleString('en-US')
}
