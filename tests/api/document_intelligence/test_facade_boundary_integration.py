import ast
import asyncio
import inspect
import json
from pathlib import Path

import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.middleware import request_context_middleware
from src.api.document_intelligence.providers import api_local_provider, facade_provider
from src.api.document_intelligence.providers.facade_provider import FacadeDocumentIntelligenceProvider
from src.api.document_intelligence.routers.documents import list_documents
from src.workflow_runtime.query_facade import InMemoryWorkflowQueryFacade, QueryFacadeError


V09_PATHS = {
    "/health", "/api/v1/health", "/api/v1/status", "/api/v1/documents",
    "/api/v1/documents/{document_id}", "/api/v1/documents/{document_id}/processing",
    "/api/v1/documents/{document_id}/validation", "/api/v1/documents/{document_id}/matching",
    "/api/v1/review-cases", "/api/v1/review-cases/{review_case_id}",
    "/api/v1/review-cases/{review_case_id}/corrections", "/api/v1/reprocess-plans",
    "/api/v1/workflow-runs", "/api/v1/audit-events",
}
SENSITIVE_KEYS = {
    "artifact_payload", "document_content", "new_value", "old_value", "raw_document",
    "raw_rows", "source_row", "stack_trace", "storage_path",
}


class FailingFacade(InMemoryWorkflowQueryFacade):
    def __init__(self, code, *, field=None):
        super().__init__()
        self.code = code
        self.field = field

    def list_documents(self, query, page):
        raise QueryFacadeError(self.code, field=self.field)

    def get_document(self, document_id):
        raise QueryFacadeError(self.code, field=self.field)


def _request(request_id="request-facade-boundary-001"):
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/documents", "headers": []})
    request.state.request_id = request_id
    return request


def _assert_safe_projection(value):
    if isinstance(value, dict):
        assert not {str(key).lower() for key in value} & SENSITIVE_KEYS
        for nested in value.values():
            _assert_safe_projection(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_safe_projection(nested)


def test_adapter_requires_structural_workflow_query_facade_port():
    with pytest.raises(ValueError, match="WorkflowQueryFacadePort"):
        FacadeDocumentIntelligenceProvider(object())


@pytest.mark.parametrize(
    ("code", "field", "status_code"),
    [("invalid_query", "status", 400), ("source_unavailable", None, 503), ("internal_error", None, 500)],
)
def test_facade_errors_translate_to_bounded_api_errors(code, field, status_code):
    provider = FacadeDocumentIntelligenceProvider(FailingFacade(code, field=field))
    with pytest.raises(DocumentIntelligenceAPIError) as raised:
        provider.list_documents()
    error = raised.value
    assert (error.code, error.status_code) == (code, status_code)
    assert error.message in {
        "Query parameters are invalid.", "Query source is unavailable.", "Query could not be completed.",
    }
    assert error.details == ({"field": field} if field else {})
    assert "payload" not in str(error).lower()


def test_facade_not_found_preserves_existing_api_404_path():
    provider = FacadeDocumentIntelligenceProvider(FailingFacade("not_found"))
    assert provider.get_document("private-document-id") is None


def test_facade_and_local_providers_preserve_v09_top_level_payload_shapes():
    reads = (
        ("list_documents", {}), ("list_processing", {"document_id": "doc-001"}),
        ("list_validation", {"document_id": "doc-002"}),
        ("list_matching", {"document_id": "doc-002"}), ("list_review_cases", {}),
        ("list_corrections", {"review_case_id": "review-001"}),
        ("list_reprocess_plans", {}), ("list_workflow_runs", {}), ("list_audit_events", {}),
    )
    for method_name, kwargs in reads:
        expected = getattr(api_local_provider, method_name)(**kwargs)
        actual = getattr(facade_provider, method_name)(**kwargs)
        assert actual and expected
        assert set(actual[0]) == set(expected[0]), method_name


def test_all_facade_api_projections_are_json_compatible_and_privacy_safe():
    payload = {
        "documents": facade_provider.list_documents(),
        "processing": facade_provider.list_processing("doc-001"),
        "validation": facade_provider.list_validation("doc-002"),
        "matching": facade_provider.list_matching("doc-002"),
        "reviews": facade_provider.list_review_cases(),
        "corrections": facade_provider.list_corrections("review-001"),
        "reprocess": facade_provider.list_reprocess_plans(),
        "workflows": facade_provider.list_workflow_runs(),
        "audit": facade_provider.list_audit_events(),
    }
    _assert_safe_projection(payload)
    json.dumps(payload)


def test_v09_paths_methods_envelope_and_pagination_remain_unchanged():
    schema = create_document_intelligence_app().openapi()
    assert V09_PATHS <= set(schema["paths"])
    assert all(set(schema["paths"][path]) == {"get"} for path in V09_PATHS)
    response = list_documents(_request(), status=None, document_type=None, limit=1, offset=0)
    assert set(response) == {"success", "data", "error", "metadata", "api_version", "request_id"}
    assert response["metadata"]["pagination"] == {"limit": 1, "offset": 0, "total": 3}


def test_request_id_and_security_headers_survive_facade_response():
    async def call_next(request):
        body = list_documents(request, status=None, document_type=None, limit=1, offset=0)
        from starlette.responses import JSONResponse
        return JSONResponse(body)

    request = Request({
        "type": "http", "method": "GET", "path": "/api/v1/documents",
        "headers": [(b"x-request-id", b"facade-request-001")],
    })
    response = asyncio.run(request_context_middleware(request, call_next))
    payload = json.loads(response.body)
    assert payload["request_id"] == "facade-request-001"
    assert response.headers["x-request-id"] == "facade-request-001"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


def test_adapter_imports_only_standard_api_error_and_public_facade_modules():
    path = Path(inspect.getsourcefile(FacadeDocumentIntelligenceProvider))
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    absolute = set()
    relative = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            absolute.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative.add(node.module)
            elif node.module:
                absolute.add(node.module)
    assert absolute <= {"__future__", "collections.abc", "typing", "src.workflow_runtime.query_facade"}
    assert relative == {"errors"}
