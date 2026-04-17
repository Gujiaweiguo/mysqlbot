from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.system.schemas.embedding_schema import EmbeddingProviderType
from common.core.config import settings


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

    import common.xpack_compat.startup as startup_module
    import main as main_module

    init_calls: list[object] = []

    def fake_init_fastapi_app(app: object) -> None:
        init_calls.append(app)

    monkeypatch.setattr(startup_module, "init_fastapi_app", fake_init_fastapi_app)

    main_module = importlib.reload(main_module)

    assert init_calls == [main_module.app]
    assert not hasattr(main_module, "mcp")


def test_main_import_initializes_mcp_only_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKIP_MCP_SETUP", raising=False)

    import main as main_module

    main_module = importlib.reload(main_module)

    assert hasattr(main_module, "mcp")


def test_mcp_health_endpoint_reports_not_ready_when_setup_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_MCP_SETUP", "true")

    import main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.mcp_app) as client:
        response = client.get(main_module.settings.MCP_HEALTH_PATH)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["service"] == "mcp"
    assert payload["ready"] is False
    assert payload["setup_enabled"] is False
    assert payload["bind_host"] == "0.0.0.0"
    assert payload["port"] == 8001
    assert payload["endpoint"] == "http://localhost:8001/mcp"
    assert payload["health_url"] == "http://localhost:8001/health"
    assert payload["issues"] == ["MCP setup is disabled via SKIP_MCP_SETUP"]


def test_mcp_health_endpoint_reports_ready_when_setup_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKIP_MCP_SETUP", raising=False)

    import main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.mcp_app) as client:
        response = client.get(main_module.settings.MCP_HEALTH_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "mcp"
    assert payload["ready"] is True
    assert payload["setup_enabled"] is True
    assert payload["bind_host"] == "0.0.0.0"
    assert payload["port"] == 8001
    assert payload["endpoint"] == "http://localhost:8001/mcp"
    assert payload["health_url"] == "http://localhost:8001/health"
    assert payload["issues"] == []


def test_mcp_metrics_endpoint_exposes_canonical_mcp_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKIP_MCP_SETUP", raising=False)

    import main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.mcp_app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "sqlbot_openclaw_mcp_requests_total" in body
    assert "sqlbot_openclaw_mcp_request_duration_seconds" in body


def test_startup_lifespan_runs_expected_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_STARTUP_TASKS", "false")
    monkeypatch.setenv("SKIP_MCP_SETUP", "true")

    import main as main_module

    main_module = importlib.reload(main_module)
    fastapi_app = main_module.app
    startup_calls: list[str] = []

    def fake_run_migrations() -> None:
        startup_calls.append("run_migrations")

    def fake_init_sqlbot_cache() -> None:
        startup_calls.append("init_sqlbot_cache")

    def fake_sync_default_admin_password(*, session: object) -> None:
        assert session is not None
        startup_calls.append("sync_default_admin_password")

    def fake_ensure_default_embedded_assistant(*, session: object) -> None:
        assert session is not None
        startup_calls.append("ensure_default_embedded_assistant")

    def fake_init_dynamic_cors(app: object) -> None:
        assert app is fastapi_app
        startup_calls.append("init_dynamic_cors")

    def fake_init_terminology_embedding_data() -> None:
        startup_calls.append("init_terminology_embedding_data")

    def fake_init_data_training_embedding_data() -> None:
        startup_calls.append("init_data_training_embedding_data")

    def fake_init_default_internal_datasource() -> None:
        startup_calls.append("init_default_internal_datasource")

    def fake_init_stale_datasource_sync_jobs() -> None:
        startup_calls.append("init_stale_datasource_sync_jobs")

    def fake_init_table_and_ds_embedding() -> None:
        startup_calls.append("init_table_and_ds_embedding")

    async def fake_async_model_info() -> None:
        startup_calls.append("async_model_info")

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(settings, "EMBEDDING_STARTUP_BACKFILL_POLICY", "eager")
    monkeypatch.setattr(main_module, "embedding_runtime_enabled", lambda: True)
    monkeypatch.setattr(
        main_module,
        "get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider_type=EmbeddingProviderType.OPENAI_COMPATIBLE,
            startup_backfill_policy="eager",
        ),
    )

    monkeypatch.setattr(main_module, "run_migrations", fake_run_migrations)
    monkeypatch.setattr(
        main_module,
        "sync_default_admin_password",
        fake_sync_default_admin_password,
    )
    monkeypatch.setattr(
        main_module,
        "ensure_default_embedded_assistant",
        fake_ensure_default_embedded_assistant,
    )
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
        "init_stale_datasource_sync_jobs",
        fake_init_stale_datasource_sync_jobs,
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
        "sync_default_admin_password",
        "ensure_default_embedded_assistant",
        "init_sqlbot_cache",
        "init_dynamic_cors",
        "init_terminology_embedding_data",
        "init_data_training_embedding_data",
        "init_default_internal_datasource",
        "init_stale_datasource_sync_jobs",
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
    fastapi_app = main_module.app
    startup_calls: list[str] = []

    def fake_run_migrations() -> None:
        startup_calls.append("run_migrations")

    def fake_init_sqlbot_cache() -> None:
        startup_calls.append("init_sqlbot_cache")

    def fake_sync_default_admin_password(*, session: object) -> None:
        assert session is not None
        startup_calls.append("sync_default_admin_password")

    def fake_ensure_default_embedded_assistant(*, session: object) -> None:
        assert session is not None
        startup_calls.append("ensure_default_embedded_assistant")

    def fake_init_dynamic_cors(app: object) -> None:
        assert app is fastapi_app
        startup_calls.append("init_dynamic_cors")

    def fake_init_terminology_embedding_data() -> None:
        startup_calls.append("init_terminology_embedding_data")

    def fake_init_data_training_embedding_data() -> None:
        startup_calls.append("init_data_training_embedding_data")

    def fake_init_default_internal_datasource() -> None:
        startup_calls.append("init_default_internal_datasource")

    def fake_init_stale_datasource_sync_jobs() -> None:
        startup_calls.append("init_stale_datasource_sync_jobs")

    def fake_init_table_and_ds_embedding() -> None:
        startup_calls.append("init_table_and_ds_embedding")

    async def fake_async_model_info() -> None:
        startup_calls.append("async_model_info")

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "remote")
    monkeypatch.setattr(settings, "EMBEDDING_STARTUP_BACKFILL_POLICY", "deferred")
    monkeypatch.setattr(main_module, "embedding_runtime_enabled", lambda: True)
    monkeypatch.setattr(
        main_module,
        "get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider_type=EmbeddingProviderType.OPENAI_COMPATIBLE,
            startup_backfill_policy="deferred",
        ),
    )
    monkeypatch.setattr(main_module, "run_migrations", fake_run_migrations)
    monkeypatch.setattr(
        main_module,
        "sync_default_admin_password",
        fake_sync_default_admin_password,
    )
    monkeypatch.setattr(
        main_module,
        "ensure_default_embedded_assistant",
        fake_ensure_default_embedded_assistant,
    )
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
        "init_stale_datasource_sync_jobs",
        fake_init_stale_datasource_sync_jobs,
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
        "sync_default_admin_password",
        "ensure_default_embedded_assistant",
        "init_sqlbot_cache",
        "init_dynamic_cors",
        "init_default_internal_datasource",
        "init_stale_datasource_sync_jobs",
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
    fastapi_app = main_module.app

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
