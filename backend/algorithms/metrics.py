"""What a search cost to run: time, memory and work done.

Measured in separate passes, because measuring changes what is measured:

1. The checked run (`runner.run`) validates every event and records the
   trace. Its overhead would inflate the timing, so it isn't timed.
2. Clean runs consume the generator with only a cheap event count and a
   deadline check. Their median wall-clock and CPU time is the algorithm's
   own time. Yielding events is part of every algorithm here, so it is
   included, along with that small bookkeeping.
3. One run under `tracemalloc` measures peak memory. Tracing allocations
   slows Python down several times, so this run isn't timed.

Every clean run must yield exactly as many events as the checked run. An
algorithm that doesn't (one that keeps state between runs, or uses
randomness) would make the numbers meaningless, so it is reported as an
error instead. The clean runs get the same event cap and time limit as the
checked run, so a run that suddenly loops can't hang the server.

The counts (visited, frontier size...) come from the checked run, since
they don't depend on timing; see `runner.SearchResult`.
"""

from __future__ import annotations

import statistics
import threading
import time
import tracemalloc
from dataclasses import dataclass

from graph import WalkGraph

from .runner import DEFAULT_TIME_LIMIT_S, AlgorithmError, SearchFunction, max_events

# Repeat the clean run until this much time has been spent (at least once,
# at most MAX_RUNS times), so short searches get a stable median and long
# ones don't take ages.
TIMING_BUDGET_S = 0.3
MAX_RUNS = 5

# One measurement at a time in this process: searches timed side by side
# (two browser tabs, or a comparison) would slow each other down and the
# cached numbers would be wrong for good. Waiting is cheap next to that.
measure_lock = threading.Lock()

# Keeps two memory measurements from overlapping. tracemalloc counts
# allocations from every thread, so the figure is only exact when no other
# thread is busy at the same time: true for gunicorn's sync workers, not
# always for the threaded development server.
_memory_lock = threading.Lock()


@dataclass(frozen=True)
class Timing:
    wall_ms: float
    cpu_ms: float
    runs: int


# tracemalloc slows Python down several times, so the memory run gets this
# many times the normal time limit before it counts as stuck.
TRACING_SLOWDOWN = 6


def _consume(
    search: SearchFunction, graph: WalkGraph, start: int, goal: int, expected_events: int, time_limit_s: float
) -> None:
    """Run the search once, under the same limits as the checked run, and
    check it yields the same number of events."""
    limit = max_events(graph)
    deadline = time.monotonic() + time_limit_s
    count = 0
    try:
        for _ in search(graph, start, goal):
            count += 1
            if count > limit:
                raise AlgorithmError(f"yielded more than {limit:,} events on a repeat run; it is probably looping")
            if count % 1024 == 0 and time.monotonic() > deadline:
                raise AlgorithmError(f"took longer than {time_limit_s:g} s on a repeat run")
    except AlgorithmError:
        raise
    except Exception as exc:
        raise AlgorithmError(f"crashed on a repeat run with {type(exc).__name__}: {exc}") from exc
    if count != expected_events:
        raise AlgorithmError(
            f"gave a different result when run again: {expected_events:,} events the first time, {count:,} on a "
            "repeat run. Does it keep state between runs, or use randomness?"
        )


def time_search(search: SearchFunction, graph: WalkGraph, start: int, goal: int, *, expected_events: int) -> Timing:
    """Median wall-clock and CPU time of clean runs, in milliseconds."""
    walls: list[float] = []
    cpus: list[float] = []
    spent = 0.0
    while len(walls) < MAX_RUNS and (not walls or spent < TIMING_BUDGET_S):
        wall0, cpu0 = time.perf_counter(), time.thread_time()
        _consume(search, graph, start, goal, expected_events, DEFAULT_TIME_LIMIT_S)
        wall, cpu = time.perf_counter() - wall0, time.thread_time() - cpu0
        walls.append(wall)
        cpus.append(cpu)
        spent += wall
    return Timing(
        wall_ms=statistics.median(walls) * 1000,
        cpu_ms=statistics.median(cpus) * 1000,
        runs=len(walls),
    )


def peak_memory_bytes(search: SearchFunction, graph: WalkGraph, start: int, goal: int, *, expected_events: int) -> int:
    """The most memory allocated during one run, above what was in use before it."""
    with _memory_lock:
        # Don't stop tracing that someone else (a profiler, PYTHONTRACEMALLOC)
        # started.
        already_tracing = tracemalloc.is_tracing()
        if not already_tracing:
            tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            baseline, _ = tracemalloc.get_traced_memory()
            _consume(search, graph, start, goal, expected_events, DEFAULT_TIME_LIMIT_S * TRACING_SLOWDOWN)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            if not already_tracing:
                tracemalloc.stop()
    return max(0, peak - baseline)
