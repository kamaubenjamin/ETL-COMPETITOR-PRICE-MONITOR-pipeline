from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from src.contracts.telemetry import IngestionLogEvent
from src.document_engine.classifiers.document_classifier import classify_document
from src.document_engine.contracts.document import DocumentIngestionResult, DocumentSource, Document
from src.document_engine.loaders.base import get_loader_for_path
from src.document_engine.normalization.document_normalizer import normalize_document
from src.telemetry.telemetry_manager import telemetry_manager


class DocumentIngestionEngine:
    def __init__(self, *, debug_path: Optional[str] = None, telemetry=None):
        self.debug_path = Path(debug_path) if debug_path else None
        self.telemetry = telemetry or telemetry_manager

    def ingest(
        self,
        file_path: str,
        source_name: str,
        source_type: str = "document",
        batch_id: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentIngestionResult:
        loader = get_loader_for_path(file_path)
        document = loader.load(file_path)
        classification = classify_document(document)
        normalized_document = normalize_document(document)
        ingestion_id = str(uuid.uuid4())

        self._record_telemetry(
            file_path=file_path,
            source_name=source_name,
            source_type=source_type,
            ingestion_id=ingestion_id,
            batch_id=batch_id,
            pipeline_run_id=pipeline_run_id,
            classification=classification,
            metadata=metadata,
        )

        result = DocumentIngestionResult(
            document=document,
            classification=classification,
            normalized_document=normalized_document,
            ingestion_id=ingestion_id,
        )

        if self.debug_path:
            self._persist_debug_artifact(result)

        return result

    def _record_telemetry(
        self,
        file_path: str,
        source_name: str,
        source_type: str,
        ingestion_id: str,
        batch_id: Optional[str],
        pipeline_run_id: Optional[str],
        classification: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        event = IngestionLogEvent(
            pipeline_name=source_type,
            source_name=source_name,
            source_type=source_type,
            status="completed",
            pipeline_run_id=pipeline_run_id,
            batch_id=batch_id,
            records_processed=1,
            metadata={
                "document_path": file_path,
                "classification": classification,
                "document_metadata": metadata or {},
            },
        )
        try:
            self.telemetry.log_ingestion(event)
        except Exception:
            pass

    def _persist_debug_artifact(self, result: DocumentIngestionResult) -> None:
        self.debug_path.mkdir(parents=True, exist_ok=True)
        artifact_path = self.debug_path / f"document_ingestion_{result.ingestion_id}.json"
        artifact_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
