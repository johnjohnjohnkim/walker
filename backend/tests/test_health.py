from routing import graph_store


def test_health_reports_loaded_graph(client, graph_file):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["graph"]["area"] == "test-grid"
    assert body["graph"]["nodes"] == 9
    assert body["graph"]["edges"] == 24


def test_health_is_degraded_without_graph(client, missing_graph_file):
    response = client.get("/api/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["graph"] is None
    # Debug is off in tests, so no server paths leak.
    assert "nope.walkgraph" not in body["detail"]


def test_health_recovers_once_graph_is_built(client, missing_graph_file, settings, grid_graph, monkeypatch):
    monkeypatch.setattr(graph_store, "RETRY_AFTER_S", 0.0)
    assert client.get("/api/health").status_code == 503

    grid_graph.save(settings.WALKER_GRAPH_PATH)

    assert client.get("/api/health").status_code == 200


def test_failed_load_is_not_retried_immediately(client, missing_graph_file, settings, grid_graph):
    assert client.get("/api/health").status_code == 503

    grid_graph.save(settings.WALKER_GRAPH_PATH)

    # Still inside the retry window, so the new file isn't read yet.
    assert client.get("/api/health").status_code == 503


def test_health_is_degraded_for_a_corrupt_graph(client, settings, tmp_path):
    path = tmp_path / "corrupt.walkgraph"
    path.write_bytes(b"PK\x03\x04 definitely not a graph")
    settings.WALKER_GRAPH_PATH = path
    graph_store.reset()
    try:
        assert client.get("/api/health").status_code == 503
    finally:
        graph_store.reset()


def test_health_rejects_post(client):
    response = client.post("/api/health")

    assert response.status_code == 405


def test_unknown_path_returns_json_404(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": "Not found."}
