"""Response builders shared by Document Intelligence API routers."""

from __future__ import annotations

from typing import Any

from .contracts import ResponseEnvelope, ResponseMetadata, SafeError


def success_response(
    data: Any,
    *,
    request_id: str,
    metadata: ResponseMetadata | None = None,
) -> dict[str, Any]:
    return ResponseEnvelope(
        success=True,
        data=data,
        error=None,
        metadata=metadata or ResponseMetadata(),
        request_id=request_id,
    ).to_dict()


def error_response(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, str | int | bool | None] | None = None,
) -> dict[str, Any]:
    return ResponseEnvelope(
        success=False,
        data=None,
        error=SafeError(code=code, message=message, details=details or {}),
        metadata=ResponseMetadata(),
        request_id=request_id,
    ).to_dict()

