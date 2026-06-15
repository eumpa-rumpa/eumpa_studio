"""Export logic for selected clips and metadata."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.domain.models import Attempt, Shot
from eumpa_studio.domain.statuses import AttemptStatus


def collect_selected_attempts(
    session: Session, project_id: str
) -> list[tuple[Shot, Attempt]]:
    """Return (shot, attempt) pairs in shot order where attempt.status == SELECTED.

    Only shots with a non-null active_attempt_id whose status is SELECTED are included.
    Results are sorted by shot.order ascending.
    """
    stmt = (
        select(Shot, Attempt)
        .join(Attempt, Shot.active_attempt_id == Attempt.id)
        .where(Shot.project_id == project_id)
        .where(Attempt.status == AttemptStatus.SELECTED.value)
        .order_by(Shot.order)
    )
    rows = session.execute(stmt).all()
    return [(shot, attempt) for shot, attempt in rows]


def export_project(
    session: Session,
    project_id: str,
    data_root: Path,
    export_root: Path,
) -> dict:
    """Export selected clips for a project.

    Steps:
    1. Collect selected attempts in shot order.
    2. Create export dir: export_root/projects/{project_id}/exports/{timestamp}/
    3. Copy each clip: if output_metadata has filename/subfolder,
       source = data_root / relative path (skip if not found locally).
       dest = export_dir/clips/{order:03d}_{filename}
    4. Write shot_list.json: list of {order, shot_id, attempt_id, lyrics_text,
       start_time, end_time, speaker, prompt_ko, prompt_en, output_metadata}
    5. Write attempt_snapshots.json: list of {attempt_id, prompt_ko, prompt_en,
       seed, workflow_template_id, execution_mode_id, param_overrides,
       workflow_snapshot, output_metadata}
    6. Return {"export_dir", "clip_count", "shot_list", "snapshots"}
    """
    pairs = collect_selected_attempts(session, project_id)

    # Build export directory with ISO timestamp (safe for filesystem)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    export_dir = export_root / "projects" / project_id / "exports" / timestamp
    clips_dir = export_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    shot_list: list[dict] = []
    snapshots: list[dict] = []
    clip_count = 0

    for shot, attempt in pairs:
        output_meta: dict = {}
        if attempt.output_metadata:
            try:
                output_meta = json.loads(attempt.output_metadata)
            except (json.JSONDecodeError, TypeError):
                output_meta = {}

        # Try to copy the clip file
        filename = output_meta.get("filename", "")
        subfolder = output_meta.get("subfolder", "")

        if filename:
            # Construct a candidate relative path inside data_root
            if subfolder:
                rel = Path(subfolder) / filename
            else:
                rel = Path(filename)
            source = data_root / rel
            if source.exists():
                dest_name = f"{shot.order:03d}_{filename}"
                shutil.copy2(source, clips_dir / dest_name)
                clip_count += 1

        shot_list.append(
            {
                "order": shot.order,
                "shot_id": shot.id,
                "attempt_id": attempt.id,
                "lyrics_text": shot.lyrics_text,
                "start_time": shot.start_time,
                "end_time": shot.end_time,
                "speaker": shot.speaker,
                "prompt_ko": attempt.prompt_ko,
                "prompt_en": attempt.prompt_en,
                "output_metadata": output_meta,
            }
        )

        snapshots.append(
            {
                "attempt_id": attempt.id,
                "prompt_ko": attempt.prompt_ko,
                "prompt_en": attempt.prompt_en,
                "seed": attempt.seed,
                "workflow_template_id": attempt.workflow_template_id,
                "execution_mode_id": attempt.execution_mode_id,
                "param_overrides": attempt.param_overrides,
                "workflow_snapshot": attempt.workflow_snapshot,
                "output_metadata": output_meta,
            }
        )

    shot_list_path = export_dir / "shot_list.json"
    snapshots_path = export_dir / "attempt_snapshots.json"

    shot_list_path.write_text(json.dumps(shot_list, indent=2, ensure_ascii=False))
    snapshots_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False))

    return {
        "export_dir": str(export_dir),
        "clip_count": clip_count,
        "shot_list": str(shot_list_path),
        "snapshots": str(snapshots_path),
    }
