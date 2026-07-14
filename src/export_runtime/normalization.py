"""Pure normalization helpers for already-structured export inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from .contracts import bounded_text, currency_code, is_unsafe_key
from .payloads import ExportPayloadLine, ExportPayloadParty


def normalize_text(value: Any, field_name: str, *, maximum: int = 256) -> str:
    """Trim and collapse whitespace without changing business-significant case."""

    result = bounded_text(value, field_name, maximum=maximum)
    return " ".join(result.split())


def normalize_optional_text(value: Any, field_name: str, *, maximum: int = 256) -> str | None:
    if value is None:
        return None
    return normalize_text(value, field_name, maximum=maximum)


def normalize_currency(value: Any) -> str:
    return currency_code(value)


def normalize_date(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a date without a time component")
    if isinstance(value, date):
        return value.isoformat()
    result = bounded_text(value, field_name, maximum=32)
    try:
        return date.fromisoformat(result).isoformat()
    except ValueError:
        raise ValueError(f"{field_name} must be an ISO-8601 date") from None


def normalize_party(value: Any) -> ExportPayloadParty:
    if not isinstance(value, ExportPayloadParty):
        raise ValueError("parties must contain ExportPayloadParty values")
    return ExportPayloadParty(
        role=value.role,
        display_name=normalize_text(value.display_name, "display_name", maximum=128),
        party_id=value.party_id,
        external_reference=value.external_reference,
        metadata=dict(value.metadata),
    )


def normalize_line(value: Any) -> ExportPayloadLine:
    if not isinstance(value, ExportPayloadLine):
        raise ValueError("lines must contain ExportPayloadLine values")
    return ExportPayloadLine(
        line_id=value.line_id,
        item_code=value.item_code,
        quantity=value.quantity,
        unit_price=value.unit_price,
        line_total=value.line_total,
        description=normalize_optional_text(value.description, "description", maximum=256),
        tax_code=value.tax_code,
        external_reference=value.external_reference,
        metadata=dict(value.metadata),
    )


def contains_unsafe_input(value: Any, *, _inside_metadata: bool = False) -> bool:
    """Detect raw/sensitive or arbitrary nested candidate input before validation."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or is_unsafe_key(key):
                return True
            if _inside_metadata and isinstance(item, (Mapping, list, tuple, set)):
                return True
            if contains_unsafe_input(item, _inside_metadata=_inside_metadata or key == "metadata"):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(contains_unsafe_input(item, _inside_metadata=_inside_metadata) for item in value)
    return False


def safe_candidate_mapping(value: Any) -> bool:
    return isinstance(value, Mapping) and not contains_unsafe_input(value)
