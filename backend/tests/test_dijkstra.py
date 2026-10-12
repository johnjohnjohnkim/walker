import pytest

from algorithms import dijkstra
from algorithms.events import Discover, Done, Visit
from algorithms.runner import run
from graph import WalkGraph


def line_graph(lengths):
    """Nodes 0..n in a two-way line with the given edge lengths."""
    coords = [(float(i), 0.0) for i in range(len(lengths) + 1)]
    edges = []
    for i, length in enumerate(lengths):
        edges += [(i, i + 1, length), (i + 1, i, length)]
    return WalkGraph.from_edges(coords, edges)


def test_matches_the_documented_example():
    events = list(dijkstra.search(line_graph([1.0, 1.0]), 0, 2))

    assert events == [
        Discover(0, None),
        Visit(0),
        Discover(1, 0),
        Visit(1),
        Discover(2, 1),
        Visit(2),
        Done([0, 1, 2]),
    ]


def test_prefers_the_shorter_route_over_fewer_steps():
    # 0 -> 3 directly is 10 m; 0 -> 1 -> 2 -> 3 is 3 m.
    coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
    edges = [(0, 3, 10.0), (0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0)]
    graph = WalkGraph.from_edges(coords, edges)

    result = run(dijkstra.search, graph, 0, 3)

    assert result.path == [0, 1, 2, 3]
    assert result.distance_m == 3.0


def test_updates_a_node_when_a_shorter_route_turns_up():
    # 2 is first discovered via 0 -> 2 (5 m), then improved via 0 -> 1 -> 2 (2 m).
    coords = [(0, 0), (1, 0), (2, 0)]
    graph = WalkGraph.from_edges(coords, [(0, 2, 5.0), (0, 1, 1.0), (1, 2, 1.0)])

    events = list(dijkstra.search(graph, 0, 2))

    assert Discover(2, 0) in events and Discover(2, 1) in events
    assert events[-1] == Done([0, 1, 2])
    # Even though 2 was pushed twice, it is visited once.
    assert events.count(Visit(2)) == 1


def test_start_is_the_goal():
    result = run(dijkstra.search, line_graph([1.0]), 1, 1)

    assert result.path == [1]
    assert result.distance_m == 0.0
    assert result.visited == 1


def test_unreachable_goal():
    # One-way 0 -> 1, so 1 can't get back to 0.
    graph = WalkGraph.from_edges([(0, 0), (1, 0)], [(0, 1, 1.0)])

    result = run(dijkstra.search, graph, 1, 0)

    assert result.path is None
    assert result.distance_m is None


def test_stops_as_soon_as_the_goal_is_visited():
    graph = line_graph([1.0] * 10)

    result = run(dijkstra.search, graph, 0, 2)

    assert result.visited == 3


def test_every_discovery_follows_a_real_edge(grid_graph):
    events = list(dijkstra.search(grid_graph, 0, 8))
    seen = {0}
    for event in events:
        if isinstance(event, Discover) and event.parent is not None:
            assert event.parent in seen
            assert grid_graph.find_edge(event.parent, event.node) is not None
            seen.add(event.node)
    assert events[-1].path[0] == 0 and events[-1].path[-1] == 8


@pytest.mark.parametrize("goal, expected", [(8, 400.0), (4, 200.0), (2, 200.0)])
def test_grid_distances(grid_graph, goal, expected):
    assert run(dijkstra.search, grid_graph, 0, goal).distance_m == expected
