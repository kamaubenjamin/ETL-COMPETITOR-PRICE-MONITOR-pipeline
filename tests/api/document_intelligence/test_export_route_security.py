import inspect

import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.providers.export_provider import ReadOnlyExportProvider
from src.api.document_intelligence.routers import exports
from src.security.providers import create_local_demo_provider


def _request():
    application = create_document_intelligence_app()
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": [], "app": application})
    request.state.request_id = "request-export-security"
    return request


@pytest.mark.parametrize("route", [exports.prepare_document_export, exports.export_document])
def test_export_mutations_are_disabled_by_default_without_authentication(route):
    with pytest.raises(DocumentIntelligenceAPIError) as disabled:
        route("doc-001", _request())
    assert disabled.value.status_code == 503
    assert disabled.value.code == "mutation_not_enabled"
    assert disabled.value.message == "Export execution is not enabled."
    assert disabled.value.details == {"activation": "deferred"}


def test_phase_five_api_router_never_imports_runtime_or_adapter_implementations():
    source = inspect.getsource(exports).lower()
    for forbidden in ("exportruntimeservice", "placeholderadapter", "successfulplaceholder", "erp", "requests", "httpx"):
        assert forbidden not in source


def test_disabled_mutation_contract_has_no_request_body_projection():
    schema = create_document_intelligence_app().openapi()
    for path in ("/api/v1/documents/{document_id}/export/prepare", "/api/v1/documents/{document_id}/export"):
        assert "requestBody" not in schema["paths"][path]["post"]


def test_export_history_is_narrowed_to_api_authorized_tenant():
    application = create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )
    application.state.document_intelligence_export_provider = ReadOnlyExportProvider((
        {"attempt_id": "visible", "tenant_id": "tenant-demo", "document_id": "doc-001", "target_id": "target", "target_type": "placeholder", "status": "failed", "created_at": "2026-07-14T10:00:00Z", "updated_at": "2026-07-14T10:00:00Z"},
        {"attempt_id": "hidden", "tenant_id": "tenant-other", "document_id": "doc-002", "target_id": "target", "target_type": "placeholder", "status": "failed", "created_at": "2026-07-14T10:00:00Z", "updated_at": "2026-07-14T10:00:00Z"},
    ))
    request = Request({
        "type": "http", "method": "GET", "path": "/", "app": application,
        "headers": [(b"x-local-identity", b"tenant-admin"), (b"x-tenant-id", b"tenant-demo")],
    })
    request.state.request_id = "request-tenant-export"

    result = exports.list_export_attempts(request, limit=50, offset=0)
    assert [item["attempt_id"] for item in result["data"]] == ["visible"]
