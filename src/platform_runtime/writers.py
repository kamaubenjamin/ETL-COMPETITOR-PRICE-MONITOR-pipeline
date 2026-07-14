"""Internal writer-service composition with lifecycle truth injected."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.document_state import DocumentStateComposition
from src.document_state.lifecycle import LifecycleAdvancementService
from src.document_state.writers import (
    IngestionDocumentStateWriter,
    ProcessingDocumentStateWriter,
    ReviewDocumentStateWriter,
    WorkflowDocumentStateWriter,
)


@dataclass(frozen=True, slots=True)
class RuntimeWriterServices:
    """The four internal writer domains sharing one lifecycle service."""

    ingestion: IngestionDocumentStateWriter = field(repr=False)
    processing: ProcessingDocumentStateWriter = field(repr=False)
    review: ReviewDocumentStateWriter = field(repr=False)
    workflow: WorkflowDocumentStateWriter = field(repr=False)


def compose_writer_services(
    document_state: DocumentStateComposition,
    lifecycle: LifecycleAdvancementService,
) -> RuntimeWriterServices:
    """Wire all writers to the same repository surfaces and lifecycle service."""

    if not isinstance(document_state, DocumentStateComposition):
        raise ValueError("document_state must be a DocumentStateComposition")
    if not isinstance(lifecycle, LifecycleAdvancementService):
        raise ValueError("lifecycle must be a LifecycleAdvancementService")
    arguments = (document_state.reader, document_state.writer, lifecycle)
    return RuntimeWriterServices(
        ingestion=IngestionDocumentStateWriter(*arguments),
        processing=ProcessingDocumentStateWriter(*arguments),
        review=ReviewDocumentStateWriter(*arguments),
        workflow=WorkflowDocumentStateWriter(*arguments),
    )
