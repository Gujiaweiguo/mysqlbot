from __future__ import annotations

import importlib
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
        "_get_xpack_core",
        lambda: _FakeXPackCore(startup_calls),
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
