"""A compact, read-only directed graph of walkable streets.

Nodes are numbered 0..node_count-1. Edges are stored in compressed sparse row
(CSR) form: the outgoing edges of node `u` are edge indices
`offsets[u]` up to (not including) `offsets[u + 1]`, and for each edge index
`e`, `targets[e]` is the node it leads to and `weights[e]` its length in metres.

Using flat `array` buffers instead of a dict of lists keeps memory small and
makes saving and loading a matter of copying bytes, which matters once the
graph covers the whole city.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from array import array
from collections.abc import Iterable, Iterator
from pathlib import Path

FORMAT_NAME = "walker-graph"
FORMAT_VERSION = 1

# Array name -> typecode. 'i' is a 4-byte int and 'd' an 8-byte float on every
# platform we target; both are checked at load time.
_ARRAYS = {
    "lon": "d",
    "lat": "d",
    "offsets": "i",
    "targets": "i",
    "weights": "d",
    "geometry_offsets": "i",
    "geometry_coords": "d",
}


class GraphFormatError(ValueError):
    """The file is not a graph this code can read."""


class WalkGraph:
    """A directed graph with coordinates on nodes and lengths on edges.

    Build one with `WalkGraph.from_edges` (or `graph.build` for OSM data) and
    persist it with `save` / `load`.
    """

    def __init__(
        self,
        *,
        lon: array,
        lat: array,
        offsets: array,
        targets: array,
        weights: array,
        geometry_offsets: array,
        geometry_coords: array,
        meta: dict | None = None,
    ) -> None:
        self.lon = lon
        self.lat = lat
        self.offsets = offsets
        self.targets = targets
        self.weights = weights
        # Intermediate points of curved edges, excluding both endpoints, as a
        # flat lon, lat, lon, lat... list. Edge e owns the pairs from
        # geometry_offsets[e] to geometry_offsets[e + 1].
        self.geometry_offsets = geometry_offsets
        self.geometry_coords = geometry_coords
        self.meta = dict(meta or {})
        self._validate()
        self._build_reverse()

    # ----------------------------------------------------------- construction

    @classmethod
    def from_edges(
        cls,
        coords: list[tuple[float, float]],
        edges: Iterable[tuple[int, int, float]],
        *,
        geometries: dict[tuple[int, int], list[tuple[float, float]]] | None = None,
        meta: dict | None = None,
    ) -> WalkGraph:
        """Build a graph from node coordinates and directed edges.

        `coords[i]` is node i's (lon, lat). Each edge is (source, target,
        length_m). `geometries` optionally maps (source, target) to the
        intermediate (lon, lat) points of that edge. Duplicate edges between
        the same pair of nodes keep the shortest.
        """
        node_count = len(coords)
        best: dict[tuple[int, int], float] = {}
        for u, v, length in edges:
            if not (0 <= u < node_count and 0 <= v < node_count):
                raise ValueError(f"edge ({u}, {v}) refers to a node that does not exist")
            if length < 0:
                raise ValueError(f"edge ({u}, {v}) has negative length {length}")
            if (u, v) not in best or length < best[(u, v)]:
                best[(u, v)] = length

        geometries = geometries or {}
        offsets = array("i", [0])
        targets = array("i")
        weights = array("d")
        geometry_offsets = array("i", [0])
        geometry_coords = array("d")

        by_source: list[list[tuple[int, float]]] = [[] for _ in range(node_count)]
        for (u, v), length in best.items():
            by_source[u].append((v, length))

        for u in range(node_count):
            for v, length in sorted(by_source[u]):
                targets.append(v)
                weights.append(length)
                for lon, lat in geometries.get((u, v), ()):
                    geometry_coords.append(lon)
                    geometry_coords.append(lat)
                geometry_offsets.append(len(geometry_coords) // 2)
            offsets.append(len(targets))

        return cls(
            lon=array("d", (c[0] for c in coords)),
            lat=array("d", (c[1] for c in coords)),
            offsets=offsets,
            targets=targets,
            weights=weights,
            geometry_offsets=geometry_offsets,
            geometry_coords=geometry_coords,
            meta=meta,
        )

    # ---------------------------------------------------------------- queries

    @property
    def node_count(self) -> int:
        return len(self.lon)

    @property
    def edge_count(self) -> int:
        return len(self.targets)

    def neighbors(self, node: int) -> Iterator[tuple[int, float]]:
        """Yield (neighbor, edge_length_m) for each edge leaving `node`."""
        targets = self.targets
        weights = self.weights
        for e in range(self.offsets[node], self.offsets[node + 1]):
            yield targets[e], weights[e]

    def incoming(self, node: int) -> Iterator[tuple[int, float]]:
        """Yield (predecessor, edge_length_m) for each edge arriving at `node`.

        A search running backwards from the goal (as in bidirectional search)
        must use this rather than `neighbors`: the graph is directed, and only
        happens to be symmetric for today's walking data.
        """
        sources = self._in_sources
        weights = self._in_weights
        for i in range(self._in_offsets[node], self._in_offsets[node + 1]):
            yield sources[i], weights[i]

    def edges_from(self, node: int) -> range:
        """Edge indices leaving `node`, for callers that need the edge id."""
        return range(self.offsets[node], self.offsets[node + 1])

    def find_edge(self, source: int, target: int) -> int | None:
        """The index of the edge source -> target, or None if there is none."""
        for e in self.edges_from(source):
            if self.targets[e] == target:
                return e
        return None

    def coord(self, node: int) -> tuple[float, float]:
        """(lon, lat) of a node."""
        return self.lon[node], self.lat[node]

    def edge_geometry(self, edge: int) -> list[tuple[float, float]]:
        """Every (lon, lat) point along an edge, including both endpoints."""
        source = self._edge_source(edge)
        points = [self.coord(source)]
        coords = self.geometry_coords
        for i in range(self.geometry_offsets[edge], self.geometry_offsets[edge + 1]):
            points.append((coords[2 * i], coords[2 * i + 1]))
        points.append(self.coord(self.targets[edge]))
        return points

    def path_geometry(self, nodes: list[int]) -> list[tuple[float, float]]:
        """The (lon, lat) line for a path given as a list of nodes."""
        if not nodes:
            return []
        line = [self.coord(nodes[0])]
        for u, v in zip(nodes, nodes[1:]):
            edge = self.find_edge(u, v)
            if edge is None:
                raise ValueError(f"path uses a missing edge {u} -> {v}")
            line.extend(self.edge_geometry(edge)[1:])
        return line

    def _build_reverse(self) -> None:
        """Build the incoming-edge arrays (a CSR of the reversed graph)."""
        n = self.node_count
        counts = array("i", bytes(4 * (n + 1)))
        for target in self.targets:
            counts[target + 1] += 1
        for i in range(n):
            counts[i + 1] += counts[i]
        in_offsets = array("i", counts)
        fill = array("i", counts[:-1])
        in_sources = array("i", bytes(4 * self.edge_count))
        in_weights = array("d", bytes(8 * self.edge_count))
        for source in range(n):
            for e in range(self.offsets[source], self.offsets[source + 1]):
                target = self.targets[e]
                slot = fill[target]
                in_sources[slot] = source
                in_weights[slot] = self.weights[e]
                fill[target] = slot + 1
        self._in_offsets = in_offsets
        self._in_sources = in_sources
        self._in_weights = in_weights

    def _edge_source(self, edge: int) -> int:
        # Binary search: the source is the last node whose offset is <= edge.
        lo, hi = 0, self.node_count - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.offsets[mid] <= edge:
                lo = mid
            else:
                hi = mid - 1
        return lo

    # ------------------------------------------------------------ persistence

    def save(self, path: str | Path) -> None:
        """Write the graph to a single file (a zip of raw arrays plus metadata)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        header = {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "byteorder": sys.byteorder,
            "itemsizes": {code: array(code).itemsize for code in set(_ARRAYS.values())},
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "meta": self.meta,
        }
        # Write to a uniquely named temporary file and rename it into place,
        # so a crash mid-write never leaves a half-written graph where the
        # server expects a good one.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as f, zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("header.json", json.dumps(header, indent=2))
                for name in _ARRAYS:
                    zf.writestr(f"{name}.bin", getattr(self, name).tobytes())
            # mkstemp creates the file readable only by its owner; a server
            # running as another user must still be able to read the graph.
            tmp.chmod(0o644)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)

    @classmethod
    def load(cls, path: str | Path) -> WalkGraph:
        """Read a graph written by `save`.

        Raises FileNotFoundError if the file is missing and GraphFormatError
        for anything else wrong with it.
        """
        path = Path(path)
        try:
            with zipfile.ZipFile(path) as zf:
                header = json.loads(zf.read("header.json"))
                if not isinstance(header, dict) or header.get("format") != FORMAT_NAME:
                    raise GraphFormatError(f"{path} is not a {FORMAT_NAME} file")
                if header.get("version") != FORMAT_VERSION:
                    raise GraphFormatError(
                        f"{path} is format version {header.get('version')}, "
                        f"expected {FORMAT_VERSION}; rebuild the graph"
                    )
                for code, size in header["itemsizes"].items():
                    if array(code).itemsize != size:
                        raise GraphFormatError(f"{path} was written with incompatible number sizes")

                arrays = {}
                for name, code in _ARRAYS.items():
                    arr = array(code)
                    arr.frombytes(zf.read(f"{name}.bin"))
                    if header["byteorder"] != sys.byteorder:
                        arr.byteswap()
                    arrays[name] = arr
                graph = cls(**arrays, meta=header.get("meta"))
                expected = (header["node_count"], header["edge_count"])
        except GraphFormatError:
            raise
        except (zipfile.BadZipFile, KeyError, TypeError, ValueError, AttributeError) as exc:
            # A truncated, hand-edited or foreign file. JSONDecodeError is a
            # ValueError; a missing zip member or header key is a KeyError.
            raise GraphFormatError(f"{path} is not a readable graph file: {exc}") from exc

        if (graph.node_count, graph.edge_count) != expected:
            raise GraphFormatError(f"{path} has inconsistent sizes")
        return graph

    # ------------------------------------------------------------- validation

    def _validate(self) -> None:
        n, m = len(self.lon), len(self.targets)
        if len(self.lat) != n:
            raise GraphFormatError("lon and lat have different lengths")
        if len(self.offsets) != n + 1 or self.offsets[0] != 0 or self.offsets[-1] != m:
            raise GraphFormatError("offsets do not match the node and edge counts")
        if len(self.weights) != m:
            raise GraphFormatError("weights and targets have different lengths")
        if len(self.geometry_offsets) != m + 1 or self.geometry_offsets[-1] * 2 != len(self.geometry_coords):
            raise GraphFormatError("edge geometry offsets do not match the coordinates")
        if any(a > b for a, b in zip(self.offsets, self.offsets[1:])):
            raise GraphFormatError("edge offsets go backwards")
        if any(a > b for a, b in zip(self.geometry_offsets, self.geometry_offsets[1:])):
            raise GraphFormatError("edge geometry offsets go backwards")
        if m and not (0 <= min(self.targets) and max(self.targets) < n):
            raise GraphFormatError("an edge points to a node that does not exist")
        if m and min(self.weights) < 0:
            raise GraphFormatError("an edge has a negative length")
