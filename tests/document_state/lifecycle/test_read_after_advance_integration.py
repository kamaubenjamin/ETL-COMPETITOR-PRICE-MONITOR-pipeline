import json

import pytest

from src.api.document_intelligence.providers.facade_provider import FacadeDocumentIntelligenceProvider
from src.document_state import DocumentRecord, LifecycleQuery, PageRequest as StatePageRequest, compose_document_state
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.document_state.errors import DocumentStateError
from src.document_state.lifecycle import LifecycleAdvancementService
from src.document_state.persistence import PersistenceConfig
from src.document_state.writers import (
    AppendLifecycleEventCommand,
    ProcessingDocumentStateWriter,
    WorkflowDocumentStateWriter,
)
from src.workflow_runtime.query_facade import (
    AuditEventQuery,
    DocumentQuery,
    PageRequest,
    ReviewCaseQuery,
    WorkflowQueryFacadePort,
    WorkflowRunQuery,
)

from tests.document_state.lifecycle.read_after_advance_fixtures import (
    SNAPSHOT_AT,
    write_advanced_lifecycle,
)


def _composition(backend, tmp_path):
    path = tmp_path / "read-after-advance.sqlite3"
    config = PersistenceConfig(backend, sqlite_path=str(path) if backend == "sqlite" else None)
    return compose_document_state(config), config


@pytest.mark.parametrize("backend", ("in_memory", "sqlite"))
def test_advanced_projection_is_visible_through_approved_read_path(backend, tmp_path):
    composition, _ = _composition(backend, tmp_path)
    write_advanced_lifecycle(composition)

    document = composition.reader.get_document("doc-raw-001")
    assert (document.status, document.current_stage, document.version) == ("exported", "export", 8)
    failed = composition.reader.get_document("doc-failed-002")
    assert (failed.status, failed.current_stage, failed.version) == ("failed", "workflow", 2)

    facade = DocumentStateQueryFacadeAdapter(composition.reader, snapshot_at=SNAPSHOT_AT)
    assert isinstance(facade, WorkflowQueryFacadePort)
    detail = facade.get_document("doc-raw-001")
    assert (detail.status, detail.current_stage) == ("exported", "export")
    api_document = FacadeDocumentIntelligenceProvider(facade).get_document("doc-raw-001")
    assert (api_document["status"], api_document["current_stage"]) == ("exported", "export")

    before = composition.reader.list_lifecycle_events(
        "doc-raw-001", LifecycleQuery(), StatePageRequest()
    )
    projected_before = composition.reader.get_document("doc-raw-001")
    replay = AppendLifecycleEventCommand(
        "lifecycle-exported",
        "source-exported-001",
        "doc-raw-001",
        "exported",
        "2026-07-13T09:05:00+00:00",
        "integration_test",
        "export",
        "exported_completed",
    )
    workflow = WorkflowDocumentStateWriter(
        composition.reader,
        composition.writer,
        LifecycleAdvancementService(composition.reader, composition.writer),
    )
    assert workflow.append_lifecycle_event(replay).status == "success"
    after = composition.reader.list_lifecycle_events(
        "doc-raw-001", LifecycleQuery(), StatePageRequest()
    )
    assert composition.reader.get_document("doc-raw-001") == projected_before
    assert after.total == before.total


def test_sqlite_projection_survives_composition_reconstruction(tmp_path):
    composition, config = _composition("sqlite", tmp_path)
    write_advanced_lifecycle(composition)

    reopened = compose_document_state(config)
    facade = DocumentStateQueryFacadeAdapter(reopened.reader, snapshot_at=SNAPSHOT_AT)
    assert facade.get_document("doc-raw-001").status == "exported"
    assert facade.get_document("doc-failed-002").status == "failed"


def test_filters_pagination_and_privacy_follow_advanced_state(tmp_path):
    composition, _ = _composition("in_memory", tmp_path)
    write_advanced_lifecycle(composition)
    facade = DocumentStateQueryFacadeAdapter(composition.reader, snapshot_at=SNAPSHOT_AT)

    exported = facade.list_documents(DocumentQuery(status="exported"), PageRequest(limit=1))
    failed = facade.list_documents(DocumentQuery(status="failed"), PageRequest(limit=1))
    first = facade.list_documents(DocumentQuery(), PageRequest(limit=1, offset=0))
    second = facade.list_documents(DocumentQuery(), PageRequest(limit=1, offset=1))
    reviews = facade.list_review_cases(ReviewCaseQuery(status="review_required", priority="high"), PageRequest())
    succeeded_runs = facade.list_workflow_runs(WorkflowRunQuery(status="succeeded"), PageRequest())
    failed_runs = facade.list_workflow_runs(WorkflowRunQuery(status="failed"), PageRequest())
    audits = facade.list_audit_events(AuditEventQuery(event_type="validation_completed"), PageRequest())

    assert [item.document_id for item in exported.items] == ["doc-raw-001"]
    assert [item.document_id for item in failed.items] == ["doc-failed-002"]
    assert first.total == second.total == 2
    assert first.items[0].document_id != second.items[0].document_id
    assert [item.review_case_id for item in reviews.items] == ["review-001"]
    assert [item.run_id for item in succeeded_runs.items] == ["run-001"]
    assert [item.run_id for item in failed_runs.items] == ["run-failed-002"]
    assert [item.event_id for item in audits.items] == ["audit-validation"]

    payload = json.dumps(
        {
            "documents": [item.to_dict() for item in first.items + second.items],
            "reviews": [item.to_dict() for item in reviews.items],
            "audit": [item.to_dict() for item in audits.items],
        }
    ).lower()
    for forbidden in (
        "raw_document",
        "raw_rows",
        "old_value",
        "new_value",
        "artifact_payload",
        "storage_path",
        "credential",
        "stack_trace",
    ):
        assert forbidden not in payload


class _ConflictDocumentWriter:
    def create_document(self, record):
        return record

    def update_document(self, record, *, expected_version):
        raise DocumentStateError("conflict")


def test_projection_pending_replay_repairs_the_approved_read_path(tmp_path):
    parsed_composition, _ = _composition("in_memory", tmp_path)
    parsed_composition.writer.create_document(
        DocumentRecord(
            "doc-repair-003",
            "invoice_003.pdf",
            "invoice",
            "classified",
            0.9,
            "classification",
            "2026-07-13T09:00:00+00:00",
            "2026-07-13T09:00:00+00:00",
            "2026-07-13T09:00:00+00:00",
        )
    )
    repair_command = AppendLifecycleEventCommand(
        "lifecycle-repair-parsed",
        "source-repair-parsed",
        "doc-repair-003",
        "parsed",
        "2026-07-13T09:01:00+00:00",
        "processing_runtime",
        "parsing_structure",
    )
    blocked = ProcessingDocumentStateWriter(
        parsed_composition.reader,
        parsed_composition.writer,
        LifecycleAdvancementService(parsed_composition.reader, _ConflictDocumentWriter()),
    )
    assert blocked.append_lifecycle_event(repair_command).status == "projection_pending"
    facade = DocumentStateQueryFacadeAdapter(parsed_composition.reader, snapshot_at=SNAPSHOT_AT)
    assert facade.get_document("doc-repair-003").status == "classified"

    repaired = ProcessingDocumentStateWriter(
        parsed_composition.reader,
        parsed_composition.writer,
        LifecycleAdvancementService(parsed_composition.reader, parsed_composition.writer),
    )
    assert repaired.append_lifecycle_event(repair_command).status == "success"
    provider = FacadeDocumentIntelligenceProvider(facade)
    assert provider.get_document("doc-repair-003")["status"] == "parsed"
    history = parsed_composition.reader.list_lifecycle_events(
        "doc-repair-003", LifecycleQuery(), StatePageRequest()
    )
    assert history.total == 1
