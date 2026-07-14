import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.providers.upload_provider import ReadOnlyUploadProvider
from src.api.document_intelligence.routers.uploads import get_upload, list_uploads


def _request(application, method="GET"):
    request = Request({"type": "http", "method": method, "path": "/", "headers": [], "app": application})
    request.state.request_id = "request-upload-001"
    return request


def _application():
    application = create_document_intelligence_app()
    application.state.document_intelligence_upload_provider = ReadOnlyUploadProvider(({
        "upload_id": "upload-001", "tenant_id": "tenant-demo", "filename": "invoice.pdf",
        "file_type": "pdf", "file_size_bytes": 1024, "source": "api", "status": "received",
        "received_at": "2026-07-14T10:00:00Z",
    },))
    return application


def test_upload_get_routes_return_safe_standard_envelopes():
    request = _request(_application())
    collection = list_uploads(request, limit=50, offset=0)
    detail = get_upload("upload-001", request)

    assert collection["metadata"]["pagination"]["total"] == 1
    assert detail["data"]["upload_id"] == "upload-001"
    assert "tenant_id" not in detail["data"]


def test_missing_upload_uses_safe_not_found_error():
    with pytest.raises(DocumentIntelligenceAPIError) as missing:
        get_upload("missing", _request(create_document_intelligence_app()))
    assert missing.value.status_code == 404
    assert missing.value.code == "upload_not_found"
    assert missing.value.message == "Upload was not found."


def test_default_upload_history_is_empty_safe_envelope():
    result = list_uploads(_request(create_document_intelligence_app()), limit=50, offset=0)
    assert result["data"] == []
    assert result["metadata"]["pagination"]["total"] == 0

