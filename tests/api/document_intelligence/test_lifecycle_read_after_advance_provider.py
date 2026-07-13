import json

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.providers.facade_provider import FacadeDocumentIntelligenceProvider
from src.document_state import compose_document_state
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.document_state.persistence import PersistenceConfig

from tests.document_state.lifecycle.read_after_advance_fixtures import (
    SNAPSHOT_AT,
    write_advanced_lifecycle,
)


EXPECTED_DOCUMENT_KEYS = {
    "document_id",
    "filename",
    "document_type",
    "status",
    "confidence",
    "current_stage",
    "received_at",
}


def _provider():
    composition = compose_document_state(PersistenceConfig("in_memory"))
    write_advanced_lifecycle(composition)
    facade = DocumentStateQueryFacadeAdapter(composition.reader, snapshot_at=SNAPSHOT_AT)
    return FacadeDocumentIntelligenceProvider(facade)


def test_advanced_projection_preserves_v09_api_provider_shapes_and_filters():
    provider = _provider()
    exported = provider.list_documents(status="exported", document_type="invoice")
    failed = provider.list_documents(status="failed", document_type="receipt")

    assert len(exported) == len(failed) == 1
    assert set(exported[0]) == EXPECTED_DOCUMENT_KEYS
    assert (exported[0]["status"], exported[0]["current_stage"]) == ("exported", "export")
    assert (failed[0]["status"], failed[0]["current_stage"]) == ("failed", "workflow")
    assert len(provider.list_review_cases(status="review_required", priority="high")) == 1
    assert len(provider.list_workflow_runs(status="succeeded")) == 1
    assert len(provider.list_workflow_runs(status="failed")) == 1
    assert len(provider.list_audit_events(event_type="validation_completed")) == 1


def test_advanced_api_projection_is_defensive_and_privacy_safe():
    provider = _provider()
    rows = provider.list_audit_events()
    rows[0]["metadata"]["attempt"] = 999
    assert provider.list_audit_events()[0]["metadata"].get("attempt") != 999

    payload = json.dumps(
        {
            "documents": provider.list_documents(),
            "reviews": provider.list_review_cases(),
            "workflows": provider.list_workflow_runs(),
            "audit": provider.list_audit_events(),
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


def test_document_intelligence_routes_remain_get_only():
    app = create_document_intelligence_app()
    for route in app.routes:
        if getattr(route, "path", "").startswith("/api/v1"):
            assert set(route.methods or ()) <= {"GET", "HEAD"}
