from dataclasses import replace
import inspect

import pytest

from src.document_state import (
    AuditEventRecord, AuditQuery, CorrectionSummaryRecord, DocumentLifecycleEvent,
    DocumentQuery, DocumentRecord, MatchingQuery, MatchingSummaryRecord, PageRequest,
    ProcessingQuery, ProcessingSnapshot, ReprocessPlanRecord, ReviewQuery,
    ReviewReferenceRecord, ValidationIssueRecord, ValidationQuery, WorkflowRunQuery,
    WorkflowRunRecord,
)
from src.document_state.contracts import LifecycleQuery
from src.document_state.errors import DocumentStateError
from src.document_state.repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
from src.document_state.persistence import PersistenceConfig
from src.document_state.persistence.sqlite import SQLiteDocumentStateRepositories


TS1 = "2026-07-13T09:00:00+00:00"
TS2 = "2026-07-13T10:00:00+00:00"


def _records(suffix="001", *, time=TS1):
    document_id, review_id, run_id = f"doc-{suffix}", f"review-{suffix}", f"run-{suffix}"
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


def _store(tmp_path, name="state.sqlite3"):
    return SQLiteDocumentStateRepositories(
        PersistenceConfig("sqlite", sqlite_path=str(tmp_path / name))
    )


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


def test_views_satisfy_protocols_and_remain_separated(tmp_path):
    store = _store(tmp_path)
    assert isinstance(store.reader, DocumentStateReadRepositories)
    assert isinstance(store.writer, DocumentStateWriteRepositories)
    assert not isinstance(store.reader, DocumentStateWriteRepositories)
    assert not isinstance(store.writer, DocumentStateReadRepositories)
    assert not any(name.startswith(("create_", "update_", "append_")) for name, _ in inspect.getmembers(store.reader, callable))


def test_create_get_list_and_reopen_work_for_all_record_groups(tmp_path):
    records = _records()
    _populate(_store(tmp_path), records)
    reader = _store(tmp_path).reader
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


def test_filters_pagination_and_order_match_in_memory_semantics(tmp_path):
    store = _store(tmp_path)
    _populate(store, _records("002", time=TS2))
    _populate(store, _records("001", time=TS1))
    page = store.reader.list_documents(DocumentQuery(status="validated", document_type="invoice"), PageRequest(limit=1))
    assert page.total == 2 and [item.document_id for item in page.items] == ["doc-001"]
    assert store.reader.list_processing_snapshots("doc-001", ProcessingQuery(status="succeeded", workflow_run_id="run-001"), PageRequest()).total == 1
    assert store.reader.list_validation_issues("doc-001", ValidationQuery(severity="warning", rule_id="date_format"), PageRequest()).total == 1
    assert store.reader.list_matching_summaries("doc-001", MatchingQuery(status="ambiguous", entity_type="supplier"), PageRequest()).total == 1
    assert store.reader.list_review_references(ReviewQuery(status="in_review", priority="high"), PageRequest()).total == 2
    assert store.reader.list_workflow_runs(WorkflowRunQuery(status="succeeded", workflow_name="invoice-workflow"), PageRequest()).total == 2
    assert store.reader.list_audit_events(AuditQuery(event_type="document_validated", document_id="doc-001"), PageRequest()).total == 1


@pytest.mark.parametrize(("create", "update", "key", "changes"), [
    ("create_document", "update_document", "document", {"status": "approved", "version": 2, "updated_at": TS2}),
    ("create_processing_snapshot", "update_processing_snapshot", "processing", {"status": "failed", "version": 2, "updated_at": TS2}),
    ("create_review_reference", "update_review_reference", "review", {"status": "approved", "version": 2, "updated_at": TS2}),
    ("create_workflow_run", "update_workflow_run", "workflow", {"status": "failed", "version": 2, "updated_at": TS2}),
])
def test_mutable_records_use_compare_and_swap(tmp_path, create, update, key, changes):
    store = _store(tmp_path)
    original = _records()[key]
    getattr(store.writer, create)(original)
    changed = replace(original, **changes)
    assert getattr(store.writer, update)(changed, expected_version=1) == changed
    with pytest.raises(DocumentStateError) as raised:
        getattr(store.writer, update)(replace(changed, version=3), expected_version=1)
    assert raised.value.code == "conflict"


@pytest.mark.parametrize(("method", "key"), [
    ("append_lifecycle_event", "lifecycle"), ("append_validation_issue", "validation"),
    ("append_matching_summary", "matching"), ("append_correction_summary", "correction"),
    ("append_reprocess_plan", "reprocess"), ("append_audit_event", "audit"),
])
def test_append_idempotency_and_duplicate_ids_conflict(tmp_path, method, key):
    store = _store(tmp_path)
    append = getattr(store.writer, method)
    record = _records()[key]
    assert append(record, idempotency_key="idem-001") == record
    assert append(record, idempotency_key="idem-001") == record
    with pytest.raises(DocumentStateError) as duplicate_id:
        append(record, idempotency_key="idem-002")
    assert duplicate_id.value.code == "conflict"
    with pytest.raises(DocumentStateError) as duplicate_key:
        append(_records("002")[key], idempotency_key="idem-001")
    assert duplicate_key.value.code == "conflict"


def test_safe_errors_and_privacy_validation_happen_before_persistence(tmp_path):
    store = _store(tmp_path)
    document = _records()["document"]
    store.writer.create_document(document)
    with pytest.raises(DocumentStateError) as duplicate:
        store.writer.create_document(document)
    assert duplicate.value.code == "conflict"
    with pytest.raises(DocumentStateError) as missing:
        store.reader.get_document("unknown-document")
    assert missing.value.code == "not_found" and "unknown-document" not in str(missing.value)
    unsafe = _records("002")["document"]
    object.__setattr__(unsafe, "metadata", {"raw_rows": "private"})
    with pytest.raises(DocumentStateError) as rejected:
        store.writer.create_document(unsafe)
    assert rejected.value.code == "invalid_record" and "private" not in str(rejected.value)
