"""Privacy rules for bounded Review Runtime metadata."""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from .errors import INVALID_TYPE, INVALID_VALUE, UNSAFE_METADATA, ReviewRuntimeError

MAX_METADATA_ENTRIES = 20
MAX_METADATA_STRING_LENGTH = 256

ALLOWED_METADATA_KEYS = frozenset(
    {
        "attempt",
        "case_type",
        "candidate_count",
        "confidence_bucket",
        "contract_name",
        "contract_version",
        "correlation_id",
        "error_code",
        "field_count",
        "invalidated_count",
        "issue_count",
        "retained_count",
        "priority_reason",
        "reason_code",
        "requested_from_stage",
        "requested_target_stage",
        "retryable",
        "source",
        "source_artifact_type",
        "source_artifact_version",
        "stage_run_id",
        "status",
        "dry_run",
        "workflow_id",
        "workflow_run_id",
    }
)

SENSITIVE_METADATA_TERMS = frozenset(
    {
        "address",
        "authorization",
        "customer",
        "document",
        "email",
        "name",
        "ocr",
        "password",
        "payload",
        "phone",
        "price",
        "raw",
        "row",
        "secret",
        "supplier",
        "token",
        "value",
    }
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(term in normalized for term in SENSITIVE_METADATA_TERMS)


def _safe_scalar(value: Any, path: tuple[str | int, ...]) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and len(value) > MAX_METADATA_STRING_LENGTH:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                f"Metadata strings must not exceed {MAX_METADATA_STRING_LENGTH} characters.",
                path,
            )
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ReviewRuntimeError(
        INVALID_TYPE,
        "Metadata values must be JSON scalar values.",
        path,
    )


def validate_safe_metadata(
    metadata: Mapping[str, Any] | None,
    path: tuple[str | int, ...] = ("metadata",),
) -> Mapping[str, Any]:
    """Return an immutable copy after strict allowlist validation."""

    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise ReviewRuntimeError(INVALID_TYPE, "Metadata must be an object.", path)
    if len(metadata) > MAX_METADATA_ENTRIES:
        raise ReviewRuntimeError(
            INVALID_VALUE,
            f"Metadata must not exceed {MAX_METADATA_ENTRIES} entries.",
            path,
        )

    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise ReviewRuntimeError(INVALID_TYPE, "Metadata keys must be strings.", path)
        if key not in ALLOWED_METADATA_KEYS or _is_sensitive_key(key):
            raise ReviewRuntimeError(
                UNSAFE_METADATA,
                f"Metadata key '{key}' is not allowed.",
                (*path, key),
            )
        safe[key] = _safe_scalar(value, (*path, key))
    return MappingProxyType(safe)


def metadata_to_dict(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return dict(metadata)
