import orjson

from apps.chat.streaming import (
    emit_chat_event,
    emit_finish_event,
    iter_error_events,
)


class TestStreamingContract:
    def test_chat_error_event_uses_shared_sse_contract(self) -> None:
        chunks = list(iter_error_events("boom", in_chat=True))

        assert chunks == ['data:{"type":"error","content":"boom"}\n\n']

    def test_markdown_error_event_uses_non_chat_contract(self) -> None:
        chunks = list(iter_error_events("boom", in_chat=False))

        assert chunks == ["&#x274c; **ERROR:**\n", "> boom\n"]

    def test_finish_event_serializes_terminal_message(self) -> None:
        payload = emit_finish_event().removeprefix("data:").strip()

        assert orjson.loads(payload) == {"type": "finish"}

    def test_generic_chat_event_serializes_payload(self) -> None:
        payload = (
            emit_chat_event(
                "recommended_question_result",
                content='["Q1"]',
                reasoning_content="why",
            )
            .removeprefix("data:")
            .strip()
        )

        assert orjson.loads(payload) == {
            "type": "recommended_question_result",
            "content": '["Q1"]',
            "reasoning_content": "why",
        }
