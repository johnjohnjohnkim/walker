"""A small per-client fixed-window rate limiter on Django's cache."""

from django.conf import settings
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
    """The address to rate-limit by.

    Behind our own reverse proxy (Caddy, in production), every request comes
    from the proxy, so the visitor's address is the one the proxy appended to
    X-Forwarded-For: the last entry. Earlier entries came from the visitor and
    can be faked, so they are ignored. Without a trusted proxy, use the
    direct connection's address.
    """
    if settings.WALKER_BEHIND_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        last = forwarded.rsplit(",", 1)[-1].strip()
        if last:
            return last
    return request.META.get("REMOTE_ADDR", "unknown")
