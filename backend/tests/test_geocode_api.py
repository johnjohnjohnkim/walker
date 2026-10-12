import pytest
from django.core.cache import caches

from routing import geocode

from .fakes import FakeGeocoder


def clear_caches():
    caches["geocode"].clear()
    caches["ratelimit"].clear()


@pytest.fixture(autouse=True)
def clean_state(settings):
    # A generous provider budget, so only the tests about it hit it.
    settings.WALKER_GEOCODER_MAX_PER_S = 1000
    settings.WALKER_GEOCODER_BURST = 1000
    clear_caches()
    geocode.upstream.reset()
    FakeGeocoder.calls.clear()
    FakeGeocoder.fail = False
    yield
    clear_caches()
    geocode.upstream.reset()


def test_returns_matching_places(client, graph_file):
    response = client.get("/api/geocode", {"q": "CN Tower"})

    assert response.status_code == 200
    assert response.json() == {
        "results": [{"name": "CN Tower", "address": "290 Bremner Boulevard, Toronto", "lon": -79.3871, "lat": 43.6426}]
    }


def test_searches_inside_the_graph_area(client, settings, tmp_path):
    from graph import WalkGraph
    from routing import graph_store

    path = tmp_path / "g.walkgraph"
    WalkGraph.from_edges([(-79.4, 43.6), (-79.3, 43.7)], [], meta={"bbox": [-79.41, 43.63, -79.34, 43.67]}).save(path)
    settings.WALKER_GRAPH_PATH = path
    graph_store.reset()
    try:
        client.get("/api/geocode", {"q": "union"})
    finally:
        graph_store.reset()

    assert FakeGeocoder.calls[-1][1] == (-79.41, 43.63, -79.34, 43.67)


def test_falls_back_to_toronto_without_a_graph(client, missing_graph_file):
    client.get("/api/geocode", {"q": "union"})

    assert FakeGeocoder.calls[-1][1] == geocode.TORONTO_BBOX


def test_normalizes_and_caches_queries(client, graph_file):
    client.get("/api/geocode", {"q": "  CN   Tower "})
    client.get("/api/geocode", {"q": "cn tower"})

    assert [call[0] for call in FakeGeocoder.calls] == ["cn tower"]


@pytest.mark.parametrize("params", [{}, {"q": "a"}, {"q": "x" * 201}, {"q": "cn", "limit": "lots"}])
def test_rejects_bad_queries(client, graph_file, params):
    response = client.get("/api/geocode", params)

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"
    assert FakeGeocoder.calls == []


def test_clamps_the_limit(client, graph_file):
    client.get("/api/geocode", {"q": "cn", "limit": "500"})
    client.get("/api/geocode", {"q": "union", "limit": "0"})

    assert [call[2] for call in FakeGeocoder.calls] == [8, 1]


def test_reports_an_outage(client, graph_file):
    FakeGeocoder.fail = True

    response = client.get("/api/geocode", {"q": "cn"})

    assert response.status_code == 503
    assert response.json()["code"] == "geocoder_unavailable"


def test_outages_are_not_cached(client, graph_file, monkeypatch):
    monkeypatch.setattr(geocode, "CIRCUIT_OPEN_S", 0.0)
    FakeGeocoder.fail = True
    client.get("/api/geocode", {"q": "cn"})
    FakeGeocoder.fail = False

    assert client.get("/api/geocode", {"q": "cn"}).status_code == 200


def test_stops_calling_a_failing_provider_for_a_while(client, graph_file):
    FakeGeocoder.fail = True
    assert client.get("/api/geocode", {"q": "cn"}).status_code == 503
    FakeGeocoder.fail = False

    response = client.get("/api/geocode", {"q": "union"})

    assert response.status_code == 503
    assert len(FakeGeocoder.calls) == 1  # the second search never reached it


def test_caps_requests_to_the_provider(client, graph_file, settings):
    settings.WALKER_GEOCODER_MAX_PER_S = 0.001
    settings.WALKER_GEOCODER_BURST = 2
    geocode.upstream.reset()

    statuses = [client.get("/api/geocode", {"q": q}).status_code for q in ("cn", "union", "tower")]

    assert statuses == [200, 200, 429]
    assert len(FakeGeocoder.calls) == 2


def test_cached_answers_do_not_use_the_provider_budget(client, graph_file, settings):
    settings.WALKER_GEOCODER_MAX_PER_S = 0.001
    settings.WALKER_GEOCODER_BURST = 1
    geocode.upstream.reset()

    statuses = [client.get("/api/geocode", {"q": "cn"}).status_code for _ in range(4)]

    assert statuses == [200, 200, 200, 200]
    assert len(FakeGeocoder.calls) == 1


def test_rate_limits_each_client(client, graph_file, settings):
    settings.WALKER_GEOCODE_RATE = 3

    statuses = [client.get("/api/geocode", {"q": f"cn{i}"}).status_code for i in range(5)]

    assert statuses == [200, 200, 200, 429, 429]
    other = client.get("/api/geocode", {"q": "cn"}, REMOTE_ADDR="10.0.0.2")
    assert other.status_code == 200


def test_provider_is_chosen_by_settings(client, graph_file, settings):
    settings.WALKER_GEOCODER = "tests.fakes.OtherGeocoder"

    response = client.get("/api/geocode", {"q": "anything"})

    assert response.json()["results"][0]["name"] == "Somewhere else"


def test_post_is_not_allowed(client):
    assert client.post("/api/geocode").status_code == 405
