import { memo, useState } from 'react'
import type { SearchMetrics } from '../api'
import { formatBytes, formatCount, formatDistance, formatMs } from '../format'

interface Props {
  metrics: SearchMetrics
  algorithmName: string
  distanceM: number
}

/** What the last search cost: time, memory and work, collapsible. */
export const MetricsCard = memo(function MetricsCard({ metrics, algorithmName, distanceM }: Props) {
  // Open by default, except on small screens where it would cover the map.
  const [open, setOpen] = useState(() => !window.matchMedia?.('(max-width: 700px)').matches)
  const [explain, setExplain] = useState(false)

  const busy = metrics.wall_ms > 1.5 * metrics.cpu_ms && metrics.wall_ms - metrics.cpu_ms > 1
  const runs = `${metrics.timing_runs} run${metrics.timing_runs === 1 ? '' : 's'}`
  const rows: [string, string, string][] = [
    ['Time', formatMs(metrics.wall_ms), `Wall-clock time of the search alone (median of ${runs}).`],
    [
      'CPU time',
      formatMs(metrics.cpu_ms),
      busy
        ? 'Processor time. Much lower than the wall-clock time, so the server was busy with other work.'
        : 'Processor time spent by the search (same runs).',
    ],
    metrics.peak_memory_bytes === null
      ? ['Peak memory', 'not measured', 'This search is too large to measure memory quickly (it slows Python down several times).']
      : ['Peak memory', formatBytes(metrics.peak_memory_bytes), 'Most memory the search allocated at once.'],
    ['Explored', formatCount(metrics.visited), 'Intersections taken off the frontier and expanded.'],
    ['Reached', formatCount(metrics.discovered), 'Different intersections ever added to the frontier.'],
    [
      'Frontier pushes',
      formatCount(metrics.frontier_pushes),
      'Additions to the frontier, counting a node again when a better route to it is found.',
    ],
    [
      'Peak frontier',
      `${formatCount(metrics.peak_frontier)} nodes`,
      'Most different intersections waiting at once (both halves, for bidirectional). A queue or heap that keeps outdated entries holds more.',
    ],
    ['Route', `${formatDistance(distanceM)} · ${formatCount(metrics.path_nodes)} nodes`, 'Length and intersections on the route.'],
    [
      'vs. shortest',
      metrics.is_shortest
        ? 'shortest'
        : `+${formatDistance(metrics.extra_distance_m)} (${metrics.extra_distance_pct}%)`,
      `The shortest walking route is ${formatDistance(metrics.optimal_distance_m)}.`,
    ],
  ]
  return (
    <section className="metrics" aria-label="Search cost">
      <button type="button" className="metrics__header" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span>Search cost · {algorithmName}</span>
        <span className="metrics__chevron" aria-hidden="true">
          {open ? '▴' : '▾'}
        </span>
      </button>
      {open && (
        <dl className={`metrics__list${explain ? ' metrics__list--explained' : ''}`}>
          {rows.map(([label, value, help]) => (
            <div key={label} className="metrics__row">
              <dt>{label}</dt>
              <dd>
                {value}
                {explain && <span className="metrics__help">{help}</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {open && (
        <p className="metrics__note">
          Times are for the search itself on the server, not the network.{' '}
          <button type="button" className="metrics__explain" aria-pressed={explain} onClick={() => setExplain(!explain)}>
            {explain ? 'Hide explanations' : 'What do these mean?'}
          </button>
        </p>
      )}
    </section>
  )
})
