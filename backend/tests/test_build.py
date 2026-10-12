import networkx as nx
import pytest
from shapely.geometry import LineString

from graph.build import from_osmnx


def osm_graph():
    """A tiny OSMnx-shaped graph: a two-way street, a curve, and an island."""
    g = nx.MultiDiGraph()
    g.add_node(100, x=-79.0, y=43.0)
    g.add_node(200, x=-79.1, y=43.0)
    g.add_node(300, x=-79.1, y=43.1)
    # An island the main part can't reach.
    g.add_node(900, x=-80.0, y=44.0)
    g.add_node(901, x=-80.0, y=44.1)

    g.add_edge(100, 200, length=10.0)
    g.add_edge(200, 100, length=10.0)
    # Two parallel ways between the same corners; the shorter should win.
    curve = LineString([(-79.1, 43.0), (-79.15, 43.05), (-79.1, 43.1)])
    g.add_edge(200, 300, length=30.0, geometry=curve)
    g.add_edge(200, 300, length=50.0)
    g.add_edge(300, 200, length=30.0, geometry=LineString(list(curve.coords)[::-1]))
    g.add_edge(900, 901, length=5.0)
    g.add_edge(901, 900, length=5.0)
    # A self-loop, which is useless for routing.
    g.add_edge(100, 100, length=1.0)
    return g


def test_keeps_only_the_largest_connected_part():
    graph = from_osmnx(osm_graph())

    assert graph.node_count == 3
    assert sorted(graph.coord(n) for n in range(3)) == sorted([(-79.0, 43.0), (-79.1, 43.0), (-79.1, 43.1)])


def test_drops_self_loops_and_parallel_duplicates():
    graph = from_osmnx(osm_graph())

    # 100<->200 and 200<->300, one edge per direction.
    assert graph.edge_count == 4
    lengths = sorted(w for n in range(graph.node_count) for _, w in graph.neighbors(n))
    assert lengths == [10.0, 10.0, 30.0, 30.0]


def test_keeps_curved_geometry_of_the_shortest_parallel_edge():
    graph = from_osmnx(osm_graph())
    node_at = {graph.coord(n): n for n in range(graph.node_count)}
    a, b = node_at[(-79.1, 43.0)], node_at[(-79.1, 43.1)]

    assert graph.edge_geometry(graph.find_edge(a, b)) == [(-79.1, 43.0), (-79.15, 43.05), (-79.1, 43.1)]
    assert graph.edge_geometry(graph.find_edge(b, a)) == [(-79.1, 43.1), (-79.15, 43.05), (-79.1, 43.0)]


def test_empty_graph_is_an_error():
    with pytest.raises(ValueError):
        from_osmnx(nx.MultiDiGraph())
