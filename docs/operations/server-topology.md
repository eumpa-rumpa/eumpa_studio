# Server Topology

## Small Server Role

The small server is the operator-facing control plane for the MVP:

- FastAPI backend
- SQLite database
- Job worker
- Codex CLI
- Project inputs such as audio, lyrics, visual bible files, and selected exports

Keep this server responsive and lightweight. It owns orchestration, metadata, and
operator access; it does not need to store every heavy render artifact.

## Large ComfyUI Server Role

The large server is the render machine:

- ComfyUI
- Render outputs
- Optional Ollama service

Use this machine for GPU-heavy work and model-local assets. Keep generated render
files on this server unless the operator explicitly selects clips for export.

## Client Machines

Client machines are browsers on the internal network. In local development,
they access the React UI from the Vite dev server and send API requests through
the Vite `/api` proxy to the FastAPI backend. A production static asset serving
path has not been wired yet.

## Storage Policy

Heavy render files stay on the ComfyUI server. Selected clips can be copied to a
small-server export directory under `EUMPA_DATA_ROOT` when they need to be
reviewed, packaged, or shared from the operator server.

## Config Example

Use `scripts/setup-env.sh` to generate `.env` from `.env.1password.tpl`.
For manual setup, use `.env` on the small server to point the backend at the
render server:

```dotenv
EUMPA_DATA_ROOT=/srv/eumpa-studio
EUMPA_DATABASE_URL=sqlite:////srv/eumpa-studio/eumpa.db
EUMPA_COMFYUI_URL=http://comfyui-server:8188
EUMPA_CODEX_CLI_PATH=/usr/local/bin/codex
```

`DATABASE_URL` is still accepted as a fallback for hosted environments, but
prefer `EUMPA_DATABASE_URL` for this app.

## Startup Troubleshooting

Check backend health first:

```bash
curl http://localhost:8000/api/health
```

Common startup errors:

- `uv: command not found`: install uv or put it on `PATH`.
- `alembic: command not found`: run `uv sync --dev`, then start with `uv run eumpa-studio start`.
- `address already in use`: another process is using port 8000; stop it or pass `--port`.
- `cannot connect to ComfyUI`: verify `EUMPA_COMFYUI_URL` and that the ComfyUI server is reachable from the small server.
- `codex: command not found`: set `EUMPA_CODEX_CLI_PATH` to the absolute Codex CLI path.
- SQLite permission errors: verify the process can read and write `EUMPA_DATA_ROOT` and the working directory that contains the SQLite database.
