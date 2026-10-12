"""
Django settings for the Walker backend.

Every value that differs between machines comes from the environment, so the
same code runs locally and in production. Copy `.env.example` to `.env` for
local development.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Test settings set WALKER_SKIP_DOTENV so a developer's local .env never
# changes what the tests see.
if not os.environ.get("WALKER_SKIP_DOTENV"):
    load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# Off unless explicitly enabled, so a deploy that forgets the variable fails
# safe. `.env.example` turns it on for local development.
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# The API is a stateless JSON service, so the session, auth and admin apps
# are left out on purpose. There is no database either: routing data lives
# in an in-memory graph.
INSTALLED_APPS = [
    "routing",
]

MIDDLEWARE = [
    # Search traces for the animation are large, repetitive JSON; gzip
    # shrinks them about four times.
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

# The prebuilt walking graph (see `graph/build.py`). The server only reads it.
# A relative path is taken relative to the backend directory, not to wherever
# the server happens to be started from.
WALKER_GRAPH_PATH = BASE_DIR / os.environ.get("WALKER_GRAPH_PATH", "data/downtown.walkgraph")

# Place search. "photon" uses the public Photon server; any other value is a
# dotted path to a class with the same interface (see geocoding/base.py).
WALKER_GEOCODER = os.environ.get("WALKER_GEOCODER", "photon")
WALKER_PHOTON_URL = os.environ.get("WALKER_PHOTON_URL", "https://photon.komoot.io")
# Public geocoders ask callers to identify themselves.
WALKER_GEOCODER_USER_AGENT = os.environ.get(
    "WALKER_GEOCODER_USER_AGENT", "walker/0.1 (https://github.com/johnjohnjohnkim/walker)"
)
# Per-client limit on /api/geocode: this many requests per window. Typing
# with the frontend's debounce needs far fewer.
WALKER_GEOCODE_RATE = int(os.environ.get("WALKER_GEOCODE_RATE", "10"))
WALKER_GEOCODE_RATE_WINDOW_S = int(os.environ.get("WALKER_GEOCODE_RATE_WINDOW_S", "10"))
# Cap on requests actually sent to the provider (cache misses), for the whole
# process, however many clients there are: a steady rate plus a short burst.
WALKER_GEOCODER_MAX_PER_S = float(os.environ.get("WALKER_GEOCODER_MAX_PER_S", "1"))
WALKER_GEOCODER_BURST = int(os.environ.get("WALKER_GEOCODER_BURST", "3"))

# In-process caches. Each worker process keeps its own, so with several
# workers the limits above apply per worker (see the deploy notes).
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "default"},
    "geocode": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "geocode",
        "OPTIONS": {"MAX_ENTRIES": 10_000},
    },
    "ratelimit": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ratelimit",
        "OPTIONS": {"MAX_ENTRIES": 10_000},
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True
