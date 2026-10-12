"""Holds the one in-memory graph the API serves from.

The graph is loaded once per process and then shared read-only by every
request. `load()` is called at startup from `config/wsgi.py`; `get()` also
loads on first use, so tests and management commands work without that hook.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from graph import WalkGraph
from graph.graph import GraphFormatError
from graph.spatial import NodeIndex

logger = logging.getLogger(__name__)


class GraphUnavailable(RuntimeError):
    """The graph file is missing or unreadable."""


@dataclass(frozen=True)
class LoadedGraph:
    graph: WalkGraph
    index: NodeIndex
    path: Path


# After a failed load, wait this long before trying the file again, so a
# missing or corrupt graph doesn't mean a disk read and a log line on every
# request.
RETRY_AFTER_S = 10.0

_lock = threading.Lock()
_loaded: LoadedGraph | None = None
_last_failure: tuple[float, str] | None = None


def load() -> LoadedGraph:
    """Load the graph (once) and return it, or raise GraphUnavailable.

    A failure is retried after RETRY_AFTER_S seconds, so building the file
    while the server runs fixes it without a restart.
    """
    global _loaded, _last_failure
    with _lock:
        if _loaded is not None:
            return _loaded
        if _last_failure is not None and time.monotonic() - _last_failure[0] < RETRY_AFTER_S:
            raise GraphUnavailable(_last_failure[1])
        path = Path(settings.WALKER_GRAPH_PATH)
        try:
            graph = WalkGraph.load(path)
        except FileNotFoundError:
            error = f"No graph file at {path}. Build one with `uv run python -m graph.build`."
        except (GraphFormatError, OSError) as exc:
            error = f"Could not read the graph file at {path}: {exc}"
        else:
            _loaded = LoadedGraph(graph=graph, index=NodeIndex(graph), path=path)
            _last_failure = None
            logger.info("Loaded graph %s: %d nodes, %d edges", path, graph.node_count, graph.edge_count)
            return _loaded
        _last_failure = (time.monotonic(), error)
        logger.warning(error)
        raise GraphUnavailable(error)


def get() -> LoadedGraph:
    return _loaded if _loaded is not None else load()


def reset() -> None:
    """Forget the loaded graph. For tests and after rebuilding the file."""
    global _loaded, _last_failure
    with _lock:
        _loaded = None
        _last_failure = None
