import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.providers.upload_provider import ReadOnlyUploadProvider
from src.api.document_intelligence.routers.uploads import (
    get_document_processing_status,
    get_upload_progress,
    get_upload_timeline,
)
from src.security.providers import create_local_demo_provider


def _application():
    app = create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )
    app.state.document_intelligence_upload_provider = ReadOnlyUploadProvider(({
        "upload_id": "upload-1", "document_id": "document-1", "tenant_id": "tenant-demo",
        "filename": "invoice.pdf", "file_type": "pdf", "file_size_bytes": 10, "source": "api",
        "status": "ingestion_requested", "received_at": "2026-07-14T10:00:00Z",
        "updated_at": "2026-07-14T10:01:00Z",
    },))
    return app


def _request(app):
    headers = [(b"x-local-identity", b"tenant-admin"), (b"x-tenant-id", b"tenant-demo")]
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "app": app})
    request.state.request_id = "request-progress-1"
    return request


def test_progress_and_document_status_routes_use_safe_envelopes():
    request = _request(_application())
    progress = get_upload_progress("upload-1", request)
    status = get_document_processing_status("document-1", request)
    timeline = get_upload_timeline("upload-1", request)
    assert progress["data"]["current_stage"] == "ingestion_requested"
    assert status["data"]["document_id"] == "document-1"
    assert timeline["data"] == {"upload_id": "upload-1", "events": []}
    assert "tenant_id" not in progress["data"]


def test_missing_progress_and_document_status_are_safe_not_found():
    request = _request(_application())
    with pytest.raises(DocumentIntelligenceAPIError) as missing_upload:
        get_upload_progress("missing", request)
    with pytest.raises(DocumentIntelligenceAPIError) as missing_document:
        get_document_processing_status("missing", request)
    assert missing_upload.value.status_code == 404
    assert missing_document.value.status_code == 404
    assert "missing" not in missing_upload.value.message.lower()


def test_phase4_routes_are_registered_as_get_only():
    paths = _application().openapi()["paths"]
    assert set(paths["/api/v1/uploads/{upload_id}/progress"]) == {"get"}
    assert set(paths["/api/v1/documents/{document_id}/processing-status"]) == {"get"}
