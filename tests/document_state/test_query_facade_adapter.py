import ast
import inspect
from pathlib import Path

import pytest

from src.document_state import (
    AuditEventRecord,
    CorrectionSummaryRecord,
    DocumentQuery as StateDocumentQuery,
    DocumentRecord,
    InMemoryDocumentStateRepositories,
    MatchingSummaryRecord,
    PageRequest as StatePageRequest,
    ProcessingSnapshot,
    ReprocessPlanRecord,
    ReviewReferenceRecord,
    ValidationIssueRecord,
    WorkflowRunRecord,
)
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.workflow_runtime.query_facade import (
    AuditEventQuery,
    AuditEventSummary,
    CorrectionHistorySummary,
    DocumentDetail,
    DocumentInboxItem,
    DocumentQuery,
    MatchingResult,
    PageRequest,
    ProcessingStatus,
    QueryFacadeError,
    ReprocessPlanSummary,
    ReviewCaseQuery,
    ReviewCaseSummary,
    ValidationIssue,
    WorkflowQueryFacadePort,
    WorkflowRunQuery,
    WorkflowRunSummary,
)


TS1 = "2026-07-13T09:00:00+00:00"
TS2 = "2026-07-13T10:00:00+00:00"
SNAPSHOT = "2026-07-13T11:00:00+00:00"


def _records(suffix: str, timestamp: str, *, workflow_status: str = "succeeded") -> dict[str, object]:
    document_id = f"doc-{suffix}"
    review_id = f"review-{suffix}"
    return {
        "document": DocumentRecord(
            document_id, f"invoice-{suffix}.pdf", "invoice", "validated", 0.95,
            "validate_data", timestamp, timestamp, timestamp,
        ),
        "processing": ProcessingSnapshot(
            f"snapshot-{suffix}", document_id, f"run-{suffix}", "validate_data",
            "succeeded", timestamp, timestamp, completed_at=timestamp,
        ),
        "validation": ValidationIssueRecord(
            f"issue-{suffix}", document_id, f"validation-{suffix}", "warning",
            "invoice_date", "date_format", "invalid_format",
            "Field does not satisfy the configured rule.", timestamp,
        ),
        "matching": MatchingSummaryRecord(
            f"match-{suffix}", document_id, f"matching-{suffix}", "supplier",
            f"supplier-{suffix}", 0.70, "unmatched", timestamp,
        ),
        "review": ReviewReferenceRecord(
            review_id, document_id, "matching_ambiguity", "high", "in_review",
            timestamp, timestamp, assigned_reviewer_id="reviewer-001",
            correction_count=1, decision_code="correct", reprocess_state="reprocess_requested",
        ),
        "correction": CorrectionSummaryRecord(
            f"correction-{suffix}", review_id, document_id, "supplier.id", "replace",
            "wrong_match", "reviewer-001", timestamp, "matching",
        ),
        "reprocess": ReprocessPlanRecord(
            f"plan-{suffix}", review_id, document_id, "matching", "validate_data",
            2, 1, "corrected_match", "reviewer-001", timestamp,
        ),
        "workflow": WorkflowRunRecord(
            f"run-{suffix}", "invoice-workflow", workflow_status, timestamp,
            timestamp, timestamp, completed_at=timestamp, duration_ms=100,
            stage_count=4, succeeded_stage_count=4 if workflow_status == "succeeded" else 3,
            failed_stage_count=0 if workflow_status == "succeeded" else 1,
        ),
        "audit": AuditEventRecord(
            f"audit-{suffix}", "review_case_created", "workflow", timestamp,
            document_id=document_id, review_case_id=review_id,
            metadata={"reason_code": "matching_ambiguity", "issue_count": 1, "attempt": 1.5},
        ),
    }


def _populate(store: InMemoryDocumentStateRepositories, records: dict[str, object]) -> None:
    writer = store.writer
    writer.create_document(records["document"])
    writer.create_processing_snapshot(records["processing"])
    writer.append_validation_issue(records["validation"], idempotency_key=f"validation-{records['validation'].issue_id}")
    writer.append_matching_summary(records["matching"], idempotency_key=f"matching-{records['matching'].match_id}")
    writer.create_review_reference(records["review"])
    writer.append_correction_summary(records["correction"], idempotency_key=f"correction-{records['correction'].correction_id}")
    writer.append_reprocess_plan(records["reprocess"], idempotency_key=f"reprocess-{records['reprocess'].plan_id}")
    writer.create_workflow_run(records["workflow"])
    writer.append_audit_event(records["audit"], idempotency_key=f"audit-{records['audit'].event_id}")


@pytest.fixture
def adapter():
    store = InMemoryDocumentStateRepositories()
    _populate(store, _records("002", TS2, workflow_status="cancelled"))
    _populate(store, _records("001", TS1))
    return DocumentStateQueryFacadeAdapter(store.reader, snapshot_at=SNAPSHOT), store


def test_adapter_satisfies_read_only_facade_port(adapter):
    facade, _ = adapter
    assert isinstance(facade, WorkflowQueryFacadePort)
    public_methods = [name for name, value in inspect.getmembers(facade, callable) if not name.startswith("_")]
    assert public_methods
    assert all(name.startswith(("get_", "list_")) for name in public_methods)
    assert not any(name.startswith(("create_", "update_", "append_", "delete_")) for name in public_methods)


def test_adapter_maps_every_supported_record_group(adapter):
    facade, _ = adapter
    assert isinstance(facade.list_documents(DocumentQuery(), PageRequest()).items[0], DocumentInboxItem)
    assert isinstance(facade.get_document("doc-001"), DocumentDetail)
    assert isinstance(facade.list_processing("doc-001", PageRequest()).items[0], ProcessingStatus)
    assert isinstance(facade.list_validation_issues("doc-001", PageRequest()).items[0], ValidationIssue)
    assert isinstance(facade.list_matching_results("doc-001", PageRequest()).items[0], MatchingResult)
    assert facade.list_matching_results("doc-001", PageRequest()).items[0].status == "no_match"
    assert isinstance(facade.list_review_cases(ReviewCaseQuery(), PageRequest()).items[0], ReviewCaseSummary)
    assert facade.get_review_case("review-001").reprocess_state == "requested"
    assert isinstance(facade.list_correction_history("review-001", PageRequest()).items[0], CorrectionHistorySummary)
    assert isinstance(facade.list_reprocess_plans("review-001", PageRequest()).items[0], ReprocessPlanSummary)
    assert isinstance(facade.list_workflow_runs(WorkflowRunQuery(), PageRequest()).items[0], WorkflowRunSummary)
    assert isinstance(facade.list_audit_events(AuditEventQuery(), PageRequest()).items[0], AuditEventSummary)


def test_filters_pagination_and_facade_ordering_are_preserved(adapter):
    facade, _ = adapter
    documents = facade.list_documents(
        DocumentQuery(status="validated", document_type="invoice"), PageRequest(limit=1, offset=0)
    )
    assert documents.total == 2
    assert [item.document_id for item in documents.items] == ["doc-001"]
    assert documents.snapshot_at == SNAPSHOT
    reviews = facade.list_review_cases(
        ReviewCaseQuery(status="in_review", priority="high"), PageRequest()
    )
    assert [item.review_case_id for item in reviews.items] == ["review-001", "review-002"]
    assert [item.plan_id for item in facade.list_reprocess_plans(None, PageRequest()).items] == ["plan-001", "plan-002"]
    failed = facade.list_workflow_runs(WorkflowRunQuery(status="failed"), PageRequest())
    assert [item.run_id for item in failed.items] == ["run-002"]
    assert facade.list_audit_events(AuditEventQuery(event_type="review_case_created"), PageRequest()).total == 2


def test_repository_errors_map_to_safe_facade_errors(adapter):
    facade, _ = adapter
    with pytest.raises(QueryFacadeError) as missing_document:
        facade.get_document("unknown-document")
    assert missing_document.value.code == "not_found"
    assert "unknown-document" not in str(missing_document.value)
    with pytest.raises(QueryFacadeError) as missing_review:
        facade.get_review_case("unknown-review")
    assert missing_review.value.code == "not_found"
    with pytest.raises(QueryFacadeError) as invalid_query:
        facade.list_documents(object(), PageRequest())
    assert invalid_query.value.code == "invalid_query"
    with pytest.raises(QueryFacadeError) as invalid_page:
        facade.list_documents(DocumentQuery(), object())
    assert invalid_page.value.code == "invalid_query"


def test_source_unavailable_maps_safely():
    store = InMemoryDocumentStateRepositories(source_available=False)
    facade = DocumentStateQueryFacadeAdapter(store.reader, snapshot_at=SNAPSHOT)
    with pytest.raises(QueryFacadeError) as raised:
        facade.list_documents(DocumentQuery(), PageRequest())
    assert raised.value.code == "source_unavailable"
    assert raised.value.to_dict()["message"] == "Query source is unavailable."


def test_projection_is_privacy_safe_and_does_not_mutate_repository(adapter):
    facade, store = adapter
    before = store.reader.list_documents(StateDocumentQuery(), StatePageRequest()).items
    payloads = [
        item.to_dict()
        for item in facade.list_audit_events(AuditEventQuery(), PageRequest()).items
    ]
    forbidden = {"raw_document", "raw_rows", "old_value", "new_value", "artifact_payload", "stack_trace", "storage_path"}
    assert not forbidden.intersection(str(payloads).lower())
    assert payloads[0]["metadata"] == {"reason_code": "matching_ambiguity", "issue_count": 1}
    after = store.reader.list_documents(StateDocumentQuery(), StatePageRequest()).items
    assert after == before


def test_adapter_imports_only_approved_public_boundaries():
    import src.document_state.adapters.query_facade_adapter as module

    path = Path(module.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    allowed = {"__future__", "collections", "typing", "src.document_state", "src.workflow_runtime.query_facade"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module]
        else:
            continue
        assert all(any(module == root or module.startswith(f"{root}.") for root in allowed) for module in modules)
