"""Depth-first search (DFS): any path, found by going as deep as possible.

To do: implement `search` below. It switches on in the app (picker, API and
conformance tests) as soon as it stops raising NotImplementedError.

What it should do
-----------------
Follow one street as far as it goes before backing up and trying another.
DFS finds *a* path, usually a long, winding one, which is exactly what the
map should show: its real route, not a shortest one.

Must return: any valid path from start to goal.

Things to get right
-------------------
- Write it iteratively, with your own stack. The downtown graph has 16,000
  nodes and the whole city will have hundreds of thousands; a recursive DFS
  goes past Python's recursion limit (about 1,000 calls) and crashes. The
  conformance tests include a graph deep enough to catch this. Don't raise
  the limit with `sys.setrecursionlimit` instead: on a big graph that can
  overflow the real stack and kill the server process outright (the tests
  check the limit is left alone).
- Report events as described in `events.py`. In particular, every `Discover`
  after the first needs a parent that has already been visited.
- With an explicit stack, a node can end up on the stack more than once.
  Think about when to skip it so it is visited only once.
- Handle `start == goal` and an unreachable goal (`Done(None)`).
- Run `uv run pytest tests/test_conformance.py -k dfs` to check your work.

Useful: `graph.neighbors(node)` yields `(neighbor, length_m)` pairs.
"""

from __future__ import annotations

from collections.abc import Iterator

from graph import WalkGraph

from .events import Event


def search(graph: WalkGraph, start: int, goal: int) -> Iterator[Event]:
    raise NotImplementedError("DFS hasn't been written yet")
    yield  # makes this a generator function
