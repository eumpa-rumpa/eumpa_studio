"""Shot production routes for eumpa_studio API."""

from __future__ import annotations

import datetime
import json
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from eumpa_studio.config import Settings, get_settings_dep
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, ExecutionMode, Project, Shot, WorkflowTemplate
from eumpa_studio.domain.statuses import AttemptStatus, ShotStatus

router = APIRouter()


class AttemptSummary(BaseModel):
    id: str
    status: str
    image_storage_backend: str | None
    image_relative_path: str | None
    prompt_ko: str | None
    prompt_en: str | None
    output_metadata: str | None
    video_url: str | None = None

    model_config = {"from_attributes": True}


class AttemptRead(BaseModel):
    id: str
    shot_id: str
    parent_attempt_id: str | None
    image_storage_backend: str | None
    image_relative_path: str | None
    end_image_storage_backend: str | None
    end_image_relative_path: str | None
    input_video_storage_backend: str | None
    input_video_relative_path: str | None
    shot_note_snapshot: str | None
    prompt_ko: str | None
    prompt_en: str | None
    workflow_template_id: str | None
    execution_mode_id: str | None
    param_overrides: str | None
    seed: int | None
    workflow_snapshot: str | None
    comfyui_prompt_id: str | None
    output_metadata: str | None
    review_note: str | None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ShotRead(BaseModel):
    id: str
    project_id: str
    order: int
    start_time: float
    end_time: float
    duration: float
    speaker: str | None
    lyrics_text: str | None
    shot_note: str | None
    status: str
    active_attempt_id: str | None
    active_attempt: AttemptSummary | None
    attempt_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": False}


class ShotCreate(BaseModel):
    order: int
    start_time: float
    end_time: float
    duration: float | None = None
    speaker: str | None = None
    lyrics_text: str | None = None
    shot_note: str | None = None
    status: str = ShotStatus.NEEDS_INPUT.value
    active_attempt_id: str | None = None


class ShotUpdate(BaseModel):
    start_time: float | None = None
    end_time: float | None = None
    shot_note: str | None = None
    active_attempt_id: str | None = None
    status: str | None = None


class AttemptUpdate(BaseModel):
    image_storage_backend: str | None = None
    image_relative_path: str | None = None
    end_image_storage_backend: str | None = None
    end_image_relative_path: str | None = None
    input_video_storage_backend: str | None = None
    input_video_relative_path: str | None = None
    shot_note_snapshot: str | None = None
    prompt_ko: str | None = None
    prompt_en: str | None = None
    workflow_template_id: str | None = None
    execution_mode_id: str | None = None
    param_overrides: str | None = None
    seed: int | None = None
    review_note: str | None = None


class AttemptCreate(BaseModel):
    image_storage_backend: str | None = None
    image_relative_path: str | None = None
    shot_note_snapshot: str | None = None
    prompt_ko: str | None = None
    prompt_en: str | None = None
    workflow_template_id: str | None = None
    execution_mode_id: str | None = None
    param_overrides: str | None = None
    seed: int | None = None


DbSession = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]

# Statuses that are valid for the review endpoint
_REVIEW_STATUSES = {
    AttemptStatus.NEEDS_REVIEW.value,
    AttemptStatus.SELECTED.value,
    AttemptStatus.REDO.value,
    AttemptStatus.REJECTED.value,
    AttemptStatus.FAILED.value,
}

_RENDER_INPUT_FIELDS = {
    "image_storage_backend",
    "image_relative_path",
    "end_image_storage_backend",
    "end_image_relative_path",
    "input_video_storage_backend",
    "input_video_relative_path",
    "shot_note_snapshot",
    "prompt_ko",
    "prompt_en",
    "workflow_template_id",
    "execution_mode_id",
    "param_overrides",
    "seed",
}


class ReviewBody(BaseModel):
    status: str
    review_note: str | None = None


def _attempt_counts(db: Session, shot_ids: list[str]) -> dict[str, int]:
    if not shot_ids:
        return {}

    rows = db.execute(
        select(Attempt.shot_id, func.count(Attempt.id))
        .where(Attempt.shot_id.in_(shot_ids))
        .group_by(Attempt.shot_id)
    ).all()
    return {shot_id: count for shot_id, count in rows}


def _build_video_url(output_metadata: str | None, settings: Settings) -> str | None:
    if not output_metadata:
        return None
    try:
        meta = json.loads(output_metadata)
    except (json.JSONDecodeError, TypeError):
        return None

    filename = meta.get("filename", "")
    if not filename:
        return None

    params = urlencode(
        {
            "filename": filename,
            "subfolder": meta.get("subfolder", ""),
            "type": meta.get("type", "output"),
        }
    )
    return f"{settings.comfyui_url.rstrip('/')}/view?{params}"


def _serialize_attempt_summary(attempt: Attempt, settings: Settings) -> AttemptSummary:
    return AttemptSummary(
        id=attempt.id,
        status=attempt.status,
        image_storage_backend=attempt.image_storage_backend,
        image_relative_path=attempt.image_relative_path,
        prompt_ko=attempt.prompt_ko,
        prompt_en=attempt.prompt_en,
        output_metadata=attempt.output_metadata,
        video_url=_build_video_url(attempt.output_metadata, settings),
    )


def _serialize_shot(shot: Shot, attempt_count: int, settings: Settings) -> ShotRead:
    active_attempt = (
        _serialize_attempt_summary(shot.active_attempt, settings)
        if shot.active_attempt is not None
        else None
    )
    return ShotRead(
        id=shot.id,
        project_id=shot.project_id,
        order=shot.order,
        start_time=shot.start_time,
        end_time=shot.end_time,
        duration=shot.duration,
        speaker=shot.speaker,
        lyrics_text=shot.lyrics_text,
        shot_note=shot.shot_note,
        status=shot.status,
        active_attempt_id=shot.active_attempt_id,
        active_attempt=active_attempt,
        attempt_count=attempt_count,
        created_at=shot.created_at,
        updated_at=shot.updated_at,
    )


def _get_shot_with_active_attempt(db: Session, shot_id: str) -> Shot:
    shot = db.scalar(
        select(Shot)
        .where(Shot.id == shot_id)
        .options(selectinload(Shot.active_attempt))
    )
    if shot is None:
        raise HTTPException(status_code=404, detail="Shot not found")
    return shot


def _validate_active_attempt(db: Session, shot: Shot, attempt_id: str | None) -> None:
    if attempt_id is None:
        return

    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.shot_id != shot.id:
        raise HTTPException(status_code=422, detail="Active attempt must belong to this shot")


def _get_attempt_for_shot(db: Session, shot_id: str, attempt_id: str) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.shot_id != shot_id:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


def _validate_attempt_workflow_config(
    db: Session,
    workflow_template_id: str | None,
    execution_mode_id: str | None,
) -> None:
    if workflow_template_id is None and execution_mode_id is None:
        return
    if workflow_template_id is None or execution_mode_id is None:
        raise HTTPException(
            status_code=422,
            detail="workflow_template_id and execution_mode_id must be set together",
        )

    template = db.get(WorkflowTemplate, workflow_template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Workflow template not found")

    mode = db.get(ExecutionMode, execution_mode_id)
    if mode is None:
        raise HTTPException(status_code=422, detail="Execution mode not found")
    if mode.workflow_template_id != workflow_template_id:
        raise HTTPException(
            status_code=422,
            detail="Execution mode must belong to the selected workflow template",
        )


def _reject_rendered_input_mutation(attempt: Attempt, update_data: dict[str, object]) -> None:
    if not attempt.output_metadata:
        return
    if _RENDER_INPUT_FIELDS.intersection(update_data):
        raise HTTPException(
            status_code=422,
            detail="Duplicate rendered attempts before changing inputs",
        )


def _read_shot(db: Session, shot: Shot, settings: Settings) -> ShotRead:
    counts = _attempt_counts(db, [shot.id])
    return _serialize_shot(shot, counts.get(shot.id, 0), settings)


@router.get("/shots", response_model=list[ShotRead])
def list_shots(project_id: str, db: DbSession, settings: SettingsDep) -> list[ShotRead]:
    """List shots for a project ordered by shot order."""
    shots = list(
        db.scalars(
            select(Shot)
            .where(Shot.project_id == project_id)
            .options(selectinload(Shot.active_attempt))
            .order_by(Shot.order, Shot.id)
        ).all()
    )
    counts = _attempt_counts(db, [shot.id for shot in shots])
    return [_serialize_shot(shot, counts.get(shot.id, 0), settings) for shot in shots]


@router.get("/shots/{shot_id}", response_model=ShotRead)
def get_shot(shot_id: str, db: DbSession, settings: SettingsDep) -> ShotRead:
    """Get a single shot with active attempt summary and attempt count."""
    return _read_shot(db, _get_shot_with_active_attempt(db, shot_id), settings)


@router.get("/shots/{shot_id}/attempts", response_model=list[AttemptRead])
def list_shot_attempts(shot_id: str, db: DbSession) -> list[AttemptRead]:
    """List all render attempts for a shot."""
    _get_shot_with_active_attempt(db, shot_id)
    attempts = list(
        db.scalars(
            select(Attempt)
            .where(Attempt.shot_id == shot_id)
            .order_by(Attempt.created_at, Attempt.id)
        ).all()
    )
    return [AttemptRead.model_validate(attempt) for attempt in attempts]


@router.post("/shots/{shot_id}/attempts", response_model=AttemptRead, status_code=201)
def create_attempt(shot_id: str, body: AttemptCreate, db: DbSession) -> AttemptRead:
    """Create an editable attempt draft for a shot and make it active."""
    shot = _get_shot_with_active_attempt(db, shot_id)
    create_data = body.model_dump(exclude_unset=True)
    _validate_attempt_workflow_config(
        db,
        create_data.get("workflow_template_id"),
        create_data.get("execution_mode_id"),
    )

    attempt = Attempt(
        shot_id=shot.id,
        status=AttemptStatus.NEEDS_INPUT.value,
        **create_data,
    )
    db.add(attempt)
    db.flush()
    shot.active_attempt_id = attempt.id
    shot.status = ShotStatus.NEEDS_INPUT.value
    db.commit()
    db.refresh(attempt)
    return AttemptRead.model_validate(attempt)


@router.patch("/shots/{shot_id}", response_model=ShotRead)
def update_shot(
    shot_id: str,
    body: ShotUpdate,
    db: DbSession,
    settings: SettingsDep,
) -> ShotRead:
    """Update editable shot fields."""
    shot = _get_shot_with_active_attempt(db, shot_id)
    update_data = body.model_dump(exclude_unset=True)

    if "active_attempt_id" in update_data:
        _validate_active_attempt(db, shot, body.active_attempt_id)

    for field, value in update_data.items():
        setattr(shot, field, value)

    if "start_time" in update_data or "end_time" in update_data:
        shot.duration = shot.end_time - shot.start_time

    db.commit()
    db.refresh(shot)
    return _read_shot(db, _get_shot_with_active_attempt(db, shot.id), settings)


@router.patch("/shots/{shot_id}/attempts/{attempt_id}", response_model=AttemptRead)
def update_shot_attempt(
    shot_id: str,
    attempt_id: str,
    body: AttemptUpdate,
    db: DbSession,
) -> AttemptRead:
    """Update review fields on a shot attempt."""
    _get_shot_with_active_attempt(db, shot_id)
    attempt = _get_attempt_for_shot(db, shot_id, attempt_id)
    update_data = body.model_dump(exclude_unset=True)
    _reject_rendered_input_mutation(attempt, update_data)

    workflow_template_id = update_data.get(
        "workflow_template_id",
        attempt.workflow_template_id,
    )
    execution_mode_id = update_data.get(
        "execution_mode_id",
        attempt.execution_mode_id,
    )
    if "workflow_template_id" in update_data or "execution_mode_id" in update_data:
        _validate_attempt_workflow_config(db, workflow_template_id, execution_mode_id)

    for field, value in update_data.items():
        setattr(attempt, field, value)

    db.commit()
    db.refresh(attempt)
    return AttemptRead.model_validate(attempt)


@router.post(
    "/shots/{shot_id}/attempts/{attempt_id}/duplicate",
    response_model=AttemptRead,
    status_code=201,
)
def duplicate_attempt(shot_id: str, attempt_id: str, db: DbSession) -> AttemptRead:
    """Duplicate render-defining attempt inputs into a new editable attempt."""
    shot = _get_shot_with_active_attempt(db, shot_id)
    source = _get_attempt_for_shot(db, shot_id, attempt_id)
    duplicate = Attempt(
        shot_id=shot.id,
        parent_attempt_id=source.id,
        image_storage_backend=source.image_storage_backend,
        image_relative_path=source.image_relative_path,
        end_image_storage_backend=source.end_image_storage_backend,
        end_image_relative_path=source.end_image_relative_path,
        input_video_storage_backend=source.input_video_storage_backend,
        input_video_relative_path=source.input_video_relative_path,
        shot_note_snapshot=source.shot_note_snapshot,
        prompt_ko=source.prompt_ko,
        prompt_en=source.prompt_en,
        workflow_template_id=source.workflow_template_id,
        execution_mode_id=source.execution_mode_id,
        param_overrides=source.param_overrides,
        seed=source.seed,
        status=AttemptStatus.NEEDS_INPUT.value,
    )
    db.add(duplicate)
    db.flush()
    shot.active_attempt_id = duplicate.id
    shot.status = ShotStatus.NEEDS_INPUT.value
    db.commit()
    db.refresh(duplicate)
    return AttemptRead.model_validate(duplicate)


@router.delete("/shots/{shot_id}/attempts/{attempt_id}", status_code=204)
def delete_shot_attempt(shot_id: str, attempt_id: str, db: DbSession) -> None:
    """Delete a shot attempt without deleting shared project assets."""
    shot = _get_shot_with_active_attempt(db, shot_id)
    attempt = _get_attempt_for_shot(db, shot_id, attempt_id)

    if shot.active_attempt_id == attempt.id:
        shot.active_attempt_id = None
        shot.status = ShotStatus.NEEDS_INPUT.value

    db.delete(attempt)
    db.commit()


@router.post("/projects/{project_id}/shots", response_model=ShotRead, status_code=201)
def create_shot(
    project_id: str,
    body: ShotCreate,
    db: DbSession,
    settings: SettingsDep,
) -> ShotRead:
    """Create a shot manually for a project."""
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    duration = body.duration
    if duration is None:
        duration = body.end_time - body.start_time

    shot = Shot(
        project_id=project_id,
        order=body.order,
        start_time=body.start_time,
        end_time=body.end_time,
        duration=duration,
        speaker=body.speaker,
        lyrics_text=body.lyrics_text,
        shot_note=body.shot_note,
        status=body.status,
        active_attempt_id=body.active_attempt_id,
    )
    _validate_active_attempt(db, shot, body.active_attempt_id)

    db.add(shot)
    db.commit()
    db.refresh(shot)
    return _read_shot(db, _get_shot_with_active_attempt(db, shot.id), settings)


@router.post(
    "/shots/{shot_id}/attempts/{attempt_id}/review",
    response_model=AttemptRead,
)
def review_attempt(
    shot_id: str,
    attempt_id: str,
    body: ReviewBody,
    db: DbSession,
) -> Attempt:
    """Update attempt review status and optionally set it as the active attempt."""
    if body.status not in _REVIEW_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid review status {body.status!r}. "
                f"Must be one of: {sorted(_REVIEW_STATUSES)}"
            ),
        )

    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.shot_id != shot_id:
        raise HTTPException(status_code=404, detail="Attempt not found")

    attempt.status = body.status
    if body.review_note is not None:
        attempt.review_note = body.review_note

    shot = db.get(Shot, shot_id)
    if shot is None:
        raise HTTPException(status_code=404, detail="Shot not found")

    if body.status == AttemptStatus.SELECTED.value:
        shot.active_attempt_id = attempt_id
        shot.status = ShotStatus.SELECTED.value
    elif shot.active_attempt_id == attempt_id:
        shot.status = body.status

    db.commit()
    db.refresh(attempt)
    return AttemptRead.model_validate(attempt)


@router.get("/shots/{shot_id}/attempts/{attempt_id}/video-url")
def get_video_url(
    shot_id: str,
    attempt_id: str,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, str]:
    """Return a ComfyUI view URL for the attempt's output video."""
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.shot_id != shot_id:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if not attempt.output_metadata:
        raise HTTPException(status_code=404, detail="No output metadata for this attempt")

    video_url = _build_video_url(attempt.output_metadata, settings)
    if video_url is None:
        raise HTTPException(status_code=404, detail="Invalid output metadata")
    return {"video_url": video_url}
