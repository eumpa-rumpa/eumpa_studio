"""Codex CLI prompt generation provider."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class PromptContext:
    lyrics: str | None
    speaker: str | None
    shot_note: str | None
    start_time: float
    end_time: float
    visual_bible: str | None
    prior_attempt_context: str | None
    image_path: str | None


@dataclass
class PromptResult:
    image_observations: str
    motion_camera_plan: str
    prompt_ko: str
    prompt_en: str
    negative_rules: str | None
    rationale: str | None


REQUIRED_KEYS = (
    "image_observations",
    "motion_camera_plan",
    "prompt_ko",
    "prompt_en",
)


def _section(title: str, value: str | None) -> str:
    return f"## {title}\n{value if value else 'None'}"


def build_prompt_text(ctx: PromptContext) -> str:
    """Build the text prompt passed to Codex CLI."""
    sections = [
        "# LTX Prompt Generation Request",
        (
            "Generate prompts for LTX video generation. "
            "Be specific about motion and camera."
        ),
        _section("Time Range", f"{ctx.start_time:.3f}s - {ctx.end_time:.3f}s"),
        _section("Visual Bible", ctx.visual_bible),
        _section("Lyrics", ctx.lyrics),
        _section("Speaker", ctx.speaker),
        _section("Shot Note", ctx.shot_note),
        _section("Prior Attempt Context", ctx.prior_attempt_context),
        (
            "Return only valid JSON with required keys: "
            "image_observations, motion_camera_plan, prompt_ko, prompt_en. "
            "Optional keys: negative_rules, rationale."
        ),
    ]
    return "\n\n".join(sections)


def _parse_result(stdout: str) -> PromptResult:
    try:
        data: Any = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Codex CLI output was not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("Codex CLI output must be a JSON object")

    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise ValueError(f"Codex CLI output missing required key(s): {', '.join(missing)}")

    return PromptResult(
        image_observations=str(data["image_observations"]),
        motion_camera_plan=str(data["motion_camera_plan"]),
        prompt_ko=str(data["prompt_ko"]),
        prompt_en=str(data["prompt_en"]),
        negative_rules=(
            None if data.get("negative_rules") is None else str(data["negative_rules"])
        ),
        rationale=None if data.get("rationale") is None else str(data["rationale"]),
    )


def run_codex_prompt(
    ctx: PromptContext,
    codex_cli_path: str,
    timeout: int = 60,
) -> PromptResult:
    """Run Codex CLI and parse its JSON prompt-generation response."""
    prompt_text = build_prompt_text(ctx)
    args = [
        codex_cli_path,
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
    ]
    if ctx.image_path:
        args.extend(["--image", ctx.image_path])

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            input=prompt_text,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Codex CLI timed out after {timeout} seconds") from exc

    if completed.returncode != 0:
        raise RuntimeError(
            f"Codex CLI failed with exit code {completed.returncode}: {completed.stderr}"
        )

    return _parse_result(completed.stdout)
