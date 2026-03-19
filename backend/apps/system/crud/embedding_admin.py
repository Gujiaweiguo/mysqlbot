from datetime import UTC, datetime
from typing import Any, cast

from sqlmodel import Session, col, select

from apps.system.models.system_variable_model import SystemVariable
from apps.system.schemas.embedding_schema import (
    EmbeddingConfigPayload,
    EmbeddingConfigResponse,
    EmbeddingProvider,
    EmbeddingState,
    EmbeddingStatusPayload,
    EmbeddingValidateResponse,
    EmbeddingValidationInfo,
)
from common.core.config import settings
from common.core.db import engine
from common.utils.aes_crypto import sqlbot_aes_decrypt, sqlbot_aes_encrypt

EMBEDDING_ADMIN_CONFIG_NAME = "embedding_admin_config"
EMBEDDING_ADMIN_VAR_TYPE = "embedding"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _default_config() -> EmbeddingConfigPayload:
    return EmbeddingConfigPayload(
        provider=EmbeddingProvider(settings.EMBEDDING_PROVIDER),
        remote_base_url=settings.REMOTE_EMBEDDING_BASE_URL,
        remote_api_key="",
        remote_api_key_configured=bool(settings.REMOTE_EMBEDDING_API_KEY),
        remote_model=settings.REMOTE_EMBEDDING_MODEL,
        remote_timeout_seconds=settings.REMOTE_EMBEDDING_TIMEOUT_SECONDS,
        local_model=settings.DEFAULT_EMBEDDING_MODEL,
        startup_backfill_policy=settings.EMBEDDING_STARTUP_BACKFILL_POLICY,
    )


def _default_status() -> EmbeddingStatusPayload:
    return EmbeddingStatusPayload()


def _default_payload() -> dict[str, Any]:
    return {
        "config": _default_config().model_dump(),
        "status": _default_status().model_dump(),
    }


def _query_record(session: Session) -> SystemVariable | None:
    return session.exec(
        select(SystemVariable).where(
            col(SystemVariable.name) == EMBEDDING_ADMIN_CONFIG_NAME
        )
    ).first()


def _decrypt_api_key_if_needed(config: dict[str, Any]) -> dict[str, Any]:
    api_key = config.get("remote_api_key")
    if isinstance(api_key, str) and api_key:
        config["remote_api_key"] = sqlbot_aes_decrypt(api_key)
        config["remote_api_key_configured"] = True
    else:
        config["remote_api_key"] = ""
        config["remote_api_key_configured"] = False
    return config


def _mask_api_key(config: dict[str, Any]) -> dict[str, Any]:
    api_key_configured = bool(config.get("remote_api_key")) or bool(
        config.get("remote_api_key_configured")
    )
    config["remote_api_key"] = ""
    config["remote_api_key_configured"] = api_key_configured
    return config


def _payload_from_record(record: SystemVariable | None) -> dict[str, Any]:
    if record is None or not record.value:
        return _default_payload()
    raw_value = record.value[0] if record.value else {}
    payload = cast(dict[str, Any], raw_value if isinstance(raw_value, dict) else {})
    config = cast(
        dict[str, Any],
        payload.get("config") if isinstance(payload.get("config"), dict) else {},
    )
    status = cast(
        dict[str, Any],
        payload.get("status") if isinstance(payload.get("status"), dict) else {},
    )
    merged = _default_payload()
    merged["config"].update(config)
    merged["status"].update(status)
    _decrypt_api_key_if_needed(cast(dict[str, Any], merged["config"]))
    return merged


def get_embedding_admin_config(session: Session) -> EmbeddingConfigResponse:
    payload = _payload_from_record(_query_record(session))
    config_payload = EmbeddingConfigPayload.model_validate(
        _mask_api_key(cast(dict[str, Any], payload["config"]))
    )
    status_payload = EmbeddingStatusPayload.model_validate(payload["status"])
    return EmbeddingConfigResponse(config=config_payload, status=status_payload)


def _persist_payload(
    session: Session, payload: dict[str, Any], user_id: int | None = None
) -> None:
    record = _query_record(session)
    if record is None:
        record = SystemVariable(
            name=EMBEDDING_ADMIN_CONFIG_NAME,
            var_type=EMBEDDING_ADMIN_VAR_TYPE,
            type="system",
            value=[payload],
            create_time=datetime.now(),
            create_by=user_id,
        )
    else:
        record.value = [payload]
    session.add(record)
    session.commit()


def save_embedding_admin_config(
    session: Session,
    config: EmbeddingConfigPayload,
    user_id: int | None = None,
) -> EmbeddingConfigResponse:
    existing_payload = _payload_from_record(_query_record(session))
    existing_config = cast(dict[str, Any], existing_payload["config"])
    existing_status = cast(dict[str, Any], existing_payload["status"])
    next_config = config.model_dump()

    changed_provider_or_model = (
        existing_config.get("provider") != next_config.get("provider")
        or existing_config.get("remote_model") != next_config.get("remote_model")
        or existing_config.get("local_model") != next_config.get("local_model")
        or existing_config.get("remote_base_url") != next_config.get("remote_base_url")
    )

    api_key_to_store = next_config.get("remote_api_key")
    if isinstance(api_key_to_store, str) and api_key_to_store:
        encrypted_key = sqlbot_aes_encrypt(api_key_to_store)
    else:
        existing_encrypted_key = existing_config.get("remote_api_key")
        encrypted_key = (
            existing_encrypted_key if isinstance(existing_encrypted_key, str) else ""
        )

    next_config["remote_api_key"] = encrypted_key
    next_config["remote_api_key_configured"] = bool(encrypted_key)

    next_status = dict(existing_status)
    next_status["enabled"] = False
    next_status["state"] = EmbeddingState.CONFIGURED_UNVERIFIED
    next_status["last_validation"] = EmbeddingValidationInfo(
        success=False,
        message="Configuration has not been validated yet",
        at=None,
    ).model_dump()
    if changed_provider_or_model:
        next_status["reindex_required"] = True
        next_status["reindex_reason"] = "Embedding provider or model changed"

    payload = {"config": next_config, "status": next_status}
    _persist_payload(session, payload, user_id=user_id)
    return get_embedding_admin_config(session)


def _runtime_payload() -> dict[str, Any]:
    with Session(engine) as session:
        return _payload_from_record(_query_record(session))


def get_effective_embedding_config() -> EmbeddingConfigPayload:
    payload = _runtime_payload()
    return EmbeddingConfigPayload.model_validate(
        cast(dict[str, Any], payload["config"])
    )


def get_embedding_runtime_status() -> EmbeddingStatusPayload:
    payload = _runtime_payload()
    return EmbeddingStatusPayload.model_validate(payload["status"])


def embedding_runtime_enabled() -> bool:
    status = get_embedding_runtime_status()
    return status.enabled and status.state == EmbeddingState.ENABLED


def validate_embedding_config(
    session: Session,
    config: EmbeddingConfigPayload,
    persist_result: bool,
) -> EmbeddingValidateResponse:
    from apps.ai_model.embedding import (
        LocalEmbeddingProvider,
        RemoteEmbeddingProvider,
        EmbeddingModelInfo,
        RemoteEmbeddingModelInfo,
        local_embedding_model,
    )

    if config.provider == EmbeddingProvider.REMOTE:
        provider = RemoteEmbeddingProvider(
            RemoteEmbeddingModelInfo(
                base_url=cast(str, config.remote_base_url),
                api_key=config.remote_api_key or None,
                model=cast(str, config.remote_model),
                timeout_seconds=config.remote_timeout_seconds,
            )
        )
    else:
        provider = LocalEmbeddingProvider(
            EmbeddingModelInfo(
                folder=local_embedding_model.folder,
                name=cast(str, config.local_model),
                device=local_embedding_model.device,
            )
        )

    validated_at = _now_iso()
    try:
        embedding = provider.embed_query("hello")
        if not embedding:
            raise ValueError("Embedding provider returned empty vector")
        response = EmbeddingValidateResponse(
            success=True,
            state=EmbeddingState.VALIDATED_DISABLED,
            message="Embedding provider validation succeeded",
            validated_at=validated_at,
        )
    except Exception as exc:
        response = EmbeddingValidateResponse(
            success=False,
            state=EmbeddingState.VALIDATION_FAILED,
            message=str(exc),
            validated_at=validated_at,
        )

    if persist_result:
        payload = _payload_from_record(_query_record(session))
        status = cast(dict[str, Any], payload["status"])
        status["enabled"] = False
        status["state"] = response.state
        status["last_validation"] = EmbeddingValidationInfo(
            success=response.success,
            message=response.message,
            at=response.validated_at,
        ).model_dump()
        payload["status"] = status
        _persist_payload(session, payload)
    return response


def enable_embedding(session: Session) -> EmbeddingStatusPayload:
    payload = _payload_from_record(_query_record(session))
    status = cast(dict[str, Any], payload["status"])
    current_state = status.get("state")
    if status.get("reindex_required"):
        raise ValueError("Embedding requires reindex review before it can be enabled")
    if current_state != EmbeddingState.VALIDATED_DISABLED:
        raise ValueError("Embedding cannot be enabled before validation succeeds")
    status["enabled"] = True
    status["state"] = EmbeddingState.ENABLED
    payload["status"] = status
    _persist_payload(session, payload)
    return EmbeddingStatusPayload.model_validate(status)


def disable_embedding(session: Session) -> EmbeddingStatusPayload:
    payload = _payload_from_record(_query_record(session))
    status = cast(dict[str, Any], payload["status"])
    status["enabled"] = False
    status["state"] = EmbeddingState.DISABLED
    payload["status"] = status
    _persist_payload(session, payload)
    return EmbeddingStatusPayload.model_validate(status)
