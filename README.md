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
uv run python manage.py runserver
```

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
| `VITE_MAP_STYLE_URL` | frontend | Map style JSON; swap to change tile provider. |
| `VITE_API_PROXY_TARGET` | frontend | Where the dev server sends `/api`. |

## Project layout

```
backend/
  config/     Django settings and URLs
  routing/    API views
  tests/
frontend/
  src/        React app
```
