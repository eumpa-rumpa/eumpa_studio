"""Tests for database URL selection."""

from __future__ import annotations

from eumpa_studio.db.session import database_url_from_env


def test_database_url_prefers_eumpa_database_url(monkeypatch):
    monkeypatch.setenv("EUMPA_DATABASE_URL", "sqlite:///data/eumpa.db")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///legacy.db")

    assert database_url_from_env() == "sqlite:///data/eumpa.db"


def test_database_url_falls_back_to_legacy_database_url(monkeypatch):
    monkeypatch.delenv("EUMPA_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///legacy.db")

    assert database_url_from_env() == "sqlite:///legacy.db"


def test_database_url_reads_dotenv_when_env_is_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("EUMPA_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "EUMPA_DATABASE_URL=sqlite:///from-dotenv.db\n",
        encoding="utf-8",
    )

    assert database_url_from_env() == "sqlite:///from-dotenv.db"
