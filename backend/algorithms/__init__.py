"""Search algorithms over the walking graph.

Each algorithm is a generator function following the event contract in
`events.py`, registered below with what the app needs to know about it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from graph import WalkGraph

from . import astar, bfs, bidirectional, dfs, dijkstra
from .runner import SearchFunction

# What an algorithm promises about the path it returns. The conformance tests
# check each promise.
Guarantee = Literal["shortest", "fewest_edges", "any"]


@dataclass(frozen=True)
class Algorithm:
    id: str
    name: str
    description: str
    guarantee: Guarantee
    uses_lengths: bool
    bidirectional: bool
    search: SearchFunction

    @property
    def implemented(self) -> bool:
        return is_implemented(self.search)


REGISTRY: tuple[Algorithm, ...] = (
    Algorithm(
        id="dijkstra",
        name="Dijkstra",
        description="Explores outward in order of walking distance. Always finds the shortest route.",
        guarantee="shortest",
        uses_lengths=True,
        bidirectional=False,
        search=dijkstra.search,
    ),
    Algorithm(
        id="astar",
        name="A*",
        description="Dijkstra steered toward the goal by straight-line distance. Shortest route, less exploring.",
        guarantee="shortest",
        uses_lengths=True,
        bidirectional=False,
        search=astar.search,
    ),
    Algorithm(
        id="bidirectional",
        name="Bidirectional",
        description="Two Dijkstra searches, from each end, meeting in the middle. Shortest route.",
        guarantee="shortest",
        uses_lengths=True,
        bidirectional=True,
        search=bidirectional.search,
    ),
    Algorithm(
        id="bfs",
        name="BFS",
        description="Explores in rings of street segments, ignoring their length. Fewest turns, not fewest metres.",
        guarantee="fewest_edges",
        uses_lengths=False,
        bidirectional=False,
        search=bfs.search,
    ),
    Algorithm(
        id="dfs",
        name="DFS",
        description="Follows one street as deep as it goes before backing up. Finds a route, rarely a good one.",
        guarantee="any",
        uses_lengths=False,
        bidirectional=False,
        search=dfs.search,
    ),
)

BY_ID: dict[str, Algorithm] = {algorithm.id: algorithm for algorithm in REGISTRY}

# id -> search function, for code that only needs to run one.
ALGORITHMS: dict[str, SearchFunction] = {algorithm.id: algorithm.search for algorithm in REGISTRY}

_PROBE_GRAPH = WalkGraph.from_edges([(0.0, 0.0), (0.0, 0.001)], [(0, 1, 120.0), (1, 0, 120.0)])


def is_implemented(search: SearchFunction) -> bool:
    """False while `search` is still a stub that raises NotImplementedError.

    Stubs raise as soon as they start, so this only asks for the first event
    on a two-node graph. That keeps the check instant and side-effect free
    even if the rest of an algorithm is unfinished or loops. Any other
    outcome, including a crash, counts as implemented: the route endpoint
    then reports the error, which is more useful than hiding it.
    """
    try:
        next(iter(search(_PROBE_GRAPH, 0, 1)), None)
    except NotImplementedError:
        return False
    except Exception:
        return True
    return True
