import inspect

import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.routers.audit import list_audit_events
from src.api.document_intelligence.routers.documents import get_document, list_documents
from src.api.document_intelligence.routers.reviews import list_review_cases


EXPECTED_DOMAIN_PATHS = {
    "/api/v1/documents", "/api/v1/documents/{document_id}",
    "/api/v1/documents/{document_id}/processing",
    "/api/v1/documents/{document_id}/validation",
    "/api/v1/documents/{document_id}/matching", "/api/v1/review-cases",
    "/api/v1/documents/{document_id}/purchase-order",
    "/api/v1/review-cases/{review_case_id}",
    "/api/v1/review-cases/{review_case_id}/corrections",
    "/api/v1/reprocess-plans", "/api/v1/workflow-runs", "/api/v1/audit-events",
}


def _request(request_id="request-read-001"):
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.request_id = request_id
    return request


def _test_client():
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        pytest.skip(f"TestClient optional dependency unavailable: {exc}")
    return TestClient(create_document_intelligence_app())


def test_direct_list_routes_return_filtered_paginated_envelopes():
    documents = list_documents(_request(), status="review_required", document_type=None, limit=10, offset=0)
    reviews = list_review_cases(_request(), status="in_review", priority="high", limit=10, offset=0)
    audit = list_audit_events(_request(), event_type="review_case_created", limit=10, offset=0)
    assert [row["document_id"] for row in documents["data"]] == ["doc-002"]
    assert [row["review_case_id"] for row in reviews["data"]] == ["review-001"]
    assert [row["event_id"] for row in audit["data"]] == ["audit-003"]
    assert documents["metadata"]["pagination"] == {"limit": 10, "offset": 0, "total": 1}


def test_invalid_filter_and_unknown_id_raise_safe_api_errors():
    with pytest.raises(DocumentIntelligenceAPIError) as invalid:
        list_documents(_request(), status="secret-status", document_type=None, limit=10, offset=0)
    assert invalid.value.status_code == 400
    assert invalid.value.details == {"field": "status"}
    assert "secret-status" not in invalid.value.message

    with pytest.raises(DocumentIntelligenceAPIError) as missing:
        get_document("doc-missing", _request())
    assert missing.value.status_code == 404
    assert missing.value.code == "document_not_found"
    assert missing.value.details == {}


def test_openapi_contains_expected_get_only_routes():
    schema = create_document_intelligence_app().openapi()
    assert EXPECTED_DOMAIN_PATHS <= set(schema["paths"])
    assert all(set(schema["paths"][path]) == {"get"} for path in EXPECTED_DOMAIN_PATHS)


def test_transport_endpoints_and_safe_errors_when_test_client_is_available():
    client = _test_client()
    for path in (
        "/api/v1/documents", "/api/v1/documents/doc-001",
        "/api/v1/documents/doc-001/processing", "/api/v1/documents/doc-001/validation",
        "/api/v1/documents/doc-001/matching", "/api/v1/review-cases",
        "/api/v1/review-cases/review-001", "/api/v1/review-cases/review-001/corrections",
        "/api/v1/reprocess-plans", "/api/v1/workflow-runs", "/api/v1/audit-events",
    ):
        response = client.get(path, headers={"x-request-id": "request-transport"})
        assert response.status_code == 200
        assert response.json()["success"] is True
    assert client.get("/api/v1/documents/missing").status_code == 404
    assert client.get("/api/v1/documents?status=invalid").status_code == 400
    invalid_page = client.get("/api/v1/documents?limit=0")
    assert invalid_page.status_code == 400
    assert invalid_page.json()["error"]["code"] == "invalid_request"


def test_api_package_has_no_forbidden_imports_or_sensitive_projection_names():
    modules = [
        __import__("src.api.document_intelligence.providers.local_provider", fromlist=["*"]),
        __import__("src.api.document_intelligence.routers.documents", fromlist=["*"]),
        __import__("src.api.document_intelligence.routers.reviews", fromlist=["*"]),
    ]
    source = "\n".join(inspect.getsource(module) for module in modules).lower()
    for forbidden in ("review_runtime", "document_engine", "entity_runtime", "matching_runtime", "workflow_runtime", "streamlit", "flowsync", "competitor"):
        assert forbidden not in source
