"""Base stage contract and stage registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult


class BaseStage(ABC):
    """Abstract base for all workflow operations.

    Each stage receives an input artifact (the previous stage's output)
    and an immutable execution context. Returns a typed StageResult.

    Stages are pure functions — no side effects beyond returning a result.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config

    @abstractmethod
    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        """Execute this stage operation.

        Args:
            input_artifact: The output artifact from the previous stage, or None
                for the first stage.
            context: Immutable execution context.

        Returns:
            A StageResult containing the output artifact and execution metadata.
        """
        ...


# Stage type → implementation class mapping.
# v1 uses a simple dict — no plugin system needed for 7 stages.
STAGE_REGISTRY: Dict[str, Type[BaseStage]] = {}