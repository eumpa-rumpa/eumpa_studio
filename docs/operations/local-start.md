# Local Start

## Prerequisites

- Python 3.11+
- uv
- Node.js 20+
- pnpm

## Install

Install backend dependencies:

```bash
uv sync
```

Install frontend dependencies:

```bash
cd apps/web
pnpm install
```

## Required Environment Variables

The local defaults are suitable for single-machine MVP development.

```bash
export EUMPA_DATA_ROOT=.eumpa
export EUMPA_COMFYUI_URL=http://localhost:8188
export EUMPA_CODEX_CLI_PATH=codex
```

- `EUMPA_DATA_ROOT`: local data directory, default `.eumpa`
- `EUMPA_COMFYUI_URL`: ComfyUI API URL, default `http://localhost:8188`
- `EUMPA_CODEX_CLI_PATH`: Codex CLI executable, default `codex`

## Start

Start the backend, apply database migrations, and launch the job worker:

```bash
uv run eumpa_studio start
```

## Dev Mode

Enable backend auto-reload:

```bash
uv run eumpa_studio start --reload
```

## Frontend Dev

Start the Vite frontend dev server:

```bash
cd apps/web
pnpm dev
```

## Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

## Run Tests

```bash
uv run pytest tests/backend -q
```
