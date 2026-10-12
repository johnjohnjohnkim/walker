import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AlgorithmInfo, RouteResponse } from '../api'
import type { ComparisonEntry } from '../useComparison'
import { ComparisonTable } from './ComparisonTable'

function algorithm(id: string, name: string, implemented = true): AlgorithmInfo {
  return { id, name, description: '', guarantee: 'shortest', uses_lengths: true, bidirectional: false, implemented }
}

function done(distance: number, visited: number, wallMs: number, extraPct = 0): ComparisonEntry {
  return {
    status: 'done',
    route: {
      route: { coordinates: [], distance_m: distance, duration_s: 0, nodes: 0 },
      metrics: { visited, wall_ms: wallMs, is_shortest: extraPct === 0, extra_distance_pct: extraPct },
    } as unknown as RouteResponse,
  }
}

const ALGORITHMS = [algorithm('dijkstra', 'Dijkstra'), algorithm('bfs', 'BFS'), algorithm('dfs', 'DFS', false)]

function row(name: string) {
  return screen.getByRole('rowheader', { name: new RegExp(name) }).closest('tr')!
}

describe('ComparisonTable', () => {
  it('lists each algorithm, marking the best and the longer routes', () => {
    render(
      <ComparisonTable
        algorithms={ALGORITHMS}
        entries={{ dijkstra: done(2000, 900, 4), bfs: done(2300, 600, 2, 15) }}
        selected="dijkstra"
        onSelect={() => {}}
        onClose={() => {}}
      />,
    )

    expect(within(row('Dijkstra')).getByText('2.0 km')).toBeInTheDocument()
    expect(within(row('BFS')).getByText(/\+15%/)).toBeInTheDocument()
    expect(within(row('BFS')).getByText('600')).toHaveClass('compare__best')
    expect(within(row('Dijkstra')).getByText('900')).not.toHaveClass('compare__best')
    expect(within(row('DFS')).getByText('not written yet')).toBeInTheDocument()
    expect(row('Dijkstra')).toHaveClass('compare__row--selected')
  })

  it('shows running and failed algorithms', () => {
    render(
      <ComparisonTable
        algorithms={ALGORITHMS}
        entries={{ dijkstra: { status: 'loading' }, bfs: { status: 'error', message: 'It crashed.' } }}
        selected="dijkstra"
        onSelect={() => {}}
        onClose={() => {}}
      />,
    )

    expect(within(row('Dijkstra')).getByText('Running…')).toBeInTheDocument()
    expect(within(row('BFS')).getByText('It crashed.')).toBeInTheDocument()
  })

  it('picks an algorithm and closes', () => {
    const onSelect = vi.fn()
    const onClose = vi.fn()
    render(
      <ComparisonTable
        algorithms={ALGORITHMS}
        entries={{ dijkstra: done(2000, 900, 4), bfs: done(2300, 600, 2, 15) }}
        selected="dijkstra"
        onSelect={onSelect}
        onClose={onClose}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'BFS' }))
    fireEvent.click(screen.getByRole('button', { name: 'Close comparison' }))

    expect(onSelect).toHaveBeenCalledWith('bfs')
    expect(onClose).toHaveBeenCalled()
  })
})
