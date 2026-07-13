from src.document_state import AuditQuery, PageRequest, WorkflowRunQuery, compose_document_state
from src.document_state.persistence import PersistenceConfig
from src.document_state.repositories_in_memory import InMemoryDocumentStateRepositories
from src.document_state.writers.commands import WriteAuditEventCommand, WriteWorkflowRunCommand
from src.document_state.writers.workflow_writer import WorkflowDocumentStateWriter


NOW = "2026-07-13T09:00:00+00:00"


def _workflow(*, expected_version=None, status="succeeded", updated_at=NOW):
    return WriteWorkflowRunCommand(
        "source-workflow", "run-001", "invoice_processing", status, NOW, NOW, updated_at,
        completed_at=updated_at, duration_ms=100, current_stage="matching", stage_count=3,
        succeeded_stage_count=3 if status == "succeeded" else 2,
        failed_stage_count=0 if status == "succeeded" else 1,
        expected_version=expected_version,
    )


def _audit(event_type="workflow_run_completed"):
    return WriteAuditEventCommand("source-audit", "audit-workflow", event_type, "system", NOW, workflow_run_id="run-001")


def _service(store):
    return WorkflowDocumentStateWriter(store.reader, store.writer)


def test_workflow_run_and_audit_are_idempotent():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)
    assert service.write_workflow_run(_workflow()).status == "success"
    assert service.write_workflow_run(_workflow()).status == "skipped_idempotent"
    assert service.write_audit_event(_audit()).status == "success"
    assert service.write_audit_event(_audit()).status == "success"
    assert store.reader.list_workflow_runs(WorkflowRunQuery(), PageRequest()).total == 1
    assert store.reader.list_audit_events(AuditQuery(), PageRequest()).total == 1


def test_workflow_version_conflicts_and_invalid_states_are_safe():
    store = InMemoryDocumentStateRepositories()
    service = _service(store)
    service.write_workflow_run(_workflow())
    update = _workflow(expected_version=1, status="failed", updated_at="2026-07-13T09:01:00+00:00")
    assert service.write_workflow_run(update).status == "success"
    assert service.write_workflow_run(update).status == "skipped_idempotent"
    stale = _workflow(expected_version=1, updated_at="2026-07-13T09:02:00+00:00")
    assert service.write_workflow_run(stale).error_code == "version_conflict"

    running = WriteWorkflowRunCommand("source", "run-002", "workflow", "running", NOW, NOW, NOW)
    assert service.write_workflow_run(running).status == "invalid_input"


def test_workflow_writer_maps_unavailable_and_invalid_commands_safely():
    unavailable = InMemoryDocumentStateRepositories(source_available=False)
    assert _service(unavailable).write_workflow_run(_workflow()).error_code == "repository_unavailable"
    assert _service(InMemoryDocumentStateRepositories()).write_workflow_run(object()).status == "invalid_input"


def test_workflow_writer_accepts_sqlite_injected_ports(tmp_path):
    store = compose_document_state(PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "workflow.sqlite3")))
    service = _service(store)
    assert service.write_workflow_run(_workflow()).status == "success"
    assert service.write_audit_event(_audit()).status == "success"
    assert store.reader.get_workflow_run("run-001").status == "succeeded"


def test_workflow_writer_exposes_no_transport_or_backend_methods():
    names = {name for name in dir(WorkflowDocumentStateWriter) if not name.startswith("_")}
    assert names == {"write_audit_event", "write_workflow_run"}
