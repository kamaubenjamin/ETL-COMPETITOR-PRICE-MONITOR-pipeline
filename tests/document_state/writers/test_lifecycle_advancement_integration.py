from src.document_state import DocumentRecord, LifecycleQuery, PageRequest, compose_document_state
from src.document_state.errors import DocumentStateError
from src.document_state.lifecycle import LifecycleAdvancementService
from src.document_state.persistence import PersistenceConfig
from src.document_state.repositories_in_memory import InMemoryDocumentStateRepositories
from src.document_state.writers.commands import AppendLifecycleEventCommand, WriteReprocessPlanCommand
from src.document_state.writers.ingestion_writer import IngestionDocumentStateWriter
from src.document_state.writers.processing_writer import ProcessingDocumentStateWriter
from src.document_state.writers.review_writer import ReviewDocumentStateWriter
from src.document_state.writers.workflow_writer import WorkflowDocumentStateWriter


TS = "2026-07-13T09:00:00+00:00"


def document(status="received", stage="ingestion"):
    return DocumentRecord(
        "doc-001", "invoice.pdf", "invoice", status, 0.95, stage, TS, TS, TS
    )


def event(status, index, stage):
    return AppendLifecycleEventCommand(
        f"event-{index}",
        f"source-{index}",
        "doc-001",
        status,
        f"2026-07-13T09:{index:02d}:00+00:00",
        "system",
        stage,
        f"{status}_completed",
    )


def service(composition):
    return LifecycleAdvancementService(composition.reader, composition.writer)


def test_ingestion_received_no_op_and_classified_advancement():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(document())
    writer = IngestionDocumentStateWriter(store.reader, store.writer, service(store))
    assert writer.append_lifecycle_event(event("received", 1, "ingestion")).status == "success"
    assert store.reader.get_document("doc-001").version == 1
    assert writer.append_lifecycle_event(event("classified", 2, "classification")).status == "success"
    projected = store.reader.get_document("doc-001")
    assert (projected.status, projected.current_stage, projected.version) == ("classified", "classification", 2)


def test_processing_advances_parsed_validated_and_matched():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(document("classified", "classification"))
    writer = ProcessingDocumentStateWriter(store.reader, store.writer, service(store))
    for status, index, stage in (
        ("parsed", 1, "parsing_structure"),
        ("validated", 2, "validate_data"),
        ("matched", 3, "matching"),
    ):
        assert writer.append_lifecycle_event(event(status, index, stage)).status == "success"
    projected = store.reader.get_document("doc-001")
    assert (projected.status, projected.current_stage, projected.version) == ("matched", "matching", 4)


def test_review_advances_required_and_approved_without_reprocess_status():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(document("matched", "matching"))
    writer = ReviewDocumentStateWriter(store.reader, store.writer, service(store))
    assert writer.append_lifecycle_event(event("review_required", 1, "review")).status == "success"
    assert writer.append_lifecycle_event(event("approved", 2, "review")).status == "success"
    reprocess = WriteReprocessPlanCommand(
        "source-plan", "plan-001", "review-001", "doc-001", "review", "validation",
        1, 0, "corrected_data", "reviewer-001", TS,
    )
    assert writer.write_reprocess_plan(reprocess).status == "success"
    assert store.reader.get_document("doc-001").status == "approved"


def test_workflow_advances_exported_and_failed_only_from_explicit_events():
    exported_store = InMemoryDocumentStateRepositories()
    exported_store.writer.create_document(document("approved", "review"))
    exported_writer = WorkflowDocumentStateWriter(
        exported_store.reader, exported_store.writer, service(exported_store)
    )
    assert exported_writer.append_lifecycle_event(event("exported", 1, "export")).status == "success"
    assert exported_store.reader.get_document("doc-001").status == "exported"

    failed_store = InMemoryDocumentStateRepositories()
    failed_store.writer.create_document(document("validated", "validate_data"))
    failed_writer = WorkflowDocumentStateWriter(
        failed_store.reader, failed_store.writer, service(failed_store)
    )
    assert failed_writer.append_lifecycle_event(event("failed", 1, "workflow")).status == "success"
    assert failed_store.reader.get_document("doc-001").status == "failed"


def test_same_event_replay_is_projection_no_op_without_version_churn():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(document("classified", "classification"))
    writer = ProcessingDocumentStateWriter(store.reader, store.writer, service(store))
    command = event("parsed", 1, "parsing_structure")
    assert writer.append_lifecycle_event(command).status == "success"
    first = store.reader.get_document("doc-001")
    assert writer.append_lifecycle_event(command).status == "success"
    assert store.reader.get_document("doc-001") == first
    assert store.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1


class ConflictDocumentWriter:
    def create_document(self, record):
        return record

    def update_document(self, record, *, expected_version):
        raise DocumentStateError("conflict")


def test_append_success_projection_conflict_and_replay_repair():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(document("classified", "classification"))
    blocked_service = LifecycleAdvancementService(store.reader, ConflictDocumentWriter())
    command = event("parsed", 1, "parsing_structure")
    blocked = ProcessingDocumentStateWriter(store.reader, store.writer, blocked_service)
    first = blocked.append_lifecycle_event(command)
    assert (first.status, first.error_code, first.record_ids) == (
        "projection_pending", "version_conflict", ("event-1",)
    )
    assert store.reader.get_document("doc-001").status == "classified"
    assert store.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1

    repaired = ProcessingDocumentStateWriter(store.reader, store.writer, service(store))
    assert repaired.append_lifecycle_event(command).status == "success"
    assert store.reader.get_document("doc-001").status == "parsed"
    assert store.reader.list_lifecycle_events("doc-001", LifecycleQuery(), PageRequest()).total == 1


def test_sqlite_writer_advancement_matches_in_memory(tmp_path):
    store = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "lifecycle.sqlite3")))
    store.writer.create_document(document("classified", "classification"))
    writer = ProcessingDocumentStateWriter(store.reader, store.writer, service(store))
    assert writer.append_lifecycle_event(event("parsed", 1, "parsing_structure")).status == "success"
    assert store.reader.get_document("doc-001").status == "parsed"


def test_writers_preserve_legacy_behavior_without_injected_service():
    store = InMemoryDocumentStateRepositories()
    store.writer.create_document(document("classified", "classification"))
    writer = ProcessingDocumentStateWriter(store.reader, store.writer)
    assert writer.append_lifecycle_event(event("parsed", 1, "parsing_structure")).status == "success"
    assert store.reader.get_document("doc-001").status == "classified"
