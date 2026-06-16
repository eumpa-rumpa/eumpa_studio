"""ComfyUI render submission client."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from eumpa_studio.domain.models import Attempt, ExecutionMode, WorkflowTemplate
from eumpa_studio.domain.statuses import AttemptStatus
from eumpa_studio.execution.workflow_patch import apply_mode


@dataclass
class RenderOutput:
    filename: str
    subfolder: str
    type: str
    server_id: str


def submit_render(
    session: Session,
    attempt_id: str,
    comfyui_url: str,
    data_root: Path = Path("data"),
    timeout: int = 300,
) -> RenderOutput:
    """Submit an attempt to ComfyUI, persist prompt and output metadata."""
    attempt = session.get(Attempt, attempt_id)
    try:
        if attempt is None:
            raise ValueError(f"Attempt {attempt_id!r} not found")

        mode, template = _load_render_config(session, attempt)
        workflow_json = _load_workflow_json(template)
        base_url = comfyui_url.rstrip("/")

        with httpx.Client(timeout=timeout) as client:
            inputs = _build_inputs(attempt, data_root, client, base_url)

            patched_workflow_json = apply_mode(
                workflow_json,
                _json_list(mode.required_inputs, "required_inputs"),
                _json_dict(mode.node_bindings, "node_bindings"),
                inputs,
            )
            patched_workflow = json.loads(patched_workflow_json)
            attempt.workflow_snapshot = patched_workflow_json

            prompt_response = client.post(
                f"{base_url}/prompt",
                json={"prompt": patched_workflow, "client_id": attempt_id},
            )
            prompt_response.raise_for_status()
            prompt_id = prompt_response.json().get("prompt_id")
            if not prompt_id:
                raise RuntimeError("ComfyUI prompt response did not include prompt_id")

            attempt.comfyui_prompt_id = prompt_id
            session.commit()

            output = _poll_for_output(client, base_url, prompt_id, comfyui_url, timeout)

        attempt.output_metadata = json.dumps(asdict(output))
        attempt.status = AttemptStatus.NEEDS_REVIEW.value
        session.commit()
        return output
    except Exception:
        if attempt is not None:
            attempt.status = AttemptStatus.FAILED.value
            session.commit()
        raise


def run_render_job(
    session: Session,
    attempt_id: str,
    comfyui_url: str,
    data_root: Path = Path("data"),
) -> None:
    """Top-level job runner for render jobs."""
    attempt = session.get(Attempt, attempt_id)
    if attempt is None:
        raise ValueError(f"Attempt {attempt_id!r} not found")
    try:
        submit_render(session, attempt_id, comfyui_url, data_root)
    except Exception:
        attempt.status = AttemptStatus.FAILED.value
        session.commit()
        raise


def _load_render_config(
    session: Session,
    attempt: Attempt,
) -> tuple[ExecutionMode, WorkflowTemplate]:
    if attempt.execution_mode_id is None:
        raise ValueError(f"Attempt {attempt.id!r} has no execution_mode_id")
    if attempt.workflow_template_id is None:
        raise ValueError(f"Attempt {attempt.id!r} has no workflow_template_id")

    mode = session.get(ExecutionMode, attempt.execution_mode_id)
    if mode is None:
        raise ValueError(f"ExecutionMode {attempt.execution_mode_id!r} not found")

    template = session.get(WorkflowTemplate, attempt.workflow_template_id)
    if template is None:
        raise ValueError(f"WorkflowTemplate {attempt.workflow_template_id!r} not found")

    return mode, template


def _load_workflow_json(template: WorkflowTemplate) -> str:
    if not os.path.exists(template.json_path):
        raise FileNotFoundError(f"Workflow template file not found: {template.json_path}")

    with open(template.json_path, encoding="utf-8") as workflow_file:
        workflow_json = workflow_file.read()

    try:
        workflow = json.loads(workflow_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Workflow template JSON is invalid: {template.json_path}") from exc

    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("Workflow template JSON must be a non-empty object")

    return workflow_json


def _build_inputs(
    attempt: Attempt,
    data_root: Path,
    client: httpx.Client,
    base_url: str,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {}

    if attempt.image_relative_path is not None:
        image_path = _resolve_local_path(data_root, attempt.image_relative_path, "image")
        inputs["image"] = _upload_input_file(client, base_url, image_path)
    if attempt.end_image_relative_path is not None:
        end_image_path = _resolve_local_path(
            data_root, attempt.end_image_relative_path, "end image"
        )
        inputs["end_image"] = _upload_input_file(client, base_url, end_image_path)
    if attempt.input_video_relative_path is not None:
        inputs["input_video"] = attempt.input_video_relative_path
    if attempt.shot.project.audio_relative_path is not None:
        audio_path = _resolve_local_path(
            data_root, attempt.shot.project.audio_relative_path, "audio"
        )
        inputs["audio"] = _upload_input_file(client, base_url, audio_path)
    if attempt.prompt_ko is not None:
        inputs["prompt_ko"] = attempt.prompt_ko
    if attempt.prompt_en is not None:
        inputs["prompt_en"] = attempt.prompt_en
    inputs["start_time"] = round(float(attempt.shot.start_time), 3)
    inputs["duration"] = round(float(attempt.shot.duration), 3)
    inputs["output_prefix"] = f"eumpa_studio/{attempt.id}"
    if attempt.seed is not None:
        inputs["seed"] = attempt.seed

    if attempt.param_overrides:
        overrides = json.loads(attempt.param_overrides)
        if not isinstance(overrides, dict):
            raise ValueError("Attempt param_overrides must be a JSON object")
        inputs.update(overrides)

    return inputs


def _resolve_local_path(data_root: Path, relative_path: str, label: str) -> Path:
    local_path = data_root / relative_path
    if not local_path.is_file():
        raise FileNotFoundError(f"Attempt {label} file not found: {local_path}")
    return local_path


def _upload_input_file(client: httpx.Client, base_url: str, local_path: Path) -> str:
    remote_name = local_path.name
    with local_path.open("rb") as file_obj:
        response = client.post(
            f"{base_url}/upload/image",
            files={"image": (remote_name, file_obj, "application/octet-stream")},
            data={"type": "input", "overwrite": "true"},
        )
    response.raise_for_status()
    return str(response.json().get("name") or remote_name)


def _poll_for_output(
    client: httpx.Client,
    base_url: str,
    prompt_id: str,
    server_id: str,
    timeout: int,
) -> RenderOutput:
    deadline = time.monotonic() + timeout

    while True:
        history_response = client.get(f"{base_url}/history/{prompt_id}")
        history_response.raise_for_status()
        prompt_history = _extract_prompt_history(history_response.json(), prompt_id)
        _raise_for_history_error(prompt_history, prompt_id)
        output = _extract_video_output(prompt_history, server_id)
        if output is not None:
            return output

        if _history_completed_without_video(prompt_history):
            raise RuntimeError(f"ComfyUI prompt {prompt_id!r} completed without a video output")

        if time.monotonic() >= deadline:
            raise RuntimeError(f"Timed out waiting for ComfyUI output for prompt {prompt_id!r}")

        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(2, remaining))


def _extract_prompt_history(
    history: dict[str, Any],
    prompt_id: str,
) -> dict[str, Any]:
    prompt_history = history.get(prompt_id, history)
    if not isinstance(prompt_history, dict):
        return {}
    return prompt_history


def _raise_for_history_error(prompt_history: dict[str, Any], prompt_id: str) -> None:
    status = prompt_history.get("status")
    if not isinstance(status, dict) or status.get("status_str") != "error":
        return

    for message in status.get("messages", []):
        if not isinstance(message, list) or len(message) < 2:
            continue
        if message[0] != "execution_error" or not isinstance(message[1], dict):
            continue
        node_id = message[1].get("node_id", "unknown")
        node_type = message[1].get("node_type", "unknown")
        exception_message = str(message[1].get("exception_message", "")).strip()
        detail = f" at node {node_id} ({node_type})"
        if exception_message:
            detail = f"{detail}: {exception_message}"
        raise RuntimeError(f"ComfyUI prompt {prompt_id!r} failed{detail}")

    raise RuntimeError(f"ComfyUI prompt {prompt_id!r} failed")


def _history_completed_without_video(prompt_history: dict[str, Any]) -> bool:
    status = prompt_history.get("status")
    return isinstance(status, dict) and status.get("completed") is True


def _extract_video_output(
    prompt_history: dict[str, Any],
    server_id: str,
) -> RenderOutput | None:
    if not prompt_history:
        return None

    outputs = prompt_history.get("outputs")
    if not isinstance(outputs, dict):
        return None

    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        for output_items in node_output.values():
            if not isinstance(output_items, list):
                continue
            for item in output_items:
                if not isinstance(item, dict) or "filename" not in item:
                    continue
                filename = str(item["filename"])
                output_type = str(item.get("type", ""))
                if output_type != "output" and not filename.lower().endswith(".mp4"):
                    continue
                return RenderOutput(
                    filename=filename,
                    subfolder=str(item.get("subfolder", "")),
                    type=output_type,
                    server_id=server_id,
                )

    return None


def _json_list(raw_json: str, field_name: str) -> list[str]:
    value = json.loads(raw_json)
    if not isinstance(value, list):
        raise ValueError(f"ExecutionMode {field_name} must be a JSON list")
    return [str(item) for item in value]


def _json_dict(raw_json: str, field_name: str) -> dict[str, dict[str, Any]]:
    value = json.loads(raw_json)
    if not isinstance(value, dict):
        raise ValueError(f"ExecutionMode {field_name} must be a JSON object")
    return value
