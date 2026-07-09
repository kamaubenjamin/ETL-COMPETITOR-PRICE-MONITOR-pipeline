"""Privacy helpers for observability records."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .registry import ALLOWED_EVENT_ATTRIBUTES, ALLOWED_METRIC_DIMENSIONS

REDACTED = "[REDACTED]"
MAX_STRING_LENGTH = 256

SENSITIVE_KEYWORDS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "credential",
        "customer_name",
        "database_url",
        "document_text",
        "erp_identifier",
        "file_contents",
        "invoice_number",
        "ocr_output",
        "password",
        "price",
        "product_name",
        "raw_document",
        "raw_entity",
        "secret",
        "supplier_name",
        "token",
    }
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*=\s*bearer\s+)[^,\s]+"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*=\s*([^,\s]+)"),
)


def is_sensitive_key(key: str) -> bool:
    """Return True when a field name is unsafe for observability output."""

    normalized = key.lower().replace("-", "_")
    return any(keyword in normalized for keyword in SENSITIVE_KEYWORDS)


def sanitize_string(value: str) -> str:
    """Redact obvious secrets and bound string size."""

    sanitized = value
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1)}{REDACTED}", sanitized)
    if len(sanitized) > MAX_STRING_LENGTH:
        return f"{sanitized[:MAX_STRING_LENGTH]}..."
    return sanitized


def sanitize_value(value: Any) -> Any:
    """Return a JSON-compatible sanitized value."""

    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, (list, tuple)):
        return [sanitize_value(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_value(item)
            for key, item in value.items()
            if not is_sensitive_key(str(key))
        }
    return sanitize_string(str(value))


def sanitize_attributes(attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    """Filter event attributes through the explicit allowlist."""

    if not attributes:
        return {}
    sanitized: dict[str, Any] = {}
    for key, value in attributes.items():
        key_str = str(key)
        if key_str not in ALLOWED_EVENT_ATTRIBUTES:
            continue
        if is_sensitive_key(key_str):
            continue
        sanitized[key_str] = sanitize_value(value)
    return sanitized


def sanitize_dimensions(dimensions: Mapping[str, Any] | None) -> dict[str, Any]:
    """Sanitize metric dimensions after registry validation."""

    if not dimensions:
        return {}
    sanitized: dict[str, Any] = {}
    for key, value in dimensions.items():
        key_str = str(key)
        if key_str not in ALLOWED_METRIC_DIMENSIONS:
            continue
        if is_sensitive_key(key_str):
            continue
        sanitized[key_str] = sanitize_value(value)
    return sanitized


def sanitize_error_message(message: str) -> str:
    """Sanitize error messages for observability records."""

    return sanitize_string(message)
