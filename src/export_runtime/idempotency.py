"""Deterministic privacy-safe export idempotency contracts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .contracts import ExportTarget, JsonContract, fingerprint, stable_id
from .statuses import ExportOperationType


_DOMAIN = "idp.export.idempotency.v1"


@dataclass(frozen=True, slots=True)
class ExportIdempotencyKey(JsonContract):
    value: str
    algorithm: str = "sha256"
    version: str = "v1"

    def __post_init__(self) -> None:
        value = stable_id(self.value, "idempotency_key")
        if not value.startswith("exp_v1_") or len(value) != 71:
            raise ValueError("idempotency_key is invalid")
        suffix = value.removeprefix("exp_v1_")
        if any(character not in "0123456789abcdef" for character in suffix):
            raise ValueError("idempotency_key is invalid")
        object.__setattr__(self, "value", value)
        if self.algorithm != "sha256" or self.version != "v1":
            raise ValueError("idempotency key algorithm or version is invalid")

    def __str__(self) -> str:
        return self.value


def generate_export_idempotency_key(
    *,
    tenant_id: str,
    document_id: str,
    export_target: ExportTarget | str,
    payload_fingerprint: str,
    operation_type: ExportOperationType | str = ExportOperationType.EXPORT,
    operation_version: str = "v1",
) -> ExportIdempotencyKey:
    safe_tenant = stable_id(tenant_id, "tenant_id")
    safe_document = stable_id(document_id, "document_id")
    safe_target = export_target.target_id if isinstance(export_target, ExportTarget) else stable_id(export_target, "export_target")
    safe_fingerprint = fingerprint(payload_fingerprint)
    try:
        safe_operation = operation_type.value if isinstance(operation_type, ExportOperationType) else ExportOperationType(operation_type).value
    except (TypeError, ValueError):
        raise ValueError("operation_type is invalid") from None
    safe_version = stable_id(operation_version, "operation_version")
    canonical = json.dumps(
        [_DOMAIN, safe_tenant, safe_document, safe_target, safe_fingerprint, safe_operation, safe_version],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return ExportIdempotencyKey(f"exp_v1_{digest}")

