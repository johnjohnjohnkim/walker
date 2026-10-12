"""Checks against the real downtown graph. Skipped until it has been built."""

import time

import pytest

from graph import WalkGraph
from graph.build import default_path
from graph.spatial import NodeIndex, haversine_m

PATH = default_path("downtown")

pytestmark = pytest.mark.skipif(not PATH.exists(), reason="run `uv run python -m graph.build --area downtown` first")


@pytest.fixture(scope="module")
def downtown():
    graph = WalkGraph.load(PATH)
    return graph, NodeIndex(graph)


def test_is_a_city_sized_graph(downtown):
    graph, _ = downtown
    assert graph.node_count > 10_000
    assert graph.meta["area"] == "downtown"


@pytest.mark.parametrize(
    "name, lon, lat",
    [
        ("CN Tower", -79.3871, 43.6426),
        ("Union Station", -79.3806, 43.6453),
        ("Nathan Phillips Square", -79.3839, 43.6525),
        ("Kensington Market", -79.4005, 43.6547),
    ],
)
def test_landmarks_snap_to_a_nearby_node(downtown, name, lon, lat):
    _, index = downtown
    result = index.nearest(lon, lat, max_distance_m=150)
    assert result is not None, f"{name} has no walkable node within 150 m"


def test_every_edge_has_a_plausible_length(downtown):
    graph, _ = downtown
    assert min(graph.weights) >= 0
    assert max(graph.weights) < 5_000


def test_every_street_is_walkable_both_ways(downtown):
    graph, _ = downtown
    for u in range(graph.node_count):
        for v, length in graph.neighbors(u):
            back = graph.find_edge(v, u)
            assert back is not None, f"{u} -> {v} has no way back"
            assert graph.weights[back] == pytest.approx(length)


def test_curved_edges_run_from_source_to_target(downtown):
    # edge_geometry puts the source first and the target last. If the bends
    # in between were stored backwards, the drawn line would zig-zag from the
    # source to the far end and back, and come out much longer than the
    # stored length.
    graph, _ = downtown
    checked = 0
    for e in range(graph.edge_count):
        line = graph.edge_geometry(e)
        if len(line) < 3:
            continue
        drawn = sum(haversine_m(*a, *b) for a, b in zip(line, line[1:]))
        assert drawn == pytest.approx(graph.weights[e], rel=0.02, abs=1.0)
        checked += 1
    assert checked > 1_000


def test_far_away_lookup_is_fast(downtown):
    _, index = downtown
    started = time.perf_counter()
    assert index.nearest(0.0, 0.0, max_distance_m=500) is None
    assert index.nearest(0.0, 0.0) is not None
    assert time.perf_counter() - started < 0.5
