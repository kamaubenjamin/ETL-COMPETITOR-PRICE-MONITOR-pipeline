"""Privacy-safe errors for durable Document State persistence."""

from __future__ import annotations

from enum import Enum

from ..privacy import optional_string


class PersistenceErrorCode(str, Enum):
    INVALID_BACKEND = "invalid_backend"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_MIGRATION = "invalid_migration"
    MIGRATION_CONFLICT = "migration_conflict"
    CONNECTION_UNAVAILABLE = "connection_unavailable"
    TRANSACTION_FAILED = "transaction_failed"
    INTERNAL_ERROR = "internal_error"


_SAFE_MESSAGES = {
    PersistenceErrorCode.INVALID_BACKEND: "Persistence backend configuration is invalid.",
    PersistenceErrorCode.INVALID_SCHEMA: "Persistence schema metadata is invalid.",
    PersistenceErrorCode.INVALID_MIGRATION: "Persistence migration metadata is invalid.",
    PersistenceErrorCode.MIGRATION_CONFLICT: "Persistence migration conflict was detected.",
    PersistenceErrorCode.CONNECTION_UNAVAILABLE: "Persistence connection is unavailable.",
    PersistenceErrorCode.TRANSACTION_FAILED: "Persistence transaction could not be completed.",
    PersistenceErrorCode.INTERNAL_ERROR: "Persistence operation could not be completed.",
}


class PersistenceError(Exception):
    def __init__(self, code: PersistenceErrorCode | str, *, field: str | None = None) -> None:
        try:
            safe_code = code if isinstance(code, PersistenceErrorCode) else PersistenceErrorCode(code)
        except ValueError as exc:
            raise ValueError("unsupported persistence error code") from exc
        self.code = safe_code.value
        self.field = optional_string(field, "field", maximum=64)
        self.message = _SAFE_MESSAGES[safe_code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "field": self.field}
