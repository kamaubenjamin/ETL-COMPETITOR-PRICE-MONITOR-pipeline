from dataclasses import FrozenInstanceError

import pytest

from src.document_state.contracts import (
    AuditQuery,
    DETERMINISTIC_ORDERING,
    DocumentQuery,
    DocumentStatus,
    DocumentType,
    MatchingQuery,
    ProcessingQuery,
    ReviewQuery,
    ValidationQuery,
    WorkflowRunQuery,
    query_to_dict,
)
from src.document_state.errors import DocumentStateError, DocumentStateErrorCode


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (DocumentQuery(status="validated", document_type="invoice"), {"status": "validated", "document_type": "invoice"}),
        (ProcessingQuery(status="running", workflow_run_id="run-001"), {"status": "running", "workflow_run_id": "run-001"}),
        (ValidationQuery(severity="error", rule_id="required"), {"severity": "error", "rule_id": "required"}),
        (MatchingQuery(status="ambiguous", entity_type="supplier"), {"status": "ambiguous", "entity_type": "supplier"}),
        (ReviewQuery(status="in_review", priority="high"), {"status": "in_review", "priority": "high"}),
        (WorkflowRunQuery(status="succeeded", workflow_name="invoice-flow"), {"status": "succeeded", "workflow_name": "invoice-flow"}),
        (AuditQuery(event_type="document_received", document_id="doc-001"), {"event_type": "document_received", "document_id": "doc-001", "review_case_id": None}),
    ],
)
def test_query_contracts_normalize_to_safe_json_values(query, expected):
    assert query_to_dict(query) == expected


def test_query_contracts_are_immutable_and_reject_unknown_values():
    query = DocumentQuery(DocumentStatus.VALIDATED, DocumentType.INVOICE)
    with pytest.raises(FrozenInstanceError):
        query.status = "failed"
    with pytest.raises(ValueError, match="status is invalid"):
        DocumentQuery(status="private-status")


def test_every_record_type_declares_deterministic_ordering_with_tie_breaker():
    assert set(DETERMINISTIC_ORDERING) == {
        "audit_event", "correction_summary", "document", "lifecycle_event",
        "matching_summary", "processing_snapshot", "reprocess_plan",
        "review_reference", "validation_issue", "workflow_run",
    }
    for ordering in DETERMINISTIC_ORDERING.values():
        assert ordering.fields
        assert ordering.fields[-1].endswith("id")
        assert len(ordering.fields) == len(ordering.directions)
        assert set(ordering.directions) <= {"asc", "desc"}


@pytest.mark.parametrize("code", list(DocumentStateErrorCode))
def test_repository_errors_have_fixed_privacy_safe_messages(code):
    error = DocumentStateError(code, field="status")
    assert error.to_dict() == {"code": code.value, "message": error.message, "field": "status"}
    assert code.value in {item.value for item in DocumentStateErrorCode}
    assert "payload" not in str(error).lower()
    assert "traceback" not in str(error).lower()


def test_repository_errors_reject_arbitrary_codes_and_unbounded_fields():
    with pytest.raises(ValueError, match="unsupported"):
        DocumentStateError("database_exception")
    with pytest.raises(ValueError, match="bounded"):
        DocumentStateError("invalid_query", field="x" * 65)
