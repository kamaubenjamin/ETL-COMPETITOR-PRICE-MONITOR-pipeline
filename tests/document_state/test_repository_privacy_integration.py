from dataclasses import FrozenInstanceError, replace

import pytest

from src.document_state import (
    AuditEventRecord,
    AuditQuery,
    CorrectionSummaryRecord,
    DocumentQuery,
    DocumentRecord,
    DocumentStateError,
    InMemoryDocumentStateRepositories,
    PageRequest,
    ReviewReferenceRecord,
)
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.workflow_runtime.query_facade import AuditEventQuery, PageRequest as FacadePageRequest


TS = "2026-07-13T09:00:00+00:00"
SNAPSHOT = "2026-07-13T11:00:00+00:00"


def _document(**changes):
    values = {
        "document_id": "doc-001",
        "filename": "invoice.pdf",
        "document_type": "invoice",
        "status": "validated",
        "confidence": 0.95,
        "current_stage": "validate_data",
        "received_at": TS,
        "created_at": TS,
        "updated_at": TS,
    }
    values.update(changes)
    return DocumentRecord(**values)


@pytest.mark.parametrize(
    "unsafe_key",
    [
        "raw_document", "raw_rows", "old_value", "new_value", "artifact_payload",
        "stack_trace", "storage_path", "document_content",
    ],
)
def test_records_reject_raw_payload_like_metadata(unsafe_key):
    with pytest.raises(ValueError) as raised:
        _document(metadata={unsafe_key: "sensitive-value"})
    assert "sensitive-value" not in str(raised.value)


def test_repository_revalidates_tampered_records_and_returns_immutable_state():
    store = InMemoryDocumentStateRepositories()
    unsafe = _document()
    object.__setattr__(unsafe, "metadata", {"raw_rows": "sensitive-value"})
    with pytest.raises(DocumentStateError) as raised:
        store.writer.create_document(unsafe)
    assert raised.value.code == "invalid_record"
    assert "sensitive-value" not in str(raised.value)

    store.writer.create_document(_document())
    returned = store.reader.get_document("doc-001")
    with pytest.raises(FrozenInstanceError):
        returned.status = "failed"
    with pytest.raises(TypeError):
        returned.metadata["status"] = "failed"
    assert store.reader.get_document("doc-001").status == "validated"


def test_adapter_projection_removes_non_facade_audit_metadata_and_raw_values_are_absent():
    store = InMemoryDocumentStateRepositories()
    writer = store.writer
    writer.create_document(_document())
    writer.create_review_reference(
        ReviewReferenceRecord(
            "review-001", "doc-001", "invalid_data", "high", "in_review", TS, TS,
            correction_count=1,
        )
    )
    writer.append_correction_summary(
        CorrectionSummaryRecord(
            "correction-001", "review-001", "doc-001", "supplier.id", "replace",
            "invalid_reference", "reviewer-001", TS, "matching",
        ),
        idempotency_key="correction-idempotency-001",
    )
    writer.append_audit_event(
        AuditEventRecord(
            "audit-001", "review_case_created", "workflow", TS,
            document_id="doc-001", review_case_id="review-001",
            metadata={"reason_code": "invalid_data", "issue_count": 1, "attempt": 1.5},
        ),
        idempotency_key="audit-idempotency-001",
    )
    adapter = DocumentStateQueryFacadeAdapter(store.reader, snapshot_at=SNAPSHOT)

    correction = adapter.list_correction_history("review-001", FacadePageRequest()).items[0].to_dict()
    audit = adapter.list_audit_events(AuditEventQuery(), FacadePageRequest()).items[0].to_dict()
    serialized = str((correction, audit)).lower()
    for forbidden in (
        "raw_document", "raw_rows", "old_value", "new_value", "artifact_payload",
        "stack_trace", "storage_path", "sensitive-value",
    ):
        assert forbidden not in serialized
    assert audit["metadata"] == {"reason_code": "invalid_data", "issue_count": 1}


def test_version_and_idempotency_conflicts_are_safe_and_leave_state_unchanged():
    store = InMemoryDocumentStateRepositories()
    original = store.writer.create_document(_document())
    update = replace(original, status="approved", version=2)
    with pytest.raises(DocumentStateError) as version_error:
        store.writer.update_document(update, expected_version=2)
    assert version_error.value.code == "conflict"
    assert store.reader.get_document("doc-001") == original

    event = AuditEventRecord("audit-001", "document_received", "workflow", TS, document_id="doc-001")
    store.writer.append_audit_event(event, idempotency_key="private-idempotency-key")
    conflicting = AuditEventRecord("audit-002", "document_received", "workflow", TS, document_id="doc-001")
    with pytest.raises(DocumentStateError) as idempotency_error:
        store.writer.append_audit_event(conflicting, idempotency_key="private-idempotency-key")
    assert idempotency_error.value.code == "conflict"
    assert "private-idempotency-key" not in str(idempotency_error.value)
    assert store.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1
    assert store.reader.list_documents(DocumentQuery(), PageRequest()).total == 1
