import json

import pytest

from src.document_state import DocumentStateComposition, compose_document_state
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.document_state.persistence import PersistenceConfig
from src.workflow_runtime.query_facade import (
    AuditEventQuery,
    DocumentQuery,
    PageRequest,
    ReviewCaseQuery,
    WorkflowQueryFacadePort,
    WorkflowRunQuery,
)

from .read_after_write_fixtures import T5, write_representative_lifecycle


def _composition(tmp_path, backend):
    if backend == "in_memory":
        return compose_document_state(PersistenceConfig("in_memory"))
    return compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "read-after-write.sqlite3")))


def _facade(composition):
    facade = DocumentStateQueryFacadeAdapter(composition.reader, snapshot_at=T5)
    assert isinstance(facade, WorkflowQueryFacadePort)
    return facade


def _projection(facade):
    page = PageRequest(limit=50)
    return {
        "documents": facade.list_documents(DocumentQuery(), page).to_dict(),
        "detail": facade.get_document("doc-raw-001").to_dict(),
        "processing": facade.list_processing("doc-raw-001", page).to_dict(),
        "validation": facade.list_validation_issues("doc-raw-001", page).to_dict(),
        "matching": facade.list_matching_results("doc-raw-001", page).to_dict(),
        "reviews": facade.list_review_cases(ReviewCaseQuery(), page).to_dict(),
        "review": facade.get_review_case("review-001").to_dict(),
        "corrections": facade.list_correction_history("review-001", page).to_dict(),
        "reprocess": facade.list_reprocess_plans("review-001", page).to_dict(),
        "workflows": facade.list_workflow_runs(WorkflowRunQuery(), page).to_dict(),
        "audit": facade.list_audit_events(AuditEventQuery(), page).to_dict(),
    }


@pytest.mark.parametrize("backend", ["in_memory", "sqlite"])
def test_writer_outputs_are_readable_through_query_facade(tmp_path, backend):
    composition = _composition(tmp_path, backend)
    assert isinstance(composition, DocumentStateComposition)
    write_representative_lifecycle(composition)
    projection = _projection(_facade(composition))

    assert projection["documents"]["total"] == 1
    assert projection["detail"]["document_id"] == "doc-raw-001"
    assert projection["processing"]["total"] == 3
    assert projection["validation"]["total"] == 2
    assert projection["matching"]["total"] == 1
    assert projection["reviews"]["total"] == 1
    assert projection["corrections"]["total"] == 1
    assert projection["reprocess"]["total"] == 1
    assert projection["workflows"]["total"] == 1
    assert projection["audit"]["total"] == 5


def test_backends_produce_equivalent_projections_and_sqlite_survives_reopen(tmp_path):
    memory = _composition(tmp_path, "in_memory")
    sqlite = _composition(tmp_path, "sqlite")
    write_representative_lifecycle(memory)
    write_representative_lifecycle(sqlite)

    reopened = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "read-after-write.sqlite3")))
    assert _projection(_facade(memory)) == _projection(_facade(reopened))


@pytest.mark.parametrize("backend", ["in_memory", "sqlite"])
def test_replay_does_not_duplicate_visible_records(tmp_path, backend):
    composition = _composition(tmp_path, backend)
    first = write_representative_lifecycle(composition)
    second = write_representative_lifecycle(composition)
    projection = _projection(_facade(composition))

    assert len(first) == len(second) == 14
    assert projection["validation"]["total"] == 2
    assert projection["audit"]["total"] == 5
    assert projection["corrections"]["total"] == 1


def test_filters_and_pagination_work_after_writes(tmp_path):
    composition = _composition(tmp_path, "in_memory")
    write_representative_lifecycle(composition)
    facade = _facade(composition)

    assert facade.list_documents(DocumentQuery(status="received", document_type="invoice"), PageRequest()).total == 1
    assert facade.list_review_cases(ReviewCaseQuery(status="review_required", priority="high"), PageRequest()).total == 1
    assert facade.list_workflow_runs(WorkflowRunQuery(status="succeeded"), PageRequest()).total == 1
    assert facade.list_audit_events(AuditEventQuery(event_type="validation_completed"), PageRequest()).total == 1
    first_page = facade.list_audit_events(AuditEventQuery(), PageRequest(limit=2, offset=0))
    second_page = facade.list_audit_events(AuditEventQuery(), PageRequest(limit=2, offset=2))
    assert first_page.total == second_page.total == 5
    assert {item.event_id for item in first_page.items}.isdisjoint(item.event_id for item in second_page.items)


def test_partial_prewrite_then_full_replay_resumes_safely(tmp_path):
    composition = _composition(tmp_path, "in_memory")
    from src.document_state.writers import CreateDocumentCommand, IngestionDocumentStateWriter

    command = CreateDocumentCommand(
        "doc-raw-001", "source-received-001", "invoice_001.pdf", "invoice", 0.93,
        "2026-07-13T09:00:00+00:00", "2026-07-13T09:00:00+00:00", "document_engine",
        metadata={"workflow_name": "invoice_processing"},
    )
    assert IngestionDocumentStateWriter(composition.reader, composition.writer).create_document(command).status == "success"
    write_representative_lifecycle(composition)
    assert _projection(_facade(composition))["documents"]["total"] == 1


def test_end_to_end_projection_excludes_sensitive_payloads(tmp_path):
    composition = _composition(tmp_path, "in_memory")
    write_representative_lifecycle(composition)
    serialized = json.dumps(_projection(_facade(composition))).lower()
    for forbidden in (
        "raw_document", "raw_rows", "old_value", "new_value", "artifact_payload",
        "storage_path", "credential", "stack_trace", "traceback", "private-row",
    ):
        assert forbidden not in serialized
