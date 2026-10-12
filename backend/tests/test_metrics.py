import json

import pytest

from algorithms import dijkstra
from algorithms.events import Discover, Done, Visit
from algorithms.metrics import MAX_RUNS, peak_memory_bytes, time_search
from algorithms.runner import run
from graph import WalkGraph

from .test_route_api import point


def line(n):
    coords = [(i * 0.001, 0.0) for i in range(n)]
    edges = [e for i in range(n - 1) for e in ((i, i + 1, 100.0), (i + 1, i, 100.0))]
    return WalkGraph.from_edges(coords, edges)


def scripted(*events):
    def search(graph, start, goal):
        yield from events

    return search


def test_counts_on_a_hand_checked_trace():
    # 0 -> {1, 2}; 1 -> 3; then 2 is improved via 1; goal 3.
    graph = WalkGraph.from_edges(
        [(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 1, 1.0), (0, 2, 9.0), (1, 2, 1.0), (1, 3, 1.0), (2, 3, 1.0)]
    )
    events = [
        Discover(0, None),  # waiting {0}
        Visit(0),  # waiting {}
        Discover(1, 0),  # {1}
        Discover(2, 0),  # {1, 2}
        Visit(1),  # {2}
        Discover(2, 1),  # {2} rediscovered
        Discover(3, 1),  # {2, 3}
        Visit(3),
        Done([0, 1, 3]),
    ]

    result = run(scripted(*events), graph, 0, 3)

    assert result.visited == 3
    assert result.discovered == 4
    assert result.frontier_pushes == 5
    assert result.peak_frontier == 2


def test_bidirectional_frontier_counts_both_sides():
    graph = WalkGraph.from_edges([(0, 0), (1, 0), (2, 0)], [(0, 1, 1.0), (1, 0, 1.0), (1, 2, 1.0), (2, 1, 1.0)])
    events = [
        Discover(0, None),
        Discover(2, None, "backward"),  # waiting: 0 forward, 2 backward
        Visit(0),
        Discover(1, 0),
        Visit(2, "backward"),
        Discover(1, 2, "backward"),  # waiting: 1 forward, 1 backward
        Done([0, 1, 2]),
    ]

    assert run(scripted(*events), graph, 0, 2).peak_frontier == 2


def test_dijkstra_on_a_line_never_has_more_than_one_waiting():
    result = run(dijkstra.search, line(50), 0, 49)

    assert result.peak_frontier == 1
    assert result.visited == 50


def events_of(search, graph, start, goal):
    return run(search, graph, start, goal).events


def test_timing_repeats_short_searches_and_reports_milliseconds():
    graph = line(20)
    timing = time_search(dijkstra.search, graph, 0, 19, expected_events=events_of(dijkstra.search, graph, 0, 19))

    assert timing.runs == MAX_RUNS
    assert 0 < timing.wall_ms < 1000
    assert 0 <= timing.cpu_ms < 1000


def test_timing_runs_long_searches_once(monkeypatch):
    from algorithms import metrics

    monkeypatch.setattr(metrics, "TIMING_BUDGET_S", 0.0)

    graph = line(20)
    assert time_search(dijkstra.search, graph, 0, 19, expected_events=events_of(dijkstra.search, graph, 0, 19)).runs == 1


def test_timing_runs_without_checking_or_recording():
    calls = []

    def counted(graph, start, goal):
        calls.append(1)
        yield from dijkstra.search(graph, start, goal)

    graph = line(5)
    time_search(counted, graph, 0, 4, expected_events=events_of(dijkstra.search, graph, 0, 4))

    assert len(calls) >= 1  # it really ran the algorithm itself


def test_peak_memory_grows_with_the_search():
    small_graph, big_graph = line(10), line(3000)
    small = peak_memory_bytes(dijkstra.search, small_graph, 0, 9, expected_events=events_of(dijkstra.search, small_graph, 0, 9))
    big = peak_memory_bytes(
        dijkstra.search, big_graph, 0, 2999, expected_events=events_of(dijkstra.search, big_graph, 0, 2999)
    )

    assert 0 < small < big


def test_route_response_includes_metrics(client, graph_file):
    body = json.loads(
        client.post(
            "/api/route",
            data=json.dumps({"origin": point(0, 0), "destination": point(2, 2)}),
            content_type="application/json",
        ).content
    )

    metrics = body["metrics"]
    assert metrics["path_nodes"] == 5
    assert metrics["optimal_distance_m"] == 400.0
    assert metrics["extra_distance_pct"] == 0.0
    assert metrics["is_shortest"] is True
    assert metrics["timing_runs"] >= 1
    assert metrics["wall_ms"] > 0
    assert metrics["peak_memory_bytes"] > 0
    assert metrics["visited"] >= 5
    assert metrics["frontier_pushes"] >= metrics["discovered"]
    assert metrics["peak_frontier"] >= 1


def test_longer_routes_are_compared_with_the_shortest(client, graph_file, monkeypatch):
    import algorithms

    # A "search" that walks the long way round the grid: 0-3-6-7-8-5-2-1 then to 4.
    def detour(graph, start, goal):
        path = [0, 3, 6, 7, 8, 5, 2, 1, 4]
        yield Discover(path[0], None)
        for a, b in zip(path, path[1:]):
            yield Visit(a)
            yield Discover(b, a)
        yield Done(path)

    monkeypatch.setitem(algorithms.ALGORITHMS, "detour", detour)
    body = json.loads(
        client.post(
            "/api/route",
            data=json.dumps({"origin": point(0, 0), "destination": point(1, 1), "algorithm": "detour"}),
            content_type="application/json",
        ).content
    )

    metrics = body["metrics"]
    assert body["route"]["distance_m"] == 800.0
    assert metrics["optimal_distance_m"] == 200.0
    assert metrics["extra_distance_pct"] == pytest.approx(300.0)
    assert metrics["extra_distance_m"] == 600.0
    assert metrics["is_shortest"] is False


def post_route(client, algorithm, origin=(0, 0), destination=(2, 2)):
    return client.post(
        "/api/route",
        data=json.dumps({"origin": point(*origin), "destination": point(*destination), "algorithm": algorithm}),
        content_type="application/json",
    )


def test_an_algorithm_that_keeps_state_between_runs_is_reported(client, graph_file, monkeypatch):
    import algorithms

    seen_before = set()

    def remembers(graph, start, goal):
        # Skips nodes it explored in earlier runs: fine once, wrong after.
        first_time = start not in seen_before
        seen_before.add(start)
        yield from dijkstra.search(graph, start, goal) if first_time else iter([Done([start])])

    monkeypatch.setitem(algorithms.ALGORITHMS, "remembers", remembers)

    response = post_route(client, "remembers")

    assert response.status_code == 500
    assert response.json()["code"] == "algorithm_error"


def test_an_algorithm_that_loops_on_a_repeat_run_cannot_hang_the_server(client, graph_file, monkeypatch):
    import algorithms

    runs = []

    def loops_later(graph, start, goal):
        runs.append(1)
        if len(runs) == 1:
            yield from dijkstra.search(graph, start, goal)
            return
        yield Discover(start, None)
        while True:  # stays within the event rules a clean run doesn't check
            yield Visit(start)

    monkeypatch.setitem(algorithms.ALGORITHMS, "loops-later", loops_later)

    response = post_route(client, "loops-later")

    assert response.status_code == 500
    assert response.json()["code"] == "algorithm_error"


def test_repeat_requests_reuse_the_measurements(client, graph_file, monkeypatch):
    import algorithms

    runs = []

    def counted(graph, start, goal):
        runs.append(1)
        yield from dijkstra.search(graph, start, goal)

    monkeypatch.setitem(algorithms.ALGORITHMS, "counted", counted)

    first = post_route(client, "counted").json()["metrics"]
    after_first = len(runs)
    second = post_route(client, "counted").json()["metrics"]

    assert after_first >= 3  # checked run, timing runs, memory run
    assert len(runs) == after_first + 1  # only the checked run again
    assert second["wall_ms"] == first["wall_ms"]


def test_a_slightly_longer_route_is_not_called_the_shortest(client, graph_file, monkeypatch):
    from routing import views

    # Pretend the shortest route is a hair shorter than the one returned.
    real_measure = views._measure

    def nearly(*args):
        timing, memory, optimal = real_measure(*args)
        return timing, memory, optimal - 0.5

    monkeypatch.setattr(views, "_measure", nearly)

    metrics = post_route(client, "dijkstra").json()["metrics"]

    assert metrics["is_shortest"] is False
    assert metrics["extra_distance_m"] == 0.5
