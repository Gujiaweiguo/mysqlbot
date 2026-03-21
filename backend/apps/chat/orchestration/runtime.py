from typing import Any, cast

from fastapi.responses import JSONResponse, StreamingResponse

from apps.chat.streaming import iter_error_events, iter_response_chunks


class ChatRuntime:
    def __init__(self, llm_service_cls: type[Any]):
        self._llm_service_cls = llm_service_cls

    async def create_service(
        self,
        session: Any,
        current_user: Any,
        request_question: Any,
        current_assistant: Any,
        *,
        embedding: bool = False,
    ) -> Any:
        return await cast(Any, self._llm_service_cls).create(
            session,
            current_user,
            request_question,
            current_assistant,
            embedding=embedding,
        )

    @staticmethod
    def error_stream_response(
        message: str, *, in_chat: bool = True
    ) -> StreamingResponse:
        return StreamingResponse(
            iter_error_events(message, in_chat=in_chat),
            media_type="text/event-stream",
        )

    @staticmethod
    def stream_response(llm_service: Any) -> StreamingResponse:
        return StreamingResponse(
            llm_service.await_result(), media_type="text/event-stream"
        )

    @staticmethod
    def error_response(
        message: str, *, stream: bool, in_chat: bool = True
    ) -> StreamingResponse | JSONResponse:
        if stream:
            return ChatRuntime.error_stream_response(message, in_chat=in_chat)
        return JSONResponse(content={"message": message}, status_code=500)

    @staticmethod
    def completion_response(
        llm_service: Any, *, stream: bool
    ) -> StreamingResponse | JSONResponse:
        if stream:
            return ChatRuntime.stream_response(llm_service)

        raw_data = iter_response_chunks(llm_service.await_result())
        status_code = 200 if raw_data.get("success") else 500
        return JSONResponse(content=raw_data, status_code=status_code)
