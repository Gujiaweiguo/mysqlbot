from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeXPackCore:
    _calls: list[str]

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def clean_xpack_cache(self) -> None:
        self._calls.append("clean_xpack_cache")

    async def monitor_app(self, _app: object) -> None:
        self._calls.append("monitor_app")


async def _record_clean_xpack_cache(startup_calls: list[str]) -> None:
    startup_calls.append("clean_xpack_cache")


async def _record_monitor_app(startup_calls: list[str], _app: object) -> None:
    startup_calls.append("monitor_app")


def test_main_import_initializes_xpack_app_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_MCP_SETUP", "true")

    import main as main_module
    import common.xpack_compat.startup as startup_module

    init_calls: list[object] = []

    def fake_init_fastapi_app(app: object) -> None:
        init_calls.append(app)

    monkeypatch.setattr(startup_module, "init_fastapi_app", fake_init_fastapi_app)

    main_module = importlib.reload(main_module)

    assert init_calls == [main_module.app]


def test_startup_lifespan_runs_expected_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_STARTUP_TASKS", "false")
    monkeypatch.setenv("SKIP_MCP_SETUP", "true")

    import main as main_module

    main_module = importlib.reload(main_module)
    fastapi_app = cast(FastAPI, main_module.app)
    startup_calls: list[str] = []

    def fake_run_migrations() -> None:
        startup_calls.append("run_migrations")

    def fake_init_sqlbot_cache() -> None:
        startup_calls.append("init_sqlbot_cache")

    def fake_init_dynamic_cors(app: object) -> None:
        assert app is fastapi_app
        startup_calls.append("init_dynamic_cors")

    def fake_init_terminology_embedding_data() -> None:
        startup_calls.append("init_terminology_embedding_data")

    def fake_init_data_training_embedding_data() -> None:
        startup_calls.append("init_data_training_embedding_data")

    def fake_init_default_internal_datasource() -> None:
        startup_calls.append("init_default_internal_datasource")

    def fake_init_table_and_ds_embedding() -> None:
        startup_calls.append("init_table_and_ds_embedding")

    async def fake_async_model_info() -> None:
        startup_calls.append("async_model_info")

    monkeypatch.setattr(main_module.settings, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(
        main_module.settings, "EMBEDDING_STARTUP_BACKFILL_POLICY", "eager"
    )
    monkeypatch.setattr(main_module, "embedding_runtime_enabled", lambda: True)
    monkeypatch.setattr(
        main_module,
        "get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider_type=main_module.EmbeddingProviderType.OPENAI_COMPATIBLE,
            startup_backfill_policy="eager",
        ),
    )

    monkeypatch.setattr(main_module, "run_migrations", fake_run_migrations)
    monkeypatch.setattr(main_module, "init_sqlbot_cache", fake_init_sqlbot_cache)
    monkeypatch.setattr(main_module, "init_dynamic_cors", fake_init_dynamic_cors)
    monkeypatch.setattr(
        main_module,
        "init_terminology_embedding_data",
        fake_init_terminology_embedding_data,
    )
    monkeypatch.setattr(
        main_module,
        "init_data_training_embedding_data",
        fake_init_data_training_embedding_data,
    )
    monkeypatch.setattr(
        main_module,
        "init_default_internal_datasource",
        fake_init_default_internal_datasource,
    )
    monkeypatch.setattr(
        main_module,
        "init_table_and_ds_embedding",
        fake_init_table_and_ds_embedding,
    )
    monkeypatch.setattr(main_module, "async_model_info", fake_async_model_info)
    monkeypatch.setattr(
        main_module,
        "clean_xpack_cache",
        lambda: _record_clean_xpack_cache(startup_calls),
    )
    monkeypatch.setattr(
        main_module,
        "monitor_app",
        lambda app: _record_monitor_app(startup_calls, app),
    )

    with TestClient(fastapi_app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert startup_calls == [
        "run_migrations",
        "init_sqlbot_cache",
        "init_dynamic_cors",
        "init_terminology_embedding_data",
        "init_data_training_embedding_data",
        "init_default_internal_datasource",
        "init_table_and_ds_embedding",
        "clean_xpack_cache",
        "async_model_info",
        "monitor_app",
    ]


def test_startup_lifespan_skips_embedding_backfill_for_remote_deferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_STARTUP_TASKS", "false")
    monkeypatch.setenv("SKIP_MCP_SETUP", "true")

    import main as main_module

    main_module = importlib.reload(main_module)
    fastapi_app = cast(FastAPI, main_module.app)
    startup_calls: list[str] = []

    def fake_run_migrations() -> None:
        startup_calls.append("run_migrations")

    def fake_init_sqlbot_cache() -> None:
        startup_calls.append("init_sqlbot_cache")

    def fake_init_dynamic_cors(app: object) -> None:
        assert app is fastapi_app
        startup_calls.append("init_dynamic_cors")

    def fake_init_terminology_embedding_data() -> None:
        startup_calls.append("init_terminology_embedding_data")

    def fake_init_data_training_embedding_data() -> None:
        startup_calls.append("init_data_training_embedding_data")

    def fake_init_default_internal_datasource() -> None:
        startup_calls.append("init_default_internal_datasource")

    def fake_init_table_and_ds_embedding() -> None:
        startup_calls.append("init_table_and_ds_embedding")

    async def fake_async_model_info() -> None:
        startup_calls.append("async_model_info")

    monkeypatch.setattr(main_module.settings, "EMBEDDING_PROVIDER", "remote")
    monkeypatch.setattr(
        main_module.settings, "EMBEDDING_STARTUP_BACKFILL_POLICY", "deferred"
    )
    monkeypatch.setattr(main_module, "embedding_runtime_enabled", lambda: True)
    monkeypatch.setattr(
        main_module,
        "get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider_type=main_module.EmbeddingProviderType.OPENAI_COMPATIBLE,
            startup_backfill_policy="deferred",
        ),
    )
    monkeypatch.setattr(main_module, "run_migrations", fake_run_migrations)
    monkeypatch.setattr(main_module, "init_sqlbot_cache", fake_init_sqlbot_cache)
    monkeypatch.setattr(main_module, "init_dynamic_cors", fake_init_dynamic_cors)
    monkeypatch.setattr(
        main_module,
        "init_terminology_embedding_data",
        fake_init_terminology_embedding_data,
    )
    monkeypatch.setattr(
        main_module,
        "init_data_training_embedding_data",
        fake_init_data_training_embedding_data,
    )
    monkeypatch.setattr(
        main_module,
        "init_default_internal_datasource",
        fake_init_default_internal_datasource,
    )
    monkeypatch.setattr(
        main_module,
        "init_table_and_ds_embedding",
        fake_init_table_and_ds_embedding,
    )
    monkeypatch.setattr(main_module, "async_model_info", fake_async_model_info)
    monkeypatch.setattr(
        main_module,
        "clean_xpack_cache",
        lambda: _record_clean_xpack_cache(startup_calls),
    )
    monkeypatch.setattr(
        main_module,
        "monitor_app",
        lambda app: _record_monitor_app(startup_calls, app),
    )

    with TestClient(fastapi_app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert startup_calls == [
        "run_migrations",
        "init_sqlbot_cache",
        "init_dynamic_cors",
        "init_default_internal_datasource",
        "clean_xpack_cache",
        "async_model_info",
        "monitor_app",
    ]


def test_startup_lifespan_skips_all_side_effects_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_STARTUP_TASKS", "true")
    monkeypatch.setenv("SKIP_MCP_SETUP", "true")

    import main as main_module

    main_module = importlib.reload(main_module)
    fastapi_app = cast(FastAPI, main_module.app)

    def fail_run_migrations() -> None:
        raise AssertionError("run_migrations should not be called")

    async def fail_async_model_info() -> None:
        raise AssertionError("async_model_info should not be called")

    async def fail_clean_xpack_cache() -> None:
        raise AssertionError("clean_xpack_cache should not be called")

    async def fail_monitor_app(_app: object) -> None:
        raise AssertionError("monitor_app should not be called")

    monkeypatch.setattr(main_module, "run_migrations", fail_run_migrations)
    monkeypatch.setattr(main_module, "async_model_info", fail_async_model_info)
    monkeypatch.setattr(main_module, "clean_xpack_cache", fail_clean_xpack_cache)
    monkeypatch.setattr(main_module, "monitor_app", fail_monitor_app)

    with TestClient(fastapi_app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
