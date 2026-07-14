import pytest

from src.api.document_intelligence.app import create_document_intelligence_app


def _test_client():
    try:
        from fastapi.testclient import TestClient
    except RuntimeError as exc:
        pytest.skip(f"TestClient optional dependency unavailable: {exc}")
    return TestClient(create_document_intelligence_app())


def test_openapi_registers_get_only_for_all_v09_paths():
    schema = create_document_intelligence_app().openapi()
    assert schema["paths"]
    disabled_posts = {
        "/api/v1/documents/{document_id}/export/prepare",
        "/api/v1/documents/{document_id}/export",
        "/api/v1/documents/upload",
    }
    assert all(
        set(operations) == ({"post"} if path in disabled_posts else {"get"})
        for path, operations in schema["paths"].items()
    )


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_mutation_methods_return_safe_405_when_transport_is_available(method):
    client = _test_client()
    response = getattr(client, method)("/api/v1/status", headers={"x-request-id": "request-method-001"})
    assert response.status_code == 405
    assert response.json()["error"] == {
        "code": "method_not_allowed",
        "message": "Method is not allowed.",
        "details": {},
    }
    assert response.json()["request_id"] == "request-method-001"
    assert response.headers["x-request-id"] == "request-method-001"


def test_unknown_route_returns_safe_404_when_transport_is_available():
    client = _test_client()
    response = client.get("/api/v1/missing-private-value", headers={"x-request-id": "request-missing-001"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "missing-private-value" not in response.text
