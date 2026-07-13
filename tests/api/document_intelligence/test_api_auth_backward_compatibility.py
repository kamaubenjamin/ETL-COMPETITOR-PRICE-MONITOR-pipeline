import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.routers.documents import list_documents
from src.security.providers import create_local_demo_provider


def _request(app, *, identity=None, tenant=None):
    headers = []
    if identity is not None:
        headers.append((b"x-local-identity", identity.encode("ascii")))
    if tenant is not None:
        headers.append((b"x-tenant-id", tenant.encode("ascii")))
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "app": app})
    request.state.request_id = "request-auth-compat"
    return request


def test_default_app_preserves_unauthenticated_local_preview_behavior():
    app = create_document_intelligence_app()
    response = list_documents(_request(app), status=None, document_type=None, limit=50, offset=0)
    assert response["success"] is True
    assert response["metadata"]["pagination"]["total"] == 3
    assert all("tenant_id" not in row for row in response["data"])


def test_auth_headers_are_ignored_when_auth_mode_is_disabled():
    app = create_document_intelligence_app()
    response = list_documents(
        _request(app, identity="unknown", tenant="tenant-alt"),
        status=None,
        document_type=None,
        limit=50,
        offset=0,
    )
    assert response["metadata"]["pagination"]["total"] == 3


def test_local_provider_requires_explicit_local_demo_mode():
    provider = create_local_demo_provider()
    with pytest.raises(ValueError, match="local identity provider"):
        create_document_intelligence_app(
            auth_config=APIAuthConfig(APIAuthMode.PRODUCTION),
            identity_provider=provider,
        )
    with pytest.raises(ValueError, match="disabled auth"):
        create_document_intelligence_app(identity_provider=provider)
    with pytest.raises(ValueError, match="requires an identity provider"):
        create_document_intelligence_app(auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO))
