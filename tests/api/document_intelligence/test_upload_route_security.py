import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.providers.upload_provider import ReadOnlyUploadProvider
from src.api.document_intelligence.routers.uploads import list_uploads, upload_document
from src.security.providers import create_local_demo_provider


VALID = {"filename": "invoice.pdf", "file_size_bytes": 1024, "file_type": "pdf", "declared_content_type": "application/pdf"}


def _app():
    return create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )


def _request(application, identity=None, tenant=None, method="POST"):
    headers = []
    if identity:
        headers.append((b"x-local-identity", identity.encode("ascii")))
    if tenant:
        headers.append((b"x-tenant-id", tenant.encode("ascii")))
    request = Request({"type": "http", "method": method, "path": "/", "headers": headers, "app": application})
    request.state.request_id = "request-upload-security"
    return request


def test_default_disabled_mode_returns_staging_not_enabled():
    with pytest.raises(DocumentIntelligenceAPIError) as disabled:
        upload_document(_request(create_document_intelligence_app()), VALID)
    assert disabled.value.status_code == 503
    assert disabled.value.code == "upload_staging_not_enabled"
    assert disabled.value.details == {"activation": "deferred"}


def test_enabled_auth_requires_identity_and_ingest_permission():
    with pytest.raises(DocumentIntelligenceAPIError) as anonymous:
        upload_document(_request(_app()), VALID)
    assert anonymous.value.status_code == 401

    with pytest.raises(DocumentIntelligenceAPIError) as viewer:
        upload_document(_request(_app(), "viewer", "tenant-demo"), VALID)
    assert viewer.value.status_code == 403


def test_authorized_valid_metadata_is_validated_then_staging_remains_disabled():
    with pytest.raises(DocumentIntelligenceAPIError) as disabled:
        upload_document(_request(_app(), "tenant-admin", "tenant-demo"), VALID)
    assert disabled.value.status_code == 503
    assert disabled.value.code == "upload_staging_not_enabled"


def test_upload_history_is_tenant_scoped_and_tenant_id_is_not_projected():
    application = _app()
    application.state.document_intelligence_upload_provider = ReadOnlyUploadProvider((
        {"upload_id": "visible", "tenant_id": "tenant-demo", "filename": "invoice.pdf", "file_type": "pdf", "file_size_bytes": 1, "source": "api", "status": "received", "received_at": "2026-07-14T10:00:00Z"},
        {"upload_id": "hidden", "tenant_id": "tenant-other", "filename": "other.pdf", "file_type": "pdf", "file_size_bytes": 1, "source": "api", "status": "received", "received_at": "2026-07-14T10:00:00Z"},
    ))
    result = list_uploads(_request(application, "tenant-admin", "tenant-demo", "GET"), limit=50, offset=0)
    assert [item["upload_id"] for item in result["data"]] == ["visible"]
    assert "tenant_id" not in result["data"][0]


def test_provider_reports_missing_tenant_and_actor_without_trusting_payload():
    command, validation = ReadOnlyUploadProvider().validate_request(VALID, tenant_id=None, actor_id=None, request_id="req")
    assert command.tenant_id is None and command.actor_id is None
    assert [issue.code for issue in validation.issues] == ["tenant_scope_missing", "actor_missing"]

