import inspect
import json

import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.routers import uploads
from src.security.providers import create_local_demo_provider


def _request():
    application = create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )
    request = Request({
        "type": "http", "method": "POST", "path": "/", "app": application,
        "headers": [(b"x-local-identity", b"tenant-admin"), (b"x-tenant-id", b"tenant-demo")],
    })
    request.state.request_id = "request-upload-privacy"
    return request


@pytest.mark.parametrize(
    ("payload", "issue"),
    [
        ({"filename": "invoice.exe", "file_size_bytes": 10, "file_type": "exe"}, "unsafe_extension"),
        ({"filename": "invoice.pdf", "file_size_bytes": 0, "file_type": "pdf"}, "upload_empty"),
        ({"filename": "../invoice.pdf", "file_size_bytes": 10, "file_type": "pdf"}, "path_traversal_detected"),
        ({"filename": "invoice.pdf", "file_size_bytes": 30 * 1024 * 1024, "file_type": "pdf"}, "upload_too_large"),
        ({"filename": "invoice.pdf", "file_size_bytes": 10, "file_type": "pdf", "declared_content_type": "text/csv"}, "mime_type_mismatch"),
    ],
)
def test_invalid_upload_metadata_returns_safe_first_issue(payload, issue):
    with pytest.raises(DocumentIntelligenceAPIError) as invalid:
        uploads.upload_document(_request(), payload)
    assert invalid.value.code == "upload_validation_failed"
    assert invalid.value.details["issue_code"] == issue
    serialized = json.dumps(invalid.value.details).lower()
    assert "invoice" not in serialized
    assert "../" not in serialized


def test_sensitive_or_nested_metadata_is_rejected_without_reflection():
    payload = {"filename": "invoice.pdf", "file_size_bytes": 10, "file_type": "pdf", "metadata": {"token": "private-secret"}}
    with pytest.raises(DocumentIntelligenceAPIError) as invalid:
        uploads.upload_document(_request(), payload)
    assert invalid.value.code == "invalid_upload_metadata"
    assert "private-secret" not in invalid.value.message
    assert "private-secret" not in str(invalid.value.details)


def test_upload_provider_and_router_import_no_ingestion_writer_export_storage_or_external_service():
    provider = __import__("src.api.document_intelligence.providers.upload_provider", fromlist=["*"])
    source = (inspect.getsource(uploads) + inspect.getsource(provider)).lower()
    for forbidden in (
        "document_engine", "document_state", "export_runtime", "ingestionpipeline", "storage",
        "sqlite", "requests", "httpx", "open(", "write_bytes", "openai", "ocr",
    ):
        assert forbidden not in source


def test_upload_openapi_contract_is_json_metadata_only_without_multipart_or_file_schema():
    operation = create_document_intelligence_app().openapi()["paths"]["/api/v1/documents/upload"]["post"]
    serialized = json.dumps(operation).lower()
    assert "application/json" in serialized
    assert "multipart/form-data" not in serialized
    assert "binary" not in serialized

