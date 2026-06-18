"""Studio-wide settings routes for eumpa_studio API."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import StudioSetting
from eumpa_studio.execution.codex_prompt import DEFAULT_SYSTEM_PROMPT

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]
PROMPT_SYSTEM_DEFAULT_KEY = "prompt_system_default"


class PromptSystemDefaultRead(BaseModel):
    system_prompt: str
    is_custom: bool
    updated_at: datetime.datetime | None


class PromptSystemDefaultUpdate(BaseModel):
    system_prompt: str


@router.get("/settings/prompt-system-default", response_model=PromptSystemDefaultRead)
def get_prompt_system_default(db: DbSession) -> PromptSystemDefaultRead:
    setting = db.get(StudioSetting, PROMPT_SYSTEM_DEFAULT_KEY)
    if setting is None:
        return PromptSystemDefaultRead(
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            is_custom=False,
            updated_at=None,
        )
    return PromptSystemDefaultRead(
        system_prompt=setting.value,
        is_custom=True,
        updated_at=setting.updated_at,
    )


@router.patch("/settings/prompt-system-default", response_model=PromptSystemDefaultRead)
def save_prompt_system_default(
    body: PromptSystemDefaultUpdate,
    db: DbSession,
) -> PromptSystemDefaultRead:
    system_prompt = body.system_prompt.strip()
    if not system_prompt:
        raise HTTPException(status_code=422, detail="System prompt cannot be empty")

    setting = db.get(StudioSetting, PROMPT_SYSTEM_DEFAULT_KEY)
    if setting is None:
        setting = StudioSetting(key=PROMPT_SYSTEM_DEFAULT_KEY, value=system_prompt)
        db.add(setting)
    else:
        setting.value = system_prompt

    db.commit()
    db.refresh(setting)
    return PromptSystemDefaultRead(
        system_prompt=setting.value,
        is_custom=True,
        updated_at=setting.updated_at,
    )
