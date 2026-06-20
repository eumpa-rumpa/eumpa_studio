# Local Development Start Guide

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Node.js](https://nodejs.org/) 18+
- [pnpm](https://pnpm.io/) — Frontend package manager
- Codex CLI on `PATH`, or configure `EUMPA_CODEX_CLI_PATH`
- ComfyUI reachable at `EUMPA_COMFYUI_URL` when rendering or previewing outputs

## Fresh clone setup

```bash
git clone https://github.com/eumpa-rumpa/eumpa_studio.git
cd eumpa_studio
uv sync --dev
pnpm --dir apps/web install
```

Generate `.env` from 1Password:

```bash
bash scripts/setup-env.sh
```

If 1Password is unavailable on a temporary machine, copy the non-secret
defaults instead:

```bash
cp .env.example .env
```

The generated `.env` keeps local runtime files under `data/` by default. That
directory is ignored by Git and is safe for local DBs, uploads, copied workflow
templates, cache files, and exports.

## 1Password setup

Install and sign in to the 1Password CLI:

```bash
brew install --cask 1password-cli
op signin
```

The template at `.env.1password.tpl` expects this 1Password item:

```text
Vault: Private
Item: eumpa_studio local
Fields:
  EUMPA_DATA_ROOT=data
  EUMPA_DATABASE_URL=sqlite:///data/eumpa.db
  EUMPA_COMFYUI_URL=http://localhost:8188
  EUMPA_CODEX_CLI_PATH=codex
  EUMPA_ALIGNMENT_COMMAND=align
```

Regenerate `.env` after changing 1Password values:

```bash
bash scripts/setup-env.sh --force
```

## Start everything for local development

```bash
bash scripts/dev.sh
```

Open `http://localhost:5173`.

The script starts:

- backend API at `http://localhost:8000`
- database migrations via Alembic
- the single background job worker
- frontend Vite dev server at `http://localhost:5173`

## Backend

Start only the FastAPI backend, migrations, and worker:

```bash
uv run eumpa-studio start --reload
```

The API will be available at `http://localhost:8000`.

### Health check

```bash
curl http://localhost:8000/api/health
```

### Run backend tests

```bash
uv run pytest tests/backend -q
```

## Frontend

Install dependencies and start the Vite dev server:

```bash
pnpm --dir apps/web dev
```

The app will be available at `http://localhost:5173`.

The Vite dev server proxies `/api` requests to `http://localhost:8000`, so you
need the backend running first.

### Type-check

```bash
pnpm --dir apps/web typecheck
```

### Build for production

```bash
pnpm --dir apps/web build
```

## Workflow seed

The bundled LTX workflow seed is versioned in the repo:

```text
src/eumpa_studio/resources/workflows/default_ltx2_ia2v_lipsync.json
```

Use `Sync skill LTX workflow` in the UI to copy it into:

```text
EUMPA_DATA_ROOT/workflows/skill-defaults/default_ltx2_ia2v_lipsync.json
```

The copied file path is what render attempts use.
