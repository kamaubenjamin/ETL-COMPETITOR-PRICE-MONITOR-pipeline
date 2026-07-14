import pytest
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.providers.upload_provider import ReadOnlyUploadProvider
from src.api.document_intelligence.routers.uploads import upload_document
from src.security.providers import create_local_demo_provider


def test_provider_validates_metadata_but_does_not_claim_staging_or_ingestion():
    provider = ReadOnlyUploadProvider()
    command, validation = provider.validate_request(
        {"filename": "invoice.pdf", "file_size_bytes": 100, "file_type": "pdf"},
        tenant_id="tenant-demo", actor_id="tenant-admin", request_id="request-001",
    )
    assert validation.valid
    assert command.to_dict().get("artifact_reference") is None
    assert not hasattr(provider, "stage")
    assert not hasattr(provider, "activate")


def test_authorized_api_still_returns_staging_not_enabled_and_cannot_supply_reference():
    application = create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )
    request = Request({
        "type": "http", "method": "POST", "path": "/", "app": application,
        "headers": [(b"x-local-identity", b"tenant-admin"), (b"x-tenant-id", b"tenant-demo")],
    })
    request.state.request_id = "request-activation-provider"
    payload = {"filename": "invoice.pdf", "file_size_bytes": 100, "file_type": "pdf"}
    with pytest.raises(DocumentIntelligenceAPIError) as disabled:
        upload_document(request, payload)
    assert disabled.value.code == "upload_staging_not_enabled"

    with pytest.raises(DocumentIntelligenceAPIError) as rejected:
        upload_document(request, {**payload, "artifact_reference": "client-controlled"})
    assert rejected.value.code == "invalid_upload_metadata"

