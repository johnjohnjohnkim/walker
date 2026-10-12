"""A small per-client fixed-window rate limiter on Django's cache."""

from django.core.cache import caches


def allow(scope: str, client: str, *, limit: int, window_s: int) -> bool:
    """True if `client` may make another `scope` request in this window."""
    cache = caches["ratelimit"]
    key = f"{scope}-rate:{client}"
    # add() only sets the key if it's missing, starting a new window.
    cache.add(key, 0, window_s)
    try:
        count = cache.incr(key)
    except ValueError:  # expired between add() and incr()
        cache.set(key, 1, window_s)
        count = 1
    return count <= limit


def client_of(request) -> str:
    # REMOTE_ADDR is the direct client. Behind a reverse proxy (M10) it must
    # come from the proxy's forwarded header instead.
    return request.META.get("REMOTE_ADDR", "unknown")
