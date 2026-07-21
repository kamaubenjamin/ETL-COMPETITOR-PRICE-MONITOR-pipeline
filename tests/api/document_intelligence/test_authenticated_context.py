import pytest

from tests.api.document_intelligence.asgi_client import asgi_request
from tests.api.document_intelligence.supabase_auth_helpers import application, token


@pytest.mark.parametrize("authorization", [None, "Basic fixture", "Bearer", "Bearer "])
def test_protected_route_requires_well_formed_bearer_credentials(authorization):
    headers = {} if authorization is None else {"Authorization": authorization}
    response = asgi_request(application(), "GET", "/api/v1/session", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_valid_token_builds_safe_authenticated_session_context():
    response = asgi_request(
        application(), "GET", "/api/v1/session", headers={"Authorization": f"Bearer {token()}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["authenticated"] is True
    assert data["tenant_name"] == "FlowSync UAT"
    assert data["tenant_slug"] == "flowsync-uat"
    assert data["role"] == "owner"
    assert "workflow:publish" in data["permissions"]
    assert "tenant_id" not in data
    assert "user_id" not in data


def test_membership_resolution_reads_authoritative_tenant_slug():
    captured = []
    response = asgi_request(
        application(capture=captured),
        "GET",
        "/api/v1/session",
        headers={"Authorization": f"Bearer {token()}"},
    )
    membership_request = next(
        request for request in captured if request.url.path.endswith("/app_tenant_memberships")
    )

    assert response.status_code == 200
    assert membership_request.url.params["select"] == (
        "tenant_id,role,status,app_tenants!inner(name,slug,status)"
    )


def test_health_routes_remain_public_without_external_calls():
    captured = []
    app = application(capture=captured)
    for path in ("/health", "/api/v1/health"):
        response = asgi_request(app, "GET", path)
        assert response.status_code == 200
    assert captured == []


@pytest.mark.parametrize("path", ["/api/v1/status", "/api/v1/documents", "/api/v1/workflow-definitions"])
def test_hosted_application_routes_require_authentication(path):
    response = asgi_request(application(), "GET", path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_local_identity_and_tenant_overrides_are_rejected_in_uat():
    response = asgi_request(
        application(),
        "GET",
        "/api/v1/session",
        headers={
            "Authorization": f"Bearer {token()}",
            "x-local-identity": "admin",
            "x-tenant-id": "tenant-other",
        },
    )
    assert response.status_code == 403


def test_external_jwks_failure_is_safely_mapped():
    sensitive = token()
    response = asgi_request(
        application(jwks_status=503), "GET", "/api/v1/session", headers={"Authorization": f"Bearer {sensitive}"}
    )
    assert response.status_code == 503
    assert sensitive.encode("ascii") not in response.body
