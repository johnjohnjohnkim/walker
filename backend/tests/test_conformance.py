"""Checks every registered algorithm against the event rules and its promise.

Algorithms that are still stubs are skipped, so this suite passes while you
work and starts checking each algorithm as soon as you write it:

    uv run pytest tests/test_conformance.py -k bfs -v

Reference answers come from NetworkX, used only here as an independent check.
"""

import math
import random
import sys

import networkx as nx
import pytest

from algorithms import REGISTRY
from algorithms.runner import run
from graph import WalkGraph
from graph.build import default_path

from .conftest import grid_coords, grid_edges
from .geo import geo_graph, lonlat, shortest_edge_ratio, straight_m


def each_algorithm():
    for algorithm in REGISTRY:
        marks = [] if algorithm.implemented else [pytest.mark.skip(reason=f"{algorithm.name} is still a stub")]
        yield pytest.param(algorithm, id=algorithm.id, marks=marks)


ALGORITHMS = list(each_algorithm())


# ---------------------------------------------------------------- test graphs
#
# Built with tests.geo, so every edge is at least as long as the straight line
# between its ends (see geo.py for why A* needs that). Distances are metres.

GRAPHS = {
    # 0 - 1 - 2 - 3, 100 m apart, running east.
    "line": geo_graph([(0, 0), (100, 0), (200, 0), (300, 0)], [(0, 1), (1, 2), (2, 3)]),
    "grid": WalkGraph.from_edges(grid_coords(), grid_edges()),
    # A 450 m direct path from 0 to 3, or three straight 100 m steps.
    # Shortest by distance and fewest edges disagree here.
    "hops_vs_metres": geo_graph(
        [(0, 0), (100, 0), (200, 0), (300, 0)], [(0, 3, 450.0), (0, 1), (1, 2), (2, 3)]
    ),
    # One-way loop 0 -> 1 -> 2 -> 0, plus node 3 that nothing reaches.
    "one_way": geo_graph([(0, 0), (100, 0), (50, 80), (300, 300)], [(0, 1), (1, 2), (2, 0)], two_way=False),
    # Bidirectional trap. The two searches first meet at node 1, on the
    # 600 m route 0 - 1 - 4, but 0 - 2 - 3 - 4 is 480 m.
    "meeting_point_trap": geo_graph(
        [(0, 0), (200, 223.6), (100, 0), (300, 0), (400, 0)],
        [(0, 1, 300.0), (1, 4, 300.0), (0, 2, 120.0), (2, 3, 240.0), (3, 4, 120.0)],
    ),
    # Lengths that differ by direction: walking 0 -> 1 -> 2 is 200 m, but
    # 2 -> 1 -> 0 is 600 m. The direct path 0 - 2 is 250 m both ways. A
    # backward search that reads lengths from the wrong direction picks the
    # direct path for 0 -> 2.
    "uphill_downhill": geo_graph(
        [(0, 0), (100, 0), (200, 0)],
        [(0, 1, 100.001), (1, 0, 300.0), (1, 2, 100.001), (2, 1, 300.0), (0, 2, 250.0), (2, 0, 250.0)],
        two_way=False,
    ),
    # A triangle 0 - 1 - 2 with 1 - 3 hanging off it. BFS reaches 1 and 2
    # first; if it then overwrites 1's parent when it sees the 2 - 1 edge,
    # the route to 3 gains an extra edge.
    "odd_cycle": geo_graph([(0, 0), (100, 50), (100, -50), (200, 50)], [(0, 1), (0, 2), (1, 2), (1, 3)]),
    # A* trap: straight-line lengths. The 1,016 m route via node 2 heads
    # away from the goal at first; the 1,154 m route via node 1 swings close
    # to it. A* with an estimate that is too large (2x, or forgetting that a
    # degree of longitude is shorter than a degree of latitude) takes the
    # longer one.
    "overestimate_trap": geo_graph(
        [(0, 0), (980, 160), (120, -60), (1000, 0)], [(0, 1), (1, 3), (0, 2), (2, 3)]
    ),
    # 3,000 nodes in a row, 1 m apart: deeper than Python's default recursion limit.
    "deep_line": geo_graph([(i, 0) for i in range(3000)], [(i, i + 1) for i in range(2999)]),
}

QUERIES = [
    ("line", 0, 3),
    ("line", 3, 0),
    ("grid", 0, 8),
    ("grid", 6, 2),
    ("hops_vs_metres", 0, 3),
    ("one_way", 1, 0),
    ("one_way", 0, 2),
    ("meeting_point_trap", 0, 4),
    ("meeting_point_trap", 4, 0),
    ("uphill_downhill", 0, 2),
    ("uphill_downhill", 2, 0),
    ("odd_cycle", 0, 3),
    ("overestimate_trap", 0, 3),
    ("overestimate_trap", 3, 0),
    ("deep_line", 0, 2999),
]


def random_graph(seed, n=60, extra_edges=90):
    """A connected, mostly two-way graph with a few one-way edges.

    Nodes are scattered over about a kilometre, and each edge is 1 to 1.5
    times the straight line, like real streets.
    """
    rng = random.Random(seed)
    points = [(rng.random() * 1000, rng.random() * 1000) for _ in range(n)]
    coords = [lonlat(x, y) for x, y in points]
    edges = []

    def add(u, v, one_way=False):
        length = straight_m(coords, u, v) * rng.uniform(1.0, 1.5) * 1.000001
        edges.append((u, v, length))
        if not one_way:
            edges.append((v, u, length))

    for v in range(1, n):  # a random spanning tree keeps it connected
        add(rng.randrange(v), v)
    for _ in range(extra_edges):
        u, v = rng.sample(range(n), 2)
        add(u, v, one_way=rng.random() < 0.2)
    return WalkGraph.from_edges(coords, edges)


def reference(graph):
    g = nx.DiGraph()
    g.add_nodes_from(range(graph.node_count))
    for u in range(graph.node_count):
        for v, w in graph.neighbors(u):
            g.add_edge(u, v, weight=w)
    return g


def check(algorithm, graph, start, goal, ref=None):
    """Run the algorithm (the runner enforces the event rules) and check its promise."""
    result = run(algorithm.search, graph, start, goal)
    ref = ref if ref is not None else reference(graph)

    if not nx.has_path(ref, start, goal):
        assert result.path is None, f"{algorithm.name} returned a path where none exists"
        return result

    assert result.path is not None, f"{algorithm.name} found no path, but one exists"
    if algorithm.guarantee == "shortest":
        expected = nx.dijkstra_path_length(ref, start, goal)
        assert result.distance_m == pytest.approx(expected), (
            f"{algorithm.name} returned a {result.distance_m:.1f} m route; the shortest is {expected:.1f} m"
        )
    elif algorithm.guarantee == "fewest_edges":
        expected = nx.shortest_path_length(ref, start, goal)
        assert len(result.path) - 1 == expected, (
            f"{algorithm.name} used {len(result.path) - 1} edges; the fewest possible is {expected}"
        )
    return result


# ---------------------------------------------------------------------- tests


@pytest.fixture(autouse=True)
def recursion_limit_unchanged():
    """Raising the recursion limit hides a recursive DFS here, but on the full
    city graph it can overflow the C stack and kill the server process."""
    before = sys.getrecursionlimit()
    yield
    assert sys.getrecursionlimit() == before, "the algorithm changed sys.setrecursionlimit"


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("graph_name, start, goal", QUERIES)
def test_small_graphs(algorithm, graph_name, start, goal):
    check(algorithm, GRAPHS[graph_name], start, goal)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_start_is_the_goal(algorithm):
    result = run(algorithm.search, GRAPHS["grid"], 4, 4)

    assert result.path == [4]
    assert result.distance_m == 0.0


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_unreachable_goal(algorithm):
    result = run(algorithm.search, GRAPHS["one_way"], 0, 3)

    assert result.path is None


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("seed", range(10))
def test_random_graphs(algorithm, seed):
    graph = random_graph(seed)
    ref = reference(graph)
    rng = random.Random(seed + 1000)
    for _ in range(10):
        check(algorithm, graph, rng.randrange(graph.node_count), rng.randrange(graph.node_count), ref)


DOWNTOWN = default_path("downtown")


@pytest.mark.skipif(not DOWNTOWN.exists(), reason="run `uv run python -m graph.build` first")
@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_real_downtown_routes(algorithm, downtown_reference):
    graph, ref = downtown_reference
    rng = random.Random(11)
    for _ in range(5):
        check(algorithm, graph, rng.randrange(graph.node_count), rng.randrange(graph.node_count), ref)


@pytest.fixture(scope="module")
def downtown_reference():
    graph = WalkGraph.load(DOWNTOWN)
    return graph, reference(graph)


# ------------------------------------------- the test graphs are what they claim


@pytest.mark.parametrize("name", sorted(GRAPHS))
def test_no_edge_is_shorter_than_a_straight_line(name):
    assert shortest_edge_ratio(GRAPHS[name]) >= 1.0


@pytest.mark.parametrize("seed", range(10))
def test_random_graph_edges_are_not_shorter_than_straight_lines(seed):
    assert shortest_edge_ratio(random_graph(seed)) >= 1.0


def test_the_meeting_point_trap_is_really_a_trap():
    """The node where the two searches first meet is not on the shortest path."""
    ref = reference(GRAPHS["meeting_point_trap"])
    assert nx.dijkstra_path(ref, 0, 4) == [0, 2, 3, 4]
    assert nx.dijkstra_path_length(ref, 0, 4) == pytest.approx(480.0)
    assert nx.path_weight(ref, [0, 1, 4], "weight") == pytest.approx(600.0)
    # From each end, node 1 (300 m) is reached before the far side of the
    # short route (360 m), so a search stopping at the first shared node fails.
    assert nx.dijkstra_path_length(ref, 0, 1) < nx.dijkstra_path_length(ref, 0, 3)
    assert nx.dijkstra_path_length(ref, 1, 4) < nx.dijkstra_path_length(ref, 2, 4)


def test_hops_and_metres_really_disagree():
    ref = reference(GRAPHS["hops_vs_metres"])
    assert nx.shortest_path(ref, 0, 3) == [0, 3]
    assert nx.dijkstra_path(ref, 0, 3) == [0, 1, 2, 3]


def test_direction_matters_in_uphill_downhill():
    ref = reference(GRAPHS["uphill_downhill"])
    assert nx.dijkstra_path(ref, 0, 2) == [0, 1, 2]
    # Reading the reverse lengths (300 m each) would make the direct path look better.
    assert ref[2][1]["weight"] + ref[1][0]["weight"] > ref[0][2]["weight"]


def test_the_overestimate_trap_is_really_a_trap():
    """Compare the priorities A* would give the two first steps (distance so far + k * estimate)."""
    graph = GRAPHS["overestimate_trap"]
    coords = [graph.coord(n) for n in range(4)]
    ref = reference(graph)
    assert nx.dijkstra_path(ref, 0, 3) == [0, 2, 3]
    near_goal, away = 1, 2

    def priority(node, inflate=1.0, lon_scale=1.0):
        g = ref[0][node]["weight"]
        (lon1, lat1), (lon2, lat2) = coords[node], coords[3]
        # lon_scale > 1 stretches east-west distance, like forgetting cos(latitude).
        lon2 = lon1 + (lon2 - lon1) * lon_scale
        return g + inflate * straight_m([(lon1, lat1), (lon2, lat2)], 0, 1)

    longer_route = nx.path_weight(ref, [0, 1, 3], "weight")
    # With an honest estimate, the shorter route's first step comes first.
    assert priority(away) < priority(near_goal)
    for bad in ({"inflate": 2.0}, {"lon_scale": 1 / math.cos(math.radians(43.648))}):
        # With an inflated estimate, the other step comes first, and the goal
        # (reached at the longer route's length) beats the shorter route's step.
        assert priority(near_goal, **bad) < priority(away, **bad)
        assert longer_route < priority(away, **bad)


# ------------------------------------------------- the checks themselves work


def _fake(guarantee, search):
    from algorithms import Algorithm

    return Algorithm(id="fake", name="Fake", description="", guarantee=guarantee,
                     uses_lengths=True, bidirectional=False, search=search)


def _dijkstra_ignoring_lengths(graph, start, goal):
    """Dijkstra run on a copy with every edge 1 m long: finds fewest edges, not fewest metres."""
    from algorithms import dijkstra

    unit = WalkGraph.from_edges(
        [graph.coord(n) for n in range(graph.node_count)],
        [(u, v, 1.0) for u in range(graph.node_count) for v, _ in graph.neighbors(u)],
    )
    yield from dijkstra.search(unit, start, goal)


def test_check_catches_a_route_that_is_not_shortest():
    with pytest.raises(AssertionError, match="the shortest is"):
        check(_fake("shortest", _dijkstra_ignoring_lengths), GRAPHS["hops_vs_metres"], 0, 3)


def test_check_catches_a_route_with_too_many_edges():
    from algorithms import dijkstra

    with pytest.raises(AssertionError, match="fewest possible"):
        check(_fake("fewest_edges", dijkstra.search), GRAPHS["hops_vs_metres"], 0, 3)


def test_check_catches_a_missing_route():
    from algorithms.events import Discover, Done, Visit

    def gives_up(graph, start, goal):
        yield Discover(start, None)
        yield Visit(start)
        yield Done(None)

    with pytest.raises(AssertionError, match="found no path"):
        check(_fake("any", gives_up), GRAPHS["line"], 0, 3)
