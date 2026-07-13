import json

from src.document_state import AuditQuery, LifecycleQuery, PageRequest, ReviewQuery, compose_document_state
from src.document_state.persistence import PersistenceConfig
from src.document_state.repositories_in_memory import InMemoryDocumentStateRepositories
from src.document_state.writers.commands import (
    AppendLifecycleEventCommand,
    WriteAuditEventCommand,
    WriteCorrectionSummaryCommand,
    WriteReprocessPlanCommand,
    WriteReviewSummaryCommand,
)
from src.document_state.writers.review_writer import ReviewDocumentStateWriter


NOW = "2026-07-13T09:00:00+00:00"


def _review(*, expected_version=None, status="review_required", updated_at=NOW):
    return WriteReviewSummaryCommand(
        "source-review", "review-001", "doc-001", "invalid_data", "high", status,
        NOW, updated_at, expected_version=expected_version,
    )


def _correction():
    return WriteCorrectionSummaryCommand(
        "source-correction", "correction-001", "review-001", "doc-001",
        "invoice.total", "replace", "invalid_data", "reviewer-001", NOW, "review",
    )


def _reprocess():
    return WriteReprocessPlanCommand(
        "source-reprocess", "plan-001", "review-001", "doc-001", "validate_data",
        "matching", 1, 2, "corrected_data", "reviewer-001", NOW,
    )


def _service(store):
    return ReviewDocumentStateWriter(store.reader, store.writer)


def test_review_summary_create_update_retry_and_conflict_are_safe():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)
    assert service.write_review_summary(_review()).status == "success"
    assert service.write_review_summary(_review()).status == "skipped_idempotent"
    update = _review(expected_version=1, status="corrected", updated_at="2026-07-13T09:01:00+00:00")
    assert service.write_review_summary(update).status == "success"
    assert service.write_review_summary(update).status == "skipped_idempotent"
    stale = _review(expected_version=1, status="approved", updated_at="2026-07-13T09:02:00+00:00")
    assert service.write_review_summary(stale).error_code == "version_conflict"


def test_correction_reprocess_lifecycle_and_audit_are_idempotent():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)
    lifecycle = AppendLifecycleEventCommand("event-review", "source-review", "doc-001", "review_required", NOW, "review_runtime", "review")
    audit = WriteAuditEventCommand("source-audit", "audit-001", "correction_submitted", "reviewer-001", NOW, document_id="doc-001", review_case_id="review-001")

    for _ in range(2):
        assert service.write_correction_summary(_correction()).status == "success"
        assert service.write_reprocess_plan(_reprocess()).status == "success"
        assert service.append_lifecycle_event(lifecycle).status == "success"
        assert service.write_audit_event(audit).status == "success"
    assert store.reader.list_correction_summaries("review-001", PageRequest()).total == 1
    assert store.reader.list_reprocess_plans("review-001", PageRequest()).total == 1
    assert store.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1
    assert store.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1


def test_correction_writer_never_persists_raw_values():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)
    command = _correction()
    object.__setattr__(command, "metadata", {"new_value": "private"})
    result = service.write_correction_summary(command)
    assert result.status == "invalid_input"
    assert "private" not in json.dumps(result.to_dict())
    assert store.reader.list_correction_summaries("review-001", PageRequest()).total == 0


def test_review_writer_maps_unavailable_and_invalid_commands_safely():
    unavailable = InMemoryDocumentStateRepositories(source_available=False)
    failed = _service(unavailable).write_review_summary(_review())
    invalid = _service(InMemoryDocumentStateRepositories()).write_reprocess_plan(object())
    assert failed.error_code == "repository_unavailable"
    assert invalid.status == "invalid_input"


def test_review_writer_accepts_sqlite_injected_ports(tmp_path):
    store = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "review.sqlite3")))
    service = _service(store)
    assert service.write_review_summary(_review()).status == "success"
    assert service.write_correction_summary(_correction()).status == "success"
    assert service.write_reprocess_plan(_reprocess()).status == "success"
    assert store.reader.list_review_references(ReviewQuery(), PageRequest()).total == 1


def test_review_writer_exposes_no_transport_or_backend_methods():
    names = {name for name in dir(ReviewDocumentStateWriter) if not name.startswith("_")}
    assert names == {"append_lifecycle_event", "write_audit_event", "write_correction_summary", "write_reprocess_plan", "write_review_summary"}
