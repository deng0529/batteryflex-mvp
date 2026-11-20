"""The public demonstration can retrieve saved data and cannot execute or publish work."""

import pytest

from batteryflex.dispatch_event import event_start_batteries, standard_scenario
from batteryflex.portfolio import default_portfolio
from batteryflex.storage import dispatch_runs, settings
from batteryflex.storage.database import TursoDatabase
from batteryflex.storage.event_forecasts import EventForecasts
from batteryflex.storage.objects import Objects
from batteryflex.storage.repository import Repository


def test_deployment_secrets_default_cloud_to_demo(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    monkeypatch.delenv("BATTERYFLEX_STORAGE_MODE", raising=False)
    monkeypatch.delenv("BATTERYFLEX_TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("BATTERYFLEX_ACCESS_MODE", raising=False)
    monkeypatch.setattr("streamlit.secrets", {"batteryflex": {"BATTERYFLEX_STORAGE_MODE": "cloud"}})
    config = settings.Settings.load()
    assert not config.writable
    with pytest.raises(ValueError, match="credentials are missing"):
        settings.runtime_repository()


def test_demo_stops_training_new_dispatch_and_storage_writes(tmp_path, monkeypatch):
    repo = Repository(None, Objects(tmp_path, read_only=True), writable=False)
    with pytest.raises(ValueError, match="owner instance"):
        repo.save_portfolio("")
    with pytest.raises(ValueError, match="owner instance"):
        EventForecasts(repo).run({}, None, ())
    with pytest.raises(ValueError, match="only permits object reads"):
        repo.objects.put(b"ignored", "test")
    db = TursoDatabase("libsql://batteryflex-mvp-test.turso.io", "placeholder", read_only=True)
    with pytest.raises(ValueError, match="only permits storage reads"):
        db.batch([("DELETE FROM portfolios", ())])

    s = standard_scenario(event_start_batteries(default_portfolio().batteries), (0,))
    monkeypatch.setattr(dispatch_runs, "_lookup", lambda *args: (None, False))
    with pytest.raises(ValueError, match="owner instance"):
        dispatch_runs.saved_or_run(repo, s, "RBC", {}, None, None)

    saved = {"fingerprint": "saved"}
    monkeypatch.setattr(dispatch_runs, "_lookup", lambda *args: (saved, False))
    assert dispatch_runs.saved_or_run(repo, s, "RBC", {}, None, None) == (saved, True)


def test_demo_ignores_disconnected_local_sqlite(monkeypatch, tmp_path):
    (tmp_path / "batteryflex.sqlite").touch()
    monkeypatch.setattr(settings.Settings, "load", lambda: settings.Settings(directory=tmp_path))
    monkeypatch.setattr(settings, "connect", lambda *a, **k: pytest.fail("unexpected connection"))
    assert settings.runtime_repository()[0] is None


def test_demo_discovery_skips_schema_one_full_day_indexes(monkeypatch, tmp_path):
    from batteryflex.storage import dispatch_runs

    index = {"value_json": '{"inputs":{},"method":"RBC","object_id":"legacy"}'}
    monkeypatch.setattr(dispatch_runs, "query", lambda *args: [index])
    repo = Repository(None, Objects(tmp_path), writable=False)
    assert dispatch_runs.discover_runs(repo, standard_only=True) == ([], 0)
