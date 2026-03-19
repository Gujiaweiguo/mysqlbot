from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import urlparse

import httpx
from sqlmodel import Session, col, select

from apps.system.models.system_variable_model import SystemVariable
from apps.system.schemas.embedding_schema import (
    EmbeddingConfigPayload,
    EmbeddingConfigResponse,
    EmbeddingProviderType,
    EmbeddingState,
    EmbeddingStatusPayload,
    EmbeddingStartupBackfillPolicy,
    EmbeddingValidateResponse,
    EmbeddingValidationInfo,
)
from common.core.config import settings
from common.core.db import engine

EMBEDDING_ADMIN_CONFIG_NAME = "embedding_admin_config"
EMBEDDING_ADMIN_VAR_TYPE = "embedding"
SUPPORTED_OPENAI_COMPATIBLE_SUPPLIERS = {1, 3, 10, 15}
GENERIC_OPENAI_SUPPLIER_ID = 15

EMBEDDING_MODELS_BY_SUPPLIER: dict[int, list[str]] = {
    1: ["text-embedding-v3", "text-embedding-v2", "text-embedding-v1"],
    3: [],
    10: ["doubao-embedding", "doubao-embedding-large"],
    15: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
}


def _supplier_id_from_base_url(base_url: str | None) -> int:
    if base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1":
        return 1
    if base_url == "https://api.deepseek.com":
        return 3
    if base_url == "https://ark.cn-beijing.volces.com/api/v3":
        return 10
    return GENERIC_OPENAI_SUPPLIER_ID


def _normalize_config_dict(config: dict[str, Any]) -> dict[str, Any]:
    if "provider_type" in config:
        normalized = dict(config)
        if normalized.get("provider_type") == EmbeddingProviderType.OPENAI_COMPATIBLE:
            supplier_id = normalized.get("supplier_id")
            if supplier_id not in SUPPORTED_OPENAI_COMPATIBLE_SUPPLIERS:
                normalized["supplier_id"] = _supplier_id_from_base_url(
                    cast(str | None, normalized.get("base_url"))
                )
        return normalized

    provider = config.get("provider")
    if provider == "local":
        return {
            "provider_type": EmbeddingProviderType.LOCAL,
            "supplier_id": None,
            "base_url": None,
            "api_key": config.get("remote_api_key", ""),
            "api_key_configured": bool(config.get("remote_api_key")),
            "model_name": None,
            "timeout_seconds": config.get("remote_timeout_seconds", 30),
            "local_model": config.get("local_model"),
            "startup_backfill_policy": config.get(
                "startup_backfill_policy", EmbeddingStartupBackfillPolicy.DEFERRED
            ),
        }

    base_url = cast(str | None, config.get("remote_base_url"))
    return {
        "provider_type": EmbeddingProviderType.OPENAI_COMPATIBLE,
        "supplier_id": _supplier_id_from_base_url(base_url),
        "base_url": base_url,
        "api_key": config.get("remote_api_key", ""),
        "api_key_configured": bool(config.get("remote_api_key")),
        "model_name": config.get("remote_model"),
        "timeout_seconds": config.get("remote_timeout_seconds", 30),
        "local_model": config.get("local_model"),
        "startup_backfill_policy": config.get(
            "startup_backfill_policy", EmbeddingStartupBackfillPolicy.DEFERRED
        ),
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _persist_validation_result(
    session: Session, response: EmbeddingValidateResponse
) -> None:
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


def _make_validation_response(
    success: bool,
    state: EmbeddingState,
    message: str,
) -> EmbeddingValidateResponse:
    return EmbeddingValidateResponse(
        success=success,
        state=state,
        message=message,
        validated_at=_now_iso(),
    )


def _format_remote_validation_error(
    config: EmbeddingConfigPayload, exc: Exception
) -> str:
    base_url = config.base_url or ""
    host = urlparse(base_url).netloc
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if host == "api.lkeap.cloud.tencent.com" and status_code == 404:
            return (
                "当前腾讯 LKEAP 的 OpenAI 兼容地址只确认支持聊天接口，"
                "不支持当前这条 /v1/embeddings 调用方式。"
                "请改用支持 OpenAI embeddings 的服务，或新增腾讯专用 embedding provider。"
            )
        if status_code == 401:
            return "远程嵌入服务鉴权失败，请检查 API Key、模型和服务权限是否正确。"
        if status_code == 404:
            return "远程嵌入接口不存在，请检查 Base URL、模型协议和服务端接口路径。"
    return f"嵌入服务验证失败：{exc}"


def _default_config() -> EmbeddingConfigPayload:
    provider_type = (
        EmbeddingProviderType.LOCAL
        if settings.EMBEDDING_PROVIDER == "local"
        else EmbeddingProviderType.OPENAI_COMPATIBLE
    )
    base_url = settings.REMOTE_EMBEDDING_BASE_URL
    return EmbeddingConfigPayload(
        provider_type=provider_type,
        supplier_id=(
            None
            if provider_type == EmbeddingProviderType.LOCAL
            else _supplier_id_from_base_url(base_url)
        ),
        base_url=base_url,
        api_key="",
        api_key_configured=bool(settings.REMOTE_EMBEDDING_API_KEY),
        model_name=settings.REMOTE_EMBEDDING_MODEL,
        timeout_seconds=settings.REMOTE_EMBEDDING_TIMEOUT_SECONDS,
        local_model=settings.DEFAULT_EMBEDDING_MODEL,
        startup_backfill_policy=EmbeddingStartupBackfillPolicy(
            cast(str, settings.EMBEDDING_STARTUP_BACKFILL_POLICY)
        ),
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
    from common.utils.aes_crypto import sqlbot_aes_decrypt

    api_key = config.get("api_key")
    if isinstance(api_key, str) and api_key:
        try:
            config["api_key"] = sqlbot_aes_decrypt(api_key)
        except Exception:
            config["api_key"] = api_key
        config["api_key_configured"] = True
    else:
        config["api_key"] = ""
        config["api_key_configured"] = False
    return config


def _mask_api_key(config: dict[str, Any]) -> dict[str, Any]:
    api_key_configured = bool(config.get("api_key")) or bool(
        config.get("api_key_configured")
    )
    config["api_key"] = ""
    config["api_key_configured"] = api_key_configured
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
    merged["config"].update(_normalize_config_dict(config))
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


def get_embedding_admin_config_unmasked(session: Session) -> EmbeddingConfigResponse:
    payload = _payload_from_record(_query_record(session))
    config_payload = EmbeddingConfigPayload.model_validate(
        cast(dict[str, Any], payload["config"])
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
    from common.utils.aes_crypto import sqlbot_aes_encrypt

    existing_payload = _payload_from_record(_query_record(session))
    existing_config = cast(dict[str, Any], existing_payload["config"])
    existing_status = cast(dict[str, Any], existing_payload["status"])
    next_config = config.model_dump()

    changed_provider_or_model = (
        existing_config.get("provider_type") != next_config.get("provider_type")
        or existing_config.get("supplier_id") != next_config.get("supplier_id")
        or existing_config.get("model_name") != next_config.get("model_name")
        or existing_config.get("local_model") != next_config.get("local_model")
        or existing_config.get("base_url") != next_config.get("base_url")
    )

    api_key_to_store = next_config.get("api_key")
    if isinstance(api_key_to_store, str) and api_key_to_store:
        encrypted_key = sqlbot_aes_encrypt(api_key_to_store)
    else:
        existing_encrypted_key = existing_config.get("api_key")
        encrypted_key = (
            existing_encrypted_key if isinstance(existing_encrypted_key, str) else ""
        )

    next_config["api_key"] = encrypted_key
    next_config["api_key_configured"] = bool(encrypted_key)

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
    if config.provider_type == EmbeddingProviderType.OPENAI_COMPATIBLE:
        if not config.base_url:
            response = _make_validation_response(
                False,
                EmbeddingState.VALIDATION_FAILED,
                "远程模式必须配置 Base URL。",
            )
            if persist_result:
                _persist_validation_result(session, response)
            return response
        if not config.model_name:
            response = _make_validation_response(
                False,
                EmbeddingState.VALIDATION_FAILED,
                "远程模式必须配置模型名称。",
            )
            if persist_result:
                _persist_validation_result(session, response)
            return response
    if config.provider_type == EmbeddingProviderType.LOCAL and not config.local_model:
        response = _make_validation_response(
            False,
            EmbeddingState.VALIDATION_FAILED,
            "本地模式必须配置本地模型。",
        )
        if persist_result:
            _persist_validation_result(session, response)
        return response

    from apps.ai_model.embedding import (
        LocalEmbeddingProvider,
        RemoteEmbeddingProvider,
        EmbeddingModelInfo,
        RemoteEmbeddingModelInfo,
        local_embedding_model,
    )

    if config.provider_type == EmbeddingProviderType.OPENAI_COMPATIBLE:
        provider = RemoteEmbeddingProvider(
            RemoteEmbeddingModelInfo(
                base_url=cast(str, config.base_url),
                api_key=config.api_key or None,
                model=cast(str, config.model_name),
                timeout_seconds=config.timeout_seconds,
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
            message="嵌入配置验证成功。",
            validated_at=validated_at,
        )
    except Exception as exc:
        message = (
            _format_remote_validation_error(config, exc)
            if config.provider_type == EmbeddingProviderType.OPENAI_COMPATIBLE
            else f"本地嵌入配置验证失败：{exc}"
        )
        response = EmbeddingValidateResponse(
            success=False,
            state=EmbeddingState.VALIDATION_FAILED,
            message=message,
            validated_at=validated_at,
        )

    if persist_result:
        _persist_validation_result(session, response)
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


def get_embedding_models(supplier_id: int) -> list[str]:
    if supplier_id not in SUPPORTED_OPENAI_COMPATIBLE_SUPPLIERS:
        return []
    return EMBEDDING_MODELS_BY_SUPPLIER.get(supplier_id, [])
