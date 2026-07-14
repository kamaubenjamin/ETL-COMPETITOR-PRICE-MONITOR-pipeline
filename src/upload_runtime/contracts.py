"""Standard-library contract primitives for the upload boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from enum import Enum
import math
import re
from types import MappingProxyType
from typing import Any, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
MAX_ID_LENGTH = 128
MAX_TEXT_LENGTH = 256
MAX_FILENAME_INPUT_LENGTH = 512
MAX_METADATA_ITEMS = 20
MAX_METADATA_KEY_LENGTH = 64
MAX_METADATA_VALUE_LENGTH = 128

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_UNSAFE_KEYS = (
    "authorization", "backend_config", "backend_path", "claim", "content", "credential",
    "document_bytes", "exception", "file_bytes", "file_path", "password", "raw", "secret",
    "stack", "storage_path", "token", "traceback",
)


class UploadSource(str, Enum):
    FLOWSYNC = "flowsync"
    API = "api"
    SERVICE_ACCOUNT = "service_account"
    LOCAL_DEMO = "local_demo"


class UploadFileType(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    TXT = "txt"
    EML = "eml"


class UploadStatus(str, Enum):
    RECEIVED = "received"
    VALIDATION_FAILED = "validation_failed"
    VALIDATED = "validated"
    STAGED = "staged"
    INGESTION_REQUESTED = "ingestion_requested"
    PROCESSING_STARTED = "processing_started"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE_PREVENTED = "duplicate_prevented"


def bounded_text(value: Any, field_name: str, *, maximum: int = MAX_TEXT_LENGTH, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{field_name} must be a bounded string")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must be a bounded non-empty string")
    if any(ord(character) < 32 for character in value):
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
    return None if value is None or value == "" else stable_id(value, field_name)


def safe_code(value: Any, field_name: str = "code") -> str:
    result = bounded_text(value, field_name, maximum=64)
    if not _CODE.fullmatch(result):
        raise ValueError(f"{field_name} must be a safe code")
    return result


def sha256_digest(value: Any, field_name: str = "content_fingerprint") -> str:
    result = bounded_text(value, field_name, maximum=64).lower()
    if not _DIGEST.fullmatch(result):
        raise ValueError(f"{field_name} must be a SHA-256 digest")
    return result


def optional_timestamp(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    result = bounded_text(value, field_name, maximum=64)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field_name} must be a UTC timestamp")
    return result


def utc_timestamp(value: Any, field_name: str) -> str:
    result = optional_timestamp(value, field_name)
    if result is None:
        raise ValueError(f"{field_name} is required")
    return result


def non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def safe_metadata(value: Mapping[str, Any] | None) -> Mapping[str, JsonScalar]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping) or len(value) > MAX_METADATA_ITEMS:
        raise ValueError("metadata must be a bounded mapping")
    result: dict[str, JsonScalar] = {}
    for key, item in value.items():
        safe_key = bounded_text(key, "metadata key", maximum=MAX_METADATA_KEY_LENGTH)
        normalized = safe_key.lower().replace("-", "_").replace(" ", "_")
        if any(part in normalized for part in _UNSAFE_KEYS):
            raise ValueError("metadata key is unsafe")
        if item is not None and (isinstance(item, (bytes, bytearray, memoryview, Mapping, list, tuple, set)) or not isinstance(item, (str, int, float, bool))):
            raise ValueError("metadata values must be JSON scalars")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("metadata numbers must be finite")
        if isinstance(item, str):
            item = bounded_text(item, "metadata value", maximum=MAX_METADATA_VALUE_LENGTH)
        result[safe_key] = item
    return MappingProxyType(dict(sorted(result.items())))


def _json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UploadContract):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    return value


class UploadContract:
    def to_dict(self) -> dict[str, Any]:
        return {item.name: _json(getattr(self, item.name)) for item in fields(self)}


@dataclass(frozen=True, slots=True)
class UploadArtifactReference(UploadContract):
    reference_id: str
    provider_code: str
    file_type: UploadFileType | str
    size_bytes: int
    staged_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_id", stable_id(self.reference_id, "reference_id"))
        object.__setattr__(self, "provider_code", safe_code(self.provider_code, "provider_code"))
        try:
            file_type = self.file_type if isinstance(self.file_type, UploadFileType) else UploadFileType(self.file_type)
        except (TypeError, ValueError):
            raise ValueError("file_type is invalid") from None
        object.__setattr__(self, "file_type", file_type.value)
        object.__setattr__(self, "size_bytes", non_negative_integer(self.size_bytes, "size_bytes"))
        if self.size_bytes == 0:
            raise ValueError("size_bytes must be positive")
        object.__setattr__(self, "staged_at", utc_timestamp(self.staged_at, "staged_at"))


@dataclass(frozen=True, slots=True)
class UploadProcessingIntent(UploadContract):
    upload_id: str
    document_id: str
    operation_version: str = "v1"
    requested_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "upload_id", stable_id(self.upload_id, "upload_id"))
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        object.__setattr__(self, "operation_version", stable_id(self.operation_version, "operation_version"))
        object.__setattr__(self, "requested_at", optional_timestamp(self.requested_at, "requested_at"))
