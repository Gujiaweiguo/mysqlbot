from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

import pytest

from apps.system.schemas.embedding_schema import (
    EmbeddingConfigPayload,
    EmbeddingConfigResponse,
    EmbeddingProvider,
    EmbeddingStartupBackfillPolicy,
    EmbeddingState,
    EmbeddingStatusPayload,
    EmbeddingValidateResponse,
    EmbeddingValidationInfo,
)


@pytest.fixture
def embedding_admin_store(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from apps.system.api import embedding as embedding_api_module

    config_store = EmbeddingConfigPayload(
        provider=EmbeddingProvider.LOCAL,
        remote_base_url=None,
        remote_api_key="",
        remote_model=None,
        remote_timeout_seconds=30,
        local_model="shibing624/text2vec-base-chinese",
        startup_backfill_policy=EmbeddingStartupBackfillPolicy.DEFERRED,
    )
    status_store = EmbeddingStatusPayload(
        enabled=False,
        state=EmbeddingState.DISABLED,
        reindex_required=False,
        reindex_reason=None,
        last_validation=EmbeddingValidationInfo(),
    )

    def get_config(_session: Any) -> EmbeddingConfigResponse:
        return EmbeddingConfigResponse(config=config_store, status=status_store)

    def save_config(
        _session: Any, config: EmbeddingConfigPayload, user_id: Any = None
    ) -> EmbeddingConfigResponse:
        nonlocal config_store, status_store
        _ = user_id
        previous = config_store
        changed = (
            previous.provider != config.provider
            or previous.remote_model != config.remote_model
            or previous.local_model != config.local_model
            or previous.remote_base_url != config.remote_base_url
        )
        preserved_key = config.remote_api_key or previous.remote_api_key
        config_store = config.model_copy(update={"remote_api_key": preserved_key})
        status_store = status_store.model_copy(
            update={
                "enabled": False,
                "state": EmbeddingState.CONFIGURED_UNVERIFIED,
                "reindex_required": changed,
                "reindex_reason": (
                    "Embedding provider or model changed" if changed else None
                ),
                "last_validation": EmbeddingValidationInfo(
                    success=False,
                    message="Configuration has not been validated yet",
                    at=None,
                ),
            }
        )
        return EmbeddingConfigResponse(config=config_store, status=status_store)

    def validate_config(
        _session: Any, config: EmbeddingConfigPayload, persist_result: bool
    ) -> EmbeddingValidateResponse:
        nonlocal status_store
        success = not (
            config.provider == EmbeddingProvider.REMOTE and not config.remote_model
        )
        response = EmbeddingValidateResponse(
            success=success,
            state=(
                EmbeddingState.VALIDATED_DISABLED
                if success
                else EmbeddingState.VALIDATION_FAILED
            ),
            message=(
                "Embedding provider validation succeeded"
                if success
                else "Validation failed"
            ),
            validated_at="2026-03-19T11:00:00Z",
        )
        if persist_result:
            status_store = status_store.model_copy(
                update={
                    "enabled": False,
                    "state": response.state,
                    "last_validation": EmbeddingValidationInfo(
                        success=response.success,
                        message=response.message,
                        at=response.validated_at,
                    ),
                }
            )
        return response

    def enable_config(_session: Any) -> EmbeddingStatusPayload:
        nonlocal status_store
        if status_store.reindex_required:
            raise ValueError(
                "Embedding requires reindex review before it can be enabled"
            )
        if status_store.state != EmbeddingState.VALIDATED_DISABLED:
            raise ValueError("Embedding cannot be enabled before validation succeeds")
        status_store = status_store.model_copy(
            update={"enabled": True, "state": EmbeddingState.ENABLED}
        )
        return status_store

    def disable_config(_session: Any) -> EmbeddingStatusPayload:
        nonlocal status_store
        status_store = status_store.model_copy(
            update={"enabled": False, "state": EmbeddingState.DISABLED}
        )
        return status_store

    monkeypatch.setattr(embedding_api_module, "get_embedding_admin_config", get_config)
    monkeypatch.setattr(
        embedding_api_module, "save_embedding_admin_config", save_config
    )
    monkeypatch.setattr(
        embedding_api_module, "validate_embedding_config", validate_config
    )
    monkeypatch.setattr(embedding_api_module, "enable_embedding", enable_config)
    monkeypatch.setattr(embedding_api_module, "disable_embedding", disable_config)

    return {
        "config": deepcopy(config_store.model_dump()),
        "status": deepcopy(status_store.model_dump()),
    }


class TestEmbeddingAdminApi:
    def test_config_defaults_are_disabled(
        self,
        test_app: Any,
        auth_headers: dict[str, str],
        embedding_admin_store: dict[str, Any],
    ) -> None:
        _ = embedding_admin_store
        response = test_app.get("/api/v1/system/embedding/config", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["status"]["enabled"] is False
        assert payload["status"]["state"] == "disabled"

    def test_cannot_enable_before_validation(
        self,
        test_app: Any,
        auth_headers: dict[str, str],
        embedding_admin_store: dict[str, Any],
    ) -> None:
        _ = embedding_admin_store
        response = test_app.post(
            "/api/v1/system/embedding/enable", headers=auth_headers
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["success"] is False
        assert "validation succeeds" in payload["message"]

    def test_save_validate_enable_flow(
        self,
        test_app: Any,
        auth_headers: dict[str, str],
        embedding_admin_store: dict[str, Any],
    ) -> None:
        _ = embedding_admin_store
        save_response = test_app.put(
            "/api/v1/system/embedding/config",
            headers=auth_headers,
            json={
                "config": {
                    "provider": "remote",
                    "remote_base_url": "http://embedding-service/v1",
                    "remote_api_key": "secret",
                    "remote_model": "text-embedding-3-small",
                    "remote_timeout_seconds": 30,
                    "local_model": "local-model",
                    "startup_backfill_policy": "deferred",
                }
            },
        )
        assert save_response.status_code == 200
        save_payload = save_response.json()["data"]
        assert save_payload["status"]["state"] == "configured_unverified"
        assert save_payload["status"]["reindex_required"] is True

        validate_response = test_app.post(
            "/api/v1/system/embedding/validate",
            headers=auth_headers,
            json={"use_saved_config": True},
        )
        assert validate_response.status_code == 200
        validate_payload = validate_response.json()["data"]
        assert validate_payload["success"] is True
        assert validate_payload["state"] == "validated_disabled"

        enable_response = test_app.post(
            "/api/v1/system/embedding/enable", headers=auth_headers
        )
        assert enable_response.status_code == 200
        enable_payload = enable_response.json()["data"]
        assert enable_payload["success"] is False
        assert "reindex" in enable_payload["message"].lower()

    def test_provider_change_marks_state_stale(
        self,
        test_app: Any,
        auth_headers: dict[str, str],
        embedding_admin_store: dict[str, Any],
    ) -> None:
        _ = embedding_admin_store
        first = test_app.put(
            "/api/v1/system/embedding/config",
            headers=auth_headers,
            json={
                "config": {
                    "provider": "local",
                    "remote_base_url": "",
                    "remote_api_key": "",
                    "remote_model": "",
                    "remote_timeout_seconds": 30,
                    "local_model": "local-model-a",
                    "startup_backfill_policy": "eager",
                }
            },
        )
        assert first.status_code == 200

        second = test_app.put(
            "/api/v1/system/embedding/config",
            headers=auth_headers,
            json={
                "config": {
                    "provider": "local",
                    "remote_base_url": "",
                    "remote_api_key": "",
                    "remote_model": "",
                    "remote_timeout_seconds": 30,
                    "local_model": "local-model-b",
                    "startup_backfill_policy": "eager",
                }
            },
        )
        assert second.status_code == 200
        payload = second.json()["data"]
        assert payload["status"]["state"] == "configured_unverified"
        assert payload["status"]["reindex_required"] is True


class TestEmbeddingRuntimeGate:
    def test_table_embedding_degrades_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from apps.datasource.embedding import table_embedding as table_embedding_module

        monkeypatch.setattr(
            table_embedding_module, "embedding_runtime_enabled", lambda: False
        )

        result = table_embedding_module.get_table_embedding(
            [{"id": 1, "schema_table": "# Table: orders"}],
            "show orders",
        )

        assert result == [
            {"id": 1, "schema_table": "# Table: orders", "cosine_similarity": 0.0}
        ]
