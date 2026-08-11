from typing import Any, Protocol


class AnalyzeStage(Protocol):
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]: ...
