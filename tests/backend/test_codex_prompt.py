"""Tests for Codex CLI prompt generation."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from eumpa_studio.execution.codex_prompt import (
    PromptContext,
    PromptResult,
    build_prompt_text,
    run_codex_prompt,
)


def _context(image_path: str | None = None) -> PromptContext:
    return PromptContext(
        lyrics="Tonight the city lights keep glowing",
        speaker="Lead vocal",
        shot_note="Close-up with soft rain",
        start_time=12.5,
        end_time=16.0,
        visual_bible="Neon noir, realistic lighting",
        prior_attempt_context="Previous attempt: static portrait",
        image_path=image_path,
    )


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["codex", "prompt"],
        returncode=returncode,
        stdout=stdout,
        stderr="boom",
    )


def test_build_prompt_text_includes_lyrics() -> None:
    prompt_text = build_prompt_text(_context())

    assert "Tonight the city lights keep glowing" in prompt_text


def test_run_codex_success() -> None:
    stdout = json.dumps(
        {
            "image_observations": "subject faces camera",
            "motion_camera_plan": "slow dolly in",
            "prompt_ko": "Korean prompt",
            "prompt_en": "English prompt",
            "negative_rules": "no extra fingers",
            "rationale": "matches lyrics",
        }
    )

    with patch("subprocess.run", return_value=_completed(stdout)) as run:
        result = run_codex_prompt(_context(image_path="/tmp/ref.png"), "codex")

    run.assert_called_once()
    assert isinstance(result, PromptResult)
    assert result.image_observations == "subject faces camera"
    assert result.motion_camera_plan == "slow dolly in"
    assert result.prompt_ko == "Korean prompt"
    assert result.prompt_en == "English prompt"
    assert result.negative_rules == "no extra fingers"
    assert result.rationale == "matches lyrics"


def test_run_codex_timeout() -> None:
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=60),
    ):
        with pytest.raises(RuntimeError):
            run_codex_prompt(_context(), "codex")


def test_run_codex_nonzero_exit() -> None:
    stdout = json.dumps(
        {
            "image_observations": "obs",
            "motion_camera_plan": "plan",
            "prompt_ko": "ko",
            "prompt_en": "en",
        }
    )

    with patch("subprocess.run", return_value=_completed(stdout, returncode=1)):
        with pytest.raises(RuntimeError):
            run_codex_prompt(_context(), "codex")


def test_run_codex_invalid_json() -> None:
    with patch("subprocess.run", return_value=_completed("not json")):
        with pytest.raises(ValueError):
            run_codex_prompt(_context(), "codex")


def test_run_codex_missing_cli() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            run_codex_prompt(_context(), "missing-codex")


def test_run_codex_missing_required_key() -> None:
    stdout = json.dumps(
        {
            "image_observations": "obs",
            "motion_camera_plan": "plan",
            "prompt_en": "en",
        }
    )

    with patch("subprocess.run", return_value=_completed(stdout)):
        with pytest.raises(ValueError):
            run_codex_prompt(_context(), "codex")
