from typing import cast

from sqlmodel import Session

from apps.chat.curd.chat import create_chat, save_question
from apps.chat.models.chat_model import (
    Chat,
    ChatRecord,
    CreateChat,
    ChatQuestion,
)
from apps.system.schemas.system_schema import UserInfoDTO


class FakeSession:
    def __init__(self) -> None:
        self._storage: dict[tuple[type[object], int], object] = {}
        self._next_id = 1

    def add(self, obj: object) -> None:
        assert hasattr(obj, "_sa_instance_state")
        obj_id = getattr(obj, "id", None)
        if obj_id is None:
            setattr(obj, "id", self._next_id)
            obj_id = self._next_id
            self._next_id += 1
        self._storage[(type(obj), obj_id)] = obj

    def flush(self) -> None:
        return None

    def refresh(self, obj: object) -> None:
        _ = obj
        return None

    def commit(self) -> None:
        return None

    def get(self, model: type[object], obj_id: int | None) -> object | None:
        if obj_id is None:
            return None
        return self._storage.get((model, obj_id))

    def close(self) -> None:
        return None


def build_user() -> UserInfoDTO:
    return UserInfoDTO(
        id=1,
        account="tester",
        oid=1,
        name="Tester",
        email="tester@example.com",
        status=1,
        origin=0,
        oid_list=[1],
        system_variables=[],
        language="en",
        weight=1,
        isAdmin=True,
    )


class TestChatCrud:
    def test_create_chat_without_datasource_persists_chat(self) -> None:
        session = FakeSession()
        db_session = cast(Session, cast(object, session))

        chat_info = create_chat(
            db_session,
            build_user(),
            CreateChat(question="hello", origin=0),
            require_datasource=False,
        )

        assert chat_info.id is not None
        db_chat = cast(Chat | None, session.get(Chat, chat_info.id))
        assert db_chat is not None
        assert db_chat.brief == "hello"
        session.close()

    def test_save_question_persists_record(self) -> None:
        session = FakeSession()
        db_session = cast(Session, cast(object, session))
        user = build_user()
        chat_info = create_chat(
            db_session,
            user,
            CreateChat(question="hello", origin=0),
            require_datasource=False,
        )

        assert chat_info.id is not None
        record = save_question(
            db_session,
            user,
            ChatQuestion(chat_id=chat_info.id, question="what is sales?"),
        )

        assert record.id is not None
        db_record = cast(ChatRecord | None, session.get(ChatRecord, record.id))
        assert db_record is not None
        assert db_record.question == "what is sales?"
        session.close()
