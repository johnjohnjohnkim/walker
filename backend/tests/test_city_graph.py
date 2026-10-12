"""Checks against the whole-city graph. Skipped until it has been built."""

import time

import pytest

from algorithms import dijkstra
from algorithms.runner import run
from graph import WalkGraph
from graph.build import default_path
from graph.spatial import NodeIndex

PATH = default_path("toronto")

pytestmark = pytest.mark.skipif(not PATH.exists(), reason="run `uv run python -m graph.build --area toronto` first")


@pytest.fixture(scope="module")
def city():
    started = time.perf_counter()
    graph = WalkGraph.load(PATH)
    index = NodeIndex(graph)
    return graph, index, time.perf_counter() - started


def test_loads_quickly_enough_for_a_server_start(city):
    graph, _, seconds = city
    assert graph.node_count > 200_000
    assert seconds < 15


@pytest.mark.parametrize(
    "name, lon, lat",
    [
        ("Scarborough Town Centre", -79.2570, 43.7760),
        ("Vaughan Mills", -79.5390, 43.8250),
        ("Humber Bay Park", -79.4800, 43.6230),
        ("North York Centre", -79.4130, 43.7680),
        ("Union Station", -79.3806, 43.6453),
    ],
)
def test_places_across_the_city_are_on_the_map(city, name, lon, lat):
    _, index, _ = city
    assert index.nearest(lon, lat, max_distance_m=300) is not None, f"{name} is not near a walkable street"


def test_a_cross_city_route_is_found_quickly(city):
    graph, index, _ = city
    start, _ = index.nearest(-79.2570, 43.7760)
    goal, _ = index.nearest(-79.5390, 43.8250)

    started = time.perf_counter()
    result = run(dijkstra.search, graph, start, goal)
    seconds = time.perf_counter() - started

    assert 25_000 < result.distance_m < 40_000
    # The checked run (with validation) must stay well inside the 10 s limit.
    assert seconds < 5
