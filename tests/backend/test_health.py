"""Tests for GET /api/health endpoint."""

import subprocess
from unittest.mock import MagicMock, patch

import httpx
import pytest


def test_health_returns_200(client):
    """Health endpoint always returns HTTP 200."""
    with (
        patch("eumpa_studio.server.routes.health._check_comfyui", return_value="ok"),
        patch("eumpa_studio.server.routes.health._check_codex_cli", return_value="ok"),
    ):
        response = client.get("/api/health")
    assert response.status_code == 200


def test_health_all_ok(client):
    """All services healthy — all fields should be 'ok'."""
    mock_result = MagicMock()
    mock_result.returncode = 0

    with (
        patch(
            "eumpa_studio.server.routes.health.httpx.Client"
        ) as mock_httpx_client_cls,
        patch(
            "eumpa_studio.server.routes.health.subprocess.run",
            return_value=mock_result,
        ),
    ):
        mock_httpx_instance = MagicMock()
        mock_httpx_instance.__enter__ = MagicMock(return_value=mock_httpx_instance)
        mock_httpx_instance.__exit__ = MagicMock(return_value=False)
        mock_response = MagicMock()
        mock_httpx_instance.get.return_value = mock_response
        mock_httpx_client_cls.return_value = mock_httpx_instance

        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "ok"
    assert data["database"] == "ok"
    assert data["comfyui"] == "ok"
    assert data["codex_cli"] == "ok"


def test_health_comfyui_unreachable(client):
    """ComfyUI unreachable — only comfyui field should be 'unreachable'."""
    mock_result = MagicMock()
    mock_result.returncode = 0

    with (
        patch(
            "eumpa_studio.server.routes.health.httpx.Client"
        ) as mock_httpx_client_cls,
        patch(
            "eumpa_studio.server.routes.health.subprocess.run",
            return_value=mock_result,
        ),
    ):
        mock_httpx_instance = MagicMock()
        mock_httpx_instance.__enter__ = MagicMock(return_value=mock_httpx_instance)
        mock_httpx_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_instance.get.side_effect = httpx.ConnectError("refused")
        mock_httpx_client_cls.return_value = mock_httpx_instance

        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["comfyui"] == "unreachable"
    assert data["backend"] == "ok"
    assert data["database"] == "ok"
    assert data["codex_cli"] == "ok"


def test_health_codex_not_found(client):
    """Codex CLI missing — only codex_cli field should be 'not_found'."""
    with (
        patch(
            "eumpa_studio.server.routes.health.httpx.Client"
        ) as mock_httpx_client_cls,
        patch(
            "eumpa_studio.server.routes.health.subprocess.run",
            side_effect=FileNotFoundError("codex not found"),
        ),
    ):
        mock_httpx_instance = MagicMock()
        mock_httpx_instance.__enter__ = MagicMock(return_value=mock_httpx_instance)
        mock_httpx_instance.__exit__ = MagicMock(return_value=False)
        mock_response = MagicMock()
        mock_httpx_instance.get.return_value = mock_response
        mock_httpx_client_cls.return_value = mock_httpx_instance

        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["codex_cli"] == "not_found"
    assert data["backend"] == "ok"
    assert data["database"] == "ok"
    assert data["comfyui"] == "ok"


def test_health_database_error(client):
    """DB unreachable — only database field should be 'error'."""
    mock_result = MagicMock()
    mock_result.returncode = 0

    with (
        patch(
            "eumpa_studio.server.routes.health.httpx.Client"
        ) as mock_httpx_client_cls,
        patch(
            "eumpa_studio.server.routes.health.subprocess.run",
            return_value=mock_result,
        ),
        patch(
            "eumpa_studio.server.routes.health._check_database",
            return_value="error",
        ),
    ):
        mock_httpx_instance = MagicMock()
        mock_httpx_instance.__enter__ = MagicMock(return_value=mock_httpx_instance)
        mock_httpx_instance.__exit__ = MagicMock(return_value=False)
        mock_response = MagicMock()
        mock_httpx_instance.get.return_value = mock_response
        mock_httpx_client_cls.return_value = mock_httpx_instance

        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "error"
    assert data["backend"] == "ok"
    assert data["comfyui"] == "ok"
    assert data["codex_cli"] == "ok"
