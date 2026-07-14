import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.providers.export_provider import ReadOnlyExportProvider
from src.api.document_intelligence.routers.exports import get_export_attempt, list_document_exports, list_export_attempts


def _request(application, request_id="request-export-001"):
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "app": application})
    request.state.request_id = request_id
    return request


def _application():
    application = create_document_intelligence_app()
    application.state.document_intelligence_export_provider = ReadOnlyExportProvider(({
        "attempt_id": "attempt-001", "tenant_id": "tenant-demo", "document_id": "doc-001",
        "target_id": "erp-placeholder", "target_type": "placeholder", "status": "failed",
        "result_status": "failed", "result_code": "adapter_unavailable",
        "created_at": "2026-07-14T10:00:00Z", "updated_at": "2026-07-14T10:00:00Z",
    },))
    return application


def test_export_get_routes_return_safe_standard_envelopes():
    request = _request(_application())
    document_history = list_document_exports("doc-001", request, limit=50, offset=0)
    attempts = list_export_attempts(request, limit=50, offset=0)
    attempt = get_export_attempt("attempt-001", request)

    assert document_history["data"][0]["attempt_id"] == "attempt-001"
    assert attempts["metadata"]["pagination"]["total"] == 1
    assert attempt["data"]["result_code"] == "adapter_unavailable"
    assert "tenant_id" not in attempt["data"]


def test_missing_export_attempt_raises_safe_not_found_error():
    with pytest.raises(DocumentIntelligenceAPIError) as missing:
        get_export_attempt("missing", _request(create_document_intelligence_app()))
    assert missing.value.status_code == 404
    assert missing.value.code == "export_attempt_not_found"
    assert missing.value.message == "Export attempt was not found."

