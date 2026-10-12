"""Place search for the API: picks the configured geocoder, caches answers and
protects the provider, which for Photon is a free public service.

Three layers keep traffic to it low:
- a per-client rate limit on our endpoint;
- a cache of answers, so repeated searches never reach the provider;
- a process-wide budget on cache misses, plus a circuit breaker that stops
  calling the provider for a while after it fails.
"""

from __future__ import annotations

import hashlib
import threading
import time
from functools import lru_cache

from django.conf import settings
from django.core.cache import caches
from django.utils.module_loading import import_string

from geocoding import Geocoder, GeocoderUnavailable, Place
from geocoding.base import BBox
from geocoding.photon import PhotonGeocoder

CACHE_TTL_S = 24 * 60 * 60

# After the provider fails, answer "unavailable" straight away for this long
# instead of making every keystroke wait for another timeout.
CIRCUIT_OPEN_S = 30.0

# Used when no graph is loaded: roughly the City of Toronto plus Vaughan.
TORONTO_BBOX: BBox = (-79.64, 43.58, -79.11, 43.86)


class Busy(RuntimeError):
    """The process-wide budget for provider requests is used up for now."""


@lru_cache(maxsize=1)
def _geocoder_for(name: str) -> Geocoder:
    if name == "photon":
        return PhotonGeocoder(
            base_url=settings.WALKER_PHOTON_URL, user_agent=settings.WALKER_GEOCODER_USER_AGENT, timeout_s=3.0
        )
    return import_string(name)()


def get_geocoder() -> Geocoder:
    return _geocoder_for(settings.WALKER_GEOCODER)


class _Upstream:
    """A token bucket for provider requests and a circuit breaker, shared by
    every request in this process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._tokens = float(settings.WALKER_GEOCODER_BURST)
            self._refilled = time.monotonic()
            self._open_until = 0.0

    def acquire(self) -> None:
        """Take one request from the budget, or raise Busy / GeocoderUnavailable."""
        with self._lock:
            now = time.monotonic()
            if now < self._open_until:
                raise GeocoderUnavailable("provider recently failed; not retrying yet")
            rate, burst = settings.WALKER_GEOCODER_MAX_PER_S, settings.WALKER_GEOCODER_BURST
            self._tokens = min(burst, self._tokens + (now - self._refilled) * rate)
            self._refilled = now
            if self._tokens < 1:
                raise Busy("too many place searches right now")
            self._tokens -= 1

    def failed(self) -> None:
        with self._lock:
            self._open_until = time.monotonic() + CIRCUIT_OPEN_S


upstream = _Upstream()


def search(query: str, *, bbox: BBox, limit: int) -> list[Place]:
    normalized = " ".join(query.lower().split())
    digest = hashlib.sha256(f"{settings.WALKER_GEOCODER}|{bbox}|{limit}|{normalized}".encode()).hexdigest()
    key = f"geocode:{digest}"
    cache = caches["geocode"]
    cached = cache.get(key)
    if cached is not None:
        return cached

    upstream.acquire()
    try:
        places = get_geocoder().search(normalized, bbox=bbox, limit=limit)
    except GeocoderUnavailable:
        upstream.failed()
        raise
    cache.set(key, places, CACHE_TTL_S)
    return places
