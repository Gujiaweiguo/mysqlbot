from typing import Any

from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import and_, select
from sqlmodel import Session, col

from apps.chat.models.chat_model import ChatQuestion, ChatRecord, QuickCommand
from apps.chat.streaming import (
    emit_empty_recommended_questions,
)
from common.utils.command_utils import parse_quick_command

from .runtime import ChatRuntime
from .types import (
    AnalysisRecordRequest,
    AnalysisRequest,
    ChatExecutionRequest,
    QuestionAnswerRequest,
    RecommendQuestionsRequest,
)


class ChatOrchestrator:
    def __init__(self, llm_service_cls: type[Any]):
        self._runtime = ChatRuntime(llm_service_cls)

    async def start_recommend_questions(
        self, request: RecommendQuestionsRequest
    ) -> StreamingResponse:
        try:
            llm_service = await self._runtime.create_service(
                request.session,
                request.current_user,
                request.request_question,
                request.current_assistant,
                embedding=True,
            )
            llm_service.set_record(request.record)
            llm_service.set_articles_number(request.articles_number)
            llm_service.run_recommend_questions_task_async()
        except Exception as exc:
            return self._runtime.error_stream_response(str(exc))

        return self._runtime.stream_response(llm_service)

    async def start_chat(
        self, request: ChatExecutionRequest
    ) -> StreamingResponse | JSONResponse:
        try:
            llm_service = await self._runtime.create_service(
                request.session,
                request.current_user,
                request.request_question,
                request.current_assistant,
                embedding=request.embedding,
            )
            llm_service.init_record(session=request.session)
            llm_service.run_task_async(
                in_chat=request.in_chat,
                stream=request.stream,
                finish_step=request.finish_step,
            )
        except Exception as exc:
            return self._runtime.error_response(
                str(exc),
                stream=request.stream,
                in_chat=request.in_chat,
            )

        return self._runtime.completion_response(llm_service, stream=request.stream)

    def _find_base_question(self, record_id: int, session: Session) -> str:
        stmt = select(
            col(ChatRecord.question), col(ChatRecord.regenerate_record_id)
        ).where(and_(col(ChatRecord.id) == record_id))
        record = session.execute(stmt).fetchone()
        if not record:
            raise Exception("Cannot find base chat record")
        rec_question, rec_regenerate_record_id = record
        base_question = rec_question if rec_question is not None else ""
        if rec_regenerate_record_id:
            return self._find_base_question(rec_regenerate_record_id, session)
        return base_question

    async def answer_question(
        self, request: QuestionAnswerRequest
    ) -> StreamingResponse | JSONResponse:
        command, text_before_command, record_id, warning_info = parse_quick_command(
            request.request_question.question or ""
        )
        _ = warning_info
        if not command:
            return await self.start_chat(
                ChatExecutionRequest(
                    session=request.session,
                    current_user=request.current_user,
                    request_question=request.request_question,
                    current_assistant=request.current_assistant,
                    in_chat=request.in_chat,
                    stream=request.stream,
                    finish_step=request.finish_step,
                    embedding=request.embedding,
                )
            )

        if request.in_chat and command in {
            QuickCommand.ANALYSIS,
            QuickCommand.PREDICT_DATA,
        }:
            raise Exception(f"Command: {command.value} temporary not supported")

        if record_id is not None:
            last_stmt = (
                select(
                    col(ChatRecord.id),
                    col(ChatRecord.chat_id),
                    col(ChatRecord.analysis_record_id),
                    col(ChatRecord.predict_record_id),
                    col(ChatRecord.regenerate_record_id),
                    col(ChatRecord.first_chat),
                )
                .where(and_(col(ChatRecord.id) == record_id))
                .order_by(col(ChatRecord.create_time).desc())
            )
            record = request.session.execute(last_stmt).fetchone()
            if not record:
                raise Exception(f"Record id: {record_id} does not exist")

            (
                rec_id,
                rec_chat_id,
                rec_analysis_record_id,
                rec_predict_record_id,
                rec_regenerate_record_id,
                rec_first_chat,
            ) = record

            if rec_chat_id != request.request_question.chat_id:
                raise Exception(f"Record id: {record_id} does not belong to this chat")
            if rec_first_chat:
                raise Exception(
                    f"Record id: {record_id} does not support this operation"
                )
            if rec_analysis_record_id:
                raise Exception("Analysis record does not support this operation")
            if rec_predict_record_id:
                raise Exception("Predict data record does not support this operation")
        else:
            stmt = (
                select(
                    col(ChatRecord.id),
                    col(ChatRecord.chat_id),
                    col(ChatRecord.regenerate_record_id),
                )
                .where(
                    and_(
                        col(ChatRecord.chat_id) == request.request_question.chat_id,
                        col(ChatRecord.first_chat).is_(False),
                        col(ChatRecord.analysis_record_id).is_(None),
                        col(ChatRecord.predict_record_id).is_(None),
                    )
                )
                .order_by(col(ChatRecord.create_time).desc())
                .limit(1)
            )
            record = request.session.execute(stmt).fetchone()
            if not record:
                raise Exception("You have not ask any question")
            rec_id, _rec_chat_id, rec_regenerate_record_id = record

        if not rec_regenerate_record_id:
            rec_regenerate_record_id = rec_id

        base_question_text = self._find_base_question(
            rec_regenerate_record_id, request.session
        )
        combined_question = text_before_command + (
            ("\n" if text_before_command else "") + base_question_text
        )

        if command == QuickCommand.REGENERATE:
            request.request_question.question = combined_question
            request.request_question.regenerate_record_id = rec_id
            return await self.start_chat(
                ChatExecutionRequest(
                    session=request.session,
                    current_user=request.current_user,
                    request_question=request.request_question,
                    current_assistant=request.current_assistant,
                    in_chat=request.in_chat,
                    stream=request.stream,
                    finish_step=request.finish_step,
                    embedding=request.embedding,
                )
            )

        if command == QuickCommand.ANALYSIS:
            return await self.start_analysis_or_predict_by_record(
                AnalysisRecordRequest(
                    session=request.session,
                    current_user=request.current_user,
                    chat_record_id=rec_id,
                    action_type="analysis",
                    current_assistant=request.current_assistant,
                    in_chat=request.in_chat,
                    stream=request.stream,
                )
            )

        if command == QuickCommand.PREDICT_DATA:
            return await self.start_analysis_or_predict_by_record(
                AnalysisRecordRequest(
                    session=request.session,
                    current_user=request.current_user,
                    chat_record_id=rec_id,
                    action_type="predict",
                    current_assistant=request.current_assistant,
                    in_chat=request.in_chat,
                    stream=request.stream,
                )
            )

        raise Exception(f"Unknown command: {command.value}")

    async def start_analysis_or_predict(
        self, request: AnalysisRequest
    ) -> StreamingResponse | JSONResponse:
        try:
            llm_service = await self._runtime.create_service(
                request.session,
                request.current_user,
                request.request_question,
                request.current_assistant,
            )
            llm_service.run_analysis_or_predict_task_async(
                request.session,
                request.action_type,
                request.chat_record,
                request.in_chat,
                request.stream,
            )
        except Exception as exc:
            return self._runtime.error_response(
                str(exc),
                stream=request.stream,
                in_chat=request.in_chat,
            )

        return self._runtime.completion_response(llm_service, stream=request.stream)

    async def start_analysis_or_predict_by_record(
        self, request: AnalysisRecordRequest
    ) -> StreamingResponse | JSONResponse:
        if request.action_type not in {"analysis", "predict"}:
            raise Exception(f"Type {request.action_type} Not Found")

        record = request.session.get(ChatRecord, request.chat_record_id)
        if not record:
            raise Exception(f"Chat record with id {request.chat_record_id} not found")
        if not record.chart:
            raise Exception(
                f"Chat record with id {request.chat_record_id} has not generated chart, do not support to analyze it"
            )

        return await self.start_analysis_or_predict(
            AnalysisRequest(
                session=request.session,
                current_user=request.current_user,
                request_question=ChatQuestion(
                    chat_id=record.chat_id, question=record.question
                ),
                chat_record=record,
                action_type=request.action_type,
                current_assistant=request.current_assistant,
                in_chat=request.in_chat,
                stream=request.stream,
            )
        )


def empty_recommended_questions_response() -> StreamingResponse:
    return StreamingResponse(
        iter([emit_empty_recommended_questions()]), media_type="text/event-stream"
    )
