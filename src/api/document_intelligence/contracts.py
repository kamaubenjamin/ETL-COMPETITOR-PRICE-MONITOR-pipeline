"""Strict JSON-compatible contracts for the Document Intelligence API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from types import MappingProxyType
from typing import Any


API_VERSION = "v1"
MAX_PAGE_SIZE = 200
MAX_ERROR_DETAILS = 10


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_string(value: Any, field_name: str, *, max_length: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ValueError(f"{field_name} must be a non-empty bounded string")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field_name} contains unsupported characters")
    return value


def _json_value(value: Any, field_name: str = "value") -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} numbers must be finite")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item, field_name) for item in value]
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} keys must be strings")
            result[key] = _json_value(item, field_name)
        return result
    raise ValueError(f"{field_name} must be JSON-compatible")


@dataclass(frozen=True, slots=True)
class PaginationMetadata:
    limit: int
    offset: int
    total: int

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or not 1 <= self.limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        for name in ("offset", "total"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    def to_dict(self) -> dict[str, int]:
        return {"limit": self.limit, "offset": self.offset, "total": self.total}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PaginationMetadata":
        if set(payload) != {"limit", "offset", "total"}:
            raise ValueError("pagination fields are invalid")
        return cls(limit=payload["limit"], offset=payload["offset"], total=payload["total"])


@dataclass(frozen=True, slots=True)
class SafeError:
    code: str
    message: str
    details: Mapping[str, str | int | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _require_string(self.code, "code", max_length=64))
        object.__setattr__(self, "message", _require_string(self.message, "message"))
        if not isinstance(self.details, Mapping) or len(self.details) > MAX_ERROR_DETAILS:
            raise ValueError("details must be a bounded object")
        safe: dict[str, str | int | bool | None] = {}
        for key, value in self.details.items():
            safe_key = _require_string(key, "details key", max_length=64)
            if value is not None and not isinstance(value, (str, int, bool)):
                raise ValueError("detail values must be JSON scalar values")
            if isinstance(value, str) and len(value) > 128:
                raise ValueError("detail strings must be bounded")
            safe[safe_key] = value
        object.__setattr__(self, "details", MappingProxyType(safe))

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SafeError":
        if set(payload) != {"code", "message", "details"}:
            raise ValueError("error fields are invalid")
        return cls(code=payload["code"], message=payload["message"], details=payload["details"])


@dataclass(frozen=True, slots=True)
class ResponseMetadata:
    generated_at: str = field(default_factory=utc_now_iso)
    pagination: PaginationMetadata | None = None

    def __post_init__(self) -> None:
        value = _require_string(self.generated_at, "generated_at", max_length=64)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("generated_at must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("generated_at must include a timezone")
        if self.pagination is not None and not isinstance(self.pagination, PaginationMetadata):
            raise ValueError("pagination must be PaginationMetadata or null")

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "pagination": self.pagination.to_dict() if self.pagination else None,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResponseMetadata":
        if set(payload) != {"generated_at", "pagination"}:
            raise ValueError("metadata fields are invalid")
        pagination = payload["pagination"]
        return cls(
            generated_at=payload["generated_at"],
            pagination=PaginationMetadata.from_dict(pagination) if pagination is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ResponseEnvelope:
    success: bool
    data: Any
    error: SafeError | None
    metadata: ResponseMetadata
    request_id: str
    api_version: str = API_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool):
            raise ValueError("success must be a boolean")
        object.__setattr__(self, "api_version", _require_string(self.api_version, "api_version", max_length=16))
        if self.api_version != API_VERSION:
            raise ValueError("api_version is unsupported")
        object.__setattr__(self, "request_id", _require_string(self.request_id, "request_id", max_length=128))
        if not isinstance(self.metadata, ResponseMetadata):
            raise ValueError("metadata must be ResponseMetadata")
        if self.success and self.error is not None:
            raise ValueError("successful responses cannot contain an error")
        if not self.success and (self.error is None or self.data is not None):
            raise ValueError("failed responses require an error and null data")
        object.__setattr__(self, "data", _json_value(self.data, "data"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "metadata": self.metadata.to_dict(),
            "api_version": self.api_version,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResponseEnvelope":
        required = {"success", "data", "error", "metadata", "api_version", "request_id"}
        if set(payload) != required:
            raise ValueError("response envelope fields are invalid")
        error = payload["error"]
        return cls(
            success=payload["success"],
            data=payload["data"],
            error=SafeError.from_dict(error) if error is not None else None,
            metadata=ResponseMetadata.from_dict(payload["metadata"]),
            api_version=payload["api_version"],
            request_id=payload["request_id"],
        )
