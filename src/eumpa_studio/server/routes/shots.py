"""Shot and attempt routes for eumpa_studio API."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]


class AttemptUpdate(BaseModel):
    prompt_ko: str | None = None
    prompt_en: str | None = None
    review_note: str | None = None


class AttemptRead(BaseModel):
    id: str
    shot_id: str
    status: str
    prompt_ko: str | None
    prompt_en: str | None
    review_note: str | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


@router.patch("/shots/{shot_id}/attempts/{attempt_id}", response_model=AttemptRead)
def update_attempt(
    shot_id: str,
    attempt_id: str,
    body: AttemptUpdate,
    db: DbSession,
) -> Attempt:
    """Update editable fields on an attempt."""
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.shot_id != shot_id:
        raise HTTPException(status_code=404, detail="Attempt not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(attempt, field, value)

    db.commit()
    db.refresh(attempt)
    return attempt
