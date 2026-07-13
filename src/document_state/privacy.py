"""Privacy and validation helpers for persistence-neutral document state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
import math
from types import MappingProxyType
from typing import Any, TypeVar


MAX_ID_LENGTH = 128
MAX_STRING_LENGTH = 256
MAX_METADATA_KEYS = 20
MAX_METADATA_KEY_LENGTH = 64
MAX_METADATA_STRING_LENGTH = 128

JsonScalar = str | int | float | bool | None

ALLOWED_METADATA_KEYS = frozenset(
    {
        "attempt",
        "correlation_id",
        "correction_count",
        "document_type",
        "issue_count",
        "match_count",
        "mode",
        "operation_count",
        "plan_count",
        "reason_code",
        "source_runtime",
        "source_stage",
        "stage_count",
        "status",
        "trace_id",
        "workflow_name",
    }
)

UNSAFE_FIELD_TOKENS = frozenset(
    {
        "artifact_payload",
        "authorization",
        "connection_string",
        "correction_value",
        "credential",
        "document_bytes",
        "document_content",
        "document_text",
        "file_contents",
        "new_value",
        "ocr_output",
        "old_value",
        "password",
        "raw_document",
        "raw_row",
        "raw_rows",
        "rows",
        "secret",
        "stack_trace",
        "storage_path",
        "token",
        "traceback",
    }
)


def normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def is_unsafe_field_name(value: str) -> bool:
    normalized = normalize_key(value)
    return any(token == normalized or token in normalized for token in UNSAFE_FIELD_TOKENS)


def reject_unsafe_fields(values: Mapping[str, Any]) -> None:
    if not isinstance(values, Mapping):
        raise ValueError("fields must be a mapping")
    for key in values:
        if not isinstance(key, str) or is_unsafe_field_name(key):
            raise ValueError("field name is not safe for document state")


def bounded_string(value: Any, field_name: str, *, maximum: int = MAX_STRING_LENGTH) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{field_name} must be a bounded non-empty string")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field_name} contains unsupported characters")
    return value


def optional_string(value: Any, field_name: str, *, maximum: int = MAX_STRING_LENGTH) -> str | None:
    return None if value is None else bounded_string(value, field_name, maximum=maximum)


def stable_id(value: Any, field_name: str) -> str:
    return bounded_string(value, field_name, maximum=MAX_ID_LENGTH)


def utc_timestamp(value: Any, field_name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    safe = bounded_string(value, field_name, maximum=64)
    try:
        parsed = datetime.fromisoformat(safe.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field_name} must be a UTC timestamp")
    return safe


def non_negative_count(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def positive_version(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("version must be a positive integer")
    return value


def confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a finite number between 0 and 1")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError("confidence must be a finite number between 0 and 1")
    return result


E = TypeVar("E", bound=Enum)


def enum_value(value: E | str, enum_type: type[E], field_name: str) -> str:
    try:
        return value.value if isinstance(value, enum_type) else enum_type(value).value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} is invalid") from exc


def optional_enum_value(value: E | str | None, enum_type: type[E], field_name: str) -> str | None:
    return None if value is None else enum_value(value, enum_type, field_name)


def validate_safe_metadata(value: Mapping[str, Any] | None) -> Mapping[str, JsonScalar]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping) or len(value) > MAX_METADATA_KEYS:
        raise ValueError("metadata must be a bounded mapping")
    safe: dict[str, JsonScalar] = {}
    for key, item in value.items():
        safe_key = bounded_string(key, "metadata key", maximum=MAX_METADATA_KEY_LENGTH)
        if is_unsafe_field_name(safe_key) or safe_key not in ALLOWED_METADATA_KEYS:
            raise ValueError("metadata key is not allowlisted")
        if item is not None and (isinstance(item, (list, tuple, dict, set)) or not isinstance(item, (str, int, float, bool))):
            raise ValueError("metadata values must be JSON scalar values")
        if isinstance(item, str) and len(item) > MAX_METADATA_STRING_LENGTH:
            raise ValueError("metadata string values must be bounded")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("metadata numbers must be finite")
        if isinstance(item, (int, float)) and not isinstance(item, bool) and abs(item) > 9_007_199_254_740_991:
            raise ValueError("metadata numbers must be bounded")
        safe[safe_key] = item
    return MappingProxyType(safe)


def json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("record contains a non-finite number")
        return value
    raise ValueError("record contains non-JSON data")
