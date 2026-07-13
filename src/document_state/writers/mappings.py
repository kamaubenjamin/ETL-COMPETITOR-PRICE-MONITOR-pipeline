"""Fixed event-to-record mappings for Document State writer adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from ..contracts import DocumentStatus, ProcessingState
from .errors import DocumentStateWriterError


class WriterMappingEvent(str, Enum):
    INGESTION_RECEIVED = "ingestion_received"
    INGESTION_CLASSIFIED = "ingestion_classified"
    PARSING_STRUCTURE_COMPLETED = "parsing_structure_completed"
    VALIDATION_COMPLETED = "validation_completed"
    MATCHING_COMPLETED = "matching_completed"
    REVIEW_REQUIRED = "review_required"
    CORRECTION_SUBMITTED = "correction_submitted"
    REPROCESS_PLANNED = "reprocess_planned"
    WORKFLOW_RUN_COMPLETED = "workflow_run_completed"
    WORKFLOW_RUN_FAILED = "workflow_run_failed"


@dataclass(frozen=True, slots=True)
class WriterMappingDefinition:
    event: str
    record_targets: tuple[str, ...]
    lifecycle_status: str | None = None
    processing_stage: str | None = None
    processing_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "record_targets": list(self.record_targets),
            "lifecycle_status": self.lifecycle_status,
            "processing_stage": self.processing_stage,
            "processing_status": self.processing_status,
        }


def _definition(
    event: WriterMappingEvent,
    targets: tuple[str, ...],
    *,
    lifecycle: DocumentStatus | None = None,
    stage: str | None = None,
    processing: ProcessingState | None = None,
) -> WriterMappingDefinition:
    return WriterMappingDefinition(
        event=event.value,
        record_targets=targets,
        lifecycle_status=lifecycle.value if lifecycle else None,
        processing_stage=stage,
        processing_status=processing.value if processing else None,
    )


WRITER_MAPPING_CATALOG = MappingProxyType(
    {
        WriterMappingEvent.INGESTION_RECEIVED.value: _definition(
            WriterMappingEvent.INGESTION_RECEIVED,
            ("document_record", "lifecycle_event"),
            lifecycle=DocumentStatus.RECEIVED,
        ),
        WriterMappingEvent.INGESTION_CLASSIFIED.value: _definition(
            WriterMappingEvent.INGESTION_CLASSIFIED,
            ("lifecycle_event", "processing_snapshot"),
            lifecycle=DocumentStatus.CLASSIFIED,
            stage="classification",
            processing=ProcessingState.SUCCEEDED,
        ),
        WriterMappingEvent.PARSING_STRUCTURE_COMPLETED.value: _definition(
            WriterMappingEvent.PARSING_STRUCTURE_COMPLETED,
            ("processing_snapshot",),
            stage="parsing_structure",
            processing=ProcessingState.SUCCEEDED,
        ),
        WriterMappingEvent.VALIDATION_COMPLETED.value: _definition(
            WriterMappingEvent.VALIDATION_COMPLETED,
            ("validation_issue_records", "processing_snapshot"),
            stage="validate_data",
            processing=ProcessingState.SUCCEEDED,
        ),
        WriterMappingEvent.MATCHING_COMPLETED.value: _definition(
            WriterMappingEvent.MATCHING_COMPLETED,
            ("matching_summary_records", "processing_snapshot"),
            stage="matching",
            processing=ProcessingState.SUCCEEDED,
        ),
        WriterMappingEvent.REVIEW_REQUIRED.value: _definition(
            WriterMappingEvent.REVIEW_REQUIRED,
            ("review_reference", "lifecycle_event"),
            lifecycle=DocumentStatus.REVIEW_REQUIRED,
        ),
        WriterMappingEvent.CORRECTION_SUBMITTED.value: _definition(
            WriterMappingEvent.CORRECTION_SUBMITTED,
            ("correction_summary", "audit_event"),
        ),
        WriterMappingEvent.REPROCESS_PLANNED.value: _definition(
            WriterMappingEvent.REPROCESS_PLANNED,
            ("reprocess_plan", "lifecycle_event"),
            lifecycle=DocumentStatus.REVIEW_REQUIRED,
        ),
        WriterMappingEvent.WORKFLOW_RUN_COMPLETED.value: _definition(
            WriterMappingEvent.WORKFLOW_RUN_COMPLETED,
            ("workflow_run", "audit_event"),
        ),
        WriterMappingEvent.WORKFLOW_RUN_FAILED.value: _definition(
            WriterMappingEvent.WORKFLOW_RUN_FAILED,
            ("workflow_run", "audit_event"),
        ),
    }
)


def get_writer_mapping(event: WriterMappingEvent | str) -> WriterMappingDefinition:
    key = event.value if isinstance(event, WriterMappingEvent) else event
    try:
        return WRITER_MAPPING_CATALOG[key]
    except (KeyError, TypeError) as exc:
        raise DocumentStateWriterError("invalid_mapping", field="event") from exc
