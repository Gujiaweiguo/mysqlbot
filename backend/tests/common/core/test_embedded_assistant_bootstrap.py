from __future__ import annotations

from apps.system.crud.assistant_manage import (
    DEFAULT_EMBEDDED_ASSISTANT_NAME,
    ensure_default_embedded_assistant,
)
from apps.system.models.system_model import AssistantModel


class FakeExecResult:
    def __init__(self, value: AssistantModel | None) -> None:
        self._value = value

    def first(self) -> AssistantModel | None:
        return self._value


class FakeSession:
    def __init__(self, assistant: AssistantModel | None) -> None:
        self.assistant = assistant
        self.added: list[AssistantModel] = []
        self.commits = 0

    def exec(self, statement: object) -> FakeExecResult:
        _ = statement
        return FakeExecResult(self.assistant)

    def add(self, instance: object, _warn: bool = True) -> None:
        assert isinstance(instance, AssistantModel)
        self.added.append(instance)

    def commit(self) -> None:
        self.commits += 1


def _build_embedded_assistant() -> AssistantModel:
    assistant = AssistantModel(
        id=7443666318579994624,
        name="Existing Embedded Assistant",
        domain="http://localhost:8000",
        type=4,
        configuration="{}",
        description="existing",
        app_id="existing-app-id",
        app_secret="existing-app-secret",
        oid=1,
    )
    assistant.create_time = 1774708376946
    return assistant


def test_ensure_default_embedded_assistant_creates_when_missing() -> None:
    session = FakeSession(None)

    created = ensure_default_embedded_assistant(session=session)

    assert created is True
    assert session.commits == 1
    assert len(session.added) == 1
    assistant = session.added[0]
    assert assistant.name == DEFAULT_EMBEDDED_ASSISTANT_NAME
    assert assistant.type == 4
    assert assistant.oid == 1
    assert assistant.domain == "http://localhost:8000"
    assert assistant.configuration == "{}"
    assert assistant.description == "Auto-created embedded assistant"
    assert assistant.app_id
    assert assistant.app_secret
    assert assistant.create_time is not None


def test_ensure_default_embedded_assistant_is_idempotent() -> None:
    existing = _build_embedded_assistant()
    session = FakeSession(existing)

    created = ensure_default_embedded_assistant(session=session)

    assert created is False
    assert session.added == []
    assert session.commits == 0
