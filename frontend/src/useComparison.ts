import { useEffect, useMemo, useState } from 'react'
import { ApiError, fetchRoute, type LngLat, type RouteResponse } from './api'

export type ComparisonEntry =
  | { status: 'loading' }
  | { status: 'done'; route: RouteResponse }
  | { status: 'error'; message: string }

interface Comparison {
  key: string
  entries: Record<string, ComparisonEntry>
}

/**
 * Runs every algorithm in `ids` between the two points (without traces), one
 * after another, when `enabled`, and returns each one's result. Results belong to a pair of
 * points: as soon as either point changes they are dropped.
 */
export function useComparison(
  origin: LngLat | null,
  destination: LngLat | null,
  ids: string[],
  enabled: boolean,
): Record<string, ComparisonEntry> | null {
  const key = origin && destination ? `${origin.join(',')}|${destination.join(',')}|${ids.join(',')}` : null
  const [comparison, setComparison] = useState<Comparison | null>(null)

  useEffect(() => {
    if (!enabled || key === null || origin === null || destination === null) return
    const controller = new AbortController()

    // One at a time: the server times each algorithm, and searches running
    // side by side would slow each other down and spoil the numbers.
    const runAll = async () => {
      for (const id of ids) {
        let entry: ComparisonEntry
        try {
          entry = { status: 'done', route: await fetchRoute(origin, destination, id, controller.signal, { trace: false }) }
        } catch (error: unknown) {
          if (controller.signal.aborted) return
          entry = { status: 'error', message: error instanceof ApiError ? error.message : 'Could not reach the server.' }
        }
        if (controller.signal.aborted) return
        setComparison((current) => ({
          key,
          entries: { ...(current?.key === key ? current.entries : {}), [id]: entry },
        }))
      }
    }
    void runAll()
    return () => controller.abort()
    // `key` captures origin, destination and ids.
  }, [enabled, key]) // eslint-disable-line react-hooks/exhaustive-deps

  // Memoized so the map isn't handed "new" routes on every animation frame.
  return useMemo(() => {
    if (!enabled || key === null) return null
    // Anything without an answer yet for these points is still running.
    const answered = comparison?.key === key ? comparison.entries : {}
    return Object.fromEntries(ids.map((id) => [id, answered[id] ?? { status: 'loading' }]))
    // `key` captures ids.
  }, [enabled, key, comparison]) // eslint-disable-line react-hooks/exhaustive-deps
}
