from collections.abc import Iterator
from typing import Any

import orjson


def emit_sse_payload(payload: dict[str, object]) -> str:
    return "data:" + orjson.dumps(payload).decode() + "\n\n"


def emit_chat_event(event_type: str, **payload: object) -> str:
    event_payload: dict[str, object] = {"type": event_type}
    event_payload.update(payload)
    return emit_sse_payload(event_payload)


def emit_chat_error(content: str) -> str:
    return emit_chat_event("error", content=content)


def emit_empty_recommended_questions() -> str:
    return emit_chat_event("recommended_question", content="[]")


def emit_finish_event() -> str:
    return emit_chat_event("finish")


def emit_markdown_error(content: str) -> Iterator[str]:
    yield "&#x274c; **ERROR:**\n"
    yield f"> {content}\n"


def iter_error_events(content: str, *, in_chat: bool = True) -> Iterator[str]:
    if in_chat:
        yield emit_chat_error(content)
        return
    yield from emit_markdown_error(content)


def iter_response_chunks(chunks: Iterator[str | dict[str, Any]]) -> dict[str, Any]:
    raw_data: dict[str, Any] = {}
    for chunk in chunks:
        if isinstance(chunk, dict):
            raw_data = chunk
    return raw_data
