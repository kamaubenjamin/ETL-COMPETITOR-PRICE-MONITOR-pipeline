import inspect
import json

from src.ui.streamlit.api_client import APIClientError
from src.ui.streamlit.api_provider import DocumentIntelligenceAPIProvider
from src.ui.streamlit.data_providers import DEFAULT_PROVIDER_MODE, PROVIDER_MODES


class StubClient:
    def __init__(self, responses):
        self.responses = responses
        self.paths = []

    def get(self, path, *, params=None):
        self.paths.append((path, params))
        value = self.responses[path]
        if isinstance(value, Exception):
            raise value
        return json.loads(json.dumps(value))


def _provider():
    return DocumentIntelligenceAPIProvider(
        StubClient(
            {
                "/api/v1/documents": [{"document_id": "doc-001", "filename": "invoice.pdf", "document_type": "invoice", "status": "review_required", "confidence": 0.8, "current_stage": "matching"}],
                "/api/v1/documents/doc-001/processing": [{"stage": "matching", "status": "review_required", "occurred_at": "2026-07-01T00:00:00+00:00"}],
                "/api/v1/documents/doc-001/validation": [{"severity": "warning", "field": "supplier_id", "rule_id": "required", "message": "Field requires review."}],
                "/api/v1/documents/doc-001/matching": [{"entity_type": "supplier", "candidate_id": "supplier-001", "confidence": 0.8, "status": "ambiguous"}],
                "/api/v1/review-cases": [{"review_case_id": "review-001", "reason_code": "matching_ambiguity", "priority": "high", "status": "in_review", "assigned_reviewer": "reviewer-01", "correction_count": 1, "decision_code": None, "reprocess_state": "not_requested"}],
                "/api/v1/workflow-runs": [{"run_id": "run-001", "workflow_name": "invoice_processing", "status": "running", "started_at": "2026-07-01T00:00:00+00:00", "duration_ms": None}],
                "/api/v1/audit-events": [{"event_type": "review_case_created", "actor_id": "system", "occurred_at": "2026-07-01T00:00:00+00:00", "metadata": {"reason_code": "matching_ambiguity"}}],
            }
        )
    )


def test_api_provider_maps_all_console_shapes():
    provider = _provider()
    assert provider.documents()[0]["document_id"] == "doc-001"
    assert provider.processing_statuses()[0]["document_id"] == "doc-001"
    assert provider.validation_issues()[0]["rule"] == "required"
    assert provider.matching_results()[0]["candidate_match"] == "supplier-001"
    assert provider.review_cases()[0]["decision"] == "pending"
    assert provider.workflow_runs()[0]["duration"] == "Running"
    assert provider.audit_events()[0]["safe_metadata"] == "reason_code=matching_ambiguity"
    assert provider.summary_metrics()["review_required"] == 1


def test_provider_filters_and_returns_defensive_results():
    provider = _provider()
    assert provider.documents(document_type="Invoice", status="review_required")
    rows = provider.review_cases(status="in_review")
    rows[0]["status"] = "changed"
    assert provider.review_cases(status="in_review")[0]["status"] == "in_review"


def test_api_unavailable_returns_safe_empty_state_without_local_fallback():
    provider = DocumentIntelligenceAPIProvider(
        StubClient({"/api/v1/documents": APIClientError("api_unavailable", "Document Intelligence API is unavailable.")})
    )
    assert provider.documents() == []
    assert provider.last_error_code == "api_unavailable"
    assert provider.last_error == "Document Intelligence API is unavailable."


def test_local_preview_remains_default_and_only_approved_modes_exist():
    assert DEFAULT_PROVIDER_MODE == "local_preview"
    assert PROVIDER_MODES == ("local_preview", "api_preview")


def test_api_adapter_contains_no_mutation_methods_or_competitor_imports():
    import src.ui.streamlit.api_client as client_module
    import src.ui.streamlit.api_provider as provider_module

    source = (inspect.getsource(client_module) + inspect.getsource(provider_module)).lower()
    for forbidden in ('method="post"', 'method="put"', 'method="patch"', 'method="delete"', "competitor"):
        assert forbidden not in source
