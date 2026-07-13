"""Deterministic lifecycle advancement fixtures for approved read-path tests."""

from src.document_state.lifecycle import LifecycleAdvancementService
from src.document_state.writers import (
    AppendLifecycleEventCommand,
    CreateDocumentCommand,
    IngestionDocumentStateWriter,
    ProcessingDocumentStateWriter,
    ReviewDocumentStateWriter,
    WorkflowDocumentStateWriter,
    WriteWorkflowRunCommand,
)

from tests.document_state.writers.read_after_write_fixtures import (
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    write_representative_lifecycle,
)


SNAPSHOT_AT = "2026-07-13T09:10:00+00:00"


def _event(event_id: str, source_event_id: str, document_id: str, status: str, occurred_at: str, stage: str):
    return AppendLifecycleEventCommand(
        event_id,
        source_event_id,
        document_id,
        status,
        occurred_at,
        "integration_test",
        stage,
        f"{status}_completed",
    )


def write_advanced_lifecycle(composition) -> None:
    """Write representative state, then advance two projections through injected services."""

    write_representative_lifecycle(composition)
    service = LifecycleAdvancementService(composition.reader, composition.writer)
    ingestion = IngestionDocumentStateWriter(composition.reader, composition.writer, service)
    processing = ProcessingDocumentStateWriter(composition.reader, composition.writer, service)
    review = ReviewDocumentStateWriter(composition.reader, composition.writer, service)
    workflow = WorkflowDocumentStateWriter(composition.reader, composition.writer, service)

    commands = (
        (
            ingestion,
            AppendLifecycleEventCommand(
                "lifecycle-received",
                "source-received-001",
                "doc-raw-001",
                "received",
                T0,
                "document_engine",
                "ingestion",
            ),
        ),
        (
            ingestion,
            AppendLifecycleEventCommand(
                "lifecycle-classified",
                "source-classified-001",
                "doc-raw-001",
                "classified",
                T1,
                "document_engine",
                "classification",
            ),
        ),
        (processing, _event("lifecycle-parsed", "source-parsed-001", "doc-raw-001", "parsed", "2026-07-13T09:01:10+00:00", "parsing_structure")),
        (processing, _event("lifecycle-validated", "source-validated-001", "doc-raw-001", "validated", T2, "validate_data")),
        (processing, _event("lifecycle-matched", "source-matched-001", "doc-raw-001", "matched", T3, "matching")),
        (
            review,
            AppendLifecycleEventCommand(
                "lifecycle-review",
                "source-review-001",
                "doc-raw-001",
                "review_required",
                T3,
                "review_runtime",
                "matching",
                "matching_ambiguity",
            ),
        ),
        (review, _event("lifecycle-approved", "source-approved-001", "doc-raw-001", "approved", T4, "review")),
        (workflow, _event("lifecycle-exported", "source-exported-001", "doc-raw-001", "exported", T5, "export")),
    )
    results = tuple(writer.append_lifecycle_event(command) for writer, command in commands)
    actual = [(item.status, item.error_code) for item in results]
    assert actual == [("success", None)] * len(commands), actual

    failed_document = CreateDocumentCommand(
        "doc-failed-002",
        "source-failed-received-002",
        "receipt_002.pdf",
        "receipt",
        0.81,
        T0,
        T0,
        "document_engine",
    )
    assert ingestion.create_document(failed_document).status == "success"
    assert ingestion.append_lifecycle_event(
        _event(
            "lifecycle-failed-received",
            "source-failed-received-002",
            "doc-failed-002",
            "received",
            T0,
            "ingestion",
        )
    ).status == "success"
    assert workflow.append_lifecycle_event(
        _event(
            "lifecycle-failed",
            "source-failed-002",
            "doc-failed-002",
            "failed",
            T1,
            "workflow",
        )
    ).status == "success"
    failed_run = WriteWorkflowRunCommand(
        "source-run-failed-002",
        "run-failed-002",
        "receipt_processing",
        "failed",
        T0,
        T0,
        T1,
        completed_at=T1,
        duration_ms=60000,
        current_stage="workflow",
        stage_count=1,
        failed_stage_count=1,
    )
    assert workflow.write_workflow_run(failed_run).status == "success"
