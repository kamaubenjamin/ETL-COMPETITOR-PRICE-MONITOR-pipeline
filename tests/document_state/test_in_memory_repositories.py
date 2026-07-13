from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import inspect

import pytest

from src.document_state import (
    AuditEventRecord,
    AuditQuery,
    CorrectionSummaryRecord,
    DocumentLifecycleEvent,
    DocumentQuery,
    DocumentRecord,
    InMemoryDocumentStateRepositories,
    MatchingQuery,
    MatchingSummaryRecord,
    PageRequest,
    ProcessingQuery,
    ProcessingSnapshot,
    ReprocessPlanRecord,
    ReviewQuery,
    ReviewReferenceRecord,
    ValidationIssueRecord,
    ValidationQuery,
    WorkflowRunQuery,
    WorkflowRunRecord,
)
from src.document_state.contracts import LifecycleQuery
from src.document_state.errors import DocumentStateError
from src.document_state.repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories


TS1 = "2026-07-13T09:00:00+00:00"
TS2 = "2026-07-13T10:00:00+00:00"


def _records(suffix="001", *, time=TS1):
    document_id = f"doc-{suffix}"
    review_id = f"review-{suffix}"
    run_id = f"run-{suffix}"
    return {
        "document": DocumentRecord(document_id, f"invoice-{suffix}.pdf", "invoice", "validated", 0.95, "validate_data", time, time, time),
        "lifecycle": DocumentLifecycleEvent(f"life-{suffix}", document_id, "validated", time, "workflow", "validate_data"),
        "processing": ProcessingSnapshot(f"snap-{suffix}", document_id, run_id, "validate_data", "succeeded", time, time, completed_at=time, duration_ms=20),
        "validation": ValidationIssueRecord(f"issue-{suffix}", document_id, f"validation-{suffix}", "warning", "invoice_date", "date_format", "invalid_format", "Field format is invalid.", time),
        "matching": MatchingSummaryRecord(f"match-{suffix}", document_id, f"matching-{suffix}", "supplier", f"supplier-{suffix}", 0.88, "ambiguous", time),
        "review": ReviewReferenceRecord(review_id, document_id, "matching_ambiguity", "high", "in_review", time, time),
        "correction": CorrectionSummaryRecord(f"correction-{suffix}", review_id, document_id, "supplier.id", "replace", "wrong_match", "reviewer-001", time, "matching"),
        "reprocess": ReprocessPlanRecord(f"plan-{suffix}", review_id, document_id, "matching", "validate_data", 2, 1, "corrected_match", "reviewer-001", time),
        "workflow": WorkflowRunRecord(run_id, "invoice-workflow", "succeeded", time, time, time, completed_at=time, duration_ms=100, stage_count=4, succeeded_stage_count=4),
        "audit": AuditEventRecord(f"audit-{suffix}", "document_validated", "workflow", time, document_id=document_id, review_case_id=review_id, workflow_run_id=run_id),
    }


def _populate(store, records):
    writer = store.writer
    writer.create_document(records["document"])
    writer.append_lifecycle_event(records["lifecycle"], idempotency_key=f"idem-{records['lifecycle'].event_id}")
    writer.create_processing_snapshot(records["processing"])
    writer.append_validation_issue(records["validation"], idempotency_key=f"idem-{records['validation'].issue_id}")
    writer.append_matching_summary(records["matching"], idempotency_key=f"idem-{records['matching'].match_id}")
    writer.create_review_reference(records["review"])
    writer.append_correction_summary(records["correction"], idempotency_key=f"idem-{records['correction'].correction_id}")
    writer.append_reprocess_plan(records["reprocess"], idempotency_key=f"idem-{records['reprocess'].plan_id}")
    writer.create_workflow_run(records["workflow"])
    writer.append_audit_event(records["audit"], idempotency_key=f"idem-{records['audit'].event_id}")


def test_read_and_write_views_satisfy_separate_structural_protocols():
    store = InMemoryDocumentStateRepositories()
    assert isinstance(store.reader, DocumentStateReadRepositories)
    assert isinstance(store.writer, DocumentStateWriteRepositories)
    assert not isinstance(store.reader, DocumentStateWriteRepositories)
    assert not isinstance(store.writer, DocumentStateReadRepositories)
    assert not any(name.startswith(("create_", "update_", "append_")) for name, _ in inspect.getmembers(store.reader, callable))
    assert not any(name.startswith(("get_", "list_")) for name, _ in inspect.getmembers(store.writer, callable))


def test_create_get_and_list_work_for_every_record_group():
    store = InMemoryDocumentStateRepositories()
    records = _records()
    _populate(store, records)
    reader = store.reader

    assert reader.get_document("doc-001") == records["document"]
    assert reader.list_documents(DocumentQuery(), PageRequest()).items == (records["document"],)
    assert reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).items == (records["lifecycle"],)
    assert reader.get_processing_snapshot("snap-001") == records["processing"]
    assert reader.list_processing_snapshots("doc-001", ProcessingQuery(), PageRequest()).items == (records["processing"],)
    assert reader.get_validation_issue("issue-001") == records["validation"]
    assert reader.list_validation_issues("doc-001", ValidationQuery(), PageRequest()).items == (records["validation"],)
    assert reader.get_matching_summary("match-001") == records["matching"]
    assert reader.list_matching_summaries("doc-001", MatchingQuery(), PageRequest()).items == (records["matching"],)
    assert reader.get_review_reference("review-001") == records["review"]
    assert reader.list_review_references(ReviewQuery(), PageRequest()).items == (records["review"],)
    assert reader.get_correction_summary("correction-001") == records["correction"]
    assert reader.list_correction_summaries("review-001", PageRequest()).items == (records["correction"],)
    assert reader.get_reprocess_plan("plan-001") == records["reprocess"]
    assert reader.list_reprocess_plans("review-001", PageRequest()).items == (records["reprocess"],)
    assert reader.get_workflow_run("run-001") == records["workflow"]
    assert reader.list_workflow_runs(WorkflowRunQuery(), PageRequest()).items == (records["workflow"],)
    assert reader.get_audit_event("audit-001") == records["audit"]
    assert reader.list_audit_events(AuditQuery(), PageRequest()).items == (records["audit"],)


def test_filters_and_pagination_are_deterministic():
    store = InMemoryDocumentStateRepositories()
    first = _records("002", time=TS2)
    second = _records("001", time=TS1)
    _populate(store, first)
    _populate(store, second)
    reader = store.reader

    page = reader.list_documents(DocumentQuery(status="validated", document_type="invoice"), PageRequest(limit=1, offset=0))
    assert page.total == 2
    assert [item.document_id for item in page.items] == ["doc-001"]
    assert [item.document_id for item in reader.list_documents(DocumentQuery(), PageRequest()).items] == ["doc-001", "doc-002"]
    assert reader.list_processing_snapshots("doc-001", ProcessingQuery(status="succeeded", workflow_run_id="run-001"), PageRequest()).total == 1
    assert reader.list_validation_issues("doc-001", ValidationQuery(severity="warning", rule_id="date_format"), PageRequest()).total == 1
    assert reader.list_matching_summaries("doc-001", MatchingQuery(status="ambiguous", entity_type="supplier"), PageRequest()).total == 1
    assert reader.list_review_references(ReviewQuery(status="in_review", priority="high"), PageRequest()).total == 2
    assert reader.list_workflow_runs(WorkflowRunQuery(status="succeeded", workflow_name="invoice-workflow"), PageRequest()).total == 2
    assert reader.list_audit_events(AuditQuery(event_type="document_validated", document_id="doc-001"), PageRequest()).total == 1


@pytest.mark.parametrize(
    ("create_name", "update_name", "record_key", "changed"),
    [
        ("create_document", "update_document", "document", {"status": "approved", "version": 2, "updated_at": TS2}),
        ("create_processing_snapshot", "update_processing_snapshot", "processing", {"status": "failed", "version": 2, "updated_at": TS2}),
        ("create_review_reference", "update_review_reference", "review", {"status": "approved", "version": 2, "updated_at": TS2}),
        ("create_workflow_run", "update_workflow_run", "workflow", {"status": "failed", "version": 2, "updated_at": TS2}),
    ],
)
def test_mutable_snapshots_enforce_expected_version(create_name, update_name, record_key, changed):
    store = InMemoryDocumentStateRepositories()
    original = _records()[record_key]
    getattr(store.writer, create_name)(original)
    updated = replace(original, **changed)
    assert getattr(store.writer, update_name)(updated, expected_version=1) == updated
    with pytest.raises(DocumentStateError) as raised:
        getattr(store.writer, update_name)(replace(updated, version=3), expected_version=1)
    assert raised.value.code == "conflict"


@pytest.mark.parametrize(
    ("method_name", "record_key"),
    [
        ("append_lifecycle_event", "lifecycle"),
        ("append_validation_issue", "validation"),
        ("append_matching_summary", "matching"),
        ("append_correction_summary", "correction"),
        ("append_reprocess_plan", "reprocess"),
        ("append_audit_event", "audit"),
    ],
)
def test_append_operations_are_idempotent_and_conflict_safely(method_name, record_key):
    store = InMemoryDocumentStateRepositories()
    record = _records()[record_key]
    append = getattr(store.writer, method_name)
    first = append(record, idempotency_key="idem-001")
    assert append(record, idempotency_key="idem-001") is first
    with pytest.raises(DocumentStateError) as duplicate_id:
        append(record, idempotency_key="idem-002")
    assert duplicate_id.value.code == "conflict"
    other = _records("002")[record_key]
    with pytest.raises(DocumentStateError) as duplicate_key:
        append(other, idempotency_key="idem-001")
    assert duplicate_key.value.code == "conflict"


def test_duplicate_create_unknown_ids_and_invalid_inputs_use_safe_errors():
    store = InMemoryDocumentStateRepositories()
    record = _records()["document"]
    store.writer.create_document(record)
    with pytest.raises(DocumentStateError) as duplicate:
        store.writer.create_document(record)
    assert duplicate.value.code == "conflict"
    with pytest.raises(DocumentStateError) as missing:
        store.reader.get_document("unknown-document")
    assert missing.value.code == "not_found"
    with pytest.raises(DocumentStateError) as invalid_record:
        store.writer.create_document(object())
    assert invalid_record.value.to_dict()["code"] == "invalid_record"
    with pytest.raises(DocumentStateError) as invalid_query:
        store.reader.list_documents(object(), PageRequest())
    assert invalid_query.value.to_dict()["code"] == "invalid_query"


@pytest.mark.parametrize(
    ("getter", "record_id"),
    [
        ("get_document", "unknown-document"),
        ("get_processing_snapshot", "unknown-snapshot"),
        ("get_validation_issue", "unknown-issue"),
        ("get_matching_summary", "unknown-match"),
        ("get_review_reference", "unknown-review"),
        ("get_correction_summary", "unknown-correction"),
        ("get_reprocess_plan", "unknown-plan"),
        ("get_workflow_run", "unknown-run"),
        ("get_audit_event", "unknown-audit"),
    ],
)
def test_all_getters_return_safe_not_found(getter, record_id):
    reader = InMemoryDocumentStateRepositories().reader
    with pytest.raises(DocumentStateError) as raised:
        getattr(reader, getter)(record_id)
    assert raised.value.to_dict()["code"] == "not_found"
    assert record_id not in str(raised.value)


def test_write_revalidates_records_and_returns_defensive_immutable_instances():
    store = InMemoryDocumentStateRepositories()
    record = _records()["document"]
    stored = store.writer.create_document(record)
    assert stored == record and stored is not record
    object.__setattr__(record, "metadata", {"raw_rows": "private"})
    assert store.reader.get_document("doc-001").metadata == {}
    unsafe_record = _records("002")["document"]
    object.__setattr__(unsafe_record, "metadata", {"raw_rows": "private"})
    with pytest.raises(DocumentStateError) as unsafe:
        store.writer.create_document(unsafe_record)
    assert unsafe.value.code == "invalid_record"
    assert "private" not in str(unsafe.value)


def test_unavailable_source_and_concurrent_idempotent_append_are_safe():
    unavailable = InMemoryDocumentStateRepositories(source_available=False)
    with pytest.raises(DocumentStateError) as read_error:
        unavailable.reader.list_documents(DocumentQuery(), PageRequest())
    assert read_error.value.code == "source_unavailable"
    with pytest.raises(DocumentStateError) as write_error:
        unavailable.writer.create_document(_records()["document"])
    assert write_error.value.code == "source_unavailable"

    store = InMemoryDocumentStateRepositories()
    event = _records()["audit"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.writer.append_audit_event(event, idempotency_key="audit-idem"), range(32)))
    assert all(item == event for item in results)
    assert store.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1


def test_in_memory_module_has_no_forbidden_imports_or_io_surface():
    import src.document_state.repositories_in_memory as module

    source = inspect.getsource(module).lower()
    for forbidden in (
        "fastapi", "streamlit", "workflow_runtime", "review_runtime", "entity_runtime",
        "matching_runtime", "document_engine", "telemetry", "database", "sqlalchemy",
        "sqlite", "requests", "httpx", "flowsync", "competitor", "openai", "ocr",
    ):
        assert forbidden not in source
    assert "open(" not in source
