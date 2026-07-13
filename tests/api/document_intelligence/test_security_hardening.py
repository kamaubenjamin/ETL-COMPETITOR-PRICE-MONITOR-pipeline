import asyncio
import json
import re

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.middleware import request_context_middleware, sanitize_request_id
from src.api.document_intelligence.security import CORS_POLICY, SECURITY_HEADERS


def _request(request_id=None):
    headers = [] if request_id is None else [(b"x-request-id", request_id.encode("latin-1"))]
    return Request({"type": "http", "method": "GET", "path": "/api/v1/status", "headers": headers})


def _run(request, call_next):
    return asyncio.run(request_context_middleware(request, call_next))


def test_request_id_is_generated_with_stable_safe_format_when_missing():
    first = sanitize_request_id(None)
    second = sanitize_request_id("")
    assert re.fullmatch(r"req_[0-9a-f]{32}", first)
    assert re.fullmatch(r"req_[0-9a-f]{32}", second)
    assert first != second


def test_client_request_id_is_sanitized_and_bounded():
    assert sanitize_request_id(" operator/request id:001 ") == "operatorrequestid:001"
    assert sanitize_request_id("a" * 100) == "a" * 64
    assert re.fullmatch(r"req_[0-9a-f]{32}", sanitize_request_id("///   "))


def test_middleware_propagates_request_id_and_security_headers():
    async def call_next(request):
        return JSONResponse({"request_id": request.state.request_id})

    response = _run(_request("request-ui-001"), call_next)
    payload = json.loads(response.body)
    assert payload["request_id"] == "request-ui-001"
    assert response.headers["x-request-id"] == "request-ui-001"
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_unhandled_exception_returns_safe_500_envelope_without_raw_text():
    async def call_next(request):
        raise RuntimeError("private row value and filesystem path")

    response = _run(_request("request-error-001"), call_next)
    payload = json.loads(response.body)
    assert response.status_code == 500
    assert payload["request_id"] == "request-error-001"
    assert payload["error"] == {
        "code": "internal_error",
        "message": "Request could not be completed.",
        "details": {},
    }
    assert "private row" not in response.body.decode("utf-8")
    assert "filesystem" not in response.body.decode("utf-8")
    assert "traceback" not in response.body.decode("utf-8").lower()


def test_cors_is_explicitly_disabled_and_no_cors_middleware_is_installed():
    application = create_document_intelligence_app()
    assert CORS_POLICY == "disabled"
    assert all("cors" not in item.cls.__name__.lower() for item in application.user_middleware)
