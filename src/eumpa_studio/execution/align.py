"""Audio alignment execution and draft shot generation."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from sqlalchemy.orm import Session

from eumpa_studio.config import Settings
from eumpa_studio.domain.models import Project, Shot
from eumpa_studio.domain.statuses import ShotStatus


@dataclass
class AlignmentResult:
    """Parsed result for a single aligned segment."""

    start: float
    end: float
    duration: float
    speaker: str | None
    lyrics: str | None


def parse_alignment_output(output: str) -> list[AlignmentResult]:
    """Parse JSON output from the alignment command.

    Accepts either a JSON array of objects, or newline-delimited JSON objects
    (JSONL). Each object must have ``start`` and ``end`` fields; ``duration``
    is computed from ``end - start`` when absent. ``speaker`` and ``text`` /
    ``lyrics`` fields are optional.

    Raises:
        ValueError: If the output cannot be parsed as valid JSON.
    """
    output = output.strip()
    if not output:
        return []

    raw_items: list[dict] = []

    # Try JSON array first.
    if output.startswith("["):
        try:
            raw_items = json.loads(output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON array in alignment output: {exc}") from exc
    else:
        # Fall back to JSONL (one JSON object per line).
        for line_no, line in enumerate(output.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw_items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_no} of alignment output: {exc}"
                ) from exc

    results: list[AlignmentResult] = []
    for item in raw_items:
        start: float = float(item["start"])
        end: float = float(item["end"])
        duration: float = float(item.get("duration", end - start))
        speaker: str | None = item.get("speaker") or None
        lyrics: str | None = item.get("text") or item.get("lyrics") or None
        results.append(
            AlignmentResult(
                start=start,
                end=end,
                duration=duration,
                speaker=speaker,
                lyrics=lyrics,
            )
        )

    return results


def run_alignment(audio_path: str, alignment_command: str) -> list[AlignmentResult]:
    """Run the alignment command against *audio_path* and return parsed results.

    The subprocess is called as ``alignment_command audio_path`` with a 30-second
    timeout. stdout is captured and parsed via :func:`parse_alignment_output`.

    Raises:
        RuntimeError: If the subprocess exits with a non-zero code or times out.
        ValueError: If stdout cannot be parsed as valid alignment JSON.
    """
    cmd = [alignment_command, audio_path]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Alignment command timed out after 30 seconds: {' '.join(cmd)}"
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"Alignment command failed with exit code {result.returncode}: "
            f"{result.stderr.strip() or '(no stderr)'}"
        )

    return parse_alignment_output(result.stdout)


def create_draft_shots(
    session: Session,
    project_id: str,
    results: list[AlignmentResult],
) -> list[Shot]:
    """Create Shot rows in the database from alignment results.

    Shots are created with 0-based ``order`` indices and
    ``ShotStatus.NEEDS_INPUT`` status. The session is flushed (not committed)
    so that IDs are assigned before returning.

    Returns:
        The list of newly created :class:`~eumpa_studio.domain.models.Shot`
        objects with populated IDs.
    """
    shots: list[Shot] = []
    for idx, result in enumerate(results):
        shot = Shot(
            project_id=project_id,
            order=idx,
            start_time=result.start,
            end_time=result.end,
            duration=result.duration,
            speaker=result.speaker,
            lyrics_text=result.lyrics,
            status=ShotStatus.NEEDS_INPUT.value,
        )
        session.add(shot)
        shots.append(shot)

    session.flush()
    session.commit()
    return shots


def run_alignment_job(
    session: Session,
    project_id: str,
    settings: Settings,
) -> None:
    """Top-level job runner for the ``align`` job type.

    Loads the project, resolves the audio path, runs the alignment subprocess,
    and persists draft shots. Raises on any error so the worker can mark the
    job as failed.

    Existing shots are never deleted on failure — callers that need a clean
    slate should remove them before enqueueing a new job.
    """
    project: Project | None = session.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id!r} not found")

    if not project.audio_relative_path:
        # No audio attached — nothing to align.
        return

    audio_path = str(settings.data_root / project.audio_relative_path)
    results = run_alignment(audio_path, settings.alignment_command)
    create_draft_shots(session, project_id, results)
