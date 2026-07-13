from dataclasses import FrozenInstanceError
import json

import pytest

from src.document_state.records import (
    AuditEventRecord,
    CorrectionSummaryRecord,
    DocumentLifecycleEvent,
    DocumentRecord,
    MatchingSummaryRecord,
    ProcessingSnapshot,
    ReprocessPlanRecord,
    ReviewReferenceRecord,
    ValidationIssueRecord,
    WorkflowRunRecord,
)


TS = "2026-07-13T09:00:00+00:00"


def _records():
    return (
        DocumentRecord("doc-001", "invoice.pdf", "invoice", "validated", 0.95, "validate_data", TS, TS, TS, metadata={"correlation_id": "corr-001"}),
        DocumentLifecycleEvent("life-001", "doc-001", "validated", TS, "workflow", "validate_data"),
        ProcessingSnapshot("snap-001", "doc-001", "run-001", "validate_data", "succeeded", TS, TS, completed_at=TS, duration_ms=20),
        ValidationIssueRecord("issue-001", "doc-001", "validation-001", "warning", "invoice_date", "date_format", "invalid_format", "Field format is invalid.", TS),
        MatchingSummaryRecord("match-001", "doc-001", "matching-001", "supplier", "supplier-001", 0.88, "ambiguous", TS),
        ReviewReferenceRecord("review-001", "doc-001", "matching_ambiguity", "high", "in_review", TS, TS, assigned_reviewer_id="reviewer-001"),
        CorrectionSummaryRecord("correction-001", "review-001", "doc-001", "supplier.id", "replace", "wrong_match", "reviewer-001", TS, "matching"),
        ReprocessPlanRecord("plan-001", "review-001", "doc-001", "matching", "validate_data", 2, 1, "corrected_match", "reviewer-001", TS),
        WorkflowRunRecord("run-001", "invoice-workflow", "succeeded", TS, TS, TS, completed_at=TS, duration_ms=100, stage_count=4, succeeded_stage_count=4),
        AuditEventRecord("audit-001", "document_validated", "workflow", TS, document_id="doc-001", workflow_run_id="run-001", metadata={"issue_count": 1}),
    )


def test_all_record_types_are_immutable_json_compatible_and_ordered():
    for record in _records():
        payload = record.to_dict()
        json.dumps(payload)
        assert record.ORDERING.fields
        with pytest.raises(FrozenInstanceError):
            record.metadata = {}


def test_metadata_is_defensively_copied_and_immutable():
    source = {"correlation_id": "corr-001"}
    record = DocumentRecord(
        "doc-001", "invoice.pdf", "invoice", "validated", 0.95,
        "validate_data", TS, TS, TS, metadata=source,
    )
    source["correlation_id"] = "changed"
    assert record.metadata["correlation_id"] == "corr-001"
    with pytest.raises(TypeError):
        record.metadata["correlation_id"] = "changed"


def test_correction_and_read_records_expose_no_raw_values_or_payload_fields():
    serialized = json.dumps([record.to_dict() for record in _records()]).lower()
    for forbidden in (
        "raw_document", "raw_rows", "old_value", "new_value", "artifact_payload",
        "stack_trace", "storage_path", "connection_string",
    ):
        assert forbidden not in serialized
    with pytest.raises(TypeError):
        CorrectionSummaryRecord(
            "correction-002", "review-001", "doc-001", "amount", "replace",
            "wrong_value", "reviewer-001", TS, "validation", old_value="private",
        )


def test_records_reject_invalid_versions_counts_confidence_and_timestamps():
    with pytest.raises(ValueError, match="version"):
        DocumentRecord("doc-001", "a.pdf", "invoice", "received", 0.9, "ingest", TS, TS, TS, version=0)
    with pytest.raises(ValueError, match="confidence"):
        MatchingSummaryRecord("m", "d", "r", "supplier", "c", 1.1, "matched", TS)
    with pytest.raises(ValueError, match="non-negative"):
        ReprocessPlanRecord("p", "r", "d", "a", "b", -1, 0, "reason", "actor", TS)
    with pytest.raises(ValueError, match="UTC"):
        AuditEventRecord("a", "event", "actor", "2026-07-13T12:00:00+03:00")


def test_records_reject_unsafe_metadata_without_echoing_values():
    with pytest.raises(ValueError, match="not allowlisted") as raised:
        AuditEventRecord("audit-002", "event", "actor", TS, metadata={"raw_rows": "private-value"})
    assert "private-value" not in str(raised.value)
