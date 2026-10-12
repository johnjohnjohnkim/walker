import pytest
from django.core.cache import caches

from graph import WalkGraph
from routing import graph_store

# A 3x3 grid of nodes about 100 m apart near King and Bay, numbered
#
#   6 - 7 - 8      north
#   |   |   |
#   3 - 4 - 5
#   |   |   |
#   0 - 1 - 2      south
#
# with every street walkable in both directions.
GRID_ORIGIN = (-79.3800, 43.6480)
# Slightly under 100 m apart, so the 100 m edges are never shorter than the
# straight line between their ends (A* depends on that; see geo.py).
GRID_STEP_LON = 0.00124  # 99.7 m at this latitude
GRID_STEP_LAT = 0.00089  # 99.0 m


def grid_coords() -> list[tuple[float, float]]:
    lon0, lat0 = GRID_ORIGIN
    return [(lon0 + col * GRID_STEP_LON, lat0 + row * GRID_STEP_LAT) for row in range(3) for col in range(3)]


def grid_edges(length: float = 100.0) -> list[tuple[int, int, float]]:
    edges = []
    for row in range(3):
        for col in range(3):
            node = row * 3 + col
            if col < 2:
                edges += [(node, node + 1, length), (node + 1, node, length)]
            if row < 2:
                edges += [(node, node + 3, length), (node + 3, node, length)]
    return edges


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    """Each test starts with no requests counted against any client."""
    caches["ratelimit"].clear()
    yield
    caches["ratelimit"].clear()


@pytest.fixture
def grid_graph() -> WalkGraph:
    return WalkGraph.from_edges(grid_coords(), grid_edges(), meta={"area": "test-grid"})


@pytest.fixture
def graph_file(tmp_path, settings, grid_graph):
    """Point the server at a saved copy of the grid graph."""
    path = tmp_path / "grid.walkgraph"
    grid_graph.save(path)
    settings.WALKER_GRAPH_PATH = path
    graph_store.reset()
    caches["metrics"].clear()
    yield path
    graph_store.reset()
    caches["metrics"].clear()


@pytest.fixture
def missing_graph_file(tmp_path, settings):
    settings.WALKER_GRAPH_PATH = tmp_path / "nope.walkgraph"
    graph_store.reset()
    yield
    graph_store.reset()
