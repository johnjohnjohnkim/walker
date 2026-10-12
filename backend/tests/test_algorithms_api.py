import json

import pytest

from algorithms import BY_ID, REGISTRY, is_implemented

from .test_route_api import point


def test_lists_every_algorithm_in_order(client):
    response = client.get("/api/algorithms")

    assert response.status_code == 200
    listed = response.json()["algorithms"]
    assert [a["id"] for a in listed] == [a.id for a in REGISTRY]
    dijkstra = listed[0]
    assert dijkstra == {
        "id": "dijkstra",
        "name": "Dijkstra",
        "description": BY_ID["dijkstra"].description,
        "guarantee": "shortest",
        "uses_lengths": True,
        "bidirectional": False,
        "implemented": True,
    }


def test_reports_which_algorithms_are_implemented(client):
    listed = {a["id"]: a["implemented"] for a in client.get("/api/algorithms").json()["algorithms"]}

    assert listed == {a.id: a.implemented for a in REGISTRY}
    assert listed["dijkstra"] is True


@pytest.mark.parametrize("algorithm", [a for a in REGISTRY if not a.implemented], ids=lambda a: a.id)
def test_routing_with_a_stub_returns_501(client, graph_file, algorithm):
    body = {"origin": point(0, 0), "destination": point(2, 2), "algorithm": algorithm.id}

    response = client.post("/api/route", data=json.dumps(body), content_type="application/json")

    assert response.status_code == 501
    assert response.json()["code"] == "not_implemented"


def test_is_implemented_detects_stubs():
    def stub(graph, start, goal):
        raise NotImplementedError
        yield

    def crashes(graph, start, goal):
        raise ValueError("bug")
        yield

    def loops_after_starting(graph, start, goal):
        from algorithms.events import Discover

        yield Discover(start, None)
        while True:
            pass

    assert is_implemented(BY_ID["dijkstra"].search)
    assert not is_implemented(stub)
    # A buggy algorithm still counts as implemented, so its error is shown.
    assert is_implemented(crashes)
    # Only the first event is requested, so a later infinite loop can't hang the check.
    assert is_implemented(loops_after_starting)


def test_post_is_not_allowed(client):
    assert client.post("/api/algorithms").status_code == 405
