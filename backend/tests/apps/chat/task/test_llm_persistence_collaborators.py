from typing import cast

import pytest
from sqlmodel import Session

from apps.chat.models.chat_model import ChatQuestion, ChatRecord, OperationEnum
from apps.chat.persistence import ChatPersistenceService
from apps.chat.task.llm import LLMService


class _FakeRecord:
    def __init__(self, record_id: int) -> None:
        self.id = record_id


class _FakePersistence(ChatPersistenceService):
    def __init__(self) -> None:
        self.saved_sql: tuple[int, str] | None = None
        self.saved_predict_data: tuple[int, str] | None = None
        self.finished_record_id: int | None = None

    def save_sql(self, session: Session, record_id: int, sql: str) -> ChatRecord:
        _ = session
        self.saved_sql = (record_id, sql)
        return cast(ChatRecord, cast(object, _FakeRecord(record_id)))

    def save_predict_data(
        self, session: Session, record_id: int, data: str
    ) -> ChatRecord:
        _ = session
        self.saved_predict_data = (record_id, data)
        return cast(ChatRecord, cast(object, _FakeRecord(record_id)))

    def finish(self, session: Session, record_id: int) -> ChatRecord:
        _ = session
        self.finished_record_id = record_id
        return cast(ChatRecord, cast(object, _FakeRecord(record_id)))


def build_service_with_persistence() -> tuple[LLMService, _FakePersistence]:
    service = object.__new__(LLMService)
    service.record = cast(ChatRecord, cast(object, _FakeRecord(12)))
    service.chat_question = ChatQuestion(chat_id=5, question="show sales")
    persistence = _FakePersistence()
    service.persistence = persistence
    return service, persistence


class TestLlmPersistenceCollaborators:
    def test_check_save_sql_uses_persistence_collaborator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service, persistence = build_service_with_persistence()

        def fake_check_sql(
            session: Session, res: str, operate: OperationEnum
        ) -> tuple[str, None]:
            _ = session
            _ = res
            _ = operate
            return ("SELECT 1", None)

        monkeypatch.setattr(service, "check_sql", fake_check_sql)

        sql = service.check_save_sql(
            session=cast(Session, object()),
            res='{"sql":"SELECT 1"}',
            operate=OperationEnum.GENERATE_SQL,
        )

        assert sql == "SELECT 1"
        assert persistence.saved_sql == (12, "SELECT 1")

    def test_check_save_predict_data_uses_persistence_collaborator(self) -> None:
        service, persistence = build_service_with_persistence()

        has_data = service.check_save_predict_data(
            session=cast(Session, object()),
            res='{"rows":[{"value":1}]}',
        )

        assert has_data is True
        assert persistence.saved_predict_data == (12, '{"rows":[{"value":1}]}')

    def test_finish_uses_persistence_collaborator(self) -> None:
        service, persistence = build_service_with_persistence()

        record = service.finish(cast(Session, object()))

        assert record.id == 12
        assert persistence.finished_record_id == 12
