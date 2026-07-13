import json

from src.document_state import (
    AuditQuery,
    DocumentQuery,
    LifecycleQuery,
    PageRequest,
    ProcessingQuery,
    compose_document_state,
)
from src.document_state.errors import DocumentStateError
from src.document_state.persistence import PersistenceConfig
from src.document_state.repositories_in_memory import InMemoryDocumentStateRepositories
from src.document_state.writers.commands import (
    AppendLifecycleEventCommand,
    ArtifactReference,
    CreateDocumentCommand,
    WriteAuditEventCommand,
    WriteProcessingSnapshotCommand,
)
from src.document_state.writers.ingestion_writer import IngestionDocumentStateWriter


NOW = "2026-07-13T09:00:00+00:00"
LATER = "2026-07-13T09:01:00+00:00"


def _document(*, filename="invoice.pdf", metadata=None):
    return CreateDocumentCommand(
        "doc-001",
        "source-received-001",
        filename,
        "invoice",
        0.95,
        NOW,
        NOW,
        "document_engine",
        ArtifactReference("artifact-001", "normalized_document", "document_engine", "a" * 64),
        metadata or {},
    )


def _lifecycle(status="received"):
    return AppendLifecycleEventCommand(
        f"event-{status}",
        f"source-{status}-001",
        "doc-001",
        status,
        NOW if status == "received" else LATER,
        "document_engine",
        "ingestion" if status == "received" else "classification",
    )


def _processing(*, expected_version=None, status="succeeded", updated_at=LATER):
    return WriteProcessingSnapshotCommand(
        "snapshot-classification-001",
        "source-classified-001",
        "doc-001",
        "run-ingestion-001",
        "classification",
        status,
        NOW,
        updated_at,
        completed_at=updated_at,
        duration_ms=25,
        expected_version=expected_version,
    )


def _audit(event_type="ingestion_received"):
    return WriteAuditEventCommand(
        "source-audit-001",
        f"audit-{event_type}",
        event_type,
        "system",
        NOW,
        document_id="doc-001",
        metadata={"source_stage": "ingestion"},
    )


def _service(repositories):
    return IngestionDocumentStateWriter(repositories.reader, repositories.writer)


def test_ingestion_received_writes_document_lifecycle_and_optional_audit():
    repositories = InMemoryDocumentStateRepositories()
    result = _service(repositories).write_ingestion_received(_document(), _lifecycle(), _audit())

    assert result.status == "success"
    assert result.record_ids == ("doc-001", "event-received", "audit-ingestion_received")
    assert repositories.reader.get_document("doc-001").status == "received"
    assert repositories.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1
    assert repositories.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1
    json.dumps(result.to_dict())


def test_ingestion_classified_writes_lifecycle_and_processing_snapshot():
    repositories = InMemoryDocumentStateRepositories()
    service = _service(repositories)
    service.write_ingestion_received(_document(), _lifecycle())

    result = service.write_ingestion_classified(_lifecycle("classified"), _processing(), _audit("ingestion_classified"))

    assert result.status == "success"
    assert repositories.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 2
    snapshot = repositories.reader.get_processing_snapshot("snapshot-classification-001")
    assert (snapshot.stage, snapshot.status, snapshot.version) == ("classification", "succeeded", 1)


def test_retries_are_idempotent_without_duplicate_records():
    repositories = InMemoryDocumentStateRepositories()
    service = _service(repositories)
    first = service.write_ingestion_received(_document(), _lifecycle(), _audit())
    second = service.write_ingestion_received(_document(), _lifecycle(), _audit())

    assert first.status == "success"
    assert second.status == "success"
    assert repositories.reader.list_documents(DocumentQuery(), PageRequest()).total == 1
    assert repositories.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1
    assert repositories.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1


class _FailLifecycleOnce:
    def __init__(self, delegate):
        self._delegate = delegate
        self._failed = False

    def append_lifecycle_event(self, record, *, idempotency_key):
        if not self._failed:
            self._failed = True
            raise DocumentStateError("source_unavailable")
        return self._delegate.append_lifecycle_event(record, idempotency_key=idempotency_key)

    def __getattr__(self, name):
        return getattr(self._delegate, name)


def test_partial_retry_resumes_after_document_create():
    repositories = InMemoryDocumentStateRepositories()
    service = IngestionDocumentStateWriter(repositories.reader, _FailLifecycleOnce(repositories.writer))

    first = service.write_ingestion_received(_document(), _lifecycle())
    second = service.write_ingestion_received(_document(), _lifecycle())

    assert first.to_dict() == {
        "status": "failed",
        "operation": "write_ingestion_received",
        "record_ids": ["doc-001"],
        "committed_count": 1,
        "error_code": "repository_unavailable",
        "message": "Document State repository is unavailable.",
    }
    assert second.status == "success"
    assert repositories.reader.list_documents(DocumentQuery(), PageRequest()).total == 1
    assert repositories.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1


def test_processing_snapshot_update_and_stale_version_retry_are_safe():
    repositories = InMemoryDocumentStateRepositories()
    service = _service(repositories)
    assert service.write_processing_snapshot(_processing()).status == "success"
    update = _processing(expected_version=1, status="failed", updated_at="2026-07-13T09:02:00+00:00")
    assert service.write_processing_snapshot(update).status == "success"
    assert service.write_processing_snapshot(update).status == "skipped_idempotent"

    stale = _processing(expected_version=1, status="succeeded", updated_at="2026-07-13T09:03:00+00:00")
    conflict = service.write_processing_snapshot(stale)
    assert conflict.status == "conflict"
    assert conflict.error_code == "version_conflict"
    assert repositories.reader.get_processing_snapshot("snapshot-classification-001").status == "failed"


def test_duplicate_document_with_different_safe_content_conflicts():
    repositories = InMemoryDocumentStateRepositories()
    service = _service(repositories)
    assert service.create_document(_document()).status == "success"

    result = service.create_document(_document(filename="different.pdf"))
    assert result.status == "conflict"
    assert result.error_code == "invalid_command"
    assert repositories.reader.get_document("doc-001").filename == "invoice.pdf"


def test_repository_unavailable_and_invalid_commands_map_safely():
    unavailable = InMemoryDocumentStateRepositories(source_available=False)
    failed = _service(unavailable).create_document(_document())
    invalid = _service(InMemoryDocumentStateRepositories()).create_document(object())

    assert failed.error_code == "repository_unavailable"
    assert "source" not in failed.message.lower()
    assert invalid.status == "invalid_input"
    assert invalid.error_code == "invalid_command"


def test_tampered_unsafe_metadata_is_rejected_before_repository_write():
    repositories = InMemoryDocumentStateRepositories()
    command = _document()
    object.__setattr__(command, "metadata", {"raw_rows": "private-row"})

    result = _service(repositories).create_document(command)
    assert result.status == "invalid_input"
    assert "private-row" not in json.dumps(result.to_dict())
    assert repositories.reader.list_documents(DocumentQuery(), PageRequest()).total == 0


def test_opaque_artifact_reference_is_accepted_but_payload_is_not_persisted():
    repositories = InMemoryDocumentStateRepositories()
    assert _service(repositories).create_document(_document()).status == "success"
    persisted = repositories.reader.get_document("doc-001").to_dict()
    assert persisted["metadata"] == {"source_runtime": "document_engine"}
    assert "artifact" not in json.dumps(persisted)


def test_sqlite_composition_is_supported_without_backend_specific_writer_logic(tmp_path):
    database = tmp_path / "ingestion-writer.sqlite3"
    composition = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(database)))
    result = IngestionDocumentStateWriter(composition.reader, composition.writer).write_ingestion_received(_document(), _lifecycle())

    assert result.status == "success"
    reopened = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(database)))
    assert reopened.reader.get_document("doc-001").status == "received"
    assert reopened.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1


def test_ingestion_writer_exposes_no_transport_or_backend_selection_methods():
    names = {name for name in dir(IngestionDocumentStateWriter) if not name.startswith("_")}
    assert {"post", "put", "patch", "delete", "compose", "select_backend"}.isdisjoint(names)
    assert names == {
        "append_lifecycle_event",
        "create_document",
        "write_audit_event",
        "write_ingestion_classified",
        "write_ingestion_received",
        "write_processing_snapshot",
    }
