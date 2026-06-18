"""Tests for Codex CLI prompt generation."""

from __future__ import annotations

from unittest.mock import patch

from eumpa_studio.execution.codex_prompt import (
    PromptContext,
    build_prompt_text,
    run_codex_prompt,
)


def test_run_codex_prompt_uses_non_interactive_exec_mode():
    ctx = PromptContext(
        lyrics="test lyric",
        speaker=None,
        shot_note="close-up",
        start_time=1.0,
        end_time=2.0,
        visual_bible=None,
        prior_attempt_context=None,
        image_path="/tmp/reference.png",
    )

    stdout = (
        '{"image_observations":"red frame",'
        '"motion_camera_plan":"slow push",'
        '"prompt_ko":"한국어 프롬프트",'
        '"prompt_en":"English prompt"}'
    )

    with patch("subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = stdout
        run.return_value.stderr = ""

        result = run_codex_prompt(ctx, "codex", timeout=12)

    args = run.call_args.args[0]
    assert args[:2] == ["codex", "exec"]
    assert "--ephemeral" in args
    assert "--skip-git-repo-check" in args
    assert "--image" in args
    assert "/tmp/reference.png" in args
    assert run.call_args.kwargs["input"].startswith("# LTX Prompt Generation Request")
    assert run.call_args.kwargs["timeout"] == 12
    assert result.prompt_ko == "한국어 프롬프트"
    assert result.prompt_en == "English prompt"


def test_build_prompt_text_includes_custom_system_prompt_and_image_roles():
    ctx = PromptContext(
        lyrics="test lyric",
        speaker="artist",
        shot_note="인물이 신나게 손을 펼치며 랩을 한다",
        start_time=1.0,
        end_time=2.0,
        visual_bible="high contrast stage",
        prior_attempt_context=None,
        image_path="/tmp/start.png",
        end_image_path="/tmp/end.png",
        system_prompt="Custom LTX direction",
    )

    prompt_text = build_prompt_text(ctx)

    assert "Custom LTX direction" in prompt_text
    assert "Start Image\n/tmp/start.png" in prompt_text
    assert "End Image\n/tmp/end.png" in prompt_text
    assert "인물이 신나게 손을 펼치며 랩을 한다" in prompt_text
