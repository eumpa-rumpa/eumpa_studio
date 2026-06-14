# Server Topology

## Small Server Role

The small server is the operator-facing control plane for the MVP:

- FastAPI backend
- React static frontend assets
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

Client machines are browsers on the internal network. They access the React UI
served by the small server and send API requests to the FastAPI backend.

## Storage Policy

Heavy render files stay on the ComfyUI server. Selected clips can be copied to a
small-server export directory under `EUMPA_DATA_ROOT` when they need to be
reviewed, packaged, or shared from the operator server.

## Config Example

Use `.env` on the small server to point the backend at the render server:

```dotenv
EUMPA_DATA_ROOT=/srv/eumpa-studio
EUMPA_COMFYUI_URL=http://comfyui-server:8188
EUMPA_CODEX_CLI_PATH=/usr/local/bin/codex
```

## Startup Troubleshooting

Check backend health first:

```bash
curl http://localhost:8000/api/health
```

Common startup errors:

- `uv: command not found`: install uv or put it on `PATH`.
- `alembic: command not found`: run `uv sync`, then start with `uv run eumpa_studio start`.
- `address already in use`: another process is using port 8000; stop it or pass `--port`.
- `cannot connect to ComfyUI`: verify `EUMPA_COMFYUI_URL` and that the ComfyUI server is reachable from the small server.
- `codex: command not found`: set `EUMPA_CODEX_CLI_PATH` to the absolute Codex CLI path.
- SQLite permission errors: verify the process can read and write `EUMPA_DATA_ROOT` and the working directory that contains the SQLite database.
