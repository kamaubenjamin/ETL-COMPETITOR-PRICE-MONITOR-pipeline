"""Standard-library privacy and serialization primitives for Workflow Studio."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields
from datetime import datetime, timezone
from enum import Enum
import math
import re
from types import MappingProxyType
from typing import Any, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
SafeArgumentValue: TypeAlias = JsonScalar | tuple[JsonScalar, ...]

MAX_ID_LENGTH = 128
MAX_TEXT_LENGTH = 256
MAX_DESCRIPTION_LENGTH = 1024
MAX_METADATA_ITEMS = 20
MAX_METADATA_KEY_LENGTH = 64
MAX_METADATA_VALUE_LENGTH = 256
MAX_ARGUMENT_ITEMS = 32
MAX_SCALAR_LIST_ITEMS = 100
MAX_HINT_ITEMS = 32

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\[\])?(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\])?)*$")

_UNSAFE_KEY_PARTS = (
    "authorization", "backend", "claim", "code", "command", "content", "cookie", "credential",
    "document_bytes", "exception", "file_path", "filesystem", "password", "payload",
    "private_key", "python", "javascript", "raw", "script", "secret", "sql", "stack",
    "storage_path", "token", "traceback", "function_body", "source_code",
)
_UNSAFE_PATH_PARTS = {
    "_internal", "internal", "system", "security", "auth", "authorization", "claims",
    "credentials", "password", "secret", "token",
}
_CODE_LIKE = re.compile(
    r"(?:__import__|\beval\s*\(|\bexec\s*\(|\bos\.system\b|\bsubprocess\b|"
    r"\bpowershell\b|\bcmd\.exe\b|\bselect\s+.+\s+from\b|\binsert\s+into\b|"
    r"\bdelete\s+from\b|\bupdate\s+.+\s+set\b|https?://|[A-Za-z]:[\\/])",
    re.IGNORECASE,
)


def bounded_text(value: Any, field_name: str, *, maximum: int = MAX_TEXT_LENGTH, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value):
        raise ValueError(f"{field_name} must be a bounded string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field_name} contains unsupported characters")
    return value


def optional_text(value: Any, field_name: str, *, maximum: int = MAX_TEXT_LENGTH) -> str | None:
    return None if value is None else bounded_text(value, field_name, maximum=maximum)


def stable_id(value: Any, field_name: str) -> str:
    result = bounded_text(value, field_name, maximum=MAX_ID_LENGTH)
    if not _ID.fullmatch(result):
        raise ValueError(f"{field_name} must be a safe identifier")
    return result


def optional_id(value: Any, field_name: str) -> str | None:
    return None if value is None else stable_id(value, field_name)


def safe_code(value: Any, field_name: str = "code") -> str:
    result = bounded_text(value, field_name, maximum=64)
    if not _CODE.fullmatch(result):
        raise ValueError(f"{field_name} must be a safe code")
    return result


def version_label(value: Any, field_name: str = "version") -> str:
    result = bounded_text(value, field_name, maximum=32)
    if not _VERSION.fullmatch(result):
        raise ValueError(f"{field_name} must be a safe version label")
    return result


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


def non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def positive_integer(value: Any, field_name: str) -> int:
    result = non_negative_integer(value, field_name)
    if result == 0:
        raise ValueError(f"{field_name} must be positive")
    return result


def logical_path(value: Any, field_name: str) -> str:
    result = bounded_text(value, field_name, maximum=256)
    if not _PATH.fullmatch(result):
        raise ValueError(f"{field_name} must be a safe logical path")
    if any(part.removesuffix("[]").lower() in _UNSAFE_PATH_PARTS for part in result.split(".")):
        raise ValueError(f"{field_name} contains a protected path segment")
    return result


def safe_string_tuple(value: Sequence[Any] | None, field_name: str, *, maximum_items: int = MAX_HINT_ITEMS) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or len(value) > maximum_items:
        raise ValueError(f"{field_name} must be a bounded string sequence")
    result = tuple(stable_id(item, field_name) for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def safe_scalar(value: Any, field_name: str, *, reject_code_like: bool = False) -> JsonScalar:
    if value is not None and (isinstance(value, (bytes, bytearray, memoryview, Mapping, Sequence)) or callable(value)):
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a JSON-safe scalar")
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError(f"{field_name} must be a JSON-safe scalar")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    if isinstance(value, str):
        value = bounded_text(value, field_name, maximum=MAX_METADATA_VALUE_LENGTH, allow_empty=True)
        if reject_code_like and _CODE_LIKE.search(value):
            raise ValueError(f"{field_name} contains prohibited executable or external configuration")
    return value


def _safe_key(value: Any, field_name: str) -> str:
    key = bounded_text(value, field_name, maximum=MAX_METADATA_KEY_LENGTH)
    normalized = key.lower().replace("-", "_").replace(" ", "_")
    if any(part in normalized for part in _UNSAFE_KEY_PARTS):
        raise ValueError(f"{field_name} is sensitive")
    return key


def safe_metadata(value: Mapping[str, Any] | None) -> Mapping[str, JsonScalar]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping) or len(value) > MAX_METADATA_ITEMS:
        raise ValueError("metadata must be a bounded mapping")
    result: dict[str, JsonScalar] = {}
    for key, item in value.items():
        safe_key = _safe_key(key, "metadata key")
        result[safe_key] = safe_scalar(item, "metadata value", reject_code_like=True)
    return MappingProxyType(dict(sorted(result.items())))


def safe_arguments(value: Mapping[str, Any] | None) -> Mapping[str, SafeArgumentValue]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping) or len(value) > MAX_ARGUMENT_ITEMS:
        raise ValueError("arguments must be a bounded mapping")
    result: dict[str, SafeArgumentValue] = {}
    for key, item in value.items():
        safe_key = _safe_key(key, "argument key")
        if isinstance(item, (list, tuple)):
            if len(item) > MAX_SCALAR_LIST_ITEMS:
                raise ValueError("argument scalar list is too large")
            result[safe_key] = tuple(safe_scalar(part, "argument value", reject_code_like=True) for part in item)
        else:
            result[safe_key] = safe_scalar(item, "argument value", reject_code_like=True)
    return MappingProxyType(dict(sorted(result.items())))


def safe_condition_value(value: Any, field_name: str = "condition value") -> SafeArgumentValue:
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_SCALAR_LIST_ITEMS:
            raise ValueError(f"{field_name} is too large")
        return tuple(safe_scalar(item, field_name, reject_code_like=True) for item in value)
    return safe_scalar(value, field_name, reject_code_like=True)


def _json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, StudioContract):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    return value


class StudioContract:
    def to_dict(self) -> dict[str, Any]:
        return {item.name: _json(getattr(self, item.name)) for item in fields(self)}
