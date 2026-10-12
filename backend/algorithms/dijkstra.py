"""Dijkstra's algorithm: the shortest path by walking distance.

The reference implementation for the event contract in `events.py`.

Dijkstra keeps a priority queue (a binary heap) of frontier nodes ordered by
their best known distance from the start. It always explores the closest
unexplored node next, so when a node is taken off the heap its distance is
final. With non-negative edge lengths that makes the first time it takes the
goal off the heap the moment it has found the shortest path.

Running time is O((V + E) log V) with a binary heap.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterator

from graph import WalkGraph

from .events import Discover, Done, Event, Visit


def search(graph: WalkGraph, start: int, goal: int) -> Iterator[Event]:
    dist = {start: 0.0}
    parent: dict[int, int | None] = {start: None}
    visited: set[int] = set()
    # Entries are (distance, node). Python's heapq has no "decrease key", so a
    # node can be pushed again when a shorter route to it turns up; the stale,
    # longer entry is skipped when it reaches the top ("lazy deletion").
    heap = [(0.0, start)]
    yield Discover(start, None)

    while heap:
        d, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        yield Visit(node)

        if node == goal:
            yield Done(_walk_back(parent, goal))
            return

        for neighbor, length in graph.neighbors(node):
            if neighbor in visited:
                continue
            candidate = d + length
            if candidate < dist.get(neighbor, float("inf")):
                dist[neighbor] = candidate
                parent[neighbor] = node
                heapq.heappush(heap, (candidate, neighbor))
                yield Discover(neighbor, node)

    yield Done(None)


def _walk_back(parent: dict[int, int | None], goal: int) -> list[int]:
    path = [goal]
    while (previous := parent[path[-1]]) is not None:
        path.append(previous)
    path.reverse()
    return path
