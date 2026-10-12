"""Breadth-first search (BFS): the path with the fewest edges.

To do: implement `search` below. It switches on in the app (picker, API and
conformance tests) as soon as it stops raising NotImplementedError.

What it should do
-----------------
Explore outward from `start` in rings: every node one edge away, then every
node two edges away, and so on. The first time the goal is reached, the path
there has the fewest edges possible. BFS ignores edge lengths, so on real
streets its route is often longer in metres than Dijkstra's. That difference
is worth seeing on the map.

Must return: a path with the fewest edges (the tests check this).

Things to get right
-------------------
- Report events as described in `events.py`: `Discover` when a node joins
  the queue, `Visit` when it is taken off, then `Done`.
- Decide when a node counts as "seen": when it is added to the queue, or
  when it is taken off. Both can be made correct; think about how often a
  node can end up in the queue, and what happens to its parent, with each.
- You may stop as soon as the goal is discovered (rule 4 in `events.py`).
- Handle `start == goal` and an unreachable goal (`Done(None)`).
- Run `uv run pytest tests/test_conformance.py -k bfs` to check your work.

Useful: `graph.neighbors(node)` yields `(neighbor, length_m)` pairs.
"""

from __future__ import annotations

from collections.abc import Iterator

from graph import WalkGraph

from .events import Event


def search(graph: WalkGraph, start: int, goal: int) -> Iterator[Event]:
    raise NotImplementedError("BFS hasn't been written yet")
    yield  # makes this a generator function
