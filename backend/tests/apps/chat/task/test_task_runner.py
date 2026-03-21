from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator

from apps.chat.task.runner import ChatTaskRunner


def _stream_values() -> Iterator[str]:
    yield "a"
    yield "b"
    yield "c"


class TestChatTaskRunner:
    def test_run_async_collects_chunks_in_order(self) -> None:
        with ThreadPoolExecutor(max_workers=1) as executor:
            runner = ChatTaskRunner[str](executor)
            runner.run_async(_stream_values)

            assert list(runner.await_result()) == ["a", "b", "c"]

    def test_pop_chunk_returns_none_when_empty(self) -> None:
        with ThreadPoolExecutor(max_workers=1) as executor:
            runner = ChatTaskRunner[str](executor)

            assert runner.pop_chunk() is None
