import ast
import inspect
import json
from pathlib import Path

from starlette.requests import Request

from src.api.document_intelligence.providers import (
    FacadeDocumentIntelligenceProvider,
    api_local_provider,
    facade_provider,
    local_provider,
)
from src.api.document_intelligence.routers.documents import list_documents
from src.workflow_runtime.query_facade import InMemoryWorkflowQueryFacade


def _provider():
    return FacadeDocumentIntelligenceProvider(InMemoryWorkflowQueryFacade())


def _request(request_id="request-facade-001"):
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.request_id = request_id
    return request


def test_facade_provider_is_preferred_and_api_local_provider_remains_available():
    assert local_provider is facade_provider
    assert isinstance(local_provider, FacadeDocumentIntelligenceProvider)
    assert api_local_provider is not facade_provider


def test_document_and_processing_models_map_to_existing_api_shapes():
    provider = _provider()
    documents = provider.list_documents()
    assert list(documents[0]) == [
        "document_id", "filename", "document_type", "status", "confidence",
        "current_stage", "received_at",
    ]
    detail = provider.get_document("doc-001")
    assert set(detail) == set(documents[0])
    assert "updated_at" not in detail
    assert "workflow_name" not in detail
    processing = provider.list_processing("doc-001")
    assert set(processing[0]) == {"stage", "status", "occurred_at"}


def test_validation_matching_review_and_correction_mapping():
    provider = _provider()
    validation = provider.list_validation("doc-002")
    assert set(validation[0]) == {"issue_id", "severity", "field", "rule_id", "code", "message"}
    matching = provider.list_matching("doc-002")
    assert set(matching[0]) == {"match_id", "entity_type", "candidate_id", "confidence", "status"}
    review = provider.get_review_case("review-001")
    assert review["assigned_reviewer"] == "reviewer-01"
    assert "assigned_reviewer_id" not in review
    assert "updated_at" not in review
    corrections = provider.list_corrections("review-001")
    assert set(corrections[0]) == {
        "correction_id", "review_case_id", "field_path", "operation",
        "reason_code", "actor_id", "occurred_at", "source_stage",
    }


def test_reprocess_workflow_and_audit_mapping_is_privacy_safe():
    provider = _provider()
    plans = provider.list_reprocess_plans()
    assert set(plans[0]) == {
        "plan_id", "review_case_id", "requested_from_stage",
        "requested_target_stage", "invalidated_artifact_count",
        "retained_artifact_count", "reason_code", "requested_by", "created_at", "mode",
    }
    runs = provider.list_workflow_runs()
    assert set(runs[0]) == {"run_id", "workflow_name", "status", "started_at", "duration_ms"}
    audit = provider.list_audit_events()
    assert set(audit[0]) == {
        "event_id", "event_type", "actor_id", "document_id",
        "review_case_id", "occurred_at", "metadata",
    }
    text = json.dumps({"plans": plans, "audit": audit}).lower()
    for forbidden in ("raw_document", "raw_rows", "old_value", "new_value", "artifact_payload", "stack_trace", "storage_path"):
        assert forbidden not in text


def test_filters_ordering_and_defensive_mapping_are_preserved():
    provider = _provider()
    assert [row["document_id"] for row in provider.list_documents(status="validated")] == ["doc-001"]
    assert [row["document_id"] for row in provider.list_documents(document_type="receipt")] == ["doc-003"]
    assert [row["review_case_id"] for row in provider.list_review_cases(status="in_review", priority="high")] == ["review-001"]
    assert [row["run_id"] for row in provider.list_workflow_runs(status="failed")] == ["run-003"]
    assert [row["event_id"] for row in provider.list_audit_events(event_type="review_case_created")] == ["audit-003"]
    rows = provider.list_audit_events()
    rows[0]["metadata"]["plan_count"] = 999
    assert provider.list_audit_events()[0]["metadata"].get("plan_count") == 1


def test_unknown_ids_map_to_none_for_existing_api_404_helpers():
    provider = _provider()
    assert provider.get_document("unknown-id") is None
    assert provider.get_review_case("unknown-id") is None


def test_route_envelope_and_pagination_remain_v09_compatible():
    response = list_documents(_request(), status=None, document_type=None, limit=1, offset=1)
    assert set(response) == {"success", "data", "error", "metadata", "api_version", "request_id"}
    assert response["success"] is True
    assert response["metadata"]["pagination"] == {"limit": 1, "offset": 1, "total": 3}
    assert [row["document_id"] for row in response["data"]] == ["doc-002"]


def test_adapter_imports_only_standard_api_and_public_facade_modules():
    source_path = Path(inspect.getsourcefile(FacadeDocumentIntelligenceProvider))
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden = {
        "document_engine", "entity_runtime", "matching_runtime", "review_runtime",
        "storage", "streamlit", "telemetry", "transform", "transforms",
        "flowsync", "competitor",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {alias.name.split(".")[0].lower() for alias in node.names} & forbidden
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            assert node.module.split(".")[0].lower() not in forbidden


def test_adapter_exposes_no_mutation_methods():
    public = {
        name for name, value in inspect.getmembers(FacadeDocumentIntelligenceProvider, inspect.isfunction)
        if not name.startswith("_")
    }
    assert public
    assert all(name.startswith(("get_", "list_")) for name in public)
