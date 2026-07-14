"""Sanitized structured export payload contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .contracts import (
    ExportTarget,
    JsonContract,
    bounded_text,
    contract_tuple,
    currency_code,
    decimal_text,
    optional_date,
    optional_id,
    optional_text,
    positive_integer,
    safe_metadata,
    stable_id,
)


@dataclass(frozen=True, slots=True)
class ExportPayloadParty(JsonContract):
    role: str
    display_name: str
    party_id: str | None = None
    external_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", stable_id(self.role, "role"))
        object.__setattr__(self, "display_name", bounded_text(self.display_name, "display_name", maximum=128))
        object.__setattr__(self, "party_id", optional_id(self.party_id, "party_id"))
        object.__setattr__(self, "external_reference", optional_id(self.external_reference, "external_reference"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ExportPayloadLine(JsonContract):
    line_id: str
    item_code: str
    quantity: str | int | float
    unit_price: str | int | float
    line_total: str | int | float
    description: str | None = None
    tax_code: str | None = None
    external_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "line_id", stable_id(self.line_id, "line_id"))
        object.__setattr__(self, "item_code", stable_id(self.item_code, "item_code"))
        object.__setattr__(self, "quantity", decimal_text(self.quantity, "quantity", positive=True))
        object.__setattr__(self, "unit_price", decimal_text(self.unit_price, "unit_price"))
        object.__setattr__(self, "line_total", decimal_text(self.line_total, "line_total"))
        object.__setattr__(self, "description", optional_text(self.description, "description", maximum=256))
        object.__setattr__(self, "tax_code", optional_id(self.tax_code, "tax_code"))
        object.__setattr__(self, "external_reference", optional_id(self.external_reference, "external_reference"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ExportPayload(JsonContract):
    payload_id: str
    document_id: str
    tenant_id: str
    export_target: ExportTarget
    currency: str
    lines: tuple[ExportPayloadLine, ...]
    schema_version: str = "v1"
    document_version: int = 1
    document_type: str | None = None
    parties: tuple[ExportPayloadParty, ...] = ()
    document_date: str | None = None
    due_date: str | None = None
    external_reference: str | None = None
    subtotal: str | int | float | None = None
    tax_total: str | int | float | None = None
    total: str | int | float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload_id", stable_id(self.payload_id, "payload_id"))
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if not isinstance(self.export_target, ExportTarget):
            raise ValueError("export_target must be an ExportTarget")
        object.__setattr__(self, "currency", currency_code(self.currency))
        object.__setattr__(self, "lines", contract_tuple(self.lines, ExportPayloadLine, "lines", allow_empty=False))
        object.__setattr__(self, "schema_version", stable_id(self.schema_version, "schema_version"))
        object.__setattr__(self, "document_version", positive_integer(self.document_version, "document_version"))
        object.__setattr__(self, "document_type", optional_id(self.document_type, "document_type"))
        object.__setattr__(self, "parties", contract_tuple(self.parties, ExportPayloadParty, "parties"))
        object.__setattr__(self, "document_date", optional_date(self.document_date, "document_date"))
        object.__setattr__(self, "due_date", optional_date(self.due_date, "due_date"))
        object.__setattr__(self, "external_reference", optional_id(self.external_reference, "external_reference"))
        for name in ("subtotal", "tax_total", "total"):
            value = getattr(self, name)
            object.__setattr__(self, name, None if value is None else decimal_text(value, name))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


def payload_fingerprint(payload: ExportPayload) -> str:
    from .fingerprints import fingerprint_export_payload

    return fingerprint_export_payload(payload)
