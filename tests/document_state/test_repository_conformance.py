"""Shared behavioral contract for every Document State repository backend."""

from dataclasses import FrozenInstanceError, replace

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
from src.document_state.persistence import PersistenceConfig
from src.document_state.persistence.sqlite import SQLiteDocumentStateRepositories


TS1 = "2026-07-13T09:00:00+00:00"
TS2 = "2026-07-13T10:00:00+00:00"


def records(suffix: str = "001", *, timestamp: str = TS1):
    document_id = f"doc-{suffix}"
    review_id = f"review-{suffix}"
    run_id = f"run-{suffix}"
    return {
        "document": DocumentRecord(document_id, f"invoice-{suffix}.pdf", "invoice", "validated", 0.95, "validate_data", timestamp, timestamp, timestamp, metadata={"source_runtime": "workflow"}),
        "lifecycle": DocumentLifecycleEvent(f"life-{suffix}", document_id, "validated", timestamp, "workflow", "validate_data"),
        "processing": ProcessingSnapshot(f"snap-{suffix}", document_id, run_id, "validate_data", "succeeded", timestamp, timestamp, completed_at=timestamp, duration_ms=20),
        "validation": ValidationIssueRecord(f"issue-{suffix}", document_id, f"validation-{suffix}", "warning", "invoice_date", "date_format", "invalid_format", "Field format is invalid.", timestamp),
        "matching": MatchingSummaryRecord(f"match-{suffix}", document_id, f"matching-{suffix}", "supplier", f"supplier-{suffix}", 0.88, "ambiguous", timestamp),
        "review": ReviewReferenceRecord(review_id, document_id, "matching_ambiguity", "high", "in_review", timestamp, timestamp),
        "correction": CorrectionSummaryRecord(f"correction-{suffix}", review_id, document_id, "supplier.id", "replace", "wrong_match", "reviewer-001", timestamp, "matching"),
        "reprocess": ReprocessPlanRecord(f"plan-{suffix}", review_id, document_id, "matching", "validate_data", 2, 1, "corrected_match", "reviewer-001", timestamp),
        "workflow": WorkflowRunRecord(run_id, "invoice-workflow", "succeeded", timestamp, timestamp, timestamp, completed_at=timestamp, duration_ms=100, stage_count=4, succeeded_stage_count=4),
        "audit": AuditEventRecord(f"audit-{suffix}", "document_validated", "workflow", timestamp, document_id=document_id, review_case_id=review_id, workflow_run_id=run_id),
    }


def populate(store, items):
    writer = store.writer
    writer.create_document(items["document"])
    writer.append_lifecycle_event(items["lifecycle"], idempotency_key=f"idem-{items['lifecycle'].event_id}")
    writer.create_processing_snapshot(items["processing"])
    writer.append_validation_issue(items["validation"], idempotency_key=f"idem-{items['validation'].issue_id}")
    writer.append_matching_summary(items["matching"], idempotency_key=f"idem-{items['matching'].match_id}")
    writer.create_review_reference(items["review"])
    writer.append_correction_summary(items["correction"], idempotency_key=f"idem-{items['correction'].correction_id}")
    writer.append_reprocess_plan(items["reprocess"], idempotency_key=f"idem-{items['reprocess'].plan_id}")
    writer.create_workflow_run(items["workflow"])
    writer.append_audit_event(items["audit"], idempotency_key=f"idem-{items['audit'].event_id}")


@pytest.fixture(params=("in_memory", "sqlite"))
def repository(request, tmp_path):
    if request.param == "in_memory":
        return InMemoryDocumentStateRepositories()
    return SQLiteDocumentStateRepositories(
        PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "conformance.sqlite3"))
    )


def test_create_get_and_list_conformance(repository):
    expected = records()
    populate(repository, expected)
    reader = repository.reader
    assert reader.get_document("doc-001") == expected["document"]
    assert reader.list_documents(DocumentQuery(), PageRequest()).items == (expected["document"],)
    assert reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).items == (expected["lifecycle"],)
    assert reader.get_processing_snapshot("snap-001") == expected["processing"]
    assert reader.list_processing_snapshots("doc-001", ProcessingQuery(), PageRequest()).items == (expected["processing"],)
    assert reader.get_validation_issue("issue-001") == expected["validation"]
    assert reader.list_validation_issues("doc-001", ValidationQuery(), PageRequest()).items == (expected["validation"],)
    assert reader.get_matching_summary("match-001") == expected["matching"]
    assert reader.list_matching_summaries("doc-001", MatchingQuery(), PageRequest()).items == (expected["matching"],)
    assert reader.get_review_reference("review-001") == expected["review"]
    assert reader.list_review_references(ReviewQuery(), PageRequest()).items == (expected["review"],)
    assert reader.get_correction_summary("correction-001") == expected["correction"]
    assert reader.list_correction_summaries("review-001", PageRequest()).items == (expected["correction"],)
    assert reader.get_reprocess_plan("plan-001") == expected["reprocess"]
    assert reader.list_reprocess_plans("review-001", PageRequest()).items == (expected["reprocess"],)
    assert reader.get_workflow_run("run-001") == expected["workflow"]
    assert reader.list_workflow_runs(WorkflowRunQuery(), PageRequest()).items == (expected["workflow"],)
    assert reader.get_audit_event("audit-001") == expected["audit"]
    assert reader.list_audit_events(AuditQuery(), PageRequest()).items == (expected["audit"],)


def test_order_filter_and_bounded_pagination_conformance(repository):
    populate(repository, records("003", timestamp=TS2))
    populate(repository, records("001", timestamp=TS1))
    populate(repository, records("002", timestamp=TS1))
    reader = repository.reader
    first = reader.list_documents(
        DocumentQuery(status="validated", document_type="invoice"),
        PageRequest(limit=2, offset=0),
    )
    second = reader.list_documents(DocumentQuery(), PageRequest(limit=2, offset=2))
    assert first.total == second.total == 3
    assert [item.document_id for item in first.items] == ["doc-001", "doc-002"]
    assert [item.document_id for item in second.items] == ["doc-003"]
    assert reader.list_processing_snapshots("doc-001", ProcessingQuery(status="succeeded", workflow_run_id="run-001"), PageRequest()).total == 1
    assert reader.list_validation_issues("doc-001", ValidationQuery(severity="warning", rule_id="date_format"), PageRequest()).total == 1
    assert reader.list_matching_summaries("doc-001", MatchingQuery(status="ambiguous", entity_type="supplier"), PageRequest()).total == 1
    assert reader.list_review_references(ReviewQuery(status="in_review", priority="high"), PageRequest()).total == 3
    assert reader.list_workflow_runs(WorkflowRunQuery(status="succeeded", workflow_name="invoice-workflow"), PageRequest()).total == 3
    assert reader.list_audit_events(AuditQuery(event_type="document_validated", document_id="doc-001"), PageRequest()).total == 1


def test_compare_and_swap_conformance(repository):
    original = records()["document"]
    repository.writer.create_document(original)
    updated = replace(original, status="approved", updated_at=TS2, version=2)
    assert repository.writer.update_document(updated, expected_version=1) == updated
    with pytest.raises(DocumentStateError) as stale:
        repository.writer.update_document(replace(updated, version=3), expected_version=1)
    assert stale.value.code == "conflict"
    assert repository.reader.get_document(original.document_id) == updated


def test_append_idempotency_and_conflicts_conformance(repository):
    append = repository.writer.append_audit_event
    original = records()["audit"]
    assert append(original, idempotency_key="audit-idem") == original
    assert append(original, idempotency_key="audit-idem") == original
    with pytest.raises(DocumentStateError) as duplicate_id:
        append(original, idempotency_key="different-idem")
    assert duplicate_id.value.code == "conflict"
    with pytest.raises(DocumentStateError) as duplicate_key:
        append(records("002")["audit"], idempotency_key="audit-idem")
    assert duplicate_key.value.code == "conflict"
    assert repository.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1


def test_safe_invalid_duplicate_and_missing_errors_conformance(repository):
    original = records()["document"]
    repository.writer.create_document(original)
    with pytest.raises(DocumentStateError) as duplicate:
        repository.writer.create_document(original)
    assert duplicate.value.code == "conflict"
    with pytest.raises(DocumentStateError) as missing:
        repository.reader.get_document("unknown-document")
    assert missing.value.code == "not_found" and "unknown-document" not in str(missing.value)
    with pytest.raises(DocumentStateError) as invalid_record:
        repository.writer.create_document(object())
    assert invalid_record.value.code == "invalid_record"
    with pytest.raises(DocumentStateError) as invalid_query:
        repository.reader.list_documents(object(), PageRequest())
    assert invalid_query.value.code == "invalid_query"


def test_privacy_validation_and_returned_record_immutability_conformance(repository):
    original = records()["document"]
    stored = repository.writer.create_document(original)
    assert stored == original and stored is not original
    returned = repository.reader.get_document(original.document_id)
    with pytest.raises(FrozenInstanceError):
        returned.status = "failed"
    with pytest.raises(TypeError):
        returned.metadata["source_code"] = "changed"
    assert repository.reader.get_document(original.document_id).metadata == {"source_runtime": "workflow"}

    unsafe = records("002")["document"]
    object.__setattr__(unsafe, "metadata", {"raw_rows": "private"})
    with pytest.raises(DocumentStateError) as rejected:
        repository.writer.create_document(unsafe)
    assert rejected.value.code == "invalid_record" and "private" not in str(rejected.value)
