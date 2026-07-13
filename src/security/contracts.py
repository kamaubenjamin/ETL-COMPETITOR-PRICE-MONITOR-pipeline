"""Provider-neutral immutable security contract primitives."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
MAX_ID_LENGTH = 128
MAX_STRING_LENGTH = 256
MAX_METADATA_ITEMS = 32
MAX_METADATA_KEY_LENGTH = 64
MAX_ACCESS_TAGS = 32

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FORBIDDEN_METADATA_PARTS = (
    "authorization",
    "cookie",
    "credential",
    "exception",
    "password",
    "secret",
    "stack",
    "storage_path",
    "token",
    "traceback",
)


def bounded_string(value: Any, field_name: str, *, maximum: int = MAX_STRING_LENGTH) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{field_name} must be a bounded non-empty string")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field_name} contains unsupported characters")
    return value


def optional_string(value: Any, field_name: str, *, maximum: int = MAX_STRING_LENGTH) -> str | None:
    return None if value is None else bounded_string(value, field_name, maximum=maximum)


def stable_id(value: Any, field_name: str) -> str:
    safe = bounded_string(value, field_name, maximum=MAX_ID_LENGTH)
    if not _ID.fullmatch(safe):
        raise ValueError(f"{field_name} must be an opaque identifier")
    return safe


def validate_safe_metadata(value: Mapping[str, Any] | None) -> Mapping[str, JsonScalar]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping) or len(value) > MAX_METADATA_ITEMS:
        raise ValueError("metadata must be a bounded mapping")
    safe: dict[str, JsonScalar] = {}
    for key, item in value.items():
        safe_key = bounded_string(key, "metadata key", maximum=MAX_METADATA_KEY_LENGTH)
        normalized_key = safe_key.lower().replace("-", "_")
        if any(part in normalized_key for part in _FORBIDDEN_METADATA_PARTS):
            raise ValueError("metadata key is not allowed")
        if item is not None and (isinstance(item, (dict, list, tuple, set, bytes)) or not isinstance(item, (str, int, float, bool))):
            raise ValueError("metadata values must be JSON scalars")
        if isinstance(item, str):
            item = bounded_string(item, "metadata value")
        safe[safe_key] = item
    return MappingProxyType(dict(sorted(safe.items())))


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, SecurityContract):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, frozenset, set)):
        return [_json_value(item) for item in value]
    return value


class SecurityContract:
    """Pure serialization helper for frozen security dataclasses."""

    def to_dict(self) -> dict[str, Any]:
        return {item.name: _json_value(getattr(self, item.name)) for item in fields(self)}


def _ordered_ids(values: Any, field_name: str, *, maximum: int = 64) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValueError(f"{field_name} must be a collection")
    try:
        items = tuple(values)
    except TypeError:
        raise ValueError(f"{field_name} must be a collection") from None
    if len(items) > maximum:
        raise ValueError(f"{field_name} is too large")
    return tuple(sorted({stable_id(item, field_name) for item in items}))


@dataclass(frozen=True, slots=True)
class TenantScope(SecurityContract):
    """Verified tenant/workspace scope assigned to a principal."""

    tenant_ids: tuple[str, ...] = ()
    workspace_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_ids", _ordered_ids(self.tenant_ids, "tenant_id"))
        object.__setattr__(self, "workspace_ids", _ordered_ids(self.workspace_ids, "workspace_id"))

    def allows_tenant(self, tenant_id: str) -> bool:
        return stable_id(tenant_id, "tenant_id") in self.tenant_ids


@dataclass(frozen=True, slots=True)
class ResourceScope(SecurityContract):
    """Payload-free resource identity evaluated by policy."""

    resource_type: str
    tenant_id: str | None = None
    resource_id: str | None = None
    workspace_id: str | None = None
    access_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "resource_type", bounded_string(self.resource_type, "resource_type", maximum=64))
        if self.tenant_id is not None:
            object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if self.resource_id is not None:
            object.__setattr__(self, "resource_id", stable_id(self.resource_id, "resource_id"))
        if self.workspace_id is not None:
            object.__setattr__(self, "workspace_id", stable_id(self.workspace_id, "workspace_id"))
        tags = _ordered_ids(self.access_tags, "access_tag", maximum=MAX_ACCESS_TAGS)
        object.__setattr__(self, "access_tags", tags)


@dataclass(frozen=True, slots=True)
class ActorAttribution(SecurityContract):
    """Safe verified actor reference for future writes and audit records."""

    principal_id: str
    principal_type: str
    tenant_id: str
    request_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "principal_id", stable_id(self.principal_id, "principal_id"))
        object.__setattr__(self, "principal_type", bounded_string(self.principal_type, "principal_type", maximum=32))
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if self.request_id is not None:
            object.__setattr__(self, "request_id", stable_id(self.request_id, "request_id"))

