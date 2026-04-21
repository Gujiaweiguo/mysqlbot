from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest


class _FakeLocalEmbeddings:
    def __init__(self, **_: object) -> None:
        return None

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeClient:
    def __init__(self, **_: object) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def post(self, path: str, json: dict[str, object]) -> _FakeResponse:
        self.calls.append((path, json))
        inputs = json["input"]
        assert isinstance(inputs, list)
        return _FakeResponse(
            {
                "data": [
                    {"index": idx, "embedding": [float(len(str(text)))]}
                    for idx, text in enumerate(inputs)
                ]
            }
        )


class _TencentEmbeddingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self._code = code

    def get_code(self) -> str:
        return self._code


class _FakeTencentResponseItem:
    def __init__(self, embedding: list[float]) -> None:
        self.Embedding = embedding


class _FakeTencentResponse:
    def __init__(self, embedding: list[float]) -> None:
        self.Data = [_FakeTencentResponseItem(embedding)]


class _FakeTencentClient:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.calls = 0

    def GetEmbedding(self, _req: object) -> _FakeTencentResponse:
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return cast(_FakeTencentResponse, response)


class _FakeGetEmbeddingRequest:
    def __init__(self) -> None:
        self.Inputs: list[str] = []
        self.Model = ""


@pytest.fixture
def embedding_module() -> ModuleType:
    import apps.ai_model.embedding as embedding_module

    return importlib.reload(embedding_module)


def _reset_cache(embedding_module: ModuleType) -> None:
    embedding_module._embedding_model.clear()
    embedding_module.locks.clear()


def test_get_model_uses_local_provider(
    monkeypatch: pytest.MonkeyPatch, embedding_module: ModuleType
) -> None:
    _reset_cache(embedding_module)
    monkeypatch.setattr(
        embedding_module,
        "_get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider_type="local",
            supplier_id=None,
            base_url=None,
            api_key="",
            api_key_configured=False,
            model_name=None,
            timeout_seconds=30,
            local_model="local-model",
            startup_backfill_policy="eager",
        ),
    )
    monkeypatch.setattr(
        embedding_module,
        "import_module",
        lambda _name: SimpleNamespace(HuggingFaceEmbeddings=_FakeLocalEmbeddings),
    )

    model = embedding_module.EmbeddingModelCache.get_model()

    assert model.embed_query("hello") == [5.0]
    assert model.embed_documents(["hi", "world"]) == [[2.0], [5.0]]


def test_get_model_uses_remote_provider(
    monkeypatch: pytest.MonkeyPatch, embedding_module: ModuleType
) -> None:
    _reset_cache(embedding_module)
    fake_client = _FakeClient()
    monkeypatch.setattr(
        embedding_module,
        "_get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider_type="openai_compatible",
            supplier_id=15,
            base_url="http://embedding-service/v1",
            api_key="test-key",
            api_key_configured=True,
            model_name="text-embedding-3-small",
            timeout_seconds=30,
            local_model=None,
            startup_backfill_policy="deferred",
        ),
    )
    monkeypatch.setattr(
        embedding_module.httpx, "Client", lambda **_: cast(Any, fake_client)
    )

    model = embedding_module.EmbeddingModelCache.get_model()

    assert model.embed_query("hello") == [5.0]
    assert model.embed_documents(["foo", "bar"]) == [[3.0], [3.0]]
    assert fake_client.calls[0][0] == "/embeddings"
    assert fake_client.calls[0][1]["model"] == "text-embedding-3-small"


def test_remote_provider_requires_configuration(
    monkeypatch: pytest.MonkeyPatch, embedding_module: ModuleType
) -> None:
    _reset_cache(embedding_module)
    monkeypatch.setattr(
        embedding_module,
        "_get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider_type="openai_compatible",
            supplier_id=15,
            base_url=None,
            api_key="",
            api_key_configured=False,
            model_name=None,
            timeout_seconds=30,
            local_model=None,
            startup_backfill_policy="deferred",
        ),
    )

    with pytest.raises(ValueError, match="base_url is required"):
        embedding_module.EmbeddingModelCache.get_model()


def test_tencent_provider_retries_internal_error(
    monkeypatch: pytest.MonkeyPatch, embedding_module: ModuleType
) -> None:
    fake_client = _FakeTencentClient(
        [
            _TencentEmbeddingError("InternalError", "internal error"),
            _FakeTencentResponse([1.0, 2.0]),
        ]
    )
    monkeypatch.setattr(embedding_module.time, "sleep", lambda _seconds: None)
    fake_tencent_module = ModuleType("tencentcloud.lkeap.v20240522")
    setattr(
        fake_tencent_module,
        "models",
        SimpleNamespace(GetEmbeddingRequest=_FakeGetEmbeddingRequest),
    )
    sys.modules["tencentcloud.lkeap.v20240522"] = fake_tencent_module
    provider = embedding_module.TencentCloudEmbeddingProvider.__new__(
        embedding_module.TencentCloudEmbeddingProvider
    )
    provider._client = fake_client
    provider._model = "demo-model"

    assert provider.embed_query("hello") == [1.0, 2.0]
    assert fake_client.calls == 2


def test_tencent_provider_raises_after_retry_exhaustion(
    monkeypatch: pytest.MonkeyPatch, embedding_module: ModuleType
) -> None:
    fake_client = _FakeTencentClient(
        [
            _TencentEmbeddingError("InternalError", "internal error"),
            _TencentEmbeddingError("InternalError", "internal error"),
            _TencentEmbeddingError("InternalError", "internal error"),
        ]
    )
    monkeypatch.setattr(embedding_module.time, "sleep", lambda _seconds: None)
    fake_tencent_module = ModuleType("tencentcloud.lkeap.v20240522")
    setattr(
        fake_tencent_module,
        "models",
        SimpleNamespace(GetEmbeddingRequest=_FakeGetEmbeddingRequest),
    )
    sys.modules["tencentcloud.lkeap.v20240522"] = fake_tencent_module
    provider = embedding_module.TencentCloudEmbeddingProvider.__new__(
        embedding_module.TencentCloudEmbeddingProvider
    )
    provider._client = fake_client
    provider._model = "demo-model"

    with pytest.raises(_TencentEmbeddingError):
        provider.embed_query("hello")
    assert fake_client.calls == 3


def test_tencent_provider_does_not_retry_long_internal_error(
    monkeypatch: pytest.MonkeyPatch, embedding_module: ModuleType
) -> None:
    fake_client = _FakeTencentClient(
        [_TencentEmbeddingError("InternalError", "internal error")]
    )
    sleep_calls: list[int] = []
    monkeypatch.setattr(
        embedding_module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )
    fake_tencent_module = ModuleType("tencentcloud.lkeap.v20240522")
    setattr(
        fake_tencent_module,
        "models",
        SimpleNamespace(GetEmbeddingRequest=_FakeGetEmbeddingRequest),
    )
    sys.modules["tencentcloud.lkeap.v20240522"] = fake_tencent_module
    provider = embedding_module.TencentCloudEmbeddingProvider.__new__(
        embedding_module.TencentCloudEmbeddingProvider
    )
    provider._client = fake_client
    provider._model = "demo-model"

    with pytest.raises(ValueError, match="Input likely exceeds API limit"):
        provider.embed_query("x" * 3001)

    assert fake_client.calls == 1
    assert sleep_calls == []
