# Walker

A walking-only map of Toronto for exploring graph search. Instead of switching
between car, transit and walking, you switch between search algorithms and
watch how each one explores the street network.

- **Backend:** Python 3.12, Django, managed with [uv](https://docs.astral.sh/uv/).
- **Frontend:** React + TypeScript (Vite) with [MapLibre GL JS](https://maplibre.org/).
- **Map data:** © OpenStreetMap contributors. Tiles from [OpenFreeMap](https://openfreemap.org/), place search from [Photon](https://photon.komoot.io/).

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
| `WALKER_GEOCODER` | backend | `photon`, or a dotted path to another geocoder class. |
| `WALKER_PHOTON_URL` | backend | Photon server. Defaults to the public one. |
| `WALKER_GEOCODE_RATE`, `WALKER_GEOCODE_RATE_WINDOW_S` | backend | Searches allowed per client per window (30 per 10 s). |
| `VITE_MAP_STYLE_URL` | frontend | Map style JSON; swap to change tile provider. |
| `VITE_API_PROXY_TARGET` | frontend | Where the dev server sends `/api`. |

## Using it

Type a place into the starting point and destination boxes and pick a
suggestion, or click the map: the first click sets the start, the second the
destination, and a third starts over. The walking route appears in blue with
its time and distance. Pick an algorithm from the chips to re-run the route
with it.

## API

`POST /api/route`

```json
{"origin": {"lon": -79.3871, "lat": 43.6426},
 "destination": {"lon": -79.4005, "lat": 43.6547},
 "algorithm": "dijkstra"}
```

Each point snaps to the nearest walkable node within 300 m. The response holds
the route line (`route.coordinates`, as `[lon, lat]` pairs), its length and an
estimated walking time at 1.4 m/s, where each point snapped to, and how many
nodes the search visited. Errors are JSON with `error` and `code`:

| Status | `code` | Meaning |
| --- | --- | --- |
| 400 | `bad_request`, `unknown_algorithm` | Malformed body or unknown algorithm |
| 501 | `not_implemented` | The algorithm is still a stub |
| 422 | `outside_coverage` | A point is more than 300 m from any street on the map |
| 422 | `no_route` | The points aren't connected |
| 503 | `graph_unavailable` | No graph is loaded |

`GET /api/geocode?q=CN%20Tower` suggests places on the map (up to 8, default
5) as `{name, address, lon, lat}`. It forwards to the configured geocoder
(Photon by default), caches answers for a day, and allows each client 30
searches per 10 seconds (429 `rate_limited` beyond that; 503
`geocoder_unavailable` if the provider is down).

`GET /api/algorithms` lists the search algorithms and which are implemented.

`GET /api/health` reports whether a graph is loaded and its size.

## Search algorithms

| Algorithm | File | Returns | Status |
| --- | --- | --- | --- |
| Dijkstra | `dijkstra.py` | shortest route | done |
| A* | `astar.py` | shortest route | to do |
| Bidirectional Dijkstra | `bidirectional.py` | shortest route | to do |
| BFS | `bfs.py` | fewest street segments | to do |
| DFS | `dfs.py` | any route | to do |

Each algorithm lives in `backend/algorithms/` as a generator function that
yields events while it runs: `Discover` when a node joins the frontier,
`Visit` when it is explored, and a final `Done` with the path. The rules, with
worked examples, are in `backend/algorithms/events.py`. The runner checks
every event and the final path, so a mistake shows up as a clear error rather
than a wrong line on the map.

### Writing one

1. Open the algorithm's file. Its docstring says what it must return and what
   tends to go wrong; the function body is a stub that raises
   `NotImplementedError`.
2. Replace the stub with your implementation. Read `dijkstra.py` for how the
   events are reported.
3. Check it:

   ```sh
   cd backend
   uv run pytest tests/test_conformance.py -k bfs -v
   ```

   The conformance tests run it on small hand-built graphs (including traps
   for common mistakes), on random graphs and on real downtown routes, and
   compare the answer with NetworkX. Every test graph is drawn to scale at
   Toronto's latitude, with no edge shorter than a straight line, so a
   correct straight-line heuristic for A* is never penalised. While the stub is in place these tests
   are skipped.
4. Reload the page. The picker enables an algorithm as soon as it stops
   raising `NotImplementedError`; the dev server picks up the change on save,
   and the page asks for the list of algorithms when it loads.

`GET /api/algorithms` lists every algorithm and whether it is implemented.

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
  algorithms/ search algorithms and the runner that checks them
  geocoding/  place search providers (Photon), no Django imports
  graph/      the walkable graph: build from OSM, storage, nearest-node lookup
              (no Django imports)
  routing/    API views and the in-memory graph store
  tests/
frontend/
  src/        React app
```
