"""Deterministic document ingestion pipeline.

Composes the existing ingestion modules into a sequential orchestration:
  load → classify → normalize → parse → validate

Side effects (debug artifacts, telemetry) are strictly limited to this
orchestration layer. Individual parsers and validators remain pure.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.document_engine import DocumentIngestionEngine
from src.document_engine.contracts.document import DocumentIngestionResult
from src.document_engine.parsers.document_parser import DocumentParser
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.document_engine.structure.models.validation_result import ValidationResult
from src.document_engine.validation.quality_scorer import score_quality
from src.document_engine.validation.validation_orchestrator import run_validation


@dataclass(frozen=True, slots=True)
class IngestionPipelineResult:
    """Immutable result of a full pipeline run.

    Contains every intermediate artifact for auditability.
    """

    ingestion_result: DocumentIngestionResult
    parsing_result: ParsingResult
    validation_result: ValidationResult
    quality_score: float
    pipeline_run_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "quality_score": self.quality_score,
            "ingestion": self.ingestion_result.to_dict(),
            "parsing": self.parsing_result.to_dict(),
            "validation": self.validation_result.to_dict(),
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)


class IngestionPipeline:
    """Thin orchestration — no business logic, only composition.

    Pipeline stages execute deterministically and sequentially:
      1. Ingest  (load → classify → normalize)
      2. Parse   (block segmentation → section detection → table extraction)
      3. Validate  (structural rules + quality scoring)
      4. Persist debug artifact
      5. Emit telemetry

    Usage::

        pipeline = IngestionPipeline(debug_path="./debug", telemetry=my_telemetry)
        result = pipeline.run("path/to/doc.pdf", source_name="supplier_a")
    """

    def __init__(
        self,
        debug_path: Optional[str] = None,
        telemetry: Optional[Any] = None,
    ):
        self._engine = DocumentIngestionEngine(debug_path=debug_path, telemetry=telemetry)
        self._parser = DocumentParser()
        self._debug_path = Path(debug_path) if debug_path else None

    def run(
        self,
        file_path: str,
        source_name: str,
        source_type: str = "document",
        batch_id: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestionPipelineResult:
        """Execute the full deterministic pipeline for a single document.

        Args:
            file_path: Path to the source document.
            source_name: Logical name of the source (e.g. supplier, feed).
            source_type: Document type hint (passed through to ingestion engine).
            batch_id: Optional batch identifier for telemetry grouping.
            pipeline_run_id: Optional run identifier (auto-generated if omitted).
            metadata: Optional metadata forwarded to the document ingestion engine.

        Returns:
            An ``IngestionPipelineResult`` containing all intermediate artifacts.
        """
        effective_run_id = pipeline_run_id or str(uuid.uuid4())

        # 1. Ingest
        ingestion_result: DocumentIngestionResult = self._engine.ingest(
            file_path=file_path,
            source_name=source_name,
            source_type=source_type,
            batch_id=batch_id,
            pipeline_run_id=effective_run_id,
            metadata=metadata,
        )

        # 2. Parse
        parsing_result: ParsingResult = self._parser.parse(ingestion_result.document.content)

        # 3. Validate
        classification: Dict[str, object] = ingestion_result.classification
        validation_result: ValidationResult = run_validation(
            document=ingestion_result.document,
            parsing_result=parsing_result,
            classification=classification,
        )

        # 4. Quality score (telemetry signal only)
        quality_score: float = score_quality(parsing_result, validation_result, classification)

        pipeline_result = IngestionPipelineResult(
            ingestion_result=ingestion_result,
            parsing_result=parsing_result,
            validation_result=validation_result,
            quality_score=quality_score,
            pipeline_run_id=effective_run_id,
        )

        # 5. Debug artifact (side effect — only at orchestration layer)
        if self._debug_path:
            self._persist_debug_artifact(pipeline_result)

        return pipeline_result

    def _persist_debug_artifact(self, result: IngestionPipelineResult) -> None:
        """Write a complete pipeline debug artifact to disk."""
        self._debug_path.mkdir(parents=True, exist_ok=True)
        artifact_path = self._debug_path / f"pipeline_{result.pipeline_run_id}.json"
        artifact_path.write_text(result.to_json(), encoding="utf-8")