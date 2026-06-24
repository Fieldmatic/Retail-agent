from collections.abc import Iterator
from typing import Protocol


class AnswerGraph(Protocol):
    def stream(
        self,
        input: dict[str, str],
        *,
        stream_mode: list[str],
    ) -> Iterator[tuple[str, object]]: ...
