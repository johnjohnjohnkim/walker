"""Settings for the test suite: production-like (debug off), no local .env."""

import os

# Forced, not defaulted, so variables exported in a developer's shell can't
# change test behaviour either.
os.environ["WALKER_SKIP_DOTENV"] = "1"
os.environ["DJANGO_DEBUG"] = "false"
os.environ["DJANGO_SECRET_KEY"] = "test-only-key"
os.environ["DJANGO_ALLOWED_HOSTS"] = "localhost,127.0.0.1"

from .settings import *  # noqa: E402,F403
