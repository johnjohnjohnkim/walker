import sys
import zipfile
from array import array

import pytest

from graph import WalkGraph
from graph.graph import GraphFormatError

from .conftest import grid_coords


def test_neighbors_lists_outgoing_edges(grid_graph):
    assert sorted(grid_graph.neighbors(4)) == [(1, 100.0), (3, 100.0), (5, 100.0), (7, 100.0)]
    assert sorted(grid_graph.neighbors(0)) == [(1, 100.0), (3, 100.0)]


def test_counts(grid_graph):
    assert grid_graph.node_count == 9
    assert grid_graph.edge_count == 24


def test_edges_are_directed():
    graph = WalkGraph.from_edges([(0, 0), (1, 0)], [(0, 1, 5.0)])

    assert list(graph.neighbors(0)) == [(1, 5.0)]
    assert list(graph.neighbors(1)) == []


def test_duplicate_edges_keep_the_shortest():
    graph = WalkGraph.from_edges([(0, 0), (1, 0)], [(0, 1, 9.0), (0, 1, 4.0), (0, 1, 7.0)])

    assert list(graph.neighbors(0)) == [(1, 4.0)]


def test_rejects_bad_edges():
    with pytest.raises(ValueError):
        WalkGraph.from_edges([(0, 0)], [(0, 1, 1.0)])
    with pytest.raises(ValueError):
        WalkGraph.from_edges([(0, 0), (1, 0)], [(0, 1, -1.0)])


def test_edge_geometry_includes_endpoints_and_bends():
    coords = [(0.0, 0.0), (1.0, 1.0)]
    graph = WalkGraph.from_edges(coords, [(0, 1, 10.0), (1, 0, 10.0)], geometries={(0, 1): [(0.0, 1.0)]})

    forward = graph.find_edge(0, 1)
    back = graph.find_edge(1, 0)
    assert graph.edge_geometry(forward) == [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    assert graph.edge_geometry(back) == [(1.0, 1.0), (0.0, 0.0)]


def test_edge_geometry_finds_source_past_nodes_without_edges():
    # Node 1 has no outgoing edges, so offsets repeat around it.
    graph = WalkGraph.from_edges([(0, 0), (1, 0), (2, 0)], [(0, 1, 1.0), (2, 1, 1.0)])

    assert graph.edge_geometry(graph.find_edge(2, 1)) == [(2, 0), (1, 0)]


def test_path_geometry_joins_edges_without_repeating_nodes(grid_graph):
    line = grid_graph.path_geometry([0, 1, 4])

    coords = grid_coords()
    assert line == [coords[0], coords[1], coords[4]]


def test_path_geometry_rejects_missing_edges(grid_graph):
    with pytest.raises(ValueError):
        grid_graph.path_geometry([0, 4])


def test_save_and_load_round_trip(tmp_path):
    coords = [(-79.0, 43.0), (-79.1, 43.1), (-79.2, 43.2)]
    original = WalkGraph.from_edges(
        coords,
        [(0, 1, 12.5), (1, 2, 3.25), (2, 0, 7.0)],
        geometries={(1, 2): [(-79.15, 43.12), (-79.17, 43.15)]},
        meta={"area": "round-trip"},
    )
    path = tmp_path / "g.walkgraph"
    original.save(path)

    loaded = WalkGraph.load(path)

    assert loaded.meta == {"area": "round-trip"}
    for name in ("lon", "lat", "offsets", "targets", "weights", "geometry_offsets", "geometry_coords"):
        assert getattr(loaded, name) == getattr(original, name)


def test_load_rejects_other_files(tmp_path):
    junk = tmp_path / "junk.walkgraph"
    junk.write_text("not a zip")
    with pytest.raises(GraphFormatError):
        WalkGraph.load(junk)


def test_load_rejects_other_versions(tmp_path, grid_graph):
    path = tmp_path / "old.walkgraph"
    grid_graph.save(path)
    rewritten = tmp_path / "rewritten.walkgraph"
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(rewritten, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == "header.json":
                data = data.replace(b'"version": 1', b'"version": 99')
            dst.writestr(item, data)

    with pytest.raises(GraphFormatError, match="rebuild"):
        WalkGraph.load(rewritten)


def test_incoming_lists_edges_arriving_at_a_node():
    # 0 -> 1 is one-way; 1 <-> 2 is two-way with different lengths each way.
    graph = WalkGraph.from_edges([(0, 0), (1, 0), (2, 0)], [(0, 1, 5.0), (1, 2, 3.0), (2, 1, 4.0)])

    assert sorted(graph.incoming(1)) == [(0, 5.0), (2, 4.0)]
    assert sorted(graph.incoming(2)) == [(1, 3.0)]
    assert list(graph.incoming(0)) == []


def test_incoming_mirrors_neighbors(grid_graph):
    forward = sorted((u, v, w) for u in range(9) for v, w in grid_graph.neighbors(u))
    backward = sorted((u, v, w) for v in range(9) for u, w in grid_graph.incoming(v))

    assert forward == backward


def _rewrite(path, out, change):
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(out, "w") as dst:
        for item in src.infolist():
            dst.writestr(item, change(item.filename, src.read(item)))


def test_load_rejects_a_corrupt_header(tmp_path, grid_graph):
    path = tmp_path / "g.walkgraph"
    grid_graph.save(path)

    broken_json = tmp_path / "broken.walkgraph"
    _rewrite(path, broken_json, lambda name, data: b"{not json" if name == "header.json" else data)
    with pytest.raises(GraphFormatError):
        WalkGraph.load(broken_json)

    missing_key = tmp_path / "missing.walkgraph"
    _rewrite(path, missing_key, lambda name, data: data.replace(b'"node_count"', b'"nodes"'))
    with pytest.raises(GraphFormatError):
        WalkGraph.load(missing_key)


def test_load_rejects_edges_to_missing_nodes(tmp_path):
    graph = WalkGraph.from_edges([(0, 0), (1, 0)], [(0, 1, 1.0)])
    path = tmp_path / "g.walkgraph"
    graph.save(path)
    bad = tmp_path / "bad.walkgraph"
    _rewrite(path, bad, lambda name, data: (7).to_bytes(4, sys.byteorder) if name == "targets.bin" else data)

    with pytest.raises(GraphFormatError):
        WalkGraph.load(bad)


def test_load_reads_files_from_the_other_byte_order(tmp_path):
    graph = WalkGraph.from_edges([(-79.0, 43.0), (-79.1, 43.1)], [(0, 1, 12.5), (1, 0, 12.5)])
    path = tmp_path / "g.walkgraph"
    graph.save(path)
    other = "big" if sys.byteorder == "little" else "little"

    def swap(name, data):
        if name == "header.json":
            return data.replace(f'"byteorder": "{sys.byteorder}"'.encode(), f'"byteorder": "{other}"'.encode())
        code = {"lon": "d", "lat": "d", "weights": "d", "geometry_coords": "d"}.get(name.removesuffix(".bin"), "i")
        arr = array(code)
        arr.frombytes(data)
        arr.byteswap()
        return arr.tobytes()

    swapped = tmp_path / "swapped.walkgraph"
    _rewrite(path, swapped, swap)

    loaded = WalkGraph.load(swapped)
    assert list(loaded.neighbors(0)) == [(1, 12.5)]
    assert loaded.coord(1) == (-79.1, 43.1)


def test_save_leaves_no_temporary_files(tmp_path, grid_graph):
    grid_graph.save(tmp_path / "g.walkgraph")
    grid_graph.save(tmp_path / "g.walkgraph")  # overwrite

    assert [p.name for p in tmp_path.iterdir()] == ["g.walkgraph"]
