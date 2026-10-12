"""Search algorithms over the walking graph.

Each algorithm is a generator function following the event contract in
`events.py`. `ALGORITHMS` maps the id the API uses to that function.
"""

from . import dijkstra
from .runner import SearchFunction

ALGORITHMS: dict[str, SearchFunction] = {
    "dijkstra": dijkstra.search,
}
