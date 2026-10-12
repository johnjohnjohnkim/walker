"""A* search: the shortest path, guided toward the goal.

To do: implement `search` below. It switches on in the app (picker, API and
conformance tests) as soon as it stops raising NotImplementedError.

What it should do
-----------------
Like Dijkstra (see `dijkstra.py`), but the priority of a node is its distance
from the start *plus an estimate of the distance still to go*. With a good
estimate the search leans toward the goal instead of spreading evenly, and
explores far fewer nodes. On the map it looks like a narrow beam rather than
Dijkstra's circle.

Must return: a shortest path by distance (the tests compare its length with
Dijkstra's).

Things to get right
-------------------
- The estimate (heuristic) must never be more than the true remaining
  walking distance, or A* can return a longer route. Straight-line distance
  works, because no walk is shorter than a straight line.
- A* stops when the goal is taken off the queue, not when it is first seen,
  for the same reason Dijkstra does.
- Report events as described in `events.py`.
- Handle `start == goal` and an unreachable goal (`Done(None)`).
- Run `uv run pytest tests/test_conformance.py -k astar` to check your work.
  The metrics card (M7) will show how many fewer nodes it visits than
  Dijkstra.

Useful:
- `graph.neighbors(node)` yields `(neighbor, length_m)` pairs.
- `graph.coord(node)` returns `(lon, lat)`.
- `haversine_m(lon1, lat1, lon2, lat2)`, from `graph.spatial`, is the
  straight-line distance in metres.
"""

from __future__ import annotations

from collections.abc import Iterator

from graph import WalkGraph

from .events import Event


def search(graph: WalkGraph, start: int, goal: int) -> Iterator[Event]:
    raise NotImplementedError("A* hasn't been written yet")
    yield  # makes this a generator function
