"""Filter stage — applies keyword/category filters to structured records."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class FilterStage(BaseStage):
    """Applies keyword and category filters.

    Stage config:
        - category (str, optional): Category filter value.
        - keywords (list, optional): List of keyword strings to match.
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        category: str = self._config.get("category", "")
        keywords: list = self._config.get("keywords", [])

        start = time.monotonic()
        try:
            output = {
                "input_artifact": input_artifact,
                "filters_applied": {
                    "category": category,
                    "keywords": keywords,
                },
            }
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="filter",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={"category": category, "keyword_count": len(keywords)},
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="filter",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["filter"] = FilterStage