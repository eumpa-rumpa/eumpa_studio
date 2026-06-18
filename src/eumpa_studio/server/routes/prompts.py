"""Prompt generation routes for eumpa_studio API."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from eumpa_studio.config import Settings
from eumpa_studio.domain.models import Attempt, Project, Shot
from eumpa_studio.execution.codex_prompt import PromptContext, run_codex_prompt
from eumpa_studio.server.deps import get_db, get_settings_dep

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]


class GeneratePromptRequest(BaseModel):
    attempt_id: str
    system_prompt: str | None = None


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
    status: str
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
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


@router.post("/prompts/generate", response_model=AttemptRead)
def generate_prompt(
    body: GeneratePromptRequest,
    db: DbSession,
    settings: AppSettings,
) -> Attempt:
    """Generate LTX prompts for an attempt using Codex CLI."""
    attempt = db.get(Attempt, body.attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    try:
        shot = db.get(Shot, attempt.shot_id)
        if shot is None:
            raise RuntimeError("Shot not found")

        project = db.get(Project, shot.project_id)
        visual_bible = (
            getattr(project, "visual_bible_text", None) if project is not None else None
        )
        image_path = (
            str(settings.data_root / attempt.image_relative_path)
            if attempt.image_relative_path
            else None
        )
        end_image_path = (
            str(settings.data_root / attempt.end_image_relative_path)
            if attempt.end_image_relative_path
            else None
        )
        shot_note = attempt.shot_note_snapshot or shot.shot_note
        ctx = PromptContext(
            lyrics=shot.lyrics_text,
            speaker=shot.speaker,
            shot_note=shot_note,
            start_time=shot.start_time,
            end_time=shot.end_time,
            visual_bible=visual_bible,
            prior_attempt_context=(
                f"Previous attempt: {attempt.prompt_ko}" if attempt.prompt_ko else None
            ),
            image_path=image_path,
            end_image_path=end_image_path,
            system_prompt=body.system_prompt,
        )

        result = run_codex_prompt(ctx, settings.codex_cli_path)
        attempt.prompt_ko = result.prompt_ko
        attempt.prompt_en = result.prompt_en
        db.commit()
        db.refresh(attempt)
        return attempt
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
