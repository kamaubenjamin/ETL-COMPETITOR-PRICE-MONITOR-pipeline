"""Request context and fail-safe response middleware."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from .responses import error_response
from .security import apply_security_headers


MAX_REQUEST_ID_LENGTH = 64
_REQUEST_ID_CHARACTER = re.compile(r"[A-Za-z0-9._:-]")


def sanitize_request_id(value: str | None) -> str:
    if value:
        sanitized = "".join(_REQUEST_ID_CHARACTER.findall(value))[:MAX_REQUEST_ID_LENGTH]
        if sanitized:
            return sanitized
    return f"req_{uuid4().hex}"


async def request_context_middleware(request: Request, call_next):
    request_id = sanitize_request_id(request.headers.get("x-request-id"))
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(
            status_code=500,
            content=error_response(
                code="internal_error",
                message="Request could not be completed.",
                request_id=request_id,
            ),
        )
    response.headers["x-request-id"] = request_id
    return apply_security_headers(response)
