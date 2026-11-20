"""Routine tests never connect to developer cloud resources or use persistent app state."""

import pytest


@pytest.fixture(autouse=True)
def isolated_storage_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("BATTERYFLEX_STORAGE_MODE", "cloud")
    monkeypatch.setenv("BATTERYFLEX_TURSO_DATABASE_URL", "")
    monkeypatch.setenv("BATTERYFLEX_STORAGE_DIRECTORY", str(tmp_path / "not-bootstrapped"))
