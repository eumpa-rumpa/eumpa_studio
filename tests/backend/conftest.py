"""Shared pytest fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient

from eumpa_studio.server.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
