"""Transport security policy for the local read-only API foundation."""

from __future__ import annotations

from starlette.responses import Response


CORS_POLICY = "disabled"
SECURITY_HEADERS = {
    "cache-control": "no-store",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
}


def apply_security_headers(response: Response) -> Response:
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value
    return response
