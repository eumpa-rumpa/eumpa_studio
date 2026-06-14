"""Workflow patching utilities for ComfyUI JSON workflows."""

from __future__ import annotations

import copy
import json
from typing import Any


class ValidationError(Exception):
    pass


def validate_inputs(mode_required: list[str], provided: dict[str, Any]) -> None:
    """Raise ValidationError listing missing required inputs."""
    missing = [k for k in mode_required if k not in provided]
    if missing:
        raise ValidationError(f"Missing required inputs: {missing}")


def patch_workflow(
    workflow: dict[str, Any],
    node_bindings: dict[str, dict[str, Any]],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Apply node_bindings to patch a ComfyUI workflow dict.

    node_bindings format: {input_key: {"node_id": "5", "field": "text"}}
    For each binding where inputs[input_key] exists, set:
        workflow[node_id]["inputs"][field] = inputs[input_key]
    Returns a deep copy of the patched workflow.
    """
    result = copy.deepcopy(workflow)
    for input_key, binding in node_bindings.items():
        if input_key in inputs:
            node_id = str(binding["node_id"])
            field = binding["field"]
            if node_id in result:
                result[node_id]["inputs"][field] = inputs[input_key]
    return result


def apply_mode(
    workflow_json: str,
    mode_required_inputs: list[str],
    mode_node_bindings: dict[str, dict[str, Any]],
    inputs: dict[str, Any],
) -> str:
    """Validate inputs, patch workflow, return patched JSON string."""
    validate_inputs(mode_required_inputs, inputs)
    workflow = json.loads(workflow_json)
    patched = patch_workflow(workflow, mode_node_bindings, inputs)
    return json.dumps(patched)
