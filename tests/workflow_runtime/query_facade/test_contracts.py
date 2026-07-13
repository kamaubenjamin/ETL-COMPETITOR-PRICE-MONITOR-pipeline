from dataclasses import FrozenInstanceError

import pytest

from src.workflow_runtime.query_facade.contracts import (
    AuditEventQuery,
    DocumentQuery,
    OrderingSpec,
    ReviewCaseQuery,
    SortDirection,
    WorkflowRunQuery,
)
from src.workflow_runtime.query_facade.errors import QueryErrorCode, QueryFacadeError


def test_filters_validate_known_values_and_serialize():
    assert DocumentQuery(status="validated", document_type="invoice").to_dict() == {
        "status": "validated", "document_type": "invoice"
    }
    assert ReviewCaseQuery(status="in_review", priority="high").to_dict() == {
        "status": "in_review", "priority": "high"
    }
    assert WorkflowRunQuery(status="running", workflow_name="invoice_processing").to_dict() == {
        "status": "running", "workflow_name": "invoice_processing"
    }
    assert AuditEventQuery(event_type="review_case_created").to_dict() == {
        "event_type": "review_case_created"
    }


@pytest.mark.parametrize(
    ("factory", "value"),
    [
        (lambda value: DocumentQuery(status=value), "private_status"),
        (lambda value: DocumentQuery(document_type=value), "unknown_type"),
        (lambda value: ReviewCaseQuery(status=value), "unknown_review"),
        (lambda value: ReviewCaseQuery(priority=value), "highest"),
        (lambda value: WorkflowRunQuery(status=value), "completed"),
        (lambda value: AuditEventQuery(event_type=value), "raw_payload_stored"),
    ],
)
def test_filters_reject_unknown_values(factory, value):
    with pytest.raises(ValueError, match="invalid"):
        factory(value)


def test_contracts_are_immutable():
    query = DocumentQuery(status="validated")
    with pytest.raises(FrozenInstanceError):
        query.status = "failed"


def test_ordering_spec_is_deterministic_and_aligned():
    ordering = OrderingSpec(("created_at", "record_id"), ("desc", "asc"))
    assert ordering.to_dict() == {
        "fields": ["created_at", "record_id"],
        "directions": ["desc", "asc"],
    }
    assert ordering.directions == (SortDirection.DESCENDING, SortDirection.ASCENDING)
    with pytest.raises(ValueError):
        OrderingSpec(("record_id",), ("asc", "desc"))


@pytest.mark.parametrize("code", list(QueryErrorCode))
def test_facade_errors_have_stable_safe_messages(code):
    error = QueryFacadeError(code, field="status")
    assert error.to_dict()["code"] == code.value
    assert error.to_dict()["field"] == "status"
    assert "payload" not in error.message.lower()
    assert "traceback" not in error.message.lower()


def test_facade_error_rejects_unknown_codes_and_unbounded_fields():
    with pytest.raises(ValueError, match="unsupported"):
        QueryFacadeError("database_exception")
    with pytest.raises(ValueError, match="bounded"):
        QueryFacadeError("invalid_query", field="x" * 65)
