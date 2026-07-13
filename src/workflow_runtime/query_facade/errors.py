"""Stable privacy-safe errors for Workflow Query Facade contracts."""

from __future__ import annotations

from enum import Enum


class QueryErrorCode(str, Enum):
    INVALID_QUERY = "invalid_query"
    NOT_FOUND = "not_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    INTERNAL_ERROR = "internal_error"


_SAFE_MESSAGES = {
    QueryErrorCode.INVALID_QUERY: "Query parameters are invalid.",
    QueryErrorCode.NOT_FOUND: "Requested record was not found.",
    QueryErrorCode.SOURCE_UNAVAILABLE: "Query source is unavailable.",
    QueryErrorCode.INTERNAL_ERROR: "Query could not be completed.",
}


class QueryFacadeError(Exception):
    """Coded facade error that never accepts raw exception text."""

    def __init__(self, code: QueryErrorCode | str, *, field: str | None = None) -> None:
        try:
            safe_code = code if isinstance(code, QueryErrorCode) else QueryErrorCode(code)
        except ValueError as exc:
            raise ValueError("unsupported query error code") from exc
        if field is not None and (not isinstance(field, str) or not field or len(field) > 64):
            raise ValueError("field must be a bounded non-empty string")
        self.code = safe_code.value
        self.field = field
        self.message = _SAFE_MESSAGES[safe_code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "field": self.field}
