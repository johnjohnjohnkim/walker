import time

import pytest

from algorithms.events import Discover, Done, Visit
from algorithms.runner import AlgorithmError, AlgorithmNotImplemented, max_events, run
from graph import WalkGraph


def scripted(*events):
    """A fake algorithm that yields exactly the given events."""

    def search(graph, start, goal):
        yield from events

    return search


def test_counts_events_and_measures_the_path(grid_graph):
    search = scripted(Discover(0, None), Visit(0), Discover(1, 0), Visit(1), Done([0, 1]))

    result = run(search, grid_graph, 0, 1)

    assert result.path == [0, 1]
    assert result.distance_m == 100.0
    assert result.visited == 2
    assert result.discovered == 2


def test_requires_done(grid_graph):
    with pytest.raises(AlgorithmError, match="without yielding Done"):
        run(scripted(Discover(0, None)), grid_graph, 0, 1)


def test_rejects_events_after_done(grid_graph):
    with pytest.raises(AlgorithmError, match="after Done"):
        run(scripted(Done([0, 1]), Visit(1)), grid_graph, 0, 1)


def test_rejects_things_that_are_not_events(grid_graph):
    with pytest.raises(AlgorithmError, match="not an event"):
        run(scripted(("visit", 0), Done([0, 1])), grid_graph, 0, 1)


@pytest.mark.parametrize(
    "path, goal, problem",
    [
        ([], 1, "must run from"),
        ([1, 2], 2, "must run from"),  # doesn't start at the start
        ([0, 1], 2, "must run from"),  # doesn't end at the goal
        ([0, 4, 1], 1, "not an edge"),  # 0 and 4 are diagonal, not connected
    ],
)
def test_rejects_invalid_paths(grid_graph, path, goal, problem):
    with pytest.raises(AlgorithmError, match=problem):
        run(scripted(Done(path)), grid_graph, 0, goal)


def test_accepts_no_route(grid_graph):
    result = run(scripted(Done(None)), grid_graph, 0, 8)

    assert result.path is None
    assert result.distance_m is None


START = Discover(0, None)


@pytest.mark.parametrize(
    "events, problem",
    [
        ([Discover(1, None)], "first forward event"),
        ([Discover(0, 4)], "first forward event"),
        ([START, Discover(1, None)], "no parent"),
        ([START, Discover(1, 0)], "hasn't been visited"),  # 0 discovered but not visited
        ([START, Visit(1)], "never discovered"),
        ([START, Visit(0), Visit(0)], "second time"),
        ([START, Visit(0), Discover(10**9, 0)], "not in the graph"),
        ([START, Visit(0), Discover(-1, 0)], "not in the graph"),
        ([START, Visit(0), Discover(True, 0)], "not in the graph"),
        ([START, Visit(0, "sideways")], "side"),
        ([START, Discover(8, None, "backward")], "first backward event"),
    ],
)
def test_rejects_traces_that_break_the_rules(grid_graph, events, problem):
    with pytest.raises(AlgorithmError, match=problem):
        run(scripted(*events, Done(None)), grid_graph, 0, 2)


def test_accepts_a_valid_bidirectional_trace(grid_graph):
    events = [
        Discover(0, None),
        Discover(2, None, "backward"),
        Visit(0),
        Discover(1, 0),
        Visit(2, "backward"),
        Discover(1, 2, "backward"),
        Done([0, 1, 2]),
    ]

    result = run(scripted(*events), grid_graph, 0, 2)

    assert result.distance_m == 200.0
    assert result.visited == 2
    assert result.discovered == 4  # 0 and 1 forward, 2 and 1 backward


def test_rediscovery_counts_each_node_once(grid_graph):
    events = [START, Visit(0), Discover(1, 0), Discover(3, 0), Visit(1), Discover(3, 1), Done(None)]

    assert run(scripted(*events), grid_graph, 0, 8).discovered == 3


def test_stops_an_algorithm_that_never_finishes(grid_graph):
    # Stays within the event rules, so only the event limit can stop it.
    def rediscovers_forever(graph, start, goal):
        yield Discover(start, None)
        yield Visit(start)
        while True:
            yield Discover(1, start)

    with pytest.raises(AlgorithmError, match="looping"):
        run(rediscovers_forever, grid_graph, 0, 8)
    assert max_events(grid_graph) < 1000


def test_enforces_the_time_limit():
    # Enough nodes that the event limit (20,000+) isn't what stops it.
    big = WalkGraph.from_edges([(float(i), 0.0) for i in range(5000)], [])

    def slow(graph, start, goal):
        yield Discover(start, None)
        yield Visit(start)
        for _ in range(5000):
            time.sleep(0.0001)
            yield Discover(1, start)
        yield Done(None)

    with pytest.raises(AlgorithmError, match="longer than"):
        run(slow, big, 0, 1, time_limit_s=0.05)


def test_crashes_become_algorithm_errors(grid_graph):
    def crashes(graph, start, goal):
        yield Discover(start, None)
        raise KeyError(42)

    with pytest.raises(AlgorithmError, match="crashed with KeyError"):
        run(crashes, grid_graph, 0, 8)


def test_stubs_are_reported_as_not_implemented(grid_graph):
    def stub(graph, start, goal):
        raise NotImplementedError("write me")
        yield

    with pytest.raises(AlgorithmNotImplemented, match="write me"):
        run(stub, grid_graph, 0, 8)


@pytest.mark.parametrize("path", [5, "01", (0, 1), iter([0, 1]), [0, 1.0], [0, True]])
def test_rejects_paths_that_are_not_lists_of_ints(grid_graph, path):
    with pytest.raises(AlgorithmError, match="list of node ids"):
        run(scripted(Done(path)), grid_graph, 0, 1)


def test_rejects_paths_through_missing_nodes(grid_graph):
    with pytest.raises(AlgorithmError, match="not in the graph"):
        run(scripted(Done([0, 99, 1])), grid_graph, 0, 1)


def test_records_a_trace_only_when_asked(grid_graph):
    from algorithms import dijkstra
    from algorithms.runner import DISCOVER, VISIT

    plain = run(dijkstra.search, grid_graph, 0, 2)
    recorded = run(dijkstra.search, grid_graph, 0, 2, record=True)

    assert plain.trace is None
    trace = recorded.trace
    assert len(trace) == len(trace.nodes) == len(trace.parents)
    assert (trace.codes[0], trace.nodes[0], trace.parents[0]) == (DISCOVER, 0, -1)
    assert (trace.codes[1], trace.nodes[1], trace.parents[1]) == (VISIT, 0, -1)
    assert recorded.path == plain.path


def test_trace_marks_backward_events():
    from algorithms.runner import DISCOVER, DISCOVER_BACKWARD, VISIT, VISIT_BACKWARD

    events = [
        Discover(0, None),
        Discover(2, None, "backward"),
        Visit(0),
        Discover(1, 0),
        Visit(2, "backward"),
        Discover(1, 2, "backward"),
        Done([0, 1, 2]),
    ]
    graph = WalkGraph.from_edges([(0, 0), (1, 0), (2, 0)], [(0, 1, 1.0), (1, 0, 1.0), (1, 2, 1.0), (2, 1, 1.0)])

    trace = run(scripted(*events), graph, 0, 2, record=True).trace

    assert list(trace.codes) == [DISCOVER, DISCOVER_BACKWARD, VISIT, DISCOVER, VISIT_BACKWARD, DISCOVER_BACKWARD]
    assert list(trace.parents) == [-1, -1, -1, 0, -1, 2]


def test_recording_stops_at_the_limit_but_counting_does_not(grid_graph):
    from algorithms import dijkstra

    full = run(dijkstra.search, grid_graph, 0, 8, record=True)
    capped = run(dijkstra.search, grid_graph, 0, 8, record=True, record_limit=5)
    exact = run(dijkstra.search, grid_graph, 0, 8, record=True, record_limit=len(full.trace))

    assert len(capped.trace) == 5
    assert capped.trace.total == len(full.trace)
    assert capped.trace.truncated
    assert not exact.trace.truncated
    assert not full.trace.truncated
    assert list(capped.trace.nodes) == list(full.trace.nodes)[:5]
