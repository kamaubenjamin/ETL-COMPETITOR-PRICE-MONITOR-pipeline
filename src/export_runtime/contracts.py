"""Shared validation and foundational export runtime contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
import math
import re
from types import MappingProxyType
from typing import Any, TypeVar

from .statuses import ExportTargetType


MAX_ID_LENGTH = 128
MAX_TEXT_LENGTH = 256
MAX_MESSAGE_LENGTH = 160
MAX_METADATA_KEYS = 20
MAX_METADATA_KEY_LENGTH = 64
MAX_METADATA_STRING_LENGTH = 128
MAX_COLLECTION_ITEMS = 500
MAX_SAFE_INTEGER = 9_007_199_254_740_991

JsonScalar = str | int | float | bool | None

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UNSAFE_KEY_TOKENS = (
    "adapter_response",
    "artifact_payload",
    "authorization",
    "backend_config",
    "backend_path",
    "claim",
    "connection_string",
    "correction_value",
    "credential",
    "document_bytes",
    "document_content",
    "document_text",
    "exception",
    "file_contents",
    "file_path",
    "raw_file",
    "new_value",
    "ocr_output",
    "old_value",
    "password",
    "raw_document",
    "raw_payload",
    "raw_row",
    "raw_rows",
    "request_body",
    "response_body",
    "secret",
    "stack_trace",
    "storage_path",
    "token",
    "traceback",
    "vendor_response",
)
_UNSAFE_TEXT_MARKERS = (
    "authorization:",
    "bearer ",
    "password=",
    "secret=",
    "stack trace",
    "traceback (most recent call last)",
    "token=",
)

E = TypeVar("E", bound=Enum)


def normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def is_unsafe_key(value: str) -> bool:
    normalized = normalize_key(value)
    return any(token == normalized or token in normalized for token in _UNSAFE_KEY_TOKENS)


def bounded_text(value: Any, field_name: str, *, maximum: int = MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    result = value.strip()
    if not result or len(result) > maximum:
        raise ValueError(f"{field_name} must be a bounded non-empty string")
    if any(ord(character) < 32 for character in result):
        raise ValueError(f"{field_name} contains unsupported characters")
    return result


def optional_text(value: Any, field_name: str, *, maximum: int = MAX_TEXT_LENGTH) -> str | None:
    return None if value is None else bounded_text(value, field_name, maximum=maximum)


def stable_id(value: Any, field_name: str) -> str:
    result = bounded_text(value, field_name, maximum=MAX_ID_LENGTH)
    if not _IDENTIFIER_PATTERN.fullmatch(result):
        raise ValueError(f"{field_name} must be a safe identifier")
    return result


def optional_id(value: Any, field_name: str) -> str | None:
    return None if value is None else stable_id(value, field_name)


def safe_code(value: Any, field_name: str) -> str:
    result = bounded_text(value, field_name, maximum=64)
    if not _CODE_PATTERN.fullmatch(result):
        raise ValueError(f"{field_name} must be a safe code")
    return result


def enum_value(value: E | str, enum_type: type[E], field_name: str) -> str:
    try:
        return value.value if isinstance(value, enum_type) else enum_type(value).value
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} is invalid") from None


def positive_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def iso_date(value: Any, field_name: str) -> str:
    result = bounded_text(value, field_name, maximum=32)
    try:
        date.fromisoformat(result)
    except ValueError:
        raise ValueError(f"{field_name} must be an ISO-8601 date") from None
    return result


def optional_date(value: Any, field_name: str) -> str | None:
    return None if value is None else iso_date(value, field_name)


def utc_timestamp(value: Any, field_name: str) -> str:
    result = bounded_text(value, field_name, maximum=64)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field_name} must be a UTC timestamp")
    return result


def optional_timestamp(value: Any, field_name: str) -> str | None:
    return None if value is None else utc_timestamp(value, field_name)


def currency_code(value: Any) -> str:
    result = bounded_text(value, "currency", maximum=3).upper()
    if not _CURRENCY_PATTERN.fullmatch(result):
        raise ValueError("currency must be a three-letter code")
    return result


def decimal_text(value: Any, field_name: str, *, positive: bool = False) -> str:
    from decimal import Decimal, InvalidOperation

    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(f"{field_name} must be a decimal value")
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{field_name} must be a decimal value") from None
    if not decimal_value.is_finite() or (positive and decimal_value <= 0):
        qualifier = "positive " if positive else ""
        raise ValueError(f"{field_name} must be a finite {qualifier}decimal value")
    normalized = format(decimal_value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return "0" if normalized in {"-0", ""} else normalized


def fingerprint(value: Any, field_name: str = "payload_fingerprint") -> str:
    result = bounded_text(value, field_name, maximum=64).lower()
    if not _FINGERPRINT_PATTERN.fullmatch(result):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return result


def safe_error_text(value: Any, field_name: str = "message") -> str:
    result = bounded_text(value, field_name, maximum=MAX_MESSAGE_LENGTH)
    lowered = result.lower()
    if any(marker in lowered for marker in _UNSAFE_TEXT_MARKERS):
        raise ValueError(f"{field_name} contains unsafe details")
    if re.search(r"(?:[A-Za-z]:\\|/home/|/var/|/etc/|\\\\)", result):
        raise ValueError(f"{field_name} contains unsafe details")
    return result


def safe_metadata(value: Mapping[str, Any] | None) -> Mapping[str, JsonScalar]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping) or len(value) > MAX_METADATA_KEYS:
        raise ValueError("metadata must be a bounded mapping")
    result: dict[str, JsonScalar] = {}
    for key, item in value.items():
        safe_key = bounded_text(key, "metadata key", maximum=MAX_METADATA_KEY_LENGTH)
        if is_unsafe_key(safe_key):
            raise ValueError("metadata key is unsafe")
        if item is not None and (isinstance(item, (Mapping, list, tuple, set)) or not isinstance(item, (str, int, float, bool))):
            raise ValueError("metadata values must be JSON scalar values")
        if isinstance(item, str):
            item = bounded_text(item, "metadata value", maximum=MAX_METADATA_STRING_LENGTH)
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("metadata numbers must be finite")
        if isinstance(item, (int, float)) and not isinstance(item, bool) and abs(item) > MAX_SAFE_INTEGER:
            raise ValueError("metadata numbers must be bounded")
        result[safe_key] = item
    return MappingProxyType(result)


def contract_tuple(value: Any, item_type: type[Any], field_name: str, *, allow_empty: bool = True) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a collection")
    result = tuple(value)
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(result) > MAX_COLLECTION_ITEMS or any(not isinstance(item, item_type) for item in result):
        raise ValueError(f"{field_name} contains invalid items")
    return result


def json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, JsonContract):
        return value.to_dict()
    if is_dataclass(value):
        return {item.name: json_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("contract contains a non-finite number")
        return value
    raise ValueError("contract contains non-JSON data")


class JsonContract:
    def to_dict(self) -> dict[str, Any]:
        return {item.name: json_value(getattr(self, item.name)) for item in fields(self)}


@dataclass(frozen=True, slots=True)
class ExportTarget(JsonContract):
    target_id: str
    target_type: ExportTargetType | str
    display_label: str
    adapter_key: str | None = None
    payload_schema: str = "export.v1"
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", stable_id(self.target_id, "target_id"))
        object.__setattr__(self, "target_type", enum_value(self.target_type, ExportTargetType, "target_type"))
        object.__setattr__(self, "display_label", bounded_text(self.display_label, "display_label", maximum=80))
        adapter_key = self.target_id if self.adapter_key is None else stable_id(self.adapter_key, "adapter_key")
        object.__setattr__(self, "adapter_key", adapter_key)
        object.__setattr__(self, "payload_schema", stable_id(self.payload_schema, "payload_schema"))
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ExportPermission(JsonContract):
    document_id: str
    tenant_id: str
    allowed: bool
    reason_code: str
    permission: str = "document:export"
    service_account: bool = False
    cross_tenant: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if not isinstance(self.allowed, bool) or not isinstance(self.service_account, bool) or not isinstance(self.cross_tenant, bool):
            raise ValueError("permission flags must be booleans")
        object.__setattr__(self, "reason_code", safe_code(self.reason_code, "reason_code"))
        if self.permission != "document:export":
            raise ValueError("permission must be document:export")


@dataclass(frozen=True, slots=True)
class ExportLifecycleDecision(JsonContract):
    permitted: bool
    target_status: str
    expected_document_version: int
    reason_code: str
    projection_pending: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.permitted, bool) or not isinstance(self.projection_pending, bool):
            raise ValueError("lifecycle decision flags must be booleans")
        object.__setattr__(self, "target_status", safe_code(self.target_status, "target_status"))
        object.__setattr__(self, "expected_document_version", positive_integer(self.expected_document_version, "expected_document_version"))
        object.__setattr__(self, "reason_code", safe_code(self.reason_code, "reason_code"))
        if self.projection_pending and not self.permitted:
            raise ValueError("projection_pending requires a permitted lifecycle decision")


@dataclass(frozen=True, slots=True)
class ExportAuditIntent(JsonContract):
    event_type: str
    document_id: str
    target_id: str
    actor_id: str
    occurred_at: str
    outcome_code: str
    attempt_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", safe_code(self.event_type, "event_type"))
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        object.__setattr__(self, "target_id", stable_id(self.target_id, "target_id"))
        object.__setattr__(self, "actor_id", stable_id(self.actor_id, "actor_id"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "outcome_code", safe_code(self.outcome_code, "outcome_code"))
        object.__setattr__(self, "attempt_id", optional_id(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))
