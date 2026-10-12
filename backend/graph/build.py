"""Download a walkable street network from OpenStreetMap and save it as a graph.

Run once per area, from the backend directory:

    uv run python -m graph.build --area toronto     # whole city, about 2 minutes
    uv run python -m graph.build --area downtown    # small, for quick work and tests

This is the only code that touches the network or OSMnx. The server just
loads the file it writes.
"""

from __future__ import annotations

import argparse
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

from .areas import AREAS, Area
from .graph import WalkGraph

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def default_path(area_name: str) -> Path:
    return DATA_DIR / f"{area_name}.walkgraph"


def from_osmnx(nx_graph, meta: dict | None = None) -> WalkGraph:
    """Convert an OSMnx MultiDiGraph into a WalkGraph.

    Keeps only the largest strongly connected component, so every node can
    reach every other node. Without this, a footpath island inside a park could
    become an origin with no route out.
    """
    import networkx as nx

    if nx_graph.number_of_nodes() == 0:
        raise ValueError("the downloaded graph is empty")

    keep = max(nx.strongly_connected_components(nx_graph), key=len)
    osm_ids = sorted(keep)
    index = {osm_id: i for i, osm_id in enumerate(osm_ids)}

    coords = [(float(nx_graph.nodes[n]["x"]), float(nx_graph.nodes[n]["y"])) for n in osm_ids]
    edges = []
    geometries: dict[tuple[int, int], list[tuple[float, float]]] = {}
    shortest: dict[tuple[int, int], float] = {}
    for u, v, data in nx_graph.edges(data=True):
        if u not in index or v not in index or u == v:
            continue
        key = (index[u], index[v])
        length = float(data["length"])
        edges.append((key[0], key[1], length))
        # Parallel edges collapse to the shortest; keep that one's shape.
        if key not in shortest or length < shortest[key]:
            shortest[key] = length
            geometry = data.get("geometry")
            if geometry is not None:
                geometries[key] = [(float(x), float(y)) for x, y in geometry.coords[1:-1]]
            else:
                geometries.pop(key, None)

    return WalkGraph.from_edges(coords, edges, geometries=geometries, meta=meta)


def download(area: Area):
    import osmnx as ox

    # OSMnx caches raw API responses; keep them with the other ignored data
    # rather than in a `cache/` folder wherever the command happens to run.
    ox.settings.cache_folder = DATA_DIR / "osm-cache"
    return ox.graph_from_bbox(area.bbox, network_type="walk", simplify=True, retain_all=True)


def build(area: Area, out: Path) -> WalkGraph:
    import osmnx as ox

    started = time.perf_counter()
    nx_graph = download(area)
    downloaded = time.perf_counter()
    graph = from_osmnx(
        nx_graph,
        meta={
            "area": area.name,
            "bbox": list(area.bbox),
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "source": "OpenStreetMap contributors, via OSMnx " + ox.__version__,
        },
    )
    graph.save(out)
    finished = time.perf_counter()

    print(f"area:        {area.name} {area.bbox}")
    print(f"downloaded:  {nx_graph.number_of_nodes():,} nodes, {nx_graph.number_of_edges():,} edges "
          f"in {downloaded - started:.1f} s")
    print(f"kept:        {graph.node_count:,} nodes, {graph.edge_count:,} edges (largest connected part)")
    print(f"wrote:       {out} ({out.stat().st_size / 1e6:.1f} MB) in {finished - downloaded:.1f} s")
    return graph


def measure_load(path: Path) -> None:
    """Print how long the server will take to load the file and how much memory it uses.

    Timed and memory-measured in separate loads: tracemalloc slows Python down
    several times, so timing a traced load would overstate it.
    """
    from .spatial import NodeIndex

    started = time.perf_counter()
    graph = WalkGraph.load(path)
    loaded = time.perf_counter()
    NodeIndex(graph)
    indexed = time.perf_counter()
    del graph

    tracemalloc.start()
    graph = WalkGraph.load(path)
    index = NodeIndex(graph)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del graph, index
    print(f"load:        {loaded - started:.2f} s, spatial index {indexed - loaded:.2f} s")
    print(f"memory:      {current / 1e6:.1f} MB held, {peak / 1e6:.1f} MB peak (graph + index)")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--area", choices=sorted(AREAS), default="toronto")
    parser.add_argument("--out", type=Path, help="output file (default: data/<area>.walkgraph)")
    args = parser.parse_args(argv)

    out = args.out or default_path(args.area)
    build(AREAS[args.area], out)
    measure_load(out)


if __name__ == "__main__":
    main()
