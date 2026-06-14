"""File storage path utilities for eumpa_studio."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import UploadFile


def project_inputs_dir(data_root: Path, project_id: str) -> Path:
    """Return the path to the inputs directory for a project.

    Returns data_root/projects/{project_id}/inputs
    """
    return data_root / "projects" / project_id / "inputs"


def ensure_project_dirs(data_root: Path, project_id: str) -> Path:
    """Create the inputs directory for a project and return it."""
    inputs_dir = project_inputs_dir(data_root, project_id)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    return inputs_dir


def save_upload(
    upload: UploadFile,
    dest_dir: Path,
    data_root: Path,
    dest_name: str | None = None,
) -> tuple[str, str]:
    """Save an uploaded file to dest_dir and return (storage_backend, relative_path).

    The relative_path is relative to data_root, e.g.
    ``"projects/{project_id}/inputs/audio.mp3"``.
    Pass ``dest_name`` to override the filename (e.g. to add a unique prefix).
    """
    raw_name = upload.filename or "upload"
    safe_name = dest_name if dest_name is not None else Path(raw_name).name
    dest_path = dest_dir / safe_name
    with dest_path.open("wb") as out:
        shutil.copyfileobj(upload.file, out)
    relative_path = str(dest_path.relative_to(data_root))
    return "local", relative_path
