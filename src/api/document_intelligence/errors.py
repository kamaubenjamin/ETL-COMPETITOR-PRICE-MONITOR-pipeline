"""Privacy-safe API errors for the Document Intelligence foundation."""

from __future__ import annotations

from collections.abc import Mapping


class DocumentIntelligenceAPIError(Exception):
    """Bounded application error intended for safe envelope serialization."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Mapping[str, str | int | bool | None] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = dict(details or {})
