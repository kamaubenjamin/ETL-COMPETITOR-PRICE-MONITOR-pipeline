import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.responses import error_response
from src.api.document_intelligence.routers.audit import list_audit_events
from src.api.document_intelligence.routers.documents import list_documents
from src.api.document_intelligence.routers.reviews import list_review_cases
from src.api.document_intelligence.routers.workflows import list_workflow_runs
from src.security.providers import create_local_demo_provider


def _app(*, allow_cross_tenant=False):
    return create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO, allow_cross_tenant=allow_cross_tenant),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )


def _request(app, identity=None, tenant=None):
    headers = []
    if identity is not None:
        headers.append((b"x-local-identity", identity.encode("ascii")))
    if tenant is not None:
        headers.append((b"x-tenant-id", tenant.encode("ascii")))
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "app": app})
    request.state.request_id = "request-auth-guard"
    return request


def test_auth_enabled_document_list_denies_missing_and_unknown_identity_safely():
    for identity in (None, "unknown-identity"):
        with pytest.raises(DocumentIntelligenceAPIError) as raised:
            list_documents(_request(_app(), identity), status=None, document_type=None, limit=50, offset=0)
        assert raised.value.status_code == 401
        payload = error_response(
            code=raised.value.code,
            message=raised.value.message,
            request_id="request-auth-guard",
        )
        assert payload["error"]["code"] == "authentication_required"
        assert "unknown-identity" not in str(payload)


def test_endpoint_permission_map_for_review_workflow_and_audit_reads():
    app = _app()
    with pytest.raises(DocumentIntelligenceAPIError) as review_denied:
        list_review_cases(_request(app, "viewer"), status=None, priority=None, limit=50, offset=0)
    assert review_denied.value.status_code == 403

    reviews = list_review_cases(_request(app, "reviewer"), status=None, priority=None, limit=50, offset=0)
    workflows = list_workflow_runs(_request(app, "viewer"), status=None, limit=50, offset=0)
    assert [item["review_case_id"] for item in reviews["data"]] == ["review-003"]
    assert [item["run_id"] for item in workflows["data"]] == ["run-002", "run-001"]

    with pytest.raises(DocumentIntelligenceAPIError) as audit_denied:
        list_audit_events(_request(app, "viewer"), event_type=None, limit=50, offset=0)
    assert audit_denied.value.status_code == 403
    audit = list_audit_events(_request(app, "tenant-admin"), event_type=None, limit=50, offset=0)
    assert all(item["document_id"] in {"doc-001", "doc-002"} for item in audit["data"])


def test_identity_provider_failure_returns_safe_unavailable_error():
    class FailingProvider:
        def resolve(self, identity_id):
            raise RuntimeError("raw provider token and stack trace")

    app = create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.AUTHENTICATED),
        identity_provider=FailingProvider(),
    )
    with pytest.raises(DocumentIntelligenceAPIError) as raised:
        list_documents(_request(app, "viewer"), status=None, document_type=None, limit=50, offset=0)
    assert raised.value.status_code == 503
    assert raised.value.code == "identity_provider_unavailable"
    assert "token" not in raised.value.message
    assert "stack" not in raised.value.message
