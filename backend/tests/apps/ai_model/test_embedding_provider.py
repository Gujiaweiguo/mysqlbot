from __future__ import annotations

import importlib
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
        "get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider="local",
            remote_base_url=None,
            remote_api_key="",
            remote_model=None,
            remote_timeout_seconds=30,
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
        "get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider="remote",
            remote_base_url="http://embedding-service/v1",
            remote_api_key="test-key",
            remote_model="text-embedding-3-small",
            remote_timeout_seconds=30,
            local_model="",
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
        "get_effective_embedding_config",
        lambda: SimpleNamespace(
            provider="remote",
            remote_base_url=None,
            remote_api_key="",
            remote_model=None,
            remote_timeout_seconds=30,
            local_model="",
            startup_backfill_policy="deferred",
        ),
    )

    with pytest.raises(ValueError, match="REMOTE_EMBEDDING_BASE_URL"):
        embedding_module.EmbeddingModelCache.get_model()
