import math
import random
import time

import pytest

from graph import WalkGraph
from graph.spatial import NodeIndex, haversine_m

from .conftest import GRID_ORIGIN


def test_haversine_known_distances():
    # One degree of latitude is about 111.2 km everywhere.
    assert haversine_m(-79.0, 43.0, -79.0, 44.0) == pytest.approx(111_195, rel=1e-3)
    # CN Tower to Union Station is roughly 600 m.
    assert haversine_m(-79.3871, 43.6426, -79.3806, 43.6453) == pytest.approx(600, abs=40)
    assert haversine_m(-79.38, 43.65, -79.38, 43.65) == 0


def test_nearest_returns_exact_node(grid_graph):
    index = NodeIndex(grid_graph)
    lon, lat = grid_graph.coord(4)

    node, distance = index.nearest(lon, lat)

    assert node == 4
    assert distance == pytest.approx(0, abs=1e-6)


def test_nearest_picks_closest_node(grid_graph):
    index = NodeIndex(grid_graph)
    lon0, lat0 = GRID_ORIGIN

    # Just north-east of node 0, closer to it than to 1 or 3.
    node, _ = index.nearest(lon0 + 0.0002, lat0 + 0.0001)

    assert node == 0


def test_nearest_respects_max_distance(grid_graph):
    index = NodeIndex(grid_graph)
    lon0, lat0 = GRID_ORIGIN

    assert index.nearest(lon0, lat0 - 0.01, max_distance_m=200) is None  # ~1.1 km south
    assert index.nearest(lon0, lat0 - 0.01) is not None


def test_nearest_far_outside_the_grid_still_works(grid_graph):
    index = NodeIndex(grid_graph)

    node, distance = index.nearest(-79.0, 44.0)

    assert node == 8  # the north-east corner
    assert distance > 40_000


@pytest.mark.parametrize("cell_m", [20.0, 100.0, 500.0])
def test_nearest_matches_brute_force(cell_m):
    rng = random.Random(42)
    coords = [(-79.40 + rng.random() * 0.05, 43.64 + rng.random() * 0.03) for _ in range(500)]
    graph = WalkGraph.from_edges(coords, [])
    index = NodeIndex(graph, cell_m=cell_m)

    for _ in range(300):
        lon, lat = -79.41 + rng.random() * 0.07, 43.63 + rng.random() * 0.05
        expected = min(range(len(coords)), key=lambda n: haversine_m(lon, lat, *coords[n]))
        node, distance = index.nearest(lon, lat)
        assert distance == pytest.approx(haversine_m(lon, lat, *coords[expected]))
        assert node == expected


def test_empty_graph_is_rejected():
    with pytest.raises(ValueError):
        NodeIndex(WalkGraph.from_edges([], []))


def test_far_away_queries_are_fast(grid_graph):
    index = NodeIndex(grid_graph, cell_m=10.0)

    started = time.perf_counter()
    for lon, lat in [(0.0, 0.0), (-79.38, -43.0), (179.9, 89.9)]:
        assert index.nearest(lon, lat) is not None
        assert index.nearest(lon, lat, max_distance_m=500) is None
    assert time.perf_counter() - started < 0.5


@pytest.mark.parametrize("lon, lat", [(math.nan, 43.6), (-79.4, math.inf), (-math.inf, math.nan)])
def test_non_finite_coordinates_are_rejected(grid_graph, lon, lat):
    with pytest.raises(ValueError):
        NodeIndex(grid_graph).nearest(lon, lat)
