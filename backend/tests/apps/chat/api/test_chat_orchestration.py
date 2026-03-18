from dataclasses import dataclass
from typing import cast

import pytest
from sqlmodel import Session
from starlette.responses import JSONResponse, StreamingResponse

import apps.chat.api.chat as chat_api
from apps.chat.models.chat_model import ChatQuestion
from apps.chat.orchestration.types import (
    AnalysisRecordRequest,
    AnalysisRequest,
    ChatExecutionRequest,
    QuestionAnswerRequest,
    RecommendQuestionsRequest,
)
from apps.system.schemas.system_schema import UserInfoDTO


@dataclass
class _FakeChatRecord:
    id: int
    chat_id: int
    question: str
    chart: str


class _FakeOrchestrator:
    def __init__(self) -> None:
        self.chat_request: ChatExecutionRequest | None = None
        self.question_request: QuestionAnswerRequest | None = None
        self.analysis_request: AnalysisRequest | None = None
        self.analysis_record_request: AnalysisRecordRequest | None = None
        self.recommend_request: RecommendQuestionsRequest | None = None

    async def start_chat(self, request: ChatExecutionRequest) -> JSONResponse:
        self.chat_request = request
        return JSONResponse({"success": True, "source": "orchestrator"})

    async def answer_question(self, request: QuestionAnswerRequest) -> JSONResponse:
        self.question_request = request
        return JSONResponse({"success": True, "source": "question-orchestrator"})

    async def start_analysis_or_predict(self, request: AnalysisRequest) -> JSONResponse:
        self.analysis_request = request
        return JSONResponse({"success": True, "source": "analysis-orchestrator"})

    async def start_analysis_or_predict_by_record(
        self, request: AnalysisRecordRequest
    ) -> JSONResponse:
        self.analysis_record_request = request
        return JSONResponse({"success": True, "source": "analysis-record-orchestrator"})

    async def start_recommend_questions(
        self, request: RecommendQuestionsRequest
    ) -> StreamingResponse:
        self.recommend_request = request
        return StreamingResponse(iter(["data:{}\n\n"]), media_type="text/event-stream")


class _AnalysisSession:
    def __init__(self, record: _FakeChatRecord) -> None:
        self._record = record

    def get(self, model: type[object], obj_id: int) -> _FakeChatRecord | None:
        _ = model
        return self._record if obj_id == self._record.id else None


@pytest.fixture
def fake_orchestrator(monkeypatch: pytest.MonkeyPatch) -> _FakeOrchestrator:
    orchestrator = _FakeOrchestrator()
    monkeypatch.setattr(chat_api, "_get_chat_orchestrator", lambda: orchestrator)
    return orchestrator


class TestChatOrchestrationDelegation:
    @pytest.mark.asyncio
    async def test_stream_sql_delegates_to_orchestrator(
        self,
        fake_orchestrator: _FakeOrchestrator,
        test_db: object,
        auth_user: UserInfoDTO,
    ) -> None:
        request_question = ChatQuestion(chat_id=1, question="show sales")

        response = await chat_api.stream_sql(
            session=cast(Session, test_db),
            current_user=auth_user,
            request_question=request_question,
            current_assistant=None,
            in_chat=False,
            stream=False,
        )

        assert isinstance(response, JSONResponse)
        assert fake_orchestrator.chat_request is not None
        assert fake_orchestrator.chat_request.request_question is request_question
        assert fake_orchestrator.chat_request.current_user == auth_user
        assert fake_orchestrator.chat_request.stream is False

    @pytest.mark.asyncio
    async def test_analysis_or_predict_delegates_to_orchestrator(
        self,
        fake_orchestrator: _FakeOrchestrator,
        auth_user: UserInfoDTO,
    ) -> None:
        record = _FakeChatRecord(7, 3, "analyze this chart", '{"type":"bar"}')
        session = _AnalysisSession(record)

        response = await chat_api.analysis_or_predict(
            session=cast(Session, cast(object, session)),
            current_user=auth_user,
            chat_record_id=7,
            action_type="analysis",
            current_assistant=None,
            in_chat=False,
            stream=False,
        )

        assert isinstance(response, JSONResponse)
        assert fake_orchestrator.analysis_record_request is not None
        assert fake_orchestrator.analysis_record_request.chat_record_id == record.id
        assert fake_orchestrator.analysis_record_request.action_type == "analysis"

    @pytest.mark.asyncio
    async def test_question_answer_inner_delegates_to_orchestrator(
        self,
        fake_orchestrator: _FakeOrchestrator,
        test_db: object,
        auth_user: UserInfoDTO,
    ) -> None:
        request_question = ChatQuestion(chat_id=9, question="show sales")

        response = await chat_api.question_answer_inner(
            session=cast(Session, test_db),
            current_user=auth_user,
            request_question=request_question,
            current_assistant=None,
            in_chat=False,
            stream=False,
        )

        assert isinstance(response, JSONResponse)
        assert fake_orchestrator.question_request is not None
        assert fake_orchestrator.question_request.request_question is request_question

    @pytest.mark.asyncio
    async def test_ask_recommend_questions_delegates_to_orchestrator(
        self,
        fake_orchestrator: _FakeOrchestrator,
        monkeypatch: pytest.MonkeyPatch,
        test_db: object,
        auth_user: UserInfoDTO,
    ) -> None:
        record = _FakeChatRecord(11, 5, "recommend something", '{"type":"bar"}')
        monkeypatch.setattr(
            chat_api, "get_chat_record_by_id", lambda session, record_id: record
        )

        response = await chat_api.ask_recommend_questions(
            session=cast(Session, test_db),
            current_user=auth_user,
            chat_record_id=11,
            current_assistant=None,
            articles_number=6,
        )

        assert isinstance(response, StreamingResponse)
        assert fake_orchestrator.recommend_request is not None
        assert fake_orchestrator.recommend_request.record.id == record.id
        assert fake_orchestrator.recommend_request.articles_number == 6
