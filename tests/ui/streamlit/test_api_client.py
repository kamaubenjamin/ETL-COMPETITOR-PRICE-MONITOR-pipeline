import json

import pytest

from src.ui.streamlit.api_client import APIClientError, DocumentIntelligenceAPIClient


def _envelope(*, success=True, data=None, error=None):
    return {
        "success": success,
        "data": data,
        "error": error,
        "metadata": {"generated_at": "2026-07-01T00:00:00+00:00", "pagination": None},
        "api_version": "v1",
        "request_id": "request-test",
    }


def _transport(payload, status=200, captured=None):
    def send(request, timeout):
        if captured is not None:
            captured.update({"method": request.get_method(), "url": request.full_url, "timeout": timeout})
        return status, json.dumps(payload).encode("utf-8")
    return send


def test_client_parses_success_envelope_and_uses_get_only():
    captured = {}
    client = DocumentIntelligenceAPIClient(
        "http://127.0.0.1:8001",
        transport=_transport(_envelope(data=[{"document_id": "doc-001"}]), captured=captured),
    )
    assert client.get("/api/v1/documents", params={"status": "validated"}) == [{"document_id": "doc-001"}]
    assert captured["method"] == "GET"
    assert "status=validated" in captured["url"]


def test_client_parses_safe_error_envelope():
    client = DocumentIntelligenceAPIClient(
        "http://127.0.0.1:8001",
        transport=_transport(_envelope(success=False, error={"code": "not_found", "message": "Resource was not found.", "details": {}}), status=404),
    )
    with pytest.raises(APIClientError) as raised:
        client.get("/api/v1/documents/missing")
    assert raised.value.code == "not_found"
    assert raised.value.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {**_envelope(data=[]), "extra": True},
        {**_envelope(data=[]), "api_version": "v2"},
        {**_envelope(data=[]), "success": "yes"},
    ],
)
def test_client_rejects_malformed_envelopes(payload):
    client = DocumentIntelligenceAPIClient("http://127.0.0.1:8001", transport=_transport(payload))
    with pytest.raises(APIClientError, match="envelope"):
        client.get("/api/v1/documents")


def test_client_rejects_credential_bearing_or_non_http_urls():
    with pytest.raises(ValueError):
        DocumentIntelligenceAPIClient("file:///private/data")
    with pytest.raises(ValueError):
        DocumentIntelligenceAPIClient("http://user:secret@127.0.0.1:8001")
