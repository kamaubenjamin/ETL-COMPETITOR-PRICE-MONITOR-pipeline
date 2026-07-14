"""Deterministic builder for sanitized ExportPayload contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .contracts import ExportTarget, JsonContract, safe_metadata, stable_id
from .errors import ExportErrorCode
from .fingerprints import fingerprint_export_payload
from .normalization import (
    contains_unsafe_input,
    normalize_currency,
    normalize_date,
    normalize_line,
    normalize_optional_text,
    normalize_party,
)
from .payloads import ExportPayload, ExportPayloadLine, ExportPayloadParty
from .readiness import ExportReadinessIssue


class ExportPayloadBuildStatus(str, Enum):
    SUCCESS = "success"
    INVALID_PAYLOAD = "invalid_payload"
    PRIVACY_REJECTED = "privacy_rejected"


_BUILD_MESSAGES = {
    ExportPayloadBuildStatus.SUCCESS: "Export payload was built successfully.",
    ExportPayloadBuildStatus.INVALID_PAYLOAD: "Export payload input is invalid.",
    ExportPayloadBuildStatus.PRIVACY_REJECTED: "Export payload input violates privacy requirements.",
}


@dataclass(frozen=True, slots=True)
class ExportPayloadBuildCommand:
    document_id: Any
    tenant_id: Any
    export_target: Any
    currency: Any
    lines: Any
    payload_id: Any = None
    schema_version: Any = "v1"
    document_version: Any = 1
    document_type: Any = None
    parties: Any = ()
    document_date: Any = None
    due_date: Any = None
    external_reference: Any = None
    subtotal: Any = None
    tax_total: Any = None
    total: Any = None
    metadata: Any = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExportPayloadBuildResult(JsonContract):
    status: ExportPayloadBuildStatus | str
    payload: ExportPayload | None
    error_code: str | None
    message: str
    readiness_issue: ExportReadinessIssue | None

    def __post_init__(self) -> None:
        try:
            status = self.status if isinstance(self.status, ExportPayloadBuildStatus) else ExportPayloadBuildStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("payload build status is invalid") from None
        object.__setattr__(self, "status", status.value)
        if self.message != _BUILD_MESSAGES[status]:
            raise ValueError("payload build message is invalid")
        if status == ExportPayloadBuildStatus.SUCCESS:
            if not isinstance(self.payload, ExportPayload) or self.error_code is not None or self.readiness_issue is not None:
                raise ValueError("successful payload build result is invalid")
        else:
            if self.payload is not None or self.error_code is None:
                raise ValueError("failed payload build result is invalid")
            if not isinstance(self.readiness_issue, ExportReadinessIssue) or self.readiness_issue.code != "payload_invalid":
                raise ValueError("failed payload build requires payload_invalid readiness issue")

    @property
    def succeeded(self) -> bool:
        return self.status == ExportPayloadBuildStatus.SUCCESS.value


def _failure(status: ExportPayloadBuildStatus) -> ExportPayloadBuildResult:
    error_code = (
        ExportErrorCode.PRIVACY_REJECTED.value
        if status == ExportPayloadBuildStatus.PRIVACY_REJECTED
        else ExportErrorCode.INVALID_PAYLOAD.value
    )
    return ExportPayloadBuildResult(
        status=status,
        payload=None,
        error_code=error_code,
        message=_BUILD_MESSAGES[status],
        readiness_issue=ExportReadinessIssue("payload_invalid", field="payload"),
    )


def _success(payload: ExportPayload) -> ExportPayloadBuildResult:
    return ExportPayloadBuildResult(
        status=ExportPayloadBuildStatus.SUCCESS,
        payload=payload,
        error_code=None,
        message=_BUILD_MESSAGES[ExportPayloadBuildStatus.SUCCESS],
        readiness_issue=None,
    )


def _candidate_contains_unsafe_input(command: ExportPayloadBuildCommand) -> bool:
    return contains_unsafe_input(
        {
            "document_id": command.document_id,
            "tenant_id": command.tenant_id,
            "export_target": command.export_target.to_dict() if isinstance(command.export_target, ExportTarget) else command.export_target,
            "lines": [line.to_dict() if isinstance(line, ExportPayloadLine) else line for line in command.lines]
            if isinstance(command.lines, Sequence) and not isinstance(command.lines, (str, bytes))
            else command.lines,
            "parties": [party.to_dict() if isinstance(party, ExportPayloadParty) else party for party in command.parties]
            if isinstance(command.parties, Sequence) and not isinstance(command.parties, (str, bytes))
            else command.parties,
            "metadata": command.metadata,
        }
    )


class ExportPayloadBuilder:
    """Build payloads from caller-supplied structured data without I/O."""

    def build(self, command: Any) -> ExportPayloadBuildResult:
        if not isinstance(command, ExportPayloadBuildCommand):
            if isinstance(command, Mapping) and contains_unsafe_input(command):
                return _failure(ExportPayloadBuildStatus.PRIVACY_REJECTED)
            return _failure(ExportPayloadBuildStatus.INVALID_PAYLOAD)
        if _candidate_contains_unsafe_input(command):
            return _failure(ExportPayloadBuildStatus.PRIVACY_REJECTED)
        try:
            if command.export_target is None or not isinstance(command.export_target, ExportTarget):
                raise ValueError("export_target must be an ExportTarget")
            document_id = stable_id(command.document_id, "document_id")
            tenant_id = stable_id(command.tenant_id, "tenant_id")
            currency = normalize_currency(command.currency)
            if isinstance(command.lines, (str, bytes, Mapping)) or not isinstance(command.lines, Sequence):
                raise ValueError("lines must be a collection")
            if isinstance(command.parties, (str, bytes, Mapping)) or not isinstance(command.parties, Sequence):
                raise ValueError("parties must be a collection")
            lines = tuple(normalize_line(item) for item in command.lines)
            parties = tuple(normalize_party(item) for item in command.parties)
            metadata = safe_metadata(command.metadata)
            common = {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "export_target": command.export_target,
                "currency": currency,
                "lines": lines,
                "schema_version": stable_id(command.schema_version, "schema_version"),
                "document_version": command.document_version,
                "document_type": command.document_type,
                "parties": parties,
                "document_date": normalize_date(command.document_date, "document_date"),
                "due_date": normalize_date(command.due_date, "due_date"),
                "external_reference": normalize_optional_text(command.external_reference, "external_reference", maximum=128),
                "subtotal": command.subtotal,
                "tax_total": command.tax_total,
                "total": command.total,
                "metadata": metadata,
            }
            if command.payload_id is None:
                draft = ExportPayload(payload_id="payload-pending", **common)
                payload_id = f"payload-{fingerprint_export_payload(draft)[:24]}"
            else:
                payload_id = stable_id(command.payload_id, "payload_id")
            return _success(ExportPayload(payload_id=payload_id, **common))
        except (TypeError, ValueError):
            return _failure(ExportPayloadBuildStatus.INVALID_PAYLOAD)


def build_export_payload(command: Any) -> ExportPayloadBuildResult:
    return ExportPayloadBuilder().build(command)
