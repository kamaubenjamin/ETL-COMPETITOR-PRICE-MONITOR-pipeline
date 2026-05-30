"""Entity extraction stage for workflow runtime."""

from __future__ import annotations

import time
from typing import Any, Dict

from src.core.execution.status import ExecutionStatus
from src.entity_runtime.engine import EntityExtractionEngine
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class EntityExtractStage(BaseStage):
    """Stage that extracts entities from a completed ingestion pipeline artifact."""

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        entity_types = self._config.get("entity_types")
        extraction_rule = self._config.get("extraction_rule", "entity_runtime_v1")

        start = time.monotonic()
        try:
            engine = EntityExtractionEngine(extraction_rule=extraction_rule)
            entity_set = engine.extract(input_artifact)

            if entity_types:
                filtered_entity_set = self._filter_entity_types(entity_set, entity_types)
            else:
                filtered_entity_set = entity_set

            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="entity_extract",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=filtered_entity_set,
                duration_ms=elapsed_ms,
                metadata={
                    "entity_types": entity_types or ["document_reference", "document_financials", "supplier", "customer", "line_item"],
                    "entity_counts": {
                        "references": len(filtered_entity_set.references),
                        "financials": len(filtered_entity_set.financials),
                        "suppliers": len(filtered_entity_set.suppliers),
                        "customers": len(filtered_entity_set.customers),
                        "line_items": len(filtered_entity_set.line_items),
                    },
                    "extraction_confidence": filtered_entity_set.extraction_confidence,
                },
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="entity_extract",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )

    def _filter_entity_types(self, entity_set: Any, entity_types: Any) -> Any:
        entity_types_set = set(entity_types)
        return EntityExtractionEngine()._filter_entity_set(entity_set, entity_types_set)


STAGE_REGISTRY["entity_extract"] = EntityExtractStage
