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
