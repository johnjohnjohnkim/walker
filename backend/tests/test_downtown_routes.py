"""Dijkstra on the real downtown graph, cross-checked against NetworkX.

NetworkX is used here only as an independent reference; the app never routes
with it. Skipped until the downtown graph has been built.
"""

import random

import networkx as nx
import pytest

from algorithms import dijkstra
from algorithms.runner import run
from graph import WalkGraph
from graph.build import default_path

PATH = default_path("downtown")

pytestmark = pytest.mark.skipif(not PATH.exists(), reason="run `uv run python -m graph.build --area downtown` first")


@pytest.fixture(scope="module")
def graphs():
    graph = WalkGraph.load(PATH)
    reference = nx.DiGraph()
    for u in range(graph.node_count):
        for v, length in graph.neighbors(u):
            reference.add_edge(u, v, weight=length)
    return graph, reference


def test_distances_match_networkx(graphs):
    graph, reference = graphs
    rng = random.Random(7)
    for _ in range(25):
        start, goal = rng.randrange(graph.node_count), rng.randrange(graph.node_count)

        result = run(dijkstra.search, graph, start, goal)

        expected = nx.dijkstra_path_length(reference, start, goal)
        assert result.distance_m == pytest.approx(expected)


def test_trace_parents_rebuild_the_returned_path(graphs):
    """The animation's tree leads to exactly the route that is drawn."""
    from algorithms.runner import DISCOVER

    graph, _ = graphs
    rng = random.Random(3)
    for _ in range(10):
        start, goal = rng.randrange(graph.node_count), rng.randrange(graph.node_count)
        result = run(dijkstra.search, graph, start, goal, record=True)
        parent = {}
        for code, node, par in zip(result.trace.codes, result.trace.nodes, result.trace.parents):
            if code == DISCOVER:
                parent[node] = par
        path = [goal]
        while parent[path[-1]] != -1:
            path.append(parent[path[-1]])
        assert path[::-1] == result.path
