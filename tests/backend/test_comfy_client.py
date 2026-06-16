"""Tests for ComfyUI render submission."""

from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.db.base import Base
from eumpa_studio.domain.models import Attempt, ExecutionMode, Project, Shot, WorkflowTemplate
from eumpa_studio.domain.statuses import AttemptStatus
from eumpa_studio.execution import comfy_client


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def json(self) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        return None


class FakeComfyHttpClient:
    uploads: list[str] = []
    prompts: list[dict] = []

    def __init__(self, timeout: int):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, **kwargs):
        if url.endswith("/upload/image"):
            upload = kwargs["files"]["image"]
            filename = upload[0]
            self.uploads.append(filename)
            return FakeResponse({"name": filename})

        if url.endswith("/prompt"):
            self.prompts.append(kwargs["json"])
            return FakeResponse({"prompt_id": "prompt-1"})

        raise AssertionError(f"unexpected POST {url}")

    def get(self, url: str):
        if url.endswith("/history/prompt-1"):
            return FakeResponse(
                {
                    "prompt-1": {
                        "outputs": {
                            "7": {
                                "videos": [
                                    {
                                        "filename": "line_01.mp4",
                                        "subfolder": "eumpa_studio",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                }
            )

        raise AssertionError(f"unexpected GET {url}")


def test_extract_video_output_skips_temp_preview_images():
    output = comfy_client._extract_video_output(
        {
            "outputs": {
                "35": {
                    "images": [
                        {
                            "filename": "ComfyUI_temp_00001_.png",
                            "subfolder": "",
                            "type": "temp",
                        }
                    ]
                },
                "7": {
                    "videos": [
                        {
                            "filename": "line_01.mp4",
                            "subfolder": "eumpa_studio",
                            "type": "output",
                        }
                    ]
                },
            }
        },
        "http://comfy.local:8188",
    )

    assert output is not None
    assert output.filename == "line_01.mp4"
    assert output.type == "output"


def test_raise_for_history_error_includes_comfy_node_detail():
    history = {
        "status": {
            "status_str": "error",
            "completed": False,
            "messages": [
                [
                    "execution_error",
                    {
                        "node_id": "14",
                        "node_type": "LoadImage",
                        "exception_message": "cannot identify image file",
                    },
                ]
            ],
        }
    }

    try:
        comfy_client._raise_for_history_error(history, "prompt-1")
    except RuntimeError as exc:
        assert "prompt-1" in str(exc)
        assert "node 14 (LoadImage)" in str(exc)
        assert "cannot identify image file" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_submit_render_uploads_local_inputs_and_patches_skill_nodes(monkeypatch, tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    data_root = tmp_path / "data"
    audio_path = data_root / "projects" / "project-1" / "inputs" / "line.wav"
    image_path = data_root / "projects" / "project-1" / "assets" / "speaker.png"
    audio_path.parent.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"RIFF")
    image_path.write_bytes(b"PNG")

    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "1": {"class_type": "Sampler", "inputs": {"noise_seed": 1}},
                "7": {"class_type": "VHS_VideoCombine", "inputs": {"filename_prefix": ""}},
                "11": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
                "14": {"class_type": "LoadImage", "inputs": {"image": ""}},
                "40": {
                    "class_type": "VHS_LoadAudioUpload",
                    "inputs": {"audio": "", "start_time": 0, "duration": 0},
                },
            }
        ),
        encoding="utf-8",
    )

    FakeComfyHttpClient.uploads = []
    FakeComfyHttpClient.prompts = []
    monkeypatch.setattr(comfy_client.httpx, "Client", FakeComfyHttpClient)

    with Session() as session:
        project = Project(
            name="Render Project",
            audio_storage_backend="local",
            audio_relative_path="projects/project-1/inputs/line.wav",
        )
        session.add(project)
        session.commit()
        shot = Shot(
            project_id=project.id,
            order=0,
            start_time=1.25,
            end_time=4.75,
            duration=3.5,
        )
        template = WorkflowTemplate(name="Skill LTX", json_path=str(workflow_path))
        session.add_all([shot, template])
        session.commit()
        mode = ExecutionMode(
            workflow_template_id=template.id,
            name="Skill LTX image audio prompt",
            required_inputs=json.dumps(
                ["image", "audio", "start_time", "duration", "prompt_en"]
            ),
            node_bindings=json.dumps(
                {
                    "image": {"node_id": "14", "field": "image"},
                    "audio": {"node_id": "40", "field": "audio"},
                    "start_time": {"node_id": "40", "field": "start_time"},
                    "duration": {"node_id": "40", "field": "duration"},
                    "prompt_en": {"node_id": "11", "field": "text"},
                    "seed": {"node_id": "1", "field": "noise_seed"},
                    "output_prefix": {"node_id": "7", "field": "filename_prefix"},
                }
            ),
        )
        session.add(mode)
        session.commit()
        attempt = Attempt(
            shot_id=shot.id,
            image_storage_backend="local",
            image_relative_path="projects/project-1/assets/speaker.png",
            prompt_en="He says hello.",
            seed=123,
            workflow_template_id=template.id,
            execution_mode_id=mode.id,
        )
        session.add(attempt)
        session.commit()
        attempt_id = attempt.id

        output = comfy_client.submit_render(
            session,
            attempt_id,
            "http://comfy.local:8188",
            data_root,
            timeout=3,
        )
        session.refresh(attempt)

    assert output.filename == "line_01.mp4"
    assert FakeComfyHttpClient.uploads == ["speaker.png", "line.wav"]
    submitted = FakeComfyHttpClient.prompts[0]["prompt"]
    assert submitted["14"]["inputs"]["image"] == "speaker.png"
    assert submitted["40"]["inputs"]["audio"] == "line.wav"
    assert submitted["40"]["inputs"]["start_time"] == 1.25
    assert submitted["40"]["inputs"]["duration"] == 3.5
    assert submitted["11"]["inputs"]["text"] == "He says hello."
    assert submitted["1"]["inputs"]["noise_seed"] == 123
    assert submitted["7"]["inputs"]["filename_prefix"] == f"eumpa_studio/{attempt_id}"
    assert attempt.status == AttemptStatus.NEEDS_REVIEW.value
    assert json.loads(attempt.output_metadata)["filename"] == "line_01.mp4"
