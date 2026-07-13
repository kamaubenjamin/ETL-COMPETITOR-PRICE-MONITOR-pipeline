from src.document_state import MatchingQuery, PageRequest, ProcessingQuery, ValidationQuery, compose_document_state
from src.document_state.errors import DocumentStateError
from src.document_state.persistence import PersistenceConfig
from src.document_state.repositories_in_memory import InMemoryDocumentStateRepositories
from src.document_state.writers.commands import (
    MatchingSummaryInput,
    ValidationIssueInput,
    WriteAuditEventCommand,
    WriteMatchingSummariesCommand,
    WriteProcessingSnapshotCommand,
    WriteValidationIssuesCommand,
)
from src.document_state.writers.processing_writer import ProcessingDocumentStateWriter


NOW = "2026-07-13T09:00:00+00:00"


def _snapshot(*, expected_version=None, status="succeeded", updated_at=NOW):
    return WriteProcessingSnapshotCommand(
        "snapshot-001", "source-001", "doc-001", "run-001", "validate_data",
        status, NOW, updated_at, completed_at=updated_at, expected_version=expected_version,
    )


def _validation():
    return WriteValidationIssuesCommand(
        "source-validation", "doc-001", "validation-001",
        (
            ValidationIssueInput("issue-002", "error", "total", "max", "too_large", "Value exceeds limit.", NOW),
            ValidationIssueInput("issue-001", "warning", "date", "required", "missing", "Required field is missing.", NOW),
        ),
    )


def _matching():
    return WriteMatchingSummariesCommand(
        "source-matching", "doc-001", "matching-001",
        (
            MatchingSummaryInput("match-002", "supplier", "candidate-b", 0.8, "ambiguous", NOW),
            MatchingSummaryInput("match-001", "supplier", "candidate-a", 0.9, "matched", NOW),
        ),
    )


def _service(store):
    return ProcessingDocumentStateWriter(store.reader, store.writer)


def test_validation_and_matching_writes_are_deterministic_and_idempotent():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)

    assert service.write_validation_issues(_validation()).record_ids == ("issue-001", "issue-002")
    assert service.write_validation_issues(_validation()).status == "success"
    assert service.write_matching_summaries(_matching()).record_ids == ("match-001", "match-002")
    assert service.write_matching_summaries(_matching()).status == "success"
    assert store.reader.list_validation_issues("doc-001", ValidationQuery(), PageRequest()).total == 2
    assert store.reader.list_matching_summaries("doc-001", MatchingQuery(), PageRequest()).total == 2


def test_processing_snapshot_expected_version_and_retry_behavior():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)
    assert service.write_processing_snapshot(_snapshot()).status == "success"
    update = _snapshot(expected_version=1, status="failed", updated_at="2026-07-13T09:01:00+00:00")
    assert service.write_processing_snapshot(update).status == "success"
    assert service.write_processing_snapshot(update).status == "skipped_idempotent"

    stale = _snapshot(expected_version=1, updated_at="2026-07-13T09:02:00+00:00")
    result = service.write_processing_snapshot(stale)
    assert (result.status, result.error_code) == ("conflict", "version_conflict")


class _FailSecondValidationOnce:
    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = 0
        self.failed = False

    def append_validation_issue(self, record, *, idempotency_key):
        self.calls += 1
        if self.calls == 2 and not self.failed:
            self.failed = True
            raise DocumentStateError("source_unavailable")
        return self.delegate.append_validation_issue(record, idempotency_key=idempotency_key)

    def __getattr__(self, name):
        return getattr(self.delegate, name)


def test_partial_validation_retry_resumes_without_duplicates():
    store = InMemoryDocumentStateRepositories()
    service = ProcessingDocumentStateWriter(store.reader, _FailSecondValidationOnce(store.writer))

    first = service.write_validation_issues(_validation())
    second = service.write_validation_issues(_validation())
    assert first.record_ids == ("issue-001",)
    assert first.error_code == "repository_unavailable"
    assert second.status == "success"
    assert store.reader.list_validation_issues("doc-001", ValidationQuery(), PageRequest()).total == 2


def test_processing_audit_is_idempotent_and_errors_are_safe():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)
    audit = WriteAuditEventCommand("source-audit", "audit-001", "validation_completed", "system", NOW, document_id="doc-001")
    assert service.write_audit_event(audit).status == "success"
    assert service.write_audit_event(audit).status == "success"
    assert service.write_processing_snapshot(object()).status == "invalid_input"

    unavailable = InMemoryDocumentStateRepositories(source_available=False)
    failed = _service(unavailable).write_validation_issues(_validation())
    assert failed.error_code == "repository_unavailable"
    assert "source-validation" not in failed.message


def test_processing_writer_accepts_sqlite_injected_ports(tmp_path):
    store = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "processing.sqlite3")))
    service = _service(store)
    assert service.write_processing_snapshot(_snapshot()).status == "success"
    assert service.write_validation_issues(_validation()).status == "success"
    assert service.write_matching_summaries(_matching()).status == "success"
    assert store.reader.list_processing_snapshots("doc-001", ProcessingQuery(), PageRequest()).total == 1


def test_batch_commands_reject_duplicate_stable_ids():
    issue = ValidationIssueInput("issue-001", "error", "total", "max", "bad", "Invalid value.", NOW)
    match = MatchingSummaryInput("match-001", "supplier", "candidate-a", 0.8, "matched", NOW)
    for factory, items in (
        (lambda values: WriteValidationIssuesCommand("source", "doc", "validation", values), (issue, issue)),
        (lambda values: WriteMatchingSummariesCommand("source", "doc", "matching", values), (match, match)),
    ):
        try:
            factory(items)
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate stable IDs must be rejected")


def test_processing_writer_exposes_no_transport_or_backend_methods():
    names = {name for name in dir(ProcessingDocumentStateWriter) if not name.startswith("_")}
    assert names == {"append_lifecycle_event", "write_audit_event", "write_matching_summaries", "write_processing_snapshot", "write_validation_issues"}
