# The Django API, served by gunicorn.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so editing code doesn't reinstall them. --no-dev also
# leaves out the graph-building tools (OSMnx): the server only reads the
# graph file, which is built on a developer machine and copied in.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Use the installed environment directly, without uv at run time.
ENV PATH="/app/.venv/bin:$PATH"

# Not root inside the container.
RUN useradd --create-home walker
USER walker

EXPOSE 8000

# Two worker processes, each serving one request at a time. --timeout kills
# a worker that doesn't answer gunicorn's heartbeat within 30 s, which is
# what stops a search stuck in a loop that never yields (the runner's own
# 10 s limit can only act between events); gunicorn then starts a fresh one.
# --preload loads the graph once before forking, so the two workers share
# its memory instead of holding a copy each.
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "30", "--preload", "--access-logfile", "-"]
