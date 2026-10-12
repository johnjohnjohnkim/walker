"""Test graphs whose lengths agree with their geometry.

Real streets are never shorter than the straight line between their ends, and
A* relies on that: it uses straight-line distance as its estimate of the
distance still to go. Test graphs must obey the same rule, or a correct A*
fails and a broken one can pass. Every graph built here does, and the
helper refuses edges that don't.

Points are given in metres east and north of a spot near King and Bay, so
tests read naturally and sit at Toronto's latitude, where a degree of
longitude is only about 80 km. A heuristic that forgets that is caught.
"""

from __future__ import annotations

import math

from graph import WalkGraph
from graph.spatial import METRES_PER_DEGREE_LAT, haversine_m

ORIGIN_LON, ORIGIN_LAT = -79.3800, 43.6480
_M_PER_DEG_LON = METRES_PER_DEGREE_LAT * math.cos(math.radians(ORIGIN_LAT))

# Straight-line edges get this tiny margin so rounding never makes them
# shorter than haversine says.
_ROUNDING = 1.000001


def lonlat(east_m: float, north_m: float) -> tuple[float, float]:
    return ORIGIN_LON + east_m / _M_PER_DEG_LON, ORIGIN_LAT + north_m / METRES_PER_DEGREE_LAT


def straight_m(coords, u: int, v: int) -> float:
    return haversine_m(*coords[u], *coords[v])


def geo_graph(points_m, edges, *, two_way: bool = True) -> WalkGraph:
    """Build a graph from points in metres and edges `(u, v)` or `(u, v, length_m)`.

    An edge without a length is as long as the straight line. With
    `two_way`, each edge is added in both directions with the same length.
    """
    coords = [lonlat(x, y) for x, y in points_m]
    built = []
    for edge in edges:
        u, v = edge[0], edge[1]
        straight = straight_m(coords, u, v)
        length = edge[2] if len(edge) > 2 else straight * _ROUNDING
        if length < straight:
            raise ValueError(f"edge {u}-{v} is {length:.1f} m but the straight line is {straight:.1f} m")
        built.append((u, v, length))
        if two_way:
            built.append((v, u, length))
    return WalkGraph.from_edges(coords, built)


def shortest_edge_ratio(graph: WalkGraph) -> float:
    """The smallest (edge length / straight-line distance) in the graph. Must be >= 1."""
    ratio = math.inf
    for u in range(graph.node_count):
        for v, length in graph.neighbors(u):
            straight = haversine_m(*graph.coord(u), *graph.coord(v))
            if straight > 0:
                ratio = min(ratio, length / straight)
    return ratio
