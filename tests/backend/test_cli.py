"""Tests for CLI runtime settings."""

from __future__ import annotations

from pathlib import Path

from eumpa_studio.cli import get_settings


def test_cli_default_data_root_matches_api_default(monkeypatch):
    monkeypatch.delenv("EUMPA_DATA_ROOT", raising=False)

    settings = get_settings()

    assert settings.data_root == Path("data")
    assert settings.output_path == Path("data") / "outputs"
    assert settings.cache_path == Path("data") / "cache"


def test_cli_settings_read_dotenv_when_env_is_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("EUMPA_DATA_ROOT", raising=False)
    monkeypatch.delenv("EUMPA_COMFYUI_URL", raising=False)
    monkeypatch.delenv("EUMPA_CODEX_CLI_PATH", raising=False)
    monkeypatch.delenv("EUMPA_ALIGNMENT_COMMAND", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "EUMPA_DATA_ROOT=runtime-data",
                "EUMPA_COMFYUI_URL=http://comfy.example:8188",
                "EUMPA_CODEX_CLI_PATH=/opt/codex",
                "EUMPA_ALIGNMENT_COMMAND=/opt/eumpa-align",
            ]
        ),
        encoding="utf-8",
    )

    settings = get_settings()

    assert settings.data_root == Path("runtime-data")
    assert settings.output_path == Path("runtime-data") / "outputs"
    assert settings.cache_path == Path("runtime-data") / "cache"
    assert settings.comfyui_url == "http://comfy.example:8188"
    assert settings.codex_cli_path == "/opt/codex"
    assert settings.alignment_command == "/opt/eumpa-align"
