import json

import pytest

from src.ui.streamlit.api_client import DocumentIntelligenceAPIClient


def _success_envelope():
    return {
        "success": True,
        "data": [],
        "error": None,
        "metadata": {},
        "api_version": "v1",
        "request_id": "request-test",
    }


def _capturing_transport(captured):
    def send(request, timeout):
        captured.update({key.lower(): value for key, value in request.header_items()})
        return 200, json.dumps(_success_envelope()).encode("utf-8")

    return send


def test_api_preview_sends_no_identity_header_by_default():
    captured = {}
    client = DocumentIntelligenceAPIClient(
        "http://127.0.0.1:8001",
        transport=_capturing_transport(captured),
    )
    client.get("/api/v1/documents")
    assert "x-local-identity" not in captured


@pytest.mark.parametrize(
    "identity",
    ["anonymous", "viewer", "reviewer", "tenant-admin", "platform-admin", "service-account"],
)
def test_api_preview_sends_only_allowlisted_local_identity_header(identity):
    captured = {}
    client = DocumentIntelligenceAPIClient(
        "http://127.0.0.1:8001",
        auth_preview_identity=identity,
        transport=_capturing_transport(captured),
    )
    client.get("/api/v1/documents")
    assert captured["x-local-identity"] == identity
    assert "authorization" not in captured
    assert "x-tenant-id" not in captured


def test_api_preview_rejects_unknown_identity_configuration():
    with pytest.raises(ValueError, match="identity"):
        DocumentIntelligenceAPIClient(
            "http://127.0.0.1:8001",
            auth_preview_identity="custom-admin",
        )

