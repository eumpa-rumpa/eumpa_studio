"""Media asset storage utilities for eumpa_studio."""

from __future__ import annotations

import shutil
from pathlib import Path


def assets_dir(data_root: Path, project_id: str) -> Path:
    """Return the path to the assets directory for a project.

    Returns data_root/projects/{project_id}/assets
    """
    return data_root / "projects" / project_id / "assets"


def ensure_assets_dir(data_root: Path, project_id: str) -> Path:
    """Create the assets directory for a project and return it."""
    a_dir = assets_dir(data_root, project_id)
    a_dir.mkdir(parents=True, exist_ok=True)
    return a_dir


def thumbnail_path(a_dir: Path, asset_id: str) -> Path:
    """Return the thumbnail path for an asset.

    Returns assets_dir/thumbs/{asset_id}.jpg
    """
    return a_dir / "thumbs" / f"{asset_id}.jpg"


def make_thumbnail(
    source_path: Path,
    thumb_path: Path,
    size: tuple[int, int] = (256, 256),
) -> None:
    """Generate a JPEG thumbnail at thumb_path from source_path.

    Uses Pillow if available; falls back to copying the original file.
    """
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image  # type: ignore[import-untyped]

        with Image.open(source_path) as img:
            img.thumbnail(size)
            img.convert("RGB").save(thumb_path, format="JPEG")
    except Exception:
        # Pillow not available or image cannot be opened — copy original
        shutil.copy2(source_path, thumb_path)


def asset_url(project_id: str, asset_id: str) -> str:
    """Return the URL for serving an asset."""
    return f"/api/assets/{project_id}/{asset_id}"


def thumbnail_url(project_id: str, asset_id: str) -> str:
    """Return the URL for serving an asset thumbnail."""
    return f"/api/assets/{project_id}/{asset_id}/thumb"
