"""The events every search algorithm reports while it runs.

A search algorithm is a generator function with this signature:

    def search(graph: WalkGraph, start: int, goal: int) -> Iterator[Event]:

It yields events as it works and finishes by yielding exactly one `Done`.
The server turns the events into the animation and the statistics, so they
must describe what the algorithm really does, in the order it does it.

The three events
----------------
- `Discover(node, parent)`: `node` was reached from `parent` and placed on
  the frontier (the queue, stack or heap of nodes waiting to be explored).
  Yield it again if a better route to an already-discovered node turns up.
- `Visit(node)`: `node` was taken off the frontier and its edges explored.
- `Done(path)`: the answer, as a list of node ids from `start` to `goal`
  inclusive, or `None` if the goal can't be reached.

Rules (the runner in `runner.py` checks all of these)
-----------------------------------------------------
1. The first event is `Discover(start, None)`. Every later `Discover` has a
   parent, and that parent must already have been visited.
2. A node can only be visited after it has been discovered, and at most once.
3. Node ids are ints from 0 to `graph.node_count - 1`.
4. Nothing comes after `Done`. You may yield `Done` as soon as you know the
   answer; you don't have to visit the goal first. (The "visited" count then
   reflects that shortcut, which is a real advantage of stopping early.)
5. Edges are directed. Use `graph.neighbors(u)` to follow edges out of `u`,
   and `graph.incoming(v)` to follow them backwards into `v`.

What each algorithm must return
-------------------------------
- Dijkstra, A* and bidirectional Dijkstra: a shortest path by distance.
  The tests compare their length with Dijkstra's.
- BFS: a path with the fewest edges (not necessarily the shortest walk).
- DFS: any valid path.

Example: on a graph 0 - 1 - 2, `search(graph, 0, 2)` with Dijkstra yields

    Discover(0, None), Visit(0), Discover(1, 0), Visit(1), Discover(2, 1),
    Visit(2), Done([0, 1, 2])

Bidirectional searches
----------------------
These run one search from the start (`side="forward"`) and one from the goal
(`side="backward"`), and tag every event with its side so the two can be
drawn in different colours. The rules apply to each side separately: the
backward side begins with `Discover(goal, None, "backward")`, and on that
side `parent` is the node you came from while walking edges backwards, that
is, the next node on the way to the goal. `Done` still carries the whole
joined path from start to goal.

On the same graph 0 - 1 - 2, a bidirectional search might yield

    Discover(0, None), Discover(2, None, "backward"),
    Visit(0), Discover(1, 0),
    Visit(2, "backward"), Discover(1, 2, "backward"),
    Done([0, 1, 2])

One-directional searches leave `side` at its default, "forward".
"""

from __future__ import annotations

from typing import Literal, NamedTuple

Side = Literal["forward", "backward"]


class Discover(NamedTuple):
    node: int
    parent: int | None
    side: Side = "forward"


class Visit(NamedTuple):
    node: int
    side: Side = "forward"


class Done(NamedTuple):
    path: list[int] | None


Event = Discover | Visit | Done
