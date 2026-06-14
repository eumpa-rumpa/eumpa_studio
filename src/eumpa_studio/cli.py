"""eumpa_studio CLI entry point."""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

import typer
import uvicorn

from eumpa_studio.execution.jobs import unsupported_job_runner
from eumpa_studio.execution.worker import WorkerLoop


app_cli = typer.Typer(no_args_is_help=True)


@dataclass(frozen=True)
class Settings:
    """Runtime settings needed by the local start command."""

    data_root: Path
    output_path: Path
    cache_path: Path
    comfyui_url: str
    codex_cli_path: str


def get_settings() -> Settings:
    """Read local runtime settings from environment variables."""
    data_root = Path(os.environ.get("EUMPA_DATA_ROOT", ".eumpa")).expanduser()
    return Settings(
        data_root=data_root,
        output_path=data_root / "outputs",
        cache_path=data_root / "cache",
        comfyui_url=os.environ.get("EUMPA_COMFYUI_URL", "http://localhost:8188"),
        codex_cli_path=os.environ.get("EUMPA_CODEX_CLI_PATH", "codex"),
    )


@app_cli.callback()
def cli() -> None:
    """eumpa_studio operator commands."""


@app_cli.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to listen on"),
    reload: bool = typer.Option(False, help="Enable auto-reload (dev only)"),
) -> None:
    """Start the eumpa_studio backend, apply DB migrations, and launch the job worker."""
    settings = get_settings()

    settings.data_root.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)
    settings.cache_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True)

    from eumpa_studio.db.session import SessionLocal

    stop_event = threading.Event()
    worker_loop = WorkerLoop(session_factory=SessionLocal, runner=unsupported_job_runner)
    worker_thread = worker_loop.start_in_thread(stop_event=stop_event)

    try:
        uvicorn.run(
            "eumpa_studio.server.app:app",
            host=host,
            port=port,
            reload=reload,
        )
    finally:
        stop_event.set()
        worker_thread.join(timeout=5)


def main() -> None:
    """Run the CLI app."""
    app_cli()


if __name__ == "__main__":
    main()
