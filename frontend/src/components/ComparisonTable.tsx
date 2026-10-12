import { memo } from 'react'
import type { AlgorithmInfo } from '../api'
import { formatCount, formatDistance, formatMs } from '../format'
import type { ComparisonEntry } from '../useComparison'

interface Props {
  algorithms: AlgorithmInfo[]
  entries: Record<string, ComparisonEntry>
  selected: string
  onSelect: (id: string) => void
  onClose: () => void
}

/** Every algorithm's result for the same two points, side by side. */
export const ComparisonTable = memo(function ComparisonTable({
  algorithms,
  entries,
  selected,
  onSelect,
  onClose,
}: Props) {
  const done = Object.values(entries).flatMap((e) => (e.status === 'done' ? [e.route] : []))
  const fewestExplored = done.length > 1 ? Math.min(...done.map((r) => r.metrics.visited)) : null
  const fastest = done.length > 1 ? Math.min(...done.map((r) => r.metrics.wall_ms)) : null

  return (
    <section className="compare" id="comparison" aria-label="Algorithm comparison">
      <div className="compare__header">
        <h2 className="compare__title">Compare algorithms</h2>
        <button type="button" className="compare__close" onClick={onClose} aria-label="Close comparison">
          ×
        </button>
      </div>
      <table className="compare__table">
        <thead>
          <tr>
            <th scope="col">Algorithm</th>
            <th scope="col">Length</th>
            <th scope="col">Explored</th>
            <th scope="col">Time</th>
          </tr>
        </thead>
        <tbody>
          {algorithms.map((algorithm) => {
            const entry = entries[algorithm.id]
            const isSelected = algorithm.id === selected
            if (!algorithm.implemented || !entry) {
              return (
                <tr key={algorithm.id} className="compare__row compare__row--missing">
                  <th scope="row">{algorithm.name}</th>
                  <td colSpan={3}>not written yet</td>
                </tr>
              )
            }
            if (entry.status !== 'done') {
              return (
                <tr key={algorithm.id} className="compare__row">
                  <th scope="row">{algorithm.name}</th>
                  <td colSpan={3} className={entry.status === 'error' ? 'compare__error' : undefined}>
                    {entry.status === 'loading' ? 'Running…' : entry.message}
                  </td>
                </tr>
              )
            }
            const m = entry.route.metrics
            return (
              <tr key={algorithm.id} className={`compare__row${isSelected ? ' compare__row--selected' : ''}`}>
                <th scope="row">
                  <button
                    type="button"
                    className="compare__pick"
                    aria-pressed={isSelected}
                    onClick={() => onSelect(algorithm.id)}
                  >
                    {algorithm.name}
                  </button>
                </th>
                <td>
                  {formatDistance(entry.route.route.distance_m)}
                  {!m.is_shortest && <span className="compare__extra"> +{m.extra_distance_pct}%</span>}
                </td>
                <td className={m.visited === fewestExplored ? 'compare__best' : undefined}>{formatCount(m.visited)}</td>
                <td className={m.wall_ms === fastest ? 'compare__best' : undefined}>{formatMs(m.wall_ms)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="compare__note">
        {done.length > 1
          ? "Grey lines on the map are the other algorithms' routes. Pick one to watch it."
          : 'Write more algorithms to compare them here.'}
      </p>
    </section>
  )
})
