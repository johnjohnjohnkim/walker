from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


def not_found(request, exception):
    return JsonResponse({"error": "Not found."}, status=404)


def server_error(request):
    return JsonResponse({"error": "Internal server error."}, status=500)
