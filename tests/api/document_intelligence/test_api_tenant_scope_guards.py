import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.routers.documents import get_document, list_documents
from src.security import Permission, TenantScope, service_account_principal
from src.security.providers import LocalIdentityProvider, LocalProviderMode, create_local_demo_provider


def _app(*, allow_cross_tenant=False, provider=None):
    return create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO, allow_cross_tenant=allow_cross_tenant),
        identity_provider=provider or create_local_demo_provider("tenant-demo"),
    )


def _request(app, identity, tenant=None):
    headers = [(b"x-local-identity", identity.encode("ascii"))]
    if tenant is not None:
        headers.append((b"x-tenant-id", tenant.encode("ascii")))
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "app": app})
    request.state.request_id = "request-tenant-guard"
    return request


def _documents(request):
    return list_documents(request, status=None, document_type=None, limit=50, offset=0)


def test_viewer_list_is_narrowed_to_authorized_tenant_without_public_tenant_fields():
    response = _documents(_request(_app(), "viewer"))
    assert [item["document_id"] for item in response["data"]] == ["doc-001"]
    assert all("tenant_id" not in item and "owner_principal_id" not in item for item in response["data"])


def test_client_tenant_filter_cannot_broaden_tenant_admin_scope():
    with pytest.raises(DocumentIntelligenceAPIError) as raised:
        _documents(_request(_app(), "tenant-admin", "tenant-alt"))
    assert raised.value.status_code == 403
    assert raised.value.code == "authorization_denied"


def test_platform_admin_cross_tenant_requires_explicit_app_configuration():
    with pytest.raises(DocumentIntelligenceAPIError) as denied:
        _documents(_request(_app(), "platform-admin", "tenant-alt"))
    assert denied.value.status_code == 403

    allowed = _documents(_request(_app(allow_cross_tenant=True), "platform-admin", "tenant-alt"))
    assert [item["document_id"] for item in allowed["data"]] == ["doc-003"]


def test_service_account_requires_explicit_list_permission_and_tenant_scope():
    with pytest.raises(DocumentIntelligenceAPIError) as denied:
        _documents(_request(_app(), "service-account"))
    assert denied.value.status_code == 403

    provider = LocalIdentityProvider(
        {
            "svc-list": service_account_principal(
                "svc-list",
                tenant_scope=TenantScope(("tenant-demo",)),
                permissions=(Permission.DOCUMENT_LIST,),
            )
        },
        mode=LocalProviderMode.TEST,
    )
    allowed = _documents(_request(_app(provider=provider), "svc-list"))
    assert [item["document_id"] for item in allowed["data"]] == ["doc-001"]


def test_authenticated_cross_tenant_detail_is_concealed_as_not_found():
    with pytest.raises(DocumentIntelligenceAPIError) as raised:
        get_document("doc-003", _request(_app(), "viewer", "tenant-alt"))
    assert raised.value.status_code == 404
    assert raised.value.code == "resource_not_found"
    assert "doc-003" not in raised.value.message
