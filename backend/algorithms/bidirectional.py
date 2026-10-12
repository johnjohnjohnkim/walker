"""Bidirectional Dijkstra: two searches, one from each end, meeting in the middle.

To do: implement `search` below. It switches on in the app (picker, API and
conformance tests) as soon as it stops raising NotImplementedError.

What it should do
-----------------
Run Dijkstra forwards from `start` and backwards from `goal` at the same
time, taking turns, until the two searches meet. Each search covers roughly
a circle with half the radius, so together they explore far fewer nodes than
one big circle. On the map the two searches are drawn in different colours.

Must return: a shortest path by distance (the tests compare its length with
Dijkstra's), joined into one list from start to goal.

Things to get right
-------------------
- The backward search walks edges in reverse. Use `graph.incoming(node)`,
  not `graph.neighbors(node)`. Today's walking graph happens to be two-way,
  but the tests include one-way edges.
- When to stop is the classic trap: the first node both searches have
  reached is *not* necessarily on the shortest path. Work out what you
  would need to know to be sure no shorter route can still turn up. The
  conformance tests include a graph where stopping at the first meeting
  point gives the wrong answer.
- Tag every event with its side, and start the backward side with
  `Discover(goal, None, "backward")`. See the bidirectional section of
  `events.py`, including what `parent` means on the backward side.
- Handle `start == goal` and an unreachable goal (`Done(None)`).
- Run `uv run pytest tests/test_conformance.py -k bidirectional` to check
  your work.

Useful:
- `graph.neighbors(node)` yields `(neighbor, length_m)` for edges leaving it.
- `graph.incoming(node)` yields `(predecessor, length_m)` for edges arriving.
"""

from __future__ import annotations

from collections.abc import Iterator

from graph import WalkGraph

from .events import Event


def search(graph: WalkGraph, start: int, goal: int) -> Iterator[Event]:
    raise NotImplementedError("Bidirectional Dijkstra hasn't been written yet")
    yield  # makes this a generator function
