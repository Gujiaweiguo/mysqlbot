import concurrent.futures
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TypeVar
from typing import Generic

ChunkT = TypeVar("ChunkT")


class ChatTaskRunner(Generic[ChunkT]):
    def __init__(self, executor: ThreadPoolExecutor):
        self._executor = executor
        self._chunks: list[ChunkT] = []
        self._future: Future[None] = Future()
        self._future.set_result(None)

    def is_running(self, timeout: float = 0.5) -> bool:
        try:
            result = concurrent.futures.wait([self._future], timeout)
            return len(result.not_done) > 0
        except Exception:
            return True

    def pop_chunk(self) -> ChunkT | None:
        try:
            return self._chunks.pop(0)
        except IndexError:
            return None

    def await_result(self) -> Iterator[ChunkT]:
        while self.is_running():
            while True:
                chunk = self.pop_chunk()
                if chunk is None:
                    break
                yield chunk

        while True:
            chunk = self.pop_chunk()
            if chunk is None:
                break
            yield chunk

    def run_async(self, target: Callable[..., Iterator[ChunkT]], *args: object) -> None:
        self._future = self._executor.submit(self._run_and_collect, target, *args)

    def _run_and_collect(
        self, target: Callable[..., Iterator[ChunkT]], *args: object
    ) -> None:
        for chunk in target(*args):
            self._chunks.append(chunk)
