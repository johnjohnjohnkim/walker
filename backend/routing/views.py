import json
import logging
import math

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from algorithms import ALGORITHMS, REGISTRY
from algorithms.runner import AlgorithmError, AlgorithmNotImplemented, run

from . import graph_store

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


def _parse_route_request(request) -> tuple[tuple[float, float], tuple[float, float], str]:
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
    return _parse_point(body, "origin"), _parse_point(body, "destination"), algorithm


def _rounded(points):
    # Six decimal places is about 10 cm, plenty for drawing, and keeps the
    # response small.
    return [[round(lon, 6), round(lat, 6)] for lon, lat in points]


@require_POST
def route(request):
    try:
        origin, destination, algorithm = _parse_route_request(request)
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
        result = run(search, graph, start, goal)
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
        }
    )


def not_found(request, exception):
    return JsonResponse({"error": "Not found."}, status=404)


def server_error(request):
    return JsonResponse({"error": "Internal server error."}, status=500)
