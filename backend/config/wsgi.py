"""
WSGI entry point for the Walker backend.

The graph is loaded here, at startup, rather than on the first request, so
the first visitor doesn't wait for it. (With gunicorn's --preload, workers
start from the loaded copy; the raw graph arrays stay shared between them,
while the Python objects in the spatial index get copied over time.)
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

from routing import graph_store  # noqa: E402

try:
    graph_store.load()
except graph_store.GraphUnavailable:
    # Logged by load(). Keep serving so /api/health can explain the problem.
    pass
