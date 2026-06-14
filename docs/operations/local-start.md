# Local Development Start Guide

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Node.js](https://nodejs.org/) 18+
- [pnpm](https://pnpm.io/) — Frontend package manager

## Backend

Install dependencies and start the FastAPI server:

```bash
uv sync --dev
uv run uvicorn eumpa_studio.server.app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### Health check

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

### Run backend tests

```bash
uv run pytest tests/backend -q
```

## Frontend

Install dependencies and start the Vite dev server:

```bash
cd apps/web
pnpm install
pnpm dev
```

The app will be available at `http://localhost:5173`.

The Vite dev server proxies `/api` requests to `http://localhost:8000`, so you
need the backend running first.

### Type-check

```bash
cd apps/web
pnpm typecheck
```

### Build for production

```bash
cd apps/web
pnpm build
```
