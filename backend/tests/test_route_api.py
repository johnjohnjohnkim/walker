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
    assert body["search"]["visited"] >= 5


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
