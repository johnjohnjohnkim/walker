from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from . import graph_store


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


def not_found(request, exception):
    return JsonResponse({"error": "Not found."}, status=404)


def server_error(request):
    return JsonResponse({"error": "Internal server error."}, status=500)
