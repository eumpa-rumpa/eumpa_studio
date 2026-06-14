"""Assets route for eumpa_studio API."""

from __future__ import annotations

import datetime
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.config import Settings
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Asset, Attempt, Shot
from eumpa_studio.domain.statuses import AttemptStatus
from eumpa_studio.server.deps import get_settings_dep
from eumpa_studio.storage.media import (
    asset_url,
    assets_dir,
    ensure_assets_dir,
    make_thumbnail,
    thumbnail_path,
    thumbnail_url,
)
from eumpa_studio.storage.paths import save_upload

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]


class AssetRead(BaseModel):
    id: str
    project_id: str
    name: str
    storage_backend: str
    relative_path: str
    mime_type: str | None
    created_at: datetime.datetime
    url: str
    thumb_url: str

    model_config = {"from_attributes": True}


class AttemptRead(BaseModel):
    id: str
    shot_id: str
    status: str
    image_storage_backend: str | None
    image_relative_path: str | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


def _asset_to_read(asset: Asset) -> AssetRead:
    return AssetRead(
        id=asset.id,
        project_id=asset.project_id,
        name=asset.name,
        storage_backend=asset.storage_backend,
        relative_path=asset.relative_path,
        mime_type=asset.mime_type,
        created_at=asset.created_at,
        url=asset_url(asset.project_id, asset.id),
        thumb_url=thumbnail_url(asset.project_id, asset.id),
    )


@router.post("/assets/{project_id}", response_model=AssetRead, status_code=201)
def upload_asset(
    project_id: str,
    file: UploadFile,
    db: DbSession,
    settings: AppSettings,
) -> AssetRead:
    """Upload a new asset file for a project."""
    a_dir = ensure_assets_dir(settings.data_root, project_id)

    asset_id = str(uuid.uuid4())
    safe_name = Path(file.filename or "upload").name
    unique_name = f"{asset_id}_{safe_name}"
    backend, relative_path = save_upload(file, a_dir, settings.data_root, dest_name=unique_name)
    asset = Asset(
        id=asset_id,
        project_id=project_id,
        name=file.filename or "upload",
        storage_backend=backend,
        relative_path=relative_path,
        mime_type=file.content_type or None,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Generate thumbnail (best-effort; do not fail if unavailable)
    source_path = settings.data_root / relative_path
    thumb = thumbnail_path(a_dir, asset_id)
    try:
        make_thumbnail(source_path, thumb)
    except Exception:
        pass

    return _asset_to_read(asset)


@router.get("/assets/{project_id}", response_model=list[AssetRead])
def list_assets(
    project_id: str,
    db: DbSession,
) -> list[AssetRead]:
    """List all assets for a project."""
    assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.project_id == project_id)
            .order_by(Asset.created_at, Asset.id)
        ).all()
    )
    return [_asset_to_read(a) for a in assets]


@router.get("/assets/{project_id}/{asset_id}/thumb")
def serve_thumbnail(
    project_id: str,
    asset_id: str,
    db: DbSession,
    settings: AppSettings,
) -> FileResponse:
    """Serve a thumbnail for an asset, falling back to the original file."""
    asset = db.get(Asset, asset_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    a_dir = assets_dir(settings.data_root, project_id)
    thumb = thumbnail_path(a_dir, asset_id)
    if thumb.exists():
        return FileResponse(str(thumb))

    # Fall back to original file
    original = settings.data_root / asset.relative_path
    if not original.exists():
        raise HTTPException(status_code=404, detail="Asset file not found")
    return FileResponse(str(original))


@router.get("/assets/{project_id}/{asset_id}")
def serve_asset(
    project_id: str,
    asset_id: str,
    db: DbSession,
    settings: AppSettings,
) -> FileResponse:
    """Serve the original asset file."""
    asset = db.get(Asset, asset_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    original = settings.data_root / asset.relative_path
    if not original.exists():
        raise HTTPException(status_code=404, detail="Asset file not found")
    return FileResponse(str(original))


@router.post(
    "/assets/{project_id}/{asset_id}/use-for-shot/{shot_id}",
    response_model=AttemptRead,
    status_code=201,
)
def use_asset_for_shot(
    project_id: str,
    asset_id: str,
    shot_id: str,
    db: DbSession,
) -> AttemptRead:
    """Create a new Attempt draft for a shot using the given asset as the image."""
    asset = db.get(Asset, asset_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    shot = db.get(Shot, shot_id)
    if shot is None or shot.project_id != project_id:
        raise HTTPException(status_code=404, detail="Shot not found")

    attempt = Attempt(
        shot_id=shot_id,
        status=AttemptStatus.NEEDS_INPUT.value,
        image_storage_backend=asset.storage_backend,
        image_relative_path=asset.relative_path,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return AttemptRead(
        id=attempt.id,
        shot_id=attempt.shot_id,
        status=attempt.status,
        image_storage_backend=attempt.image_storage_backend,
        image_relative_path=attempt.image_relative_path,
        created_at=attempt.created_at,
    )
