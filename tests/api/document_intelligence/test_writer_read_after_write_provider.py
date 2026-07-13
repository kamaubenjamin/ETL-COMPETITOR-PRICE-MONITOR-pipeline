import json

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.providers.facade_provider import FacadeDocumentIntelligenceProvider
from src.document_state import compose_document_state
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.document_state.persistence import PersistenceConfig

from tests.document_state.writers.read_after_write_fixtures import T5, write_representative_lifecycle


def _provider():
    composition = compose_document_state(PersistenceConfig("in_memory"))
    write_representative_lifecycle(composition)
    facade = DocumentStateQueryFacadeAdapter(composition.reader, snapshot_at=T5)
    return FacadeDocumentIntelligenceProvider(facade)


def test_writer_state_maps_to_existing_v09_api_provider_shapes():
    provider = _provider()
    document = provider.get_document("doc-raw-001")
    assert set(document) == {"document_id", "filename", "document_type", "status", "confidence", "current_stage", "received_at"}
    assert set(provider.list_processing("doc-raw-001")[0]) == {"stage", "status", "occurred_at"}
    assert set(provider.list_validation("doc-raw-001")[0]) == {"issue_id", "severity", "field", "rule_id", "code", "message"}
    assert set(provider.list_matching("doc-raw-001")[0]) == {"match_id", "entity_type", "candidate_id", "confidence", "status"}
    assert set(provider.list_corrections("review-001")[0]) == {
        "correction_id", "review_case_id", "field_path", "operation", "reason_code",
        "actor_id", "occurred_at", "source_stage",
    }
    assert len(provider.list_reprocess_plans()) == 1
    assert len(provider.list_workflow_runs(status="succeeded")) == 1
    assert len(provider.list_audit_events(event_type="validation_completed")) == 1


def test_api_provider_filters_and_defensive_results_remain_compatible():
    provider = _provider()
    assert len(provider.list_documents(status="received", document_type="invoice")) == 1
    assert len(provider.list_review_cases(status="review_required", priority="high")) == 1
    rows = provider.list_audit_events()
    rows[0]["metadata"]["attempt"] = 999
    assert provider.list_audit_events()[0]["metadata"].get("attempt") != 999


def test_api_provider_projection_is_privacy_safe():
    provider = _provider()
    payload = {
        "documents": provider.list_documents(),
        "processing": provider.list_processing("doc-raw-001"),
        "validation": provider.list_validation("doc-raw-001"),
        "matching": provider.list_matching("doc-raw-001"),
        "reviews": provider.list_review_cases(),
        "corrections": provider.list_corrections("review-001"),
        "reprocess": provider.list_reprocess_plans(),
        "workflows": provider.list_workflow_runs(),
        "audit": provider.list_audit_events(),
    }
    text = json.dumps(payload).lower()
    for forbidden in ("raw_document", "raw_rows", "old_value", "new_value", "artifact_payload", "storage_path", "credential", "stack_trace"):
        assert forbidden not in text


def test_document_intelligence_api_remains_get_only():
    app = create_document_intelligence_app()
    for route in app.routes:
        if getattr(route, "path", "").startswith("/api/v1"):
            assert set(route.methods or ()) <= {"GET", "HEAD"}
