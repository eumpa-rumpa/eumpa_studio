"""Shots route for eumpa_studio API."""

from __future__ import annotations

import datetime
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from eumpa_studio.config import Settings, get_settings_dep
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Shot
from eumpa_studio.domain.statuses import AttemptStatus

router = APIRouter()

# Statuses that are valid for the review endpoint
_REVIEW_STATUSES = {
    AttemptStatus.NEEDS_REVIEW.value,
    AttemptStatus.SELECTED.value,
    AttemptStatus.REDO.value,
    AttemptStatus.REJECTED.value,
    AttemptStatus.FAILED.value,
}

DbSession = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


class AttemptRead(BaseModel):
    id: str
    shot_id: str
    status: str
    review_note: str | None
    output_metadata: str | None
    comfyui_prompt_id: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ReviewBody(BaseModel):
    status: str
    review_note: str | None = None


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

    if body.status == AttemptStatus.SELECTED.value:
        shot = db.get(Shot, shot_id)
        if shot is None:
            raise HTTPException(status_code=404, detail="Shot not found")
        shot.active_attempt_id = attempt_id

    db.commit()
    db.refresh(attempt)
    return attempt


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

    try:
        meta = json.loads(attempt.output_metadata)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=404, detail="Invalid output metadata")

    filename = meta.get("filename", "")
    subfolder = meta.get("subfolder", "")
    file_type = meta.get("type", "output")
    base_url = settings.comfyui_url.rstrip("/")

    video_url = f"{base_url}/view?filename={filename}&subfolder={subfolder}&type={file_type}"
    return {"video_url": video_url}
