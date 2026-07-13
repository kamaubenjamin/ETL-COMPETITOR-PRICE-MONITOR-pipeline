import ast
from dataclasses import FrozenInstanceError, fields
import inspect
import json
from pathlib import Path

import pytest

from src.workflow_runtime.query_facade import (
    AuditEventQuery,
    DocumentQuery,
    InMemoryWorkflowQueryFacade,
    PageRequest,
    QueryFacadeError,
    ReviewCaseQuery,
    WorkflowQueryFacadePort,
    WorkflowRunQuery,
)


def test_provider_structurally_satisfies_facade_port():
    assert isinstance(InMemoryWorkflowQueryFacade(), WorkflowQueryFacadePort)


def test_document_list_detail_filters_and_pagination():
    provider = InMemoryWorkflowQueryFacade()
    first = provider.list_documents(DocumentQuery(), PageRequest(limit=2))
    second = provider.list_documents(DocumentQuery(), PageRequest(limit=2, offset=2))
    assert first.total == second.total == 3
    assert [item.document_id for item in first.items] == ["doc-001", "doc-002"]
    assert [item.document_id for item in second.items] == ["doc-003"]
    assert provider.get_document("doc-002").status == "review_required"
    assert [item.document_id for item in provider.list_documents(DocumentQuery(status="validated"), PageRequest()).items] == ["doc-001"]
    assert [item.document_id for item in provider.list_documents(DocumentQuery(document_type="receipt"), PageRequest()).items] == ["doc-003"]


def test_processing_validation_matching_and_alias_reads():
    provider = InMemoryWorkflowQueryFacade()
    processing = provider.list_processing("doc-002", PageRequest(limit=1))
    alias = provider.get_processing_status("doc-002", PageRequest(limit=1))
    assert processing == alias
    assert processing.total == 2
    assert [item.stage for item in processing.items] == ["ingest"]
    validation = provider.list_validation_issues("doc-002", PageRequest(limit=1))
    assert validation.total == 2
    assert validation.items[0].severity == "error"
    matching = provider.list_matching_results("doc-002", PageRequest())
    assert [item.confidence for item in matching.items] == [0.72, 0.68]


def test_review_correction_and_reprocess_reads_and_filters():
    provider = InMemoryWorkflowQueryFacade()
    reviews = provider.list_review_cases(ReviewCaseQuery(status="in_review", priority="high"), PageRequest())
    assert [item.review_case_id for item in reviews.items] == ["review-001"]
    assert provider.get_review_case("review-003").reprocess_state == "planned"
    corrections = provider.list_correction_history("review-001", PageRequest())
    assert corrections == provider.list_corrections("review-001", PageRequest())
    assert corrections.items[0].field_path == "supplier_id"
    plans = provider.list_reprocess_plans("review-003", PageRequest())
    assert plans.total == 1
    assert plans.items[0].mode == "dry_run"
    assert provider.list_reprocess_plans(None, PageRequest()).total == 1


def test_workflow_and_audit_filters_and_descending_order():
    provider = InMemoryWorkflowQueryFacade()
    runs = provider.list_workflow_runs(WorkflowRunQuery(), PageRequest())
    assert [item.run_id for item in runs.items] == ["run-003", "run-002", "run-001"]
    assert [item.run_id for item in provider.list_workflow_runs(WorkflowRunQuery(status="failed"), PageRequest()).items] == ["run-003"]
    assert [item.run_id for item in provider.list_workflow_runs(WorkflowRunQuery(workflow_name="invoice_processing"), PageRequest()).items] == ["run-001"]
    audit = provider.list_audit_events(AuditEventQuery(), PageRequest(limit=2))
    assert audit.total == 5
    assert [item.event_id for item in audit.items] == ["audit-005", "audit-004"]
    filtered = provider.list_audit_events(AuditEventQuery(event_type="review_case_created"), PageRequest())
    assert [item.event_id for item in filtered.items] == ["audit-003"]


@pytest.mark.parametrize(
    "read",
    [
        lambda provider: provider.list_processing("doc-001", PageRequest(limit=1)),
        lambda provider: provider.list_validation_issues("doc-002", PageRequest(limit=1)),
        lambda provider: provider.list_matching_results("doc-002", PageRequest(limit=1)),
        lambda provider: provider.list_review_cases(ReviewCaseQuery(), PageRequest(limit=1)),
        lambda provider: provider.list_correction_history("review-001", PageRequest(limit=1)),
        lambda provider: provider.list_reprocess_plans(None, PageRequest(limit=1)),
        lambda provider: provider.list_workflow_runs(WorkflowRunQuery(), PageRequest(limit=1)),
        lambda provider: provider.list_audit_events(AuditEventQuery(), PageRequest(limit=1)),
    ],
)
def test_all_list_reads_return_bounded_pages(read):
    page = read(InMemoryWorkflowQueryFacade())
    assert len(page.items) <= page.limit == 1
    assert page.offset == 0
    json.dumps(page.to_dict())


@pytest.mark.parametrize("read", [lambda provider: provider.get_document("missing"), lambda provider: provider.get_review_case("missing"), lambda provider: provider.list_validation_issues("missing", PageRequest())])
def test_unknown_ids_raise_safe_not_found(read):
    with pytest.raises(QueryFacadeError) as raised:
        read(InMemoryWorkflowQueryFacade())
    assert raised.value.code == "not_found"
    assert "missing" not in raised.value.message


@pytest.mark.parametrize(
    "read",
    [
        lambda provider: provider.list_documents(object(), PageRequest()),
        lambda provider: provider.list_documents(DocumentQuery(), object()),
        lambda provider: provider.get_document(""),
        lambda provider: provider.list_review_cases(object(), PageRequest()),
        lambda provider: provider.list_workflow_runs(object(), PageRequest()),
        lambda provider: provider.list_audit_events(object(), PageRequest()),
    ],
)
def test_invalid_query_objects_raise_safe_invalid_query(read):
    with pytest.raises(QueryFacadeError) as raised:
        read(InMemoryWorkflowQueryFacade())
    assert raised.value.code == "invalid_query"


def test_explicit_unavailable_simulation_is_safe_and_deterministic():
    provider = InMemoryWorkflowQueryFacade(simulate_unavailable=True)
    with pytest.raises(QueryFacadeError) as raised:
        provider.list_documents(DocumentQuery(), PageRequest())
    assert raised.value.to_dict() == {"code": "source_unavailable", "message": "Query source is unavailable.", "field": None}


def test_returned_models_are_immutable_and_provider_state_cannot_leak():
    provider = InMemoryWorkflowQueryFacade()
    document = provider.list_documents(DocumentQuery(), PageRequest()).items[0]
    with pytest.raises(FrozenInstanceError):
        document.status = "failed"
    audit = provider.list_audit_events(AuditEventQuery(), PageRequest()).items[0]
    with pytest.raises(TypeError):
        audit.metadata["count"] = 999
    assert provider.list_documents(DocumentQuery(), PageRequest()).items[0].status == "validated"


def test_provider_exposes_no_sensitive_fields_or_mutation_methods():
    provider = InMemoryWorkflowQueryFacade()
    models = [
        *provider.list_documents(DocumentQuery(), PageRequest()).items,
        *provider.list_validation_issues("doc-002", PageRequest()).items,
        *provider.list_matching_results("doc-002", PageRequest()).items,
        *provider.list_review_cases(ReviewCaseQuery(), PageRequest()).items,
        *provider.list_correction_history("review-001", PageRequest()).items,
        *provider.list_reprocess_plans(None, PageRequest()).items,
        *provider.list_audit_events(AuditEventQuery(), PageRequest()).items,
    ]
    unsafe = {"raw_document", "raw_rows", "old_value", "new_value", "artifact_payload", "stack_trace", "storage_path"}
    assert all(not ({item.name for item in fields(model)} & unsafe) for model in models)
    public = {name for name, value in inspect.getmembers(provider, callable) if not name.startswith("_")}
    assert not any(name.startswith(("create_", "update_", "delete_", "save_", "execute_", "submit_")) for name in public)


def test_provider_imports_are_local_or_standard_library_only():
    source_path = Path(inspect.getsourcefile(InMemoryWorkflowQueryFacade))
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden = {"api", "document_engine", "entity_runtime", "matching_runtime", "review_runtime", "storage", "streamlit", "telemetry", "transform", "transforms", "flowsync", "competitor"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {alias.name.split(".")[0].lower() for alias in node.names} & forbidden
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            assert node.module.split(".")[0].lower() not in forbidden
