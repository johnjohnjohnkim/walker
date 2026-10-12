"""Runs a search algorithm and checks what it reports.

The runner never trusts an algorithm: it checks every event against the rules
in `events.py`, checks that the final path really goes from start to goal
along existing edges, and measures the path's length from the graph itself.
A broken algorithm raises AlgorithmError with a message saying what it did
wrong, which is what you want to see while writing one.

The time limit is only checked between events: Python can't interrupt a
generator that loops forever without yielding. In production the server's
own request timeout (gunicorn --timeout) is the backstop for that case.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from graph import WalkGraph

from .events import Discover, Done, Event, Visit

SearchFunction = Callable[[WalkGraph, int, int], Iterator[Event]]

SIDES = ("forward", "backward")

DEFAULT_TIME_LIMIT_S = 10.0


def max_events(graph: WalkGraph) -> int:
    """A correct search reports each node a bounded number of times, so far
    more events than this means it is looping. The bound allows for two
    sides and for a node being rediscovered once per incoming edge."""
    return 4 * (graph.node_count + graph.edge_count) + 16


class AlgorithmError(RuntimeError):
    """The algorithm crashed, broke the event rules or returned an invalid path."""


class AlgorithmNotImplemented(AlgorithmError):
    """The algorithm is still a stub."""


@dataclass(frozen=True)
class SearchResult:
    path: list[int] | None
    distance_m: float | None
    # Visit events: nodes taken off the frontier and explored.
    visited: int
    # Distinct nodes ever placed on the frontier (per side), however many
    # times each was rediscovered.
    discovered: int


def run(
    search: SearchFunction,
    graph: WalkGraph,
    start: int,
    goal: int,
    *,
    time_limit_s: float = DEFAULT_TIME_LIMIT_S,
) -> SearchResult:
    checker = _TraceChecker(graph, start, goal)
    limit = max_events(graph)
    deadline = time.monotonic() + time_limit_s
    done: Done | None = None
    count = 0

    try:
        for event in search(graph, start, goal):
            count += 1
            if done is not None:
                raise AlgorithmError("yielded events after Done")
            if count > limit:
                raise AlgorithmError(f"yielded more than {limit:,} events; it is probably looping")
            if count % 1024 == 0 and time.monotonic() > deadline:
                raise AlgorithmError(f"took longer than {time_limit_s:g} s")
            if isinstance(event, Done):
                done = event
            else:
                checker.check(event)
    except AlgorithmError:
        raise
    except NotImplementedError as exc:
        raise AlgorithmNotImplemented(str(exc) or "not implemented yet") from exc
    except Exception as exc:
        # A bug inside the algorithm itself: report it as the algorithm's
        # fault, with the original error attached for the traceback.
        raise AlgorithmError(f"crashed with {type(exc).__name__}: {exc}") from exc

    if done is None:
        raise AlgorithmError("finished without yielding Done")

    path = done.path
    distance = None if path is None else path_length(graph, path, start, goal)
    return SearchResult(path=path, distance_m=distance, visited=checker.visited, discovered=checker.discovered)


class _TraceChecker:
    """Enforces the event rules from events.py, one event at a time."""

    def __init__(self, graph: WalkGraph, start: int, goal: int) -> None:
        self.node_count = graph.node_count
        self.roots = {"forward": start, "backward": goal}
        self.seen = {side: set() for side in SIDES}
        self.explored = {side: set() for side in SIDES}

    @property
    def visited(self) -> int:
        return sum(len(nodes) for nodes in self.explored.values())

    @property
    def discovered(self) -> int:
        return sum(len(nodes) for nodes in self.seen.values())

    def check(self, event: Event) -> None:
        if isinstance(event, Discover):
            self._discover(event)
        elif isinstance(event, Visit):
            self._visit(event)
        else:
            raise AlgorithmError(f"yielded {event!r}, which is not an event")

    def _side(self, event) -> str:
        if event.side not in SIDES:
            raise AlgorithmError(f"{event!r} has side {event.side!r}; use 'forward' or 'backward'")
        return event.side

    def _node(self, node, event) -> int:
        if isinstance(node, bool) or not isinstance(node, int) or not 0 <= node < self.node_count:
            raise AlgorithmError(f"{event!r} refers to node {node!r}, which is not in the graph")
        return node

    def _discover(self, event: Discover) -> None:
        side = self._side(event)
        node = self._node(event.node, event)
        seen = self.seen[side]
        root = self.roots[side]
        if not seen:
            if node != root or event.parent is not None:
                raise AlgorithmError(
                    f"the first {side} event must be Discover({root}, None"
                    + (")" if side == "forward" else ", 'backward')")
                    + f", got {event!r}"
                )
        else:
            if event.parent is None:
                raise AlgorithmError(f"{event!r} has no parent; only the first node on a side may")
            parent = self._node(event.parent, event)
            if parent not in self.explored[side]:
                raise AlgorithmError(f"{event!r} names parent {parent}, which hasn't been visited on that side")
        seen.add(node)

    def _visit(self, event: Visit) -> None:
        side = self._side(event)
        node = self._node(event.node, event)
        if node not in self.seen[side]:
            raise AlgorithmError(f"{event!r} visits a node that was never discovered on that side")
        if node in self.explored[side]:
            raise AlgorithmError(f"{event!r} visits node {node} a second time")
        self.explored[side].add(node)


def path_length(graph: WalkGraph, path, start: int, goal: int) -> float:
    """Total length of `path` in metres, or AlgorithmError if it is not a real path."""
    if not isinstance(path, list) or not all(isinstance(n, int) and not isinstance(n, bool) for n in path):
        raise AlgorithmError(f"Done.path must be a list of node ids or None, got {type(path).__name__}")
    if not path or path[0] != start or path[-1] != goal:
        raise AlgorithmError(f"path must run from {start} to {goal}")
    total = 0.0
    for u, v in zip(path, path[1:]):
        for node in (u, v):
            if not 0 <= node < graph.node_count:
                raise AlgorithmError(f"path uses node {node}, which is not in the graph")
        edge = graph.find_edge(u, v)
        if edge is None:
            raise AlgorithmError(f"path uses {u} -> {v}, which is not an edge")
        total += graph.weights[edge]
    return total
