import os.path
import threading
import time
from importlib import import_module
from typing import Any, Protocol, cast

import httpx
from sqlmodel import Session, col, select

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel

from apps.system.models.system_variable_model import SystemVariable
from apps.system.schemas.embedding_schema import (
    EmbeddingConfigPayload,
    EmbeddingProviderType,
    EmbeddingStartupBackfillPolicy,
)

from common.core.config import settings
from common.core.db import engine
from common.utils.utils import SQLBotLogUtil

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class EmbeddingModelInfo(BaseModel):
    folder: str
    name: str
    device: str = "cpu"


class RemoteEmbeddingModelInfo(BaseModel):
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: int = 30


class TencentCloudEmbeddingModelInfo(BaseModel):
    secret_id: str
    secret_key: str
    region: str = "ap-guangzhou"
    model: str


local_embedding_model = EmbeddingModelInfo(
    folder=settings.LOCAL_MODEL_PATH,
    name=os.path.join(
        settings.LOCAL_MODEL_PATH, "embedding", "shibing624_text2vec-base-chinese"
    ),
)


class EmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


_lock = threading.Lock()
locks: dict[str, threading.Lock] = {}

_embedding_model: dict[str, EmbeddingProvider | None] = {}


def _supplier_id_from_base_url(base_url: str | None) -> int:
    if base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1":
        return 1
    if base_url == "https://api.deepseek.com":
        return 3
    if base_url == "https://ark.cn-beijing.volces.com/api/v3":
        return 10
    return 15


def _default_embedding_config() -> EmbeddingConfigPayload:
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


def _normalize_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    if "provider_type" in config:
        normalized = dict(config)
        if normalized.get("provider_type") == EmbeddingProviderType.OPENAI_COMPATIBLE:
            supplier_id = normalized.get("supplier_id")
            if supplier_id not in {1, 3, 10, 15}:
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


def _get_effective_embedding_config() -> EmbeddingConfigPayload:
    with Session(engine) as session:
        record = session.exec(
            select(SystemVariable).where(
                col(SystemVariable.name) == "embedding_admin_config"
            )
        ).first()

    if record is None or not record.value:
        return _default_embedding_config()

    raw_value = record.value[0] if record.value else {}
    payload = cast(dict[str, Any], raw_value if isinstance(raw_value, dict) else {})
    config = cast(
        dict[str, Any],
        payload.get("config") if isinstance(payload.get("config"), dict) else {},
    )
    merged = _default_embedding_config().model_dump()
    merged.update(_normalize_runtime_config(config))
    _decrypt_api_key_if_needed(merged)

    return EmbeddingConfigPayload.model_validate(merged)


class LocalEmbeddingProvider:
    def __init__(self, config: EmbeddingModelInfo):
        try:
            huggingface_embeddings_cls = import_module(
                "langchain_huggingface"
            ).HuggingFaceEmbeddings
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Local embedding provider requires local embedding dependencies. "
                "Install them with `uv sync --extra cpu`."
            ) from exc
        self._provider = cast(
            Embeddings,
            huggingface_embeddings_cls(
                model_name=config.name,
                cache_folder=config.folder,
                model_kwargs={"device": config.device},
                encode_kwargs={"normalize_embeddings": True},
            ),
        )

    def embed_query(self, text: str) -> list[float]:
        return cast(list[float], self._provider.embed_query(text))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return cast(list[list[float]], self._provider.embed_documents(texts))


class RemoteEmbeddingProvider:
    def __init__(self, config: RemoteEmbeddingModelInfo):
        headers: dict[str, str] = {}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            headers=headers,
            timeout=config.timeout_seconds,
        )
        self._model = config.model

    @staticmethod
    def _normalize_text(text: str) -> str:
        return text.replace("\n", " ")

    def _create_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload = {
            "input": [self._normalize_text(text) for text in texts],
            "model": self._model,
            "encoding_format": "float",
        }
        response = self._client.post("/embeddings", json=payload)
        response.raise_for_status()
        body = response.json()
        data = body.get("data")
        if not isinstance(data, list):
            raise ValueError("Remote embedding response missing data list")

        sorted_items = sorted(
            data,
            key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0,
        )
        embeddings: list[list[float]] = []
        for item in sorted_items:
            if not isinstance(item, dict) or not isinstance(
                item.get("embedding"), list
            ):
                raise ValueError(
                    "Remote embedding response item missing embedding list"
                )
            embeddings.append(cast(list[float], item["embedding"]))
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        embeddings = self._create_embeddings([text])
        if not embeddings:
            raise ValueError(
                "Remote embedding provider returned no embedding for query"
            )
        return embeddings[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._create_embeddings(texts)


class TencentCloudEmbeddingProvider:
    _TRANSIENT_ERROR_CODES = {
        "InternalError",
        "ServerNetworkError",
        "ClientNetworkError",
        "LimitExceeded",
        "RequestLimitExceeded",
    }

    def __init__(self, config: TencentCloudEmbeddingModelInfo):
        from tencentcloud.common import credential
        from tencentcloud.lkeap.v20240522 import lkeap_client

        cred = credential.Credential(config.secret_id, config.secret_key)
        self._client = lkeap_client.LkeapClient(cred, config.region)
        self._model = config.model

    def embed_query(self, text: str) -> list[float]:
        return self._create_embedding(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._create_embedding(text) for text in texts]

    @classmethod
    def _get_error_code(cls, exc: Exception) -> str | None:
        get_code = getattr(exc, "get_code", None)
        if callable(get_code):
            code = get_code()
            if isinstance(code, str):
                return code
        return None

    @classmethod
    def _is_retryable_error(cls, exc: Exception) -> bool:
        code = cls._get_error_code(exc)
        return isinstance(code, str) and code in cls._TRANSIENT_ERROR_CODES

    def _create_embedding(self, text: str) -> list[float]:
        from tencentcloud.lkeap.v20240522 import models

        req = models.GetEmbeddingRequest()
        req.Inputs = [text.replace("\n", " ")]
        req.Model = self._model

        max_attempts = 3
        resp = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._client.GetEmbedding(req)
                break
            except Exception as exc:
                if not self._is_retryable_error(exc) or attempt == max_attempts:
                    raise
                sleep_seconds = attempt
                SQLBotLogUtil.warning(
                    "Tencent embedding request failed with retryable error "
                    f"[{self._get_error_code(exc)}], retrying in {sleep_seconds}s "
                    f"(attempt {attempt}/{max_attempts}): {exc}"
                )
                time.sleep(sleep_seconds)
        if resp is None:
            raise RuntimeError("Tencent Cloud embedding response missing after retries")
        if not resp.Data or not isinstance(resp.Data, list) or len(resp.Data) == 0:
            raise ValueError("Tencent Cloud embedding response missing data list")
        embedding_obj = resp.Data[0]
        if not embedding_obj.Embedding or not isinstance(embedding_obj.Embedding, list):
            raise ValueError(
                "Tencent Cloud embedding response missing embedding vector"
            )
        return list(embedding_obj.Embedding)


class EmbeddingModelCache:
    @staticmethod
    def _get_remote_config() -> RemoteEmbeddingModelInfo:
        config = _get_effective_embedding_config()
        if not config.base_url:
            raise ValueError(
                "base_url is required when provider_type=openai_compatible"
            )
        if not config.model_name:
            raise ValueError(
                "model_name is required when provider_type=openai_compatible"
            )
        return RemoteEmbeddingModelInfo(
            base_url=config.base_url,
            model=config.model_name,
            api_key=config.api_key or None,
            timeout_seconds=config.timeout_seconds,
        )

    @staticmethod
    def _get_tencent_cloud_config() -> TencentCloudEmbeddingModelInfo:
        config = _get_effective_embedding_config()
        if not config.tencent_secret_id:
            raise ValueError(
                "tencent_secret_id is required when provider_type=tencent_cloud"
            )
        if not config.tencent_secret_key:
            raise ValueError(
                "tencent_secret_key is required when provider_type=tencent_cloud"
            )
        if not config.model_name:
            raise ValueError("model_name is required when provider_type=tencent_cloud")
        return TencentCloudEmbeddingModelInfo(
            secret_id=config.tencent_secret_id,
            secret_key=config.tencent_secret_key,
            region=config.tencent_region,
            model=config.model_name,
        )

    @staticmethod
    def _get_cache_key(key: str | None = None) -> str:
        config = _get_effective_embedding_config()
        if config.provider_type == EmbeddingProviderType.OPENAI_COMPATIBLE:
            remote_model = config.model_name or ""
            remote_url = config.base_url or ""
            return key or f"remote:{remote_url}:{remote_model}"
        if config.provider_type == EmbeddingProviderType.TENCENT_CLOUD:
            return key or f"tencent:{config.tencent_region}:{config.model_name}"
        return key or f"local:{config.local_model or settings.DEFAULT_EMBEDDING_MODEL}"

    @staticmethod
    def _new_instance(
        config: EmbeddingModelInfo = local_embedding_model,
    ) -> EmbeddingProvider:
        runtime_config = _get_effective_embedding_config()
        if runtime_config.provider_type == EmbeddingProviderType.OPENAI_COMPATIBLE:
            return RemoteEmbeddingProvider(EmbeddingModelCache._get_remote_config())
        if runtime_config.provider_type == EmbeddingProviderType.TENCENT_CLOUD:
            return TencentCloudEmbeddingProvider(
                EmbeddingModelCache._get_tencent_cloud_config()
            )
        local_config = EmbeddingModelInfo(
            folder=config.folder,
            name=runtime_config.local_model or config.name,
            device=config.device,
        )
        return LocalEmbeddingProvider(local_config)

    @staticmethod
    def _get_lock(key: str | None = None) -> threading.Lock:
        cache_key = EmbeddingModelCache._get_cache_key(key)
        lock = locks.get(cache_key)
        if lock is None:
            with _lock:
                lock = locks.get(cache_key)
                if lock is None:
                    lock = threading.Lock()
                    locks[cache_key] = lock

        return lock

    @staticmethod
    def get_model(
        key: str | None = None,
        config: EmbeddingModelInfo = local_embedding_model,
    ) -> EmbeddingProvider:
        cache_key = EmbeddingModelCache._get_cache_key(key)
        model_instance = _embedding_model.get(cache_key)
        if model_instance is None:
            lock = EmbeddingModelCache._get_lock(cache_key)
            with lock:
                model_instance = _embedding_model.get(cache_key)
                if model_instance is None:
                    model_instance = EmbeddingModelCache._new_instance(config)
                    _embedding_model[cache_key] = model_instance

        return cast(EmbeddingProvider, model_instance)
