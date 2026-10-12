"""Distances on the Earth and nearest-node lookup.

`NodeIndex` buckets nodes into a grid of square cells roughly `cell_m` metres
across, then searches outward ring by ring from the query's cell. That turns
"which of 16,000 nodes is closest?" into checking a handful of cells.
"""

from __future__ import annotations

import math
from collections import defaultdict

from .graph import WalkGraph

EARTH_RADIUS_M = 6_371_008.8
METRES_PER_DEGREE_LAT = math.pi * EARTH_RADIUS_M / 180


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in metres between two (lon, lat) points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


class NodeIndex:
    """Finds the graph node nearest to a (lon, lat) point."""

    def __init__(self, graph: WalkGraph, cell_m: float = 100.0) -> None:
        if graph.node_count == 0:
            raise ValueError("cannot index an empty graph")
        self.graph = graph
        self.cell_m = cell_m

        # Size cells in degrees so they are about cell_m on each side at the
        # graph's latitude. Over a single city the error from using one
        # latitude is well under 1%.
        mid_lat = (min(graph.lat) + max(graph.lat)) / 2
        self._cell_lat = cell_m / METRES_PER_DEGREE_LAT
        self._cell_lon = cell_m / (METRES_PER_DEGREE_LAT * math.cos(math.radians(mid_lat)))

        self._cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        for node in range(graph.node_count):
            self._cells[self._cell_of(graph.lon[node], graph.lat[node])].append(node)

        rows = [r for r, _ in self._cells]
        cols = [c for _, c in self._cells]
        self._row_range = (min(rows), max(rows))
        self._col_range = (min(cols), max(cols))

    def _cell_of(self, lon: float, lat: float) -> tuple[int, int]:
        return math.floor(lat / self._cell_lat), math.floor(lon / self._cell_lon)

    def nearest(self, lon: float, lat: float, max_distance_m: float | None = None) -> tuple[int, float] | None:
        """Return (node, distance_m) for the closest node, or None.

        None means no node lies within `max_distance_m` (when given).
        Raises ValueError for coordinates that aren't finite numbers.
        """
        if not (math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError(f"coordinates must be finite, got ({lon}, {lat})")
        row, col = self._cell_of(lon, lat)
        best_node, best_dist = -1, math.inf

        # Every point outside the square of rings 0..r is at least r cells
        # (r * cell_m metres) from the query, so once the best distance found
        # is within that, nothing further out can beat it. The 0.99 margin
        # covers cells being slightly narrower away from the middle latitude.
        # Rings closer than the nearest occupied row or column are empty, so a
        # query far outside the map starts at the map's edge.
        (rmin, rmax), (cmin, cmax) = self._row_range, self._col_range
        ring = max(0, rmin - row, row - rmax, cmin - col, col - cmax)
        while True:
            for cell in self._ring_cells(row, col, ring):
                for node in self._cells.get(cell, ()):
                    d = haversine_m(lon, lat, self.graph.lon[node], self.graph.lat[node])
                    if d < best_dist:
                        best_node, best_dist = node, d

            searched_m = ring * self.cell_m * 0.99
            if best_dist <= searched_m:
                break
            if max_distance_m is not None and searched_m > max_distance_m:
                break
            if self._beyond_grid(row, col, ring):
                break
            ring += 1

        if best_node < 0 or (max_distance_m is not None and best_dist > max_distance_m):
            return None
        return best_node, best_dist

    def _beyond_grid(self, row: int, col: int, ring: int) -> bool:
        """True once the searched square covers every occupied cell."""
        (rmin, rmax), (cmin, cmax) = self._row_range, self._col_range
        return row - ring <= rmin and row + ring >= rmax and col - ring <= cmin and col + ring >= cmax

    def _ring_cells(self, row: int, col: int, ring: int):
        """The cells on the square ring `ring` steps out, clipped to the
        occupied grid. Clipping keeps a far-away query from walking millions
        of empty cells."""
        if ring == 0:
            yield row, col
            return
        (rmin, rmax), (cmin, cmax) = self._row_range, self._col_range
        cols = range(max(col - ring, cmin), min(col + ring, cmax) + 1)
        for r in (row - ring, row + ring):
            if rmin <= r <= rmax:
                for c in cols:
                    yield r, c
        rows = range(max(row - ring + 1, rmin), min(row + ring - 1, rmax) + 1)
        for c in (col - ring, col + ring):
            if cmin <= c <= cmax:
                for r in rows:
                    yield r, c
