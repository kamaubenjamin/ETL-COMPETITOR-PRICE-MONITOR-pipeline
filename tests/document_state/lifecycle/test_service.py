import ast
from dataclasses import replace
from pathlib import Path

import pytest

from src.document_state import DocumentLifecycleEvent, DocumentRecord, LifecycleQuery, PageRequest
from src.document_state.errors import DocumentStateError
from src.document_state.lifecycle import (
    LifecycleAdvancementService,
    LifecycleRecoveryPolicy,
    LifecycleTransitionRequest,
)
from src.document_state.persistence import PersistenceConfig
from src.document_state.composition import compose_document_state
from src.document_state.repositories_in_memory import InMemoryDocumentStateRepositories


TS = "2026-07-13T09:00:00+00:00"
LATER = "2026-07-13T09:01:00+00:00"


def document(status="received", *, version=1, stage="ingestion"):
    return DocumentRecord(
        "doc-001",
        "invoice.pdf",
        "invoice",
        status,
        0.95,
        stage,
        TS,
        TS,
        TS,
        version,
        {"correlation_id": "corr-001"},
    )


def request(source="received", target="classified", *, expected=1, recovery=None):
    return LifecycleTransitionRequest(
        "doc-001",
        source,
        target,
        "event-001",
        expected,
        "safe_reason",
        "system",
        LATER,
        source_stage="classification",
        metadata={"correlation_id": "corr-001"},
        recovery_policy=recovery,
    )


def in_memory(status="received", *, version=1):
    repositories = InMemoryDocumentStateRepositories()
    current = repositories.writer.create_document(document(status))
    for next_version in range(2, version + 1):
        current = repositories.writer.update_document(
            replace(current, version=next_version), expected_version=next_version - 1
        )
    return repositories


def test_service_advances_valid_transition_in_memory():
    repositories = in_memory()
    result = LifecycleAdvancementService(repositories.reader, repositories.writer).advance(request())
    updated = repositories.reader.get_document("doc-001")
    assert result.status == "advanced"
    assert result.new_version == 2
    assert (updated.status, updated.current_stage, updated.updated_at, updated.version) == (
        "classified",
        "classification",
        LATER,
        2,
    )
    assert updated.metadata == {"correlation_id": "corr-001"}


def test_service_advances_valid_transition_in_sqlite(tmp_path):
    composed = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "state.sqlite3")))
    composed.writer.create_document(document())
    result = LifecycleAdvancementService(composed.reader, composed.writer).advance(request())
    assert result.status == "advanced"
    assert composed.reader.get_document("doc-001").status == "classified"


def test_same_status_replay_is_no_op_even_with_stale_observed_version():
    repositories = in_memory("classified", version=2)
    result = LifecycleAdvancementService(repositories.reader, repositories.writer).advance(request(expected=1))
    assert result.status == "no_op"
    assert result.new_version is None
    assert repositories.reader.get_document("doc-001").version == 2


@pytest.mark.parametrize(
    ("source", "target"),
    [("matched", "parsed"), ("exported", "approved"), ("failed", "validated")],
)
def test_invalid_terminal_and_unauthorized_recovery_are_rejected(source, target):
    repositories = in_memory(source)
    result = LifecycleAdvancementService(repositories.reader, repositories.writer).advance(request(source, target))
    assert result.status == "rejected"
    assert result.error_code == "invalid_transition"
    assert repositories.reader.get_document("doc-001").status == source


def test_approved_failed_recovery_advances():
    repositories = in_memory("failed")
    recovery = LifecycleRecoveryPolicy("validated", reprocess_plan_id="plan-001")
    result = LifecycleAdvancementService(repositories.reader, repositories.writer).advance(
        request("failed", "validated", recovery=recovery)
    )
    assert result.status == "advanced"
    assert repositories.reader.get_document("doc-001").status == "validated"


def test_missing_document_maps_safely():
    repositories = InMemoryDocumentStateRepositories()
    result = LifecycleAdvancementService(repositories.reader, repositories.writer).advance(request())
    assert result.status == "rejected"
    assert result.error_code == "missing_document"
    assert "invoice" not in str(result.to_dict()).lower()


def test_stale_expected_version_is_conflict_until_event_is_persisted():
    repositories = in_memory(version=2)
    service = LifecycleAdvancementService(repositories.reader, repositories.writer)
    assert service.advance(request(expected=1)).status == "conflict"
    pending = service.advance(request(expected=1), lifecycle_event_persisted=True)
    assert pending.status == "projection_pending"
    assert pending.error_code == "version_conflict"


def test_two_same_version_advancements_cannot_both_succeed():
    repositories = in_memory()
    service = LifecycleAdvancementService(repositories.reader, repositories.writer)
    first = service.advance(request())
    second = service.advance(
        LifecycleTransitionRequest(
            "doc-001",
            "received",
            "failed",
            "event-002",
            1,
            "processing_failed",
            "system",
            LATER,
            source_stage="classification",
        )
    )
    assert first.status == "advanced"
    assert second.status == "conflict"
    assert repositories.reader.get_document("doc-001").status == "classified"


class ConflictWriter:
    def create_document(self, record):
        return record

    def update_document(self, record, *, expected_version):
        raise DocumentStateError("conflict")


def test_repository_update_conflict_maps_safely():
    repositories = in_memory()
    service = LifecycleAdvancementService(repositories.reader, ConflictWriter())
    assert service.advance(request()).status == "conflict"
    assert service.advance(request(), lifecycle_event_persisted=True).status == "projection_pending"


class UnavailableReader:
    def get_document(self, document_id):
        raise DocumentStateError("source_unavailable")

    def list_documents(self, query, page):
        raise DocumentStateError("source_unavailable")


def test_repository_unavailable_maps_without_raw_details():
    repositories = InMemoryDocumentStateRepositories()
    result = LifecycleAdvancementService(UnavailableReader(), repositories.writer).advance(request())
    assert result.status == "failed"
    assert result.error_code == "repository_unavailable"
    assert "source_unavailable" not in str(result.to_dict())


def test_service_does_not_mutate_append_only_lifecycle_event():
    repositories = in_memory()
    event = DocumentLifecycleEvent(
        "event-001", "doc-001", "classified", LATER, "document_engine", "classification"
    )
    repositories.writer.append_lifecycle_event(event, idempotency_key="lifecycle-event-001")
    before = repositories.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).items
    result = LifecycleAdvancementService(repositories.reader, repositories.writer).advance(
        request(), lifecycle_event_persisted=True
    )
    after = repositories.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).items
    assert result.status == "advanced"
    assert before == after == (event,)


def test_source_status_mismatch_is_rejected_without_update():
    repositories = in_memory("ingested")
    result = LifecycleAdvancementService(repositories.reader, repositories.writer).advance(request())
    assert result.status == "rejected"
    assert repositories.reader.get_document("doc-001").version == 1


def test_service_constructor_requires_narrow_repository_ports():
    with pytest.raises(ValueError):
        LifecycleAdvancementService(object(), object())


def test_service_has_no_backend_selection_or_forbidden_imports():
    path = Path("src/document_state/lifecycle/service.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    forbidden = ("src.api", "src.ui", "src.workflow_runtime", "src.document_state.persistence", "src.document_state.writers")
    assert not {name for name in imports if name.startswith(forbidden)}
    assert "compose_document_state" not in source
    assert "sqlite" not in source.lower()
