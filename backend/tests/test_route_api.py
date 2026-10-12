import json

import pytest

import algorithms
from algorithms.events import Done

from .conftest import GRID_ORIGIN, GRID_STEP_LAT, GRID_STEP_LON


def point(col, row, nudge=0.00003):
    """A point a few metres off grid node (col, row)."""
    lon0, lat0 = GRID_ORIGIN
    return {"lon": lon0 + col * GRID_STEP_LON + nudge, "lat": lat0 + row * GRID_STEP_LAT + nudge}


def post(client, body):
    return client.post("/api/route", data=json.dumps(body), content_type="application/json")


def test_finds_a_route_across_the_grid(client, graph_file):
    response = post(client, {"origin": point(0, 0), "destination": point(2, 2), "algorithm": "dijkstra"})

    assert response.status_code == 200
    body = response.json()
    assert body["algorithm"] == "dijkstra"
    assert body["route"]["distance_m"] == 400.0
    assert body["route"]["duration_s"] == round(400 / 1.4)
    assert body["route"]["nodes"] == 5
    coords = body["route"]["coordinates"]
    assert coords[0] == body["origin"]["snapped"]
    assert coords[-1] == body["destination"]["snapped"]
    assert 0 < body["origin"]["snap_distance_m"] < 10
    assert body["metrics"]["visited"] >= 5


def test_algorithm_defaults_to_dijkstra(client, graph_file):
    response = post(client, {"origin": point(0, 0), "destination": point(1, 0)})

    assert response.status_code == 200
    assert response.json()["algorithm"] == "dijkstra"


def test_same_point_gives_an_empty_route(client, graph_file):
    response = post(client, {"origin": point(1, 1), "destination": point(1, 1)})

    assert response.status_code == 200
    assert response.json()["route"]["distance_m"] == 0.0
    assert response.json()["route"]["nodes"] == 1


def test_points_off_the_map_are_rejected(client, graph_file):
    far = {"lon": GRID_ORIGIN[0], "lat": GRID_ORIGIN[1] - 0.01}  # ~1 km south

    response = post(client, {"origin": point(0, 0), "destination": far})

    assert response.status_code == 422
    assert response.json()["code"] == "outside_coverage"
    assert response.json()["which"] == "destination"


@pytest.mark.parametrize(
    "body",
    [
        {"destination": {"lon": -79.38, "lat": 43.65}},
        {"origin": [1, 2], "destination": {"lon": -79.38, "lat": 43.65}},
        {"origin": {"lon": "x", "lat": 43.65}, "destination": {"lon": -79.38, "lat": 43.65}},
        {"origin": {"lon": True, "lat": 43.65}, "destination": {"lon": -79.38, "lat": 43.65}},
        {"origin": {"lon": -200, "lat": 43.65}, "destination": {"lon": -79.38, "lat": 43.65}},
        {"origin": {"lon": -79.38, "lat": 43.65}, "destination": {"lon": -79.38, "lat": 43.65}, "algorithm": 3},
    ],
)
def test_malformed_requests_are_rejected(client, graph_file, body):
    response = post(client, body)

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_non_finite_numbers_are_rejected(client, graph_file):
    # Python's json module accepts NaN and Infinity literals.
    raw = '{"origin": {"lon": NaN, "lat": 43.65}, "destination": {"lon": -79.38, "lat": Infinity}}'

    response = client.post("/api/route", data=raw, content_type="application/json")

    assert response.status_code == 400


@pytest.mark.parametrize("raw", ["not json", "[1, 2]", "\xff"])
def test_non_object_bodies_are_rejected(client, graph_file, raw):
    response = client.post("/api/route", data=raw, content_type="application/json")

    assert response.status_code == 400


def test_unknown_algorithm(client, graph_file):
    response = post(client, {"origin": point(0, 0), "destination": point(1, 0), "algorithm": "teleport"})

    assert response.status_code == 400
    assert response.json()["code"] == "unknown_algorithm"
    assert "dijkstra" in response.json()["algorithms"]


def test_get_is_not_allowed(client, graph_file):
    assert client.get("/api/route").status_code == 405


def test_missing_graph(client, missing_graph_file):
    response = post(client, {"origin": point(0, 0), "destination": point(1, 0)})

    assert response.status_code == 503
    assert response.json()["code"] == "graph_unavailable"


def test_no_route(client, graph_file, monkeypatch):
    def gives_up(graph, start, goal):
        yield Done(None)

    monkeypatch.setitem(algorithms.ALGORITHMS, "gives-up", gives_up)

    response = post(client, {"origin": point(0, 0), "destination": point(2, 2), "algorithm": "gives-up"})

    assert response.status_code == 422
    assert response.json()["code"] == "no_route"


def test_broken_algorithm_is_reported(client, graph_file, monkeypatch):
    def teleports(graph, start, goal):
        yield Done([start, goal])  # not connected by an edge

    monkeypatch.setitem(algorithms.ALGORITHMS, "teleports", teleports)

    response = post(client, {"origin": point(0, 0), "destination": point(2, 2), "algorithm": "teleports"})

    assert response.status_code == 500
    assert response.json()["code"] == "algorithm_error"


def test_crashing_algorithm_is_reported(client, graph_file, monkeypatch):
    def crashes(graph, start, goal):
        raise RuntimeError("boom")
        yield  # makes this a generator

    monkeypatch.setitem(algorithms.ALGORITHMS, "crashes", crashes)
    client.raise_request_exception = False

    response = post(client, {"origin": point(0, 0), "destination": point(2, 2), "algorithm": "crashes"})

    assert response.status_code == 500
    assert response.json()["code"] == "algorithm_error"
    # Debug is off in tests, so the exception text isn't shown.
    assert "boom" not in response.json()["error"]


def test_stub_algorithm_returns_501(client, graph_file, monkeypatch):
    def stub(graph, start, goal):
        raise NotImplementedError
        yield

    monkeypatch.setitem(algorithms.ALGORITHMS, "stub", stub)

    response = post(client, {"origin": point(0, 0), "destination": point(2, 2), "algorithm": "stub"})

    assert response.status_code == 501
    assert response.json()["code"] == "not_implemented"


def test_huge_numbers_are_rejected(client, graph_file):
    raw = '{"origin": {"lon": 1' + "0" * 400 + ', "lat": 43.65}, "destination": {"lon": -79.38, "lat": 43.65}}'

    response = client.post("/api/route", data=raw, content_type="application/json")

    assert response.status_code == 400


def test_deeply_nested_json_is_rejected(client, graph_file):
    response = client.post("/api/route", data="[" * 100_000, content_type="application/json")

    assert response.status_code == 400


def test_no_trace_unless_asked(client, graph_file):
    response = post(client, {"origin": point(0, 0), "destination": point(2, 2)})

    assert response.json()["trace"] is None


def test_trace_lists_every_event_compactly(client, graph_file):
    response = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True})

    body = response.json()
    trace = body["trace"]
    events = trace["events"]
    assert len(events) == 3 * trace["count"]
    assert trace["truncated"] is False
    # Each node appears once in the coordinate table, and every index is valid.
    assert len(trace["coordinates"]) == len({tuple(c) for c in trace["coordinates"]})
    indexes = events[1::3] + [p for p in events[2::3] if p != -1]
    assert all(0 <= i < len(trace["coordinates"]) for i in indexes)
    # It starts by discovering then visiting the snapped origin.
    assert events[:6] == [0, 0, -1, 1, 0, -1]
    assert trace["coordinates"][0] == body["origin"]["snapped"]
    # Visits match the reported count.
    assert events[0::3].count(1) == body["metrics"]["visited"]


def test_long_traces_are_sampled_evenly(client, graph_file, monkeypatch):
    from routing import views

    full = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True}).json()["trace"]
    monkeypatch.setattr(views, "MAX_TRACE_EVENTS", 4)

    sampled = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True}).json()["trace"]

    stride = -(-full["count"] // 4)
    assert sampled["stride"] == stride
    assert sampled["count"] <= 5  # at most the limit, plus the last event
    assert sampled["total"] == full["total"] == full["count"]
    assert sampled["truncated"] is False
    # Every k-th event, starting with the first, so the whole search is covered.
    assert sampled["events"][:3] == full["events"][:3]
    full_codes = full["events"][0::3]
    expected = full_codes[::stride]
    if (full["count"] - 1) % stride:
        expected.append(full_codes[-1])
    assert sampled["events"][0::3] == expected


def test_sampled_traces_always_end_on_the_last_event(client, graph_file, monkeypatch):
    from routing import views

    full = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True}).json()["trace"]
    # Pick a limit whose stride doesn't land on the last event by itself.
    limit = next(n for n in range(2, full["count"]) if (full["count"] - 1) % -(-full["count"] // n) != 0)
    monkeypatch.setattr(views, "MAX_TRACE_EVENTS", limit)

    sampled = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True}).json()["trace"]

    assert sampled["events"][-3:][0] == full["events"][-3:][0]
    last_node = sampled["coordinates"][sampled["events"][-2]]
    assert last_node == full["coordinates"][full["events"][-2]]


def test_route_requests_are_rate_limited(client, graph_file, settings):
    settings.WALKER_ROUTE_RATE = 2

    statuses = [post(client, {"origin": point(0, 0), "destination": point(1, 0)}).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]
    other = client.post(
        "/api/route",
        data=json.dumps({"origin": point(0, 0), "destination": point(1, 0)}),
        content_type="application/json",
        REMOTE_ADDR="10.0.0.9",
    )
    assert other.status_code == 200


def test_unsampled_traces_say_so(client, graph_file):
    trace = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True}).json()["trace"]

    assert trace["stride"] == 1
    assert trace["total"] == trace["count"]


def test_recording_stops_at_the_memory_guard(client, graph_file, monkeypatch):
    from routing import views

    monkeypatch.setattr(views, "MAX_RECORDED_EVENTS", 4)

    trace = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True}).json()["trace"]

    assert trace["truncated"] is True
    assert trace["count"] == 4
    assert trace["total"] > 4


def test_trace_flag_must_be_boolean(client, graph_file):
    response = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": "yes"})

    assert response.status_code == 400


def test_large_responses_are_compressed(client, graph_file):
    response = client.post(
        "/api/route",
        data=json.dumps({"origin": point(0, 0), "destination": point(2, 2), "trace": True}),
        content_type="application/json",
        HTTP_ACCEPT_ENCODING="gzip",
    )

    assert response["Content-Encoding"] == "gzip"


def test_trace_ends_on_the_returned_route(client, graph_file):
    """Following each node's last discovered parent back from the goal gives
    the route that was drawn, so the animation finishes on the same path."""
    body = post(client, {"origin": point(0, 0), "destination": point(2, 2), "trace": True}).json()
    trace = body["trace"]
    coords = trace["coordinates"]
    events = trace["events"]
    parent = {}
    for i in range(trace["count"]):
        code, node, par = events[3 * i : 3 * i + 3]
        if code == 0:
            parent[node] = par

    goal = coords.index(body["destination"]["snapped"])
    path = [goal]
    while parent[path[-1]] != -1:
        path.append(parent[path[-1]])
    traced = [coords[i] for i in reversed(path)]

    route = body["route"]["coordinates"]
    # The grid has no curved streets, so the route is exactly the node chain.
    assert traced == route
