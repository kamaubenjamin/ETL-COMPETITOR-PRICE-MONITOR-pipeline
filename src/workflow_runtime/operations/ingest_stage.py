"""Document ingestion stage — wraps the public IngestionPipeline API."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.document_engine.orchestration.ingestion_pipeline import IngestionPipeline
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class IngestStage(BaseStage):
    """Wraps ``IngestionPipeline.run()`` as a workflow stage.

    Stage config:
        - source_name (str): Logical source name.
        - source_type (str): Document type (default: "document").
        - file_path (str): Path to the source document.
        - batch_id (str, optional): Batch identifier.
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        source_name: str = self._config.get("source_name", "unknown")
        source_type: str = self._config.get("source_type", "document")
        file_path: str = self._config.get("file_path", "")

        pipeline = IngestionPipeline(
            debug_path=context.debug_path,
        )

        start = time.monotonic()
        try:
            result = pipeline.run(
                file_path=file_path,
                source_name=source_name,
                source_type=source_type,
                batch_id=self._config.get("batch_id"),
                pipeline_run_id=context.pipeline_run_id,
                metadata={"workspace_id": context.workspace_id},
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="ingest",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=result,
                duration_ms=elapsed_ms,
                metadata={
                    "source_name": source_name,
                    "source_type": source_type,
                    "quality_score": result.quality_score,
                    "ingestion_id": result.ingestion_result.ingestion_id,
                },
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="ingest",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["document_ingest"] = IngestStage