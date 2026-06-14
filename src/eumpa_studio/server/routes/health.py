"""Health check route for eumpa_studio API."""

import subprocess

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from eumpa_studio.config import Settings
from eumpa_studio.server.deps import get_db, get_settings_dep

router = APIRouter()


def _check_database(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


def _check_comfyui(comfyui_url: str) -> str:
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{comfyui_url}/system_stats")
            response.raise_for_status()
            return "ok"
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        return "unreachable"
    except Exception:
        return "unreachable"


def _check_codex_cli(codex_cli_path: str) -> str:
    try:
        result = subprocess.run(
            [codex_cli_path, "--version"],
            timeout=3,
            capture_output=True,
        )
        if result.returncode == 0:
            return "ok"
        return "not_found"
    except FileNotFoundError:
        return "not_found"
    except Exception:
        return "not_found"


@router.get("/health")
async def health(
    settings: Settings = Depends(get_settings_dep),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Extended health check endpoint returning status of all services."""
    return {
        "backend": "ok",
        "database": _check_database(db),
        "comfyui": _check_comfyui(settings.comfyui_url),
        "codex_cli": _check_codex_cli(settings.codex_cli_path),
    }
