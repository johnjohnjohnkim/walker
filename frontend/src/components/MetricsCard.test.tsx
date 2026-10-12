import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SearchMetrics } from '../api'
import { MetricsCard } from './MetricsCard'

const METRICS: SearchMetrics = {
  wall_ms: 11.784,
  cpu_ms: 0.042,
  timing_runs: 5,
  peak_memory_bytes: 2673380,
  visited: 16009,
  discovered: 16023,
  frontier_pushes: 18522,
  peak_frontier: 154,
  path_nodes: 168,
  optimal_distance_m: 6340,
  is_shortest: true,
  extra_distance_m: 0,
  extra_distance_pct: 0,
}

function value(label: string) {
  return screen.getByText(label, { selector: 'dt' }).nextElementSibling?.textContent
}

describe('MetricsCard', () => {
  it('shows each measurement readably', () => {
    render(<MetricsCard metrics={METRICS} algorithmName="Dijkstra" distanceM={6340} />)

    expect(screen.getByRole('button', { name: /Search cost · Dijkstra/ })).toHaveAttribute('aria-expanded', 'true')
    expect(value('Time')).toBe('12 ms')
    expect(value('CPU time')).toBe('0.042 ms')
    expect(value('Peak memory')).toBe('2.7 MB')
    expect(value('Explored')).toBe('16,009')
    expect(value('Peak frontier')).toBe('154 nodes')
    expect(value('Route')).toBe('6.3 km · 168 nodes')
    expect(value('vs. shortest')).toBe('shortest')
  })

  it('says how much longer a non-optimal route is', () => {
    render(
      <MetricsCard
        metrics={{ ...METRICS, is_shortest: false, extra_distance_m: 300, extra_distance_pct: 37.5, optimal_distance_m: 800 }}
        algorithmName="DFS"
        distanceM={1100}
      />,
    )

    expect(value('vs. shortest')).toBe('+300 m (37.5%)')
  })

  it('collapses and expands', () => {
    render(<MetricsCard metrics={METRICS} algorithmName="Dijkstra" distanceM={6340} />)
    const header = screen.getByRole('button', { name: /Search cost/ })

    fireEvent.click(header)

    expect(header).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Explored')).not.toBeInTheDocument()
  })

  it('never calls a slightly longer route the shortest', () => {
    render(
      <MetricsCard
        metrics={{ ...METRICS, is_shortest: false, extra_distance_m: 1, extra_distance_pct: 0.02 }}
        algorithmName="A*"
        distanceM={6341}
      />,
    )

    expect(value('vs. shortest')).toBe('+1 m (0.02%)')
  })

  it('shows explanations on request', () => {
    render(<MetricsCard metrics={METRICS} algorithmName="Dijkstra" distanceM={6340} />)
    expect(screen.queryByText(/Most different intersections waiting/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'What do these mean?' }))

    expect(screen.getByText(/Most different intersections waiting/)).toBeInTheDocument()
  })

  it('points out when the server was busy', () => {
    render(
      <MetricsCard metrics={{ ...METRICS, wall_ms: 40, cpu_ms: 12 }} algorithmName="Dijkstra" distanceM={6340} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'What do these mean?' }))

    expect(screen.getByText(/server was busy/)).toBeInTheDocument()
  })
})
