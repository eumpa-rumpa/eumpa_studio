# eumpa_studio

Internal AI music-video production tool for planning shots, managing attempts,
generating prompts, queueing ComfyUI renders, and reviewing rendered clips.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- [pnpm](https://pnpm.io/)
- Codex CLI on `PATH`, or set `EUMPA_CODEX_CLI_PATH`
- ComfyUI reachable at `EUMPA_COMFYUI_URL` for render jobs and video previews

## Fresh Clone Setup

```bash
git clone https://github.com/eumpa-rumpa/eumpa_studio.git
cd eumpa_studio
uv sync --dev
pnpm --dir apps/web install
```

Generate the local `.env` file from 1Password:

```bash
bash scripts/setup-env.sh
```

If you are not using 1Password on a machine, copy the non-secret defaults:

```bash
cp .env.example .env
```

The generated `.env` stores app data and the SQLite database under `data/` by
default. Both `.env` and `data/` are intentionally git-ignored.

## Start Locally

Start the backend, worker, migrations, and frontend dev server together:

```bash
bash scripts/dev.sh
```

Open `http://localhost:5173`.

The script runs:

- `uv run eumpa-studio start --reload` for the FastAPI API, DB migrations, and job worker.
- `pnpm --dir apps/web dev -- --host 0.0.0.0` for the Vite frontend.

Backend API health is available at `http://localhost:8000/api/health`.

## Useful Commands

```bash
uv run eumpa-studio start --reload
pnpm --dir apps/web dev
UV_CACHE_DIR=/tmp/eumpa-uv-cache uv run pytest -q
pnpm --dir apps/web typecheck
pnpm --dir apps/web test -- --run
pnpm --dir apps/web build
```

## Workflow Templates

The default LTX lip-sync workflow seed is bundled in the repo at
`src/eumpa_studio/resources/workflows/default_ltx2_ia2v_lipsync.json`.

In the UI, use `Sync skill LTX workflow` to copy that bundled workflow into
`EUMPA_DATA_ROOT/workflows/skill-defaults/` and register the matching execution
mode in the database.

## Secrets

Local configuration is generated from `.env.1password.tpl` with
`scripts/setup-env.sh`. The template stores only 1Password secret references;
resolved values are written to `.env`, which is ignored by Git and chmodded to
`0600`.

The expected 1Password item is:

```text
Vault: Private
Item: eumpa_studio local
Fields:
  EUMPA_DATA_ROOT
  EUMPA_DATABASE_URL
  EUMPA_COMFYUI_URL
  EUMPA_CODEX_CLI_PATH
  EUMPA_ALIGNMENT_COMMAND
```

Regenerate `.env` after changing the item:

```bash
bash scripts/setup-env.sh --force
```

## Docs

- [Local start guide](docs/operations/local-start.md)
- [Server topology](docs/operations/server-topology.md)
