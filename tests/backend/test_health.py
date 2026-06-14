"""Tests for GET /api/health endpoint."""

from fastapi.testclient import TestClient

from eumpa_studio.server.app import app


def test_health_returns_200():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_ok_json():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.json() == {"status": "ok"}
