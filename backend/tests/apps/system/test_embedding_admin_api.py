from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

import httpx
import pytest

from apps.system.schemas.embedding_schema import (
    EmbeddingConfigPayload,
    EmbeddingConfigResponse,
    EmbeddingProviderType,
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
        provider_type=EmbeddingProviderType.LOCAL,
        supplier_id=None,
        model_name=None,
        base_url=None,
        api_key="",
        api_key_configured=False,
        timeout_seconds=30,
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
            previous.provider_type != config.provider_type
            or previous.supplier_id != config.supplier_id
            or previous.model_name != config.model_name
            or previous.local_model != config.local_model
            or previous.base_url != config.base_url
        )
        preserved_key = config.api_key or previous.api_key
        config_store = config.model_copy(
            update={"api_key": preserved_key, "api_key_configured": bool(preserved_key)}
        )
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
            config.provider_type == EmbeddingProviderType.OPENAI_COMPATIBLE
            and not config.model_name
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

    def enable_config(
        _session: Any, confirm_reindex: bool = False
    ) -> EmbeddingStatusPayload:
        nonlocal status_store
        if status_store.reindex_required and not confirm_reindex:
            raise ValueError(
                "Embedding requires reindex review before it can be enabled"
            )
        if status_store.state != EmbeddingState.VALIDATED_DISABLED:
            raise ValueError("Embedding cannot be enabled before validation succeeds")
        status_store = status_store.model_copy(
            update={
                "enabled": True,
                "state": EmbeddingState.ENABLED,
                "reindex_required": False,
                "reindex_reason": None,
            }
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
        embedding_api_module, "get_embedding_admin_config_unmasked", get_config
    )
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
                    "provider_type": "openai_compatible",
                    "supplier_id": 15,
                    "base_url": "http://embedding-service/v1",
                    "api_key": "secret",
                    "model_name": "text-embedding-3-small",
                    "timeout_seconds": 30,
                    "local_model": None,
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

        confirmed_enable_response = test_app.post(
            "/api/v1/system/embedding/enable",
            headers=auth_headers,
            json={"confirm_reindex": True},
        )
        assert confirmed_enable_response.status_code == 200
        confirmed_enable_payload = confirmed_enable_response.json()["data"]
        assert confirmed_enable_payload["success"] is True
        assert confirmed_enable_payload["state"] == "enabled"

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
                    "provider_type": "local",
                    "supplier_id": None,
                    "base_url": None,
                    "api_key": "",
                    "model_name": None,
                    "timeout_seconds": 30,
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
                    "provider_type": "local",
                    "supplier_id": None,
                    "base_url": None,
                    "api_key": "",
                    "model_name": None,
                    "timeout_seconds": 30,
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


class TestEmbeddingValidationMessages:
    def test_tencent_chat_base_url_returns_protocol_hint(self) -> None:
        from apps.system.crud.embedding_admin import _format_remote_validation_error

        request = httpx.Request(
            "POST", "https://api.lkeap.cloud.tencent.com/v1/embeddings"
        )
        response = httpx.Response(404, request=request)
        error = httpx.HTTPStatusError("not found", request=request, response=response)

        message = _format_remote_validation_error(
            EmbeddingConfigPayload(
                provider_type=EmbeddingProviderType.OPENAI_COMPATIBLE,
                supplier_id=9,
                base_url="https://api.lkeap.cloud.tencent.com/v1",
                api_key="secret",
                model_name="some-model",
                timeout_seconds=30,
                local_model=None,
                startup_backfill_policy=EmbeddingStartupBackfillPolicy.DEFERRED,
            ),
            error,
        )

        assert "不支持当前这条 /v1/embeddings 调用方式" in message
        assert "腾讯专用 embedding provider" in message

    def test_remote_401_returns_chinese_auth_message(self) -> None:
        from apps.system.crud.embedding_admin import _format_remote_validation_error

        request = httpx.Request("POST", "https://example.com/v1/embeddings")
        response = httpx.Response(401, request=request)
        error = httpx.HTTPStatusError(
            "unauthorized", request=request, response=response
        )

        message = _format_remote_validation_error(
            EmbeddingConfigPayload(
                provider_type=EmbeddingProviderType.OPENAI_COMPATIBLE,
                supplier_id=15,
                base_url="https://example.com/v1",
                api_key="secret",
                model_name="text-embedding-3-small",
                timeout_seconds=30,
                local_model=None,
                startup_backfill_policy=EmbeddingStartupBackfillPolicy.DEFERRED,
            ),
            error,
        )

        assert "鉴权失败" in message
