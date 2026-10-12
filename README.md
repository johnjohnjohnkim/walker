# Walker

A walking-only map of Toronto for exploring graph search. Instead of switching
between car, transit and walking, you switch between search algorithms and
watch how each one explores the street network.

- **Backend:** Python 3.12, Django, managed with [uv](https://docs.astral.sh/uv/).
- **Frontend:** React + TypeScript (Vite) with [MapLibre GL JS](https://maplibre.org/).
- **Map data:** © OpenStreetMap contributors. Tiles from [OpenFreeMap](https://openfreemap.org/).

## Running locally

You need `uv` and Node.js 22.22+ or 24.15+ (`.nvmrc` pins 24).

### Backend

```sh
cd backend
cp .env.example .env
uv sync
uv run python -m graph.build --area downtown   # one-time, downloads from OpenStreetMap
uv run python manage.py runserver
```

The build step downloads downtown Toronto's walkable streets and saves them to
`backend/data/downtown.walkgraph`. The server only ever reads that file; it
never contacts OpenStreetMap itself. Rerun the build to refresh the data.

Don't skip the `cp` step: without a `.env`, debug is off and Django refuses
to start until `DJANGO_SECRET_KEY` is set.

The API runs on http://127.0.0.1:8000. Check it with
`curl http://127.0.0.1:8000/api/health`.

### Frontend

In a second terminal:

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` requests to the
backend, so both must be running.

## Tests

```sh
cd backend && uv run pytest
cd frontend && npm test
```

`npm run build` type-checks and builds the frontend, and `npm run lint` lints it.

## Configuration

Settings come from environment variables. See `backend/.env.example` and
`frontend/.env.example`.

| Variable | Where | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | backend | Debug mode. Off unless set; `.env.example` turns it on. |
| `DJANGO_SECRET_KEY` | backend | Required when debug is off. |
| `DJANGO_ALLOWED_HOSTS` | backend | Comma-separated host names. |
| `WALKER_GRAPH_PATH` | backend | Graph file to serve. Relative paths are relative to `backend/`. Defaults to `data/downtown.walkgraph`. |
| `VITE_MAP_STYLE_URL` | frontend | Map style JSON; swap to change tile provider. |
| `VITE_API_PROXY_TARGET` | frontend | Where the dev server sends `/api`. |

## The graph

| Area | Nodes | Edges | File | Build | Load + index | Memory |
| --- | --- | --- | --- | --- | --- | --- |
| downtown | 16,139 | 43,914 | 1.1 MB | ~30 s (mostly download) | 0.2 s | ~4 MB |

Measured on 2026-10-09 on an Apple Silicon Mac. Edges are directed, so each
two-way street counts twice. Only the largest connected part of the network is
kept, so every node can reach every other node. Load time is mostly building
the reverse (incoming) edge lists and validating the file, both plain Python
loops; expect it to grow in proportion to the edge count as the area grows.

The graph is stored in compressed sparse row form: one array of node
coordinates, and for each node a slice of a shared array of outgoing edges.
See `backend/graph/graph.py`.

## Project layout

```
backend/
  config/     Django settings and URLs
  graph/      the walkable graph: build from OSM, storage, nearest-node lookup
              (no Django imports)
  routing/    API views and the in-memory graph store
  tests/
frontend/
  src/        React app
```
