import orjson
import pytest
from fastapi.responses import StreamingResponse
from sqlmodel import Session

import apps.chat.api.chat as chat_api
from apps.chat.models.chat_model import ChatQuestion
from apps.system.schemas.system_schema import UserInfoDTO


def _sanitized_quota_event() -> str:
    payload = {
        "content": orjson.dumps(
            {
                "message": "模型服务额度不足，请检查模型供应商余额/配额后重试",
                "type": "llm-quota-err",
                "retryable": False,
            }
        ).decode(),
        "type": "error",
    }
    return "data:" + orjson.dumps(payload).decode() + "\n\n"


class _FakeLlmService:
    @classmethod
    async def create(
        cls,
        session: Session,
        current_user: UserInfoDTO,
        request_question: ChatQuestion,
        current_assistant: object | None,
        *,
        embedding: bool = False,
    ) -> "_FakeLlmService":
        _ = session
        _ = current_user
        _ = request_question
        _ = current_assistant
        _ = embedding
        return cls()

    def init_record(self, session: Session) -> None:
        _ = session

    def run_task_async(
        self,
        *,
        in_chat: bool = True,
        stream: bool = True,
        finish_step: object | None = None,
    ) -> None:
        _ = in_chat
        _ = stream
        _ = finish_step

    def await_result(self):
        yield _sanitized_quota_event()


class TestChatStreamSql:
    @pytest.mark.asyncio
    async def test_stream_sql_preserves_sanitized_quota_error_payload(
        self,
        monkeypatch: pytest.MonkeyPatch,
        test_db: Session,
        auth_user: UserInfoDTO,
    ) -> None:
        monkeypatch.setattr(chat_api, "_get_llm_service_class", lambda: _FakeLlmService)

        response = await chat_api.stream_sql(
            session=test_db,
            current_user=auth_user,
            request_question=ChatQuestion(chat_id=1, question="test quota error"),
            current_assistant=None,
            in_chat=True,
            stream=True,
        )

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

        chunks: list[str] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))

        body = "".join(chunks)
        event = orjson.loads(body.removeprefix("data:").strip())
        error_payload = orjson.loads(event["content"])

        assert event["type"] == "error"
        assert error_payload == {
            "message": "模型服务额度不足，请检查模型供应商余额/配额后重试",
            "type": "llm-quota-err",
            "retryable": False,
        }
        assert "not enough quota" not in body
        assert "20031" not in body
