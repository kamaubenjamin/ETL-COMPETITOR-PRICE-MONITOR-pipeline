"""Deterministic full-lifecycle fixtures shared by read-after-write tests."""

from src.document_state.writers import (
    AppendLifecycleEventCommand,
    ArtifactReference,
    CreateDocumentCommand,
    IngestionDocumentStateWriter,
    MatchingSummaryInput,
    ProcessingDocumentStateWriter,
    ReviewDocumentStateWriter,
    ValidationIssueInput,
    WorkflowDocumentStateWriter,
    WriteAuditEventCommand,
    WriteCorrectionSummaryCommand,
    WriteMatchingSummariesCommand,
    WriteProcessingSnapshotCommand,
    WriteReprocessPlanCommand,
    WriteReviewSummaryCommand,
    WriteValidationIssuesCommand,
    WriteWorkflowRunCommand,
)


T0 = "2026-07-13T09:00:00+00:00"
T1 = "2026-07-13T09:01:00+00:00"
T2 = "2026-07-13T09:02:00+00:00"
T3 = "2026-07-13T09:03:00+00:00"
T4 = "2026-07-13T09:04:00+00:00"
T5 = "2026-07-13T09:05:00+00:00"


def write_representative_lifecycle(composition) -> tuple[dict, ...]:
    ingestion = IngestionDocumentStateWriter(composition.reader, composition.writer)
    processing = ProcessingDocumentStateWriter(composition.reader, composition.writer)
    review = ReviewDocumentStateWriter(composition.reader, composition.writer)
    workflow = WorkflowDocumentStateWriter(composition.reader, composition.writer)

    document = CreateDocumentCommand(
        "doc-raw-001",
        "source-received-001",
        "invoice_001.pdf",
        "invoice",
        0.93,
        T0,
        T0,
        "document_engine",
        ArtifactReference("artifact-001", "normalized_document", "document_engine", "a" * 64),
        {"workflow_name": "invoice_processing"},
    )
    received = AppendLifecycleEventCommand(
        "lifecycle-received", "source-received-001", "doc-raw-001", "received", T0,
        "document_engine", "ingestion",
    )
    received_audit = WriteAuditEventCommand(
        "source-audit-received", "audit-received", "ingestion_received", "system", T0,
        document_id="doc-raw-001", metadata={"source_stage": "ingestion"},
    )
    classified = AppendLifecycleEventCommand(
        "lifecycle-classified", "source-classified-001", "doc-raw-001", "classified", T1,
        "document_engine", "classification",
    )
    classification_snapshot = WriteProcessingSnapshotCommand(
        "snapshot-classification", "source-classified-001", "doc-raw-001", "run-001",
        "classification", "succeeded", T0, T1, completed_at=T1, duration_ms=50,
    )
    classified_audit = WriteAuditEventCommand(
        "source-audit-classified", "audit-classified", "ingestion_classified", "system", T1,
        document_id="doc-raw-001", metadata={"source_stage": "classification"},
    )
    validation_snapshot = WriteProcessingSnapshotCommand(
        "snapshot-validation", "source-validation-001", "doc-raw-001", "run-001",
        "validate_data", "succeeded", T1, T2, completed_at=T2, duration_ms=75,
    )
    validation = WriteValidationIssuesCommand(
        "source-validation-001",
        "doc-raw-001",
        "validation-001",
        (
            ValidationIssueInput("issue-002", "warning", "invoice_date", "date_range", "review", "Field requires operator confirmation.", T2),
            ValidationIssueInput("issue-001", "error", "supplier_id", "required_supplier", "required", "Required field is missing.", T2),
        ),
    )
    validation_audit = WriteAuditEventCommand(
        "source-audit-validation", "audit-validation", "validation_completed", "system", T2,
        document_id="doc-raw-001", metadata={"issue_count": 2, "source_stage": "validate_data"},
    )
    matching_snapshot = WriteProcessingSnapshotCommand(
        "snapshot-matching", "source-matching-001", "doc-raw-001", "run-001",
        "matching", "succeeded", T2, T3, completed_at=T3, duration_ms=90,
    )
    matching = WriteMatchingSummariesCommand(
        "source-matching-001",
        "doc-raw-001",
        "matching-001",
        (MatchingSummaryInput("match-001", "supplier", "supplier-100", 0.72, "ambiguous", T3),),
    )
    review_summary = WriteReviewSummaryCommand(
        "source-review-001", "review-001", "doc-raw-001", "matching_ambiguity", "high",
        "review_required", T3, T4, assigned_reviewer_id="reviewer-01", correction_count=1,
        reprocess_state="planned", metadata={"source_stage": "matching"},
    )
    review_lifecycle = AppendLifecycleEventCommand(
        "lifecycle-review", "source-review-001", "doc-raw-001", "review_required", T3,
        "review_runtime", "matching", reason_code="matching_ambiguity",
    )
    correction = WriteCorrectionSummaryCommand(
        "source-correction-001", "correction-001", "review-001", "doc-raw-001",
        "supplier_id", "replace", "operator_verified", "reviewer-01", T4, "matching",
    )
    reprocess = WriteReprocessPlanCommand(
        "source-reprocess-001", "plan-001", "review-001", "doc-raw-001", "matching",
        "validate_data", 1, 2, "operator_verified", "reviewer-01", T4,
    )
    reprocess_audit = WriteAuditEventCommand(
        "source-audit-reprocess", "audit-reprocess", "reprocess_planned", "reviewer-01", T4,
        document_id="doc-raw-001", review_case_id="review-001", metadata={"plan_count": 1, "mode": "dry_run"},
    )
    workflow_run = WriteWorkflowRunCommand(
        "source-workflow-001", "run-001", "invoice_processing", "succeeded", T0, T0, T5,
        completed_at=T5, duration_ms=300000, current_stage="matching", stage_count=3,
        succeeded_stage_count=3,
    )
    workflow_audit = WriteAuditEventCommand(
        "source-audit-workflow", "audit-workflow", "workflow_run_completed", "system", T5,
        document_id="doc-raw-001", workflow_run_id="run-001", metadata={"stage_count": 3},
    )

    results = (
        ingestion.write_ingestion_received(document, received, received_audit),
        ingestion.write_ingestion_classified(classified, classification_snapshot, classified_audit),
        processing.write_processing_snapshot(validation_snapshot),
        processing.write_validation_issues(validation),
        processing.write_audit_event(validation_audit),
        processing.write_processing_snapshot(matching_snapshot),
        processing.write_matching_summaries(matching),
        review.write_review_summary(review_summary),
        review.append_lifecycle_event(review_lifecycle),
        review.write_correction_summary(correction),
        review.write_reprocess_plan(reprocess),
        review.write_audit_event(reprocess_audit),
        workflow.write_workflow_run(workflow_run),
        workflow.write_audit_event(workflow_audit),
    )
    assert all(item.status in {"success", "skipped_idempotent"} for item in results)
    return tuple(item.to_dict() for item in results)
