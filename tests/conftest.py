"""Shared fixtures for all test layers."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from epc.api import router
from epc.db import EPCRepository


@pytest.fixture
def repo(tmp_path):
    """Isolated repository backed by a temp SQLite file."""
    return EPCRepository(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def client(tmp_path):
    """TestClient with its own isolated repo (no shared singleton)."""
    db_path = str(tmp_path / "api_test.db")
    test_repo = EPCRepository(db_path=db_path)

    app = FastAPI()
    app.include_router(router)

    from epc import api as api_mod
    api_mod._repo_singleton = test_repo

    yield TestClient(app)

    api_mod._repo_singleton = None
