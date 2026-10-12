import json
import logging
import math

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from algorithms import ALGORITHMS, REGISTRY
from algorithms.runner import AlgorithmError, AlgorithmNotImplemented, run

from geocoding import GeocoderUnavailable

from . import geocode, graph_store

logger = logging.getLogger(__name__)

# A clicked or searched point further than this from any walkable street is
# treated as outside the map, rather than silently routed from somewhere far.
MAX_SNAP_DISTANCE_M = 300.0

# Average walking speed, about 5 km/h.
WALKING_SPEED_M_PER_S = 1.4


def error(message: str, code: str, status: int, **extra) -> JsonResponse:
    return JsonResponse({"error": message, "code": code, **extra}, status=status)


@require_GET
def health(request):
    try:
        loaded = graph_store.get()
    except graph_store.GraphUnavailable as exc:
        # The detail names a server path, so only show it in development.
        detail = str(exc) if settings.DEBUG else "The routing graph is not loaded."
        return JsonResponse({"status": "degraded", "graph": None, "detail": detail}, status=503)

    graph = loaded.graph
    return JsonResponse(
        {
            "status": "ok",
            "graph": {
                "area": graph.meta.get("area"),
                "nodes": graph.node_count,
                "edges": graph.edge_count,
                "built_at": graph.meta.get("built_at"),
            },
        }
    )


@require_GET
def algorithms(request):
    return JsonResponse(
        {
            "algorithms": [
                {
                    "id": a.id,
                    "name": a.name,
                    "description": a.description,
                    "guarantee": a.guarantee,
                    "uses_lengths": a.uses_lengths,
                    "bidirectional": a.bidirectional,
                    "implemented": a.implemented,
                }
                for a in REGISTRY
            ]
        }
    )


MAX_QUERY_LENGTH = 200
MAX_RESULTS = 8


@require_GET
def geocode_view(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return error("Type at least two characters.", "bad_request", 400)
    if len(query) > MAX_QUERY_LENGTH:
        return error(f"Queries are limited to {MAX_QUERY_LENGTH} characters.", "bad_request", 400)
    try:
        limit = min(max(int(request.GET.get("limit", 5)), 1), MAX_RESULTS)
    except ValueError:
        return error("`limit` must be a number.", "bad_request", 400)

    # REMOTE_ADDR is the direct client. Behind a reverse proxy (M10) it must
    # come from the proxy's forwarded header instead.
    if not geocode.allow(request.META.get("REMOTE_ADDR", "unknown")):
        return error("Too many searches; wait a few seconds.", "rate_limited", 429)

    # Only suggest places on the map, so every suggestion can be routed to.
    try:
        bbox = tuple(graph_store.get().graph.meta["bbox"])
    except (graph_store.GraphUnavailable, KeyError, TypeError):
        bbox = geocode.TORONTO_BBOX

    try:
        places = geocode.search(query, bbox=bbox, limit=limit)
    except geocode.Busy:
        return error("Place search is busy; try again in a moment.", "rate_limited", 429)
    except GeocoderUnavailable:
        logger.warning("Geocoder unavailable", exc_info=True)
        return error("Place search is unavailable right now. You can still click the map.", "geocoder_unavailable", 503)

    return JsonResponse({"results": [place.to_json() for place in places]})


class BadRequest(ValueError):
    pass


def _parse_point(body: dict, key: str) -> tuple[float, float]:
    point = body.get(key)
    if not isinstance(point, dict):
        raise BadRequest(f"`{key}` must be an object with `lon` and `lat`.")
    values = []
    for axis, limit in (("lon", 180), ("lat", 90)):
        value = point.get(axis)
        # bool is a subclass of int in Python, so rule it out explicitly.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BadRequest(f"`{key}.{axis}` must be a number.")
        # A huge JSON integer (e.g. 10**400) can't become a float at all.
        try:
            value = float(value)
        except OverflowError:
            raise BadRequest(f"`{key}.{axis}` must be between -{limit} and {limit}.") from None
        if not math.isfinite(value) or abs(value) > limit:
            raise BadRequest(f"`{key}.{axis}` must be between -{limit} and {limit}.")
        values.append(value)
    return values[0], values[1]


def _parse_route_request(request) -> tuple[tuple[float, float], tuple[float, float], str, bool]:
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        # RecursionError: deeply nested input like "[[[[...".
        raise BadRequest("The request body must be JSON.") from exc
    if not isinstance(body, dict):
        raise BadRequest("The request body must be a JSON object.")
    algorithm = body.get("algorithm", "dijkstra")
    if not isinstance(algorithm, str):
        raise BadRequest("`algorithm` must be a string.")
    trace = body.get("trace", False)
    if not isinstance(trace, bool):
        raise BadRequest("`trace` must be true or false.")
    return _parse_point(body, "origin"), _parse_point(body, "destination"), algorithm, trace


# Beyond this many events the animation is cut short rather than recording
# and sending megabytes. Downtown searches stay far below it (about 35,000 at
# most); the whole-city graph (M9) needs a decision on a binary encoding or
# sampling before raising it.
MAX_TRACE_EVENTS = 200_000


def _trace_payload(graph, trace) -> dict:
    """The search's events for the animation, compactly.

    `coordinates` lists each node the search touched once, as [lon, lat].
    `events` is a flat list of three numbers per event: the event code
    (0 discover, 1 visit, 2 discover backward, 3 visit backward), the node's
    index in `coordinates`, and its parent's index (-1 if none).
    """
    count = len(trace)
    index: dict[int, int] = {}
    coordinates: list[list[float]] = []

    def local(node: int) -> int:
        if node < 0:
            return -1
        i = index.get(node)
        if i is None:
            i = index[node] = len(coordinates)
            lon, lat = graph.coord(node)
            coordinates.append([round(lon, 6), round(lat, 6)])
        return i

    events: list[int] = []
    codes, nodes, parents = trace.codes, trace.nodes, trace.parents
    for i in range(count):
        events.append(codes[i])
        events.append(local(nodes[i]))
        events.append(local(parents[i]))
    return {"coordinates": coordinates, "events": events, "count": count, "truncated": trace.truncated}


def _rounded(points):
    # Six decimal places is about 10 cm, plenty for drawing, and keeps the
    # response small.
    return [[round(lon, 6), round(lat, 6)] for lon, lat in points]


@require_POST
def route(request):
    try:
        origin, destination, algorithm, want_trace = _parse_route_request(request)
    except BadRequest as exc:
        return error(str(exc), "bad_request", 400)

    search = ALGORITHMS.get(algorithm)
    if search is None:
        return error(f"Unknown algorithm `{algorithm}`.", "unknown_algorithm", 400, algorithms=sorted(ALGORITHMS))

    try:
        loaded = graph_store.get()
    except graph_store.GraphUnavailable:
        return error("The routing graph is not loaded.", "graph_unavailable", 503)
    graph, index = loaded.graph, loaded.index

    snapped = {}
    for name, (lon, lat) in (("origin", origin), ("destination", destination)):
        found = index.nearest(lon, lat, max_distance_m=MAX_SNAP_DISTANCE_M)
        if found is None:
            return error(
                f"The {name} is too far from any walkable street on the map.",
                "outside_coverage",
                422,
                which=name,
            )
        snapped[name] = found

    start, start_offset = snapped["origin"]
    goal, goal_offset = snapped["destination"]
    try:
        result = run(search, graph, start, goal, record=want_trace, record_limit=MAX_TRACE_EVENTS)
    except AlgorithmNotImplemented:
        return error(f"The {algorithm} algorithm hasn't been implemented yet.", "not_implemented", 501)
    except AlgorithmError as exc:
        logger.exception("Algorithm %s failed", algorithm)
        message = f"The {algorithm} implementation failed"
        # Show the details while developing; they point at the bug.
        return error(f"{message}: {exc}" if settings.DEBUG else f"{message}.", "algorithm_error", 500)

    if result.path is None:
        return error("No walking route connects these points.", "no_route", 422)

    return JsonResponse(
        {
            "algorithm": algorithm,
            "route": {
                "coordinates": _rounded(graph.path_geometry(result.path)),
                "distance_m": round(result.distance_m, 1),
                "duration_s": round(result.distance_m / WALKING_SPEED_M_PER_S),
                "nodes": len(result.path),
            },
            "origin": {
                "requested": _rounded([origin])[0],
                "snapped": _rounded([graph.coord(start)])[0],
                "snap_distance_m": round(start_offset, 1),
            },
            "destination": {
                "requested": _rounded([destination])[0],
                "snapped": _rounded([graph.coord(goal)])[0],
                "snap_distance_m": round(goal_offset, 1),
            },
            "search": {
                "visited": result.visited,
                "discovered": result.discovered,
            },
            "trace": _trace_payload(graph, result.trace) if result.trace is not None else None,
        }
    )


def not_found(request, exception):
    return JsonResponse({"error": "Not found."}, status=404)


def server_error(request):
    return JsonResponse({"error": "Internal server error."}, status=500)
