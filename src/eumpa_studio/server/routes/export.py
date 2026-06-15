"""Export routes for eumpa_studio API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.config import Settings, get_settings_dep
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Shot
from eumpa_studio.domain.statuses import AttemptStatus
from eumpa_studio.export.selected import export_project

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


class ExportResult(BaseModel):
    """Response model for a project export."""

    export_dir: str
    clip_count: int
    shot_list: str
    snapshots: str


class ExportStatus(BaseModel):
    """Quick summary of selected attempts for a project."""

    project_id: str
    selected_count: int


@router.post(
    "/export/projects/{project_id}",
    response_model=ExportResult,
)
def run_export(
    project_id: str,
    db: DbSession,
    settings: SettingsDep,
) -> ExportResult:
    """Trigger an export of selected clips for a project.

    Returns 200 even when there are no selected clips (clip_count == 0).
    """
    result = export_project(
        session=db,
        project_id=project_id,
        data_root=settings.data_root,
        export_root=settings.output_path,
    )
    return ExportResult(**result)


@router.get(
    "/export/projects/{project_id}/status",
    response_model=ExportStatus,
)
def export_status(
    project_id: str,
    db: DbSession,
) -> ExportStatus:
    """Return the count of selected attempts for a project."""
    stmt = (
        select(Attempt)
        .join(Shot, Attempt.shot_id == Shot.id)
        .where(Shot.project_id == project_id)
        .where(Attempt.status == AttemptStatus.SELECTED.value)
    )
    selected_count = len(db.scalars(stmt).all())
    return ExportStatus(project_id=project_id, selected_count=selected_count)
