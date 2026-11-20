"""Dedicated SQL/object storage, bootstrapping and exact forecast reuse acceptance tests."""

import io
import json
from dataclasses import replace

import pandas as pd
import pytest
from test_forecast_training import frame as frame_fixture

from batteryflex.forecast_contracts import ForecastDatasetConfig, ForecastModelConfig
from batteryflex.forecast_persistence import SavedForecaster, activate_bundle
from batteryflex.portfolio import HOUSEHOLDS
from batteryflex.portfolio_storage import export_configuration
from batteryflex.storage.bootstrap import bootstrap, load_prepared
from batteryflex.storage.database import SQLiteDatabase, TursoDatabase, migrate, query
from batteryflex.storage.forecast_cache import ForecastCache, fingerprint
from batteryflex.storage.objects import Objects, sha256
from batteryflex.storage.repository import Repository, canonical


@pytest.fixture(scope="module")
def prepared_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("prepared")
    prepared = root / "data/lcl/prepared"
    prepared.mkdir(parents=True)
    frame = frame_fixture.__wrapped__()
    frame.to_parquet(prepared / "observations.parquet", index=False)
    for name in ("candidates.csv", "recommended.csv"):
        pd.DataFrame({"household_id": HOUSEHOLDS}).to_csv(prepared / name, index=False)
    pd.DataFrame({"scenario_id": []}).to_csv(prepared / "replay.csv", index=False)
    audit = {
        "parser_version": 1,
        "artifacts": {p.name: sha256(p.read_bytes()) for p in prepared.iterdir()},
    }
    (prepared / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
    return root, frame, audit


@pytest.fixture
def repo(tmp_path, prepared_root):
    repository = Repository(
        SQLiteDatabase(tmp_path / "app.sqlite", create=True), Objects(tmp_path / "objects")
    )
    bootstrap(repository, prepared_root[0])
    return repository


def test_empty_bootstrap_idempotency_and_database_only_load(repo, prepared_root):
    count = len(query(repo.db, "SELECT * FROM objects"))
    bootstrap(repo, prepared_root[0])
    migrate(repo.db)
    assert len(query(repo.db, "SELECT * FROM households")) == 5
    assert len(query(repo.db, "SELECT * FROM neso_events")) == 5
    assert len(query(repo.db, "SELECT * FROM replay_mappings")) == 5
    assert len(query(repo.db, "SELECT * FROM batteries")) == 5
    assert len(query(repo.db, "SELECT * FROM objects")) == count
    assert not query(repo.db, "SELECT * FROM forecast_models")
    stored, *_ = load_prepared(repo)
    pd.testing.assert_frame_equal(stored, prepared_root[1])


def test_run_reuse_changed_config_battery_and_saved_inference(
    repo, prepared_root, tmp_path, monkeypatch
):
    frame = prepared_root[1]
    source = prepared_root[2]["artifacts"]["observations.parquet"]
    configs = (ForecastModelConfig("Ridge Regression"), ForecastModelConfig("LightGBM"))
    dataset = ForecastDatasetConfig()
    cache = ForecastCache(repo, tmp_path)
    first = cache.run(frame, configs, dataset, source)
    assert len(cache.trained) == 3
    assert len(query(repo.db, "SELECT * FROM forecast_models")) == 3
    assert len(query(repo.db, "SELECT * FROM forecast_metrics")) == 36
    assert repo.setting("forecast_model") is None

    def forbidden(*args, **kwargs):
        raise AssertionError("fit called on exact cached request")

    monkeypatch.setattr("batteryflex.storage.forecast_cache.run_models", forbidden)
    second = cache.run(frame, configs, dataset, source)
    assert len(cache.reused) == 3 and not cache.trained
    pd.testing.assert_frame_equal(first.predictions, second.predictions)
    assert cache.lookup(configs, dataset, source) is not None
    changed = ForecastModelConfig("Ridge Regression", '{"alpha":2.0}')
    assert fingerprint(changed, dataset, source) != fingerprint(configs[0], dataset, source)
    assert cache.lookup((changed,), dataset, source) is None
    assert fingerprint(
        configs[0], replace(dataset, household_ids=HOUSEHOLDS[::-1]), source
    ) != fingerprint(configs[0], dataset, source)
    old = repo.setting("portfolio")
    portfolio = repo.portfolio()
    new = replace(
        portfolio,
        batteries=(replace(portfolio.batteries[0], capacity_kwh=12), *portfolio.batteries[1:]),
    )
    new_id = repo.save_portfolio(export_configuration(new))
    assert old != new_id and repo.save_portfolio(export_configuration(new)) == new_id
    assert len(query(repo.db, "SELECT * FROM portfolios")) == 2
    cache.run(frame, configs, dataset, source)  # battery changes have no load-model dependency
    record = next(r for r in cache.registry.read().records if r.config.method == "Ridge Regression")
    activate_bundle(cache.registry, record.reference)
    assert cache.registry.read().active == record.reference
    from datetime import UTC, datetime

    forecaster = SavedForecaster(cache.registry, frame, source)
    assert (
        len(
            forecaster.predict(
                household_ids=HOUSEHOLDS, forecast_origin=datetime(2013, 4, 2, tzinfo=UTC)
            )
        )
        == 240
    )
    with pytest.raises(ValueError, match="later than"):
        forecaster.predict(
            household_ids=HOUSEHOLDS, forecast_origin=datetime(2013, 3, 20, tzinfo=UTC)
        )


def test_concurrent_request_does_not_train(repo, prepared_root, tmp_path, monkeypatch):
    import time

    config = ForecastModelConfig()
    dataset = ForecastDatasetConfig()
    source = prepared_root[2]["artifacts"]["observations.parquet"]
    identity = fingerprint(config, dataset, source)
    repo.db.batch(
        [
            (
                "INSERT INTO model_leases VALUES(?,?,?)",
                (identity, "another-worker", int(time.time()) + 600),
            )
        ]
    )
    monkeypatch.setattr(
        "batteryflex.storage.forecast_cache.run_models", lambda *a: pytest.fail("concurrent fit")
    )
    with pytest.raises(ValueError, match="already being computed"):
        ForecastCache(repo, tmp_path).run(prepared_root[1], (config,), dataset, source)
    assert not query(repo.db, "SELECT * FROM forecast_models")


def test_partial_upload_does_not_publish_or_leave_lease(repo, prepared_root, tmp_path, monkeypatch):
    monkeypatch.setattr(
        repo.objects, "put", lambda *a: (_ for _ in ()).throw(ValueError("upload interrupted"))
    )
    with pytest.raises(ValueError, match="upload interrupted"):
        ForecastCache(repo, tmp_path).run(
            prepared_root[1],
            (ForecastModelConfig(),),
            ForecastDatasetConfig(),
            prepared_root[2]["artifacts"]["observations.parquet"],
        )
    assert not query(repo.db, "SELECT * FROM forecast_models")
    assert not query(repo.db, "SELECT * FROM model_leases")


def test_corrupt_prediction_object_is_not_a_cache_hit(repo, prepared_root, tmp_path, monkeypatch):
    config = ForecastModelConfig()
    source = prepared_root[2]["artifacts"]["observations.parquet"]
    cache = ForecastCache(repo, tmp_path)
    cache.run(prepared_root[1], (config,), ForecastDatasetConfig(), source)
    row = query(repo.db, "SELECT predictions_id FROM forecast_models")[0]
    path = repo.objects.cache / repo.reference(row["predictions_id"]).object_key
    path.write_bytes(b"corrupt")
    monkeypatch.setattr(
        "batteryflex.storage.forecast_cache.run_models",
        lambda *a: pytest.fail("bad cache retrained"),
    )
    with pytest.raises(ValueError, match="missing or corrupted"):
        cache.run(prepared_root[1], (config,), ForecastDatasetConfig(), source)


class FakeR2:
    def __init__(self):
        self.data = {}
        self.fail = False

    def put_object(self, **kwargs):
        assert kwargs["Bucket"] == "batteryflex-mvp" and kwargs["IfNoneMatch"] == "*"
        if self.fail:
            raise OSError("connection lost")
        self.data.setdefault(kwargs["Key"], kwargs["Body"])

    def get_object(self, **kwargs):
        assert kwargs["Bucket"] == "batteryflex-mvp"
        return {"Body": io.BytesIO(self.data[kwargs["Key"]])}


def test_r2_integrity_repair_and_failure(tmp_path):
    remote = FakeR2()
    store = Objects(tmp_path, remote)
    ref = store.put(b"verified", "test")
    (tmp_path / ref.object_key).write_bytes(b"bad cache")
    assert store.get(ref) == b"verified"
    (tmp_path / ref.object_key).unlink()
    remote.data[ref.object_key] = b"bad remote"
    with pytest.raises(ValueError, match="integrity"):
        store.get(ref)
    remote.fail = True
    with pytest.raises(ValueError, match="upload failed"):
        store.put(b"new", "test")
    with pytest.raises(ValueError, match="Invalid confined"):
        store.get(replace(ref, object_key="../../escape"))


def test_turso_dedicated_guard_and_atomic_parameterized_protocol(monkeypatch):
    with pytest.raises(ValueError, match="dedicated"):
        TursoDatabase("libsql://other-mvp-team.turso.io", "secret")
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(
                {
                    "results": [
                        {
                            "type": "ok",
                            "response": {
                                "result": {
                                    "step_errors": [None] * 4,
                                    "step_results": [
                                        {},
                                        {},
                                        {
                                            "cols": [{"name": "value"}],
                                            "rows": [[{"type": "integer", "value": "1"}]],
                                        },
                                        {},
                                    ],
                                }
                            },
                        }
                    ]
                }
            ).encode()

    def request(req, **kwargs):
        captured.append(json.loads(req.data))
        return Response()

    monkeypatch.setattr("batteryflex.storage.database.urlopen", request)
    db = TursoDatabase("libsql://batteryflex-mvp-team.turso.io", "secret")
    assert query(db, "SELECT ? AS value", (1,)) == [{"value": 1}]
    batch = captured[0]["requests"][0]["batch"]["steps"]
    assert batch[2]["stmt"]["args"] == [{"type": "integer", "value": "1"}]
    assert len(batch[-1]["condition"]["conds"]) == 3
    assert captured[0]["requests"][-1] == {"type": "close"}


def test_changed_household_selection_has_its_own_complete_bundle(repo, prepared_root, tmp_path):
    from batteryflex.forecast_persistence import load_bundle

    source = prepared_root[2]["artifacts"]["observations.parquet"]
    dataset = replace(ForecastDatasetConfig(), household_ids=HOUSEHOLDS[:2])
    cache = ForecastCache(repo, tmp_path)
    result = cache.run(prepared_root[1], (ForecastModelConfig(),), dataset, source)
    assert set(result.models["Seasonal Naive"]) == set(HOUSEHOLDS[:2])
    assert set(result.predictions.household) == {*HOUSEHOLDS[:2], "Portfolio"}
    record = cache.registry.read().records[0]
    assert set(load_bundle(cache.registry, record)) == set(HOUSEHOLDS[:2])
    assert (
        len(
            query(
                repo.db,
                "SELECT * FROM selection_members WHERE selection_id=?",
                (sha256(canonical(dataset.household_ids).encode()),),
            )
        )
        == 2
    )


def test_failed_sql_publication_rolls_back_models_and_metrics(
    repo, prepared_root, tmp_path, monkeypatch
):
    original = repo.db.batch

    def fail(statements):
        if any("INSERT INTO forecast_models" in sql for sql, _ in statements):
            # Exercise actual SQL rollback after several metadata inserts.
            statements = [*statements, ("INSERT INTO nonexistent_table VALUES(1)", ())]
        return original(statements)

    monkeypatch.setattr(repo.db, "batch", fail)
    with pytest.raises(ValueError, match="Local SQL transaction failed"):
        ForecastCache(repo, tmp_path).run(
            prepared_root[1],
            (ForecastModelConfig(),),
            ForecastDatasetConfig(),
            prepared_root[2]["artifacts"]["observations.parquet"],
        )
    assert not query(repo.db, "SELECT * FROM forecast_models")
    assert not query(repo.db, "SELECT * FROM forecast_metrics")
    assert not query(repo.db, "SELECT * FROM model_leases")


def test_source_changes_invalidate_only_forecast_fingerprints(prepared_root):
    source = prepared_root[2]["artifacts"]["observations.parquet"]
    config = ForecastModelConfig("Ridge Regression")
    dataset = ForecastDatasetConfig()
    assert fingerprint(config, dataset, source) != fingerprint(config, dataset, "c" * 64)
    assert fingerprint(config, dataset, source) == fingerprint(
        ForecastModelConfig("Ridge Regression", '{"alpha":1.0}'), dataset, source
    )


def test_no_startup_database_creation_and_secret_redaction(tmp_path, monkeypatch):
    from batteryflex.storage.settings import Settings, connect, runtime_repository

    monkeypatch.setenv("BATTERYFLEX_STORAGE_MODE", "local")
    monkeypatch.setenv("BATTERYFLEX_STORAGE_DIRECTORY", str(tmp_path / "fresh"))
    with pytest.raises(ValueError, match="not bootstrapped"):
        runtime_repository()
    assert not (tmp_path / "fresh").exists()
    assert "do-not-log" not in repr(
        Settings(token="do-not-log", secret="do-not-log", access="do-not-log")
    )
    with pytest.raises(ValueError, match="dedicated"):
        connect(
            Settings(
                url="libsql://old-mvp-team.turso.io",
                token="do-not-log",
                account="account",
                access="key",
                secret="secret",
            )
        )


def test_legacy_saved_bundle_migration_without_training(repo, prepared_root, tmp_path):
    from batteryflex.forecast_persistence import save_bundle
    from batteryflex.forecast_registry import LocalModelRegistry
    from batteryflex.forecast_training import run_models
    from batteryflex.storage.import_legacy import import_models

    root = tmp_path / "legacy"
    local = LocalModelRegistry(root / "outputs/forecast_models")
    source = prepared_root[2]["artifacts"]["observations.parquet"]
    result = run_models(prepared_root[1], (ForecastModelConfig(),), ForecastDatasetConfig(), source)
    record = save_bundle(local, result, "Seasonal Naive", "legacy-v1")
    activate_bundle(local, record.reference)
    selection = repo.setting("households")
    assert import_models(repo, root, source, selection) == 1
    assert import_models(repo, root, source, selection) == 0
    row = query(repo.db, "SELECT * FROM forecast_models")[0]
    assert row["predictions_id"] is None  # An imported estimator alone is not a ready result cache.
    assert repo.setting("forecast_model")["model_version"] == "legacy-v1"
    assert (
        ForecastCache(repo, tmp_path).lookup(
            (ForecastModelConfig(),), ForecastDatasetConfig(), source
        )
        is None
    )


def test_changed_parameters_train_only_missing_and_recommend_exact_version(
    repo, prepared_root, tmp_path, monkeypatch
):
    from batteryflex.ui.forecast_results import recommended_label

    source = prepared_root[2]["artifacts"]["observations.parquet"]
    cache = ForecastCache(repo, tmp_path)
    first = ForecastModelConfig("Ridge Regression", '{"alpha":1.0}')
    second = ForecastModelConfig("Ridge Regression", '{"alpha":2.0}')
    dataset = ForecastDatasetConfig()
    cache.run(prepared_root[1], (first,), dataset, source)
    result = cache.run(prepared_root[1], (second,), dataset, source)
    assert cache.trained == ["Ridge Regression"] and cache.reused == ["Seasonal Naive"]
    assert len(query(repo.db, "SELECT * FROM forecast_models")) == 3
    validation = result.metrics.partition.eq("validation") & result.metrics.household.eq(
        "Portfolio"
    )
    result.metrics.loc[validation, "rmse_kw"] = 10.0
    result.metrics.loc[validation & result.metrics.method.eq("Ridge Regression"), "rmse_kw"] = 0.1
    assert recommended_label(
        cache.registry.read(), result
    ) == "Ridge Regression / auto-" + fingerprint(second, dataset, source)


def test_provisioning_never_uses_previous_database_token(monkeypatch):
    from batteryflex.storage.provision import prepare_database

    monkeypatch.setattr(
        "batteryflex.storage.provision.platform_request",
        lambda *a, **k: pytest.fail("old token used"),
    )
    with pytest.raises(ValueError, match="platform token"):
        prepare_database(
            {
                "TURSO_DATABASE_URL": "libsql://old-team.turso.io",
                "TURSO_AUTH_TOKEN": "old-db-secret",
            }
        )


def test_dedicated_provisioning_checks_before_create_and_mints_only_when_needed(monkeypatch):
    from batteryflex.storage.provision import prepare_database

    calls = []

    def platform(token, path, **kwargs):
        calls.append((path, kwargs.get("method", "GET")))
        if len(calls) == 1:
            raise FileNotFoundError()
        if path.endswith("/auth/tokens?authorization=full-access"):
            return {"jwt": "dedicated-sql-secret"}
        return {
            "database": {"Name": "batteryflex-mvp", "Hostname": "batteryflex-mvp-team.turso.io"}
        }

    monkeypatch.setattr("batteryflex.storage.provision.platform_request", platform)
    monkeypatch.setattr("batteryflex.storage.provision.query", lambda *args: [{"connected": 1}])
    values = {"BATTERYFLEX_TURSO_PLATFORM_TOKEN": "platform-secret", "TURSO_ORGANIZATION": "team"}
    url, token = prepare_database(values)
    assert url == "libsql://batteryflex-mvp-team.turso.io" and token == "dedicated-sql-secret"
    assert [method for _, method in calls] == ["GET", "POST", "GET", "POST"]
    calls.clear()
    prepare_database({"BATTERYFLEX_TURSO_DATABASE_URL": url, "BATTERYFLEX_TURSO_AUTH_TOKEN": token})
    assert not calls


def test_provisioning_preserves_env_and_backs_up_without_logging(tmp_path, monkeypatch, capsys):
    from batteryflex.storage.provision import provision

    path = tmp_path / ".env"
    original = (
        b"TURSO_AUTH_TOKEN=old-db-secret\nOPENAI_API_KEY=existing-ai-secret\n"
        b"R2_ACCOUNT_ID=test\nR2_ACCESS_KEY_ID=existing-r2-key\n"
        b"R2_SECRET_ACCESS_KEY=existing-r2-secret\n"
    )
    path.write_bytes(original)
    monkeypatch.setattr(
        "batteryflex.storage.provision.prepare_database",
        lambda values: ("libsql://batteryflex-mvp-team.turso.io", "new-dedicated-secret"),
    )

    class Bucket:
        def head_bucket(self, **kwargs):
            assert kwargs == {"Bucket": "batteryflex-mvp"}

    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: Bucket())
    provision(path)
    assert (tmp_path / ".env.task05c.backup").read_bytes() == original
    content = path.read_text(encoding="utf-8")
    assert (
        "TURSO_AUTH_TOKEN=old-db-secret" in content
        and "OPENAI_API_KEY=existing-ai-secret" in content
    )
    assert "BATTERYFLEX_TURSO_AUTH_TOKEN='new-dedicated-secret'" in content
    assert capsys.readouterr().out == ""


def test_runtime_schema_checksum_verification(repo):
    from batteryflex.storage.database import verify_schema

    verify_schema(repo.db)
    repo.db.batch([("UPDATE schema_migrations SET sha256='invalid'", ())])
    with pytest.raises(ValueError, match="checksum"):
        verify_schema(repo.db)
