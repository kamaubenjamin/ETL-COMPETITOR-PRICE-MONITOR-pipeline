import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.providers.upload_provider import ReadOnlyUploadProvider
from src.api.document_intelligence.routers.uploads import get_document_processing_status, get_upload_progress, upload_document
from src.security.providers import create_local_demo_provider


def _application():
    app = create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )
    app.state.document_intelligence_upload_provider = ReadOnlyUploadProvider((
        {"upload_id": "visible", "document_id": "document-visible", "tenant_id": "tenant-demo", "filename": "a.pdf", "file_type": "pdf", "file_size_bytes": 1, "source": "api", "status": "received", "received_at": "2026-07-14T10:00:00Z"},
        {"upload_id": "hidden", "document_id": "document-hidden", "tenant_id": "tenant-other", "filename": "b.pdf", "file_type": "pdf", "file_size_bytes": 1, "source": "api", "status": "received", "received_at": "2026-07-14T10:00:00Z"},
    ))
    return app


def _request(app, identity="tenant-admin", tenant="tenant-demo", method="GET"):
    headers = [(b"x-local-identity", identity.encode()), (b"x-tenant-id", tenant.encode())]
    request = Request({"type": "http", "method": method, "path": "/", "headers": headers, "app": app})
    request.state.request_id = "request-progress-security"
    return request


def test_cross_tenant_upload_and_document_status_are_concealed():
    request = _request(_application())
    with pytest.raises(DocumentIntelligenceAPIError) as upload_missing:
        get_upload_progress("hidden", request)
    with pytest.raises(DocumentIntelligenceAPIError) as document_missing:
        get_document_processing_status("document-hidden", request)
    assert upload_missing.value.status_code == document_missing.value.status_code == 404


def test_progress_routes_require_authorized_read_identity():
    app = _application()
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "app": app})
    request.state.request_id = "anonymous-progress"
    with pytest.raises(DocumentIntelligenceAPIError) as denied:
        get_upload_progress("visible", request)
    assert denied.value.status_code == 401


def test_reading_progress_does_not_enable_upload_or_ingestion_mutation():
    app = _application()
    progress = get_upload_progress("visible", _request(app))
    assert progress["data"]["status"] == "received"
    payload = {"filename": "invoice.pdf", "file_size_bytes": 10, "file_type": "pdf"}
    with pytest.raises(DocumentIntelligenceAPIError) as staging_disabled:
        upload_document(_request(app, method="POST"), payload)
    assert staging_disabled.value.code == "upload_staging_not_enabled"

