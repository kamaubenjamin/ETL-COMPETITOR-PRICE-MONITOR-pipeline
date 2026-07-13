import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.routers.health import root_health, versioned_status


HEADERS = {"x-request-id": "request-health-001"}


def _request(request_id):
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.request_id = request_id
    return request


def _test_client():
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        pytest.skip(f"TestClient optional dependency unavailable: {exc}")
    return TestClient(create_document_intelligence_app())


def test_root_and_versioned_health_return_success_envelopes():
    client = _test_client()
    root = client.get("/health", headers=HEADERS)
    versioned = client.get("/api/v1/health", headers=HEADERS)
    assert root.status_code == versioned.status_code == 200
    assert root.json()["data"] == versioned.json()["data"] == {
        "service": "document-intelligence-api",
        "status": "ok",
        "mode": "read_only_foundation",
    }
    assert root.json()["success"] is True
    assert root.json()["request_id"] == "request-health-001"
    assert root.headers["x-request-id"] == "request-health-001"


def test_status_response_is_deterministic():
    client = _test_client()
    response = client.get("/api/v1/status", headers={"x-request-id": "request-status-001"})
    assert response.status_code == 200
    assert response.json()["data"] == {
        "service_name": "document-intelligence-api",
        "api_version": "v1",
        "mode": "read_only_foundation",
        "capabilities": ["health", "pagination_metadata", "response_envelopes", "status"],
    }


def test_unknown_route_uses_privacy_safe_error_envelope():
    client = _test_client()
    response = client.get("/api/v1/private-payload", headers={"x-request-id": "request-404"})
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "Resource not found.",
        "details": {},
    }
    assert "private-payload" not in str(response.json())


def test_route_functions_serialize_health_and_status_without_transport():
    health = root_health(_request("request-direct-health"))
    status = versioned_status(_request("request-direct-status"))
    assert health["success"] is True
    assert health["data"]["status"] == "ok"
    assert status["data"] == {
        "service_name": "document-intelligence-api",
        "api_version": "v1",
        "mode": "read_only_foundation",
        "capabilities": ["health", "pagination_metadata", "response_envelopes", "status"],
    }
