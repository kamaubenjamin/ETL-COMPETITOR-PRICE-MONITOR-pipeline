"""Immutable export readiness outcome contracts."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from .contracts import ExportTarget, JsonContract, contract_tuple, optional_text, safe_code, stable_id
from .statuses import ExportReadinessIssueCode, ExportStatus


_ISSUE_MESSAGES = {
    ExportReadinessIssueCode.DOCUMENT_NOT_FOUND: "Document is unavailable for export.",
    ExportReadinessIssueCode.TENANT_SCOPE_DENIED: "Document is outside the permitted export scope.",
    ExportReadinessIssueCode.PERMISSION_DENIED: "Export permission is required.",
    ExportReadinessIssueCode.INVALID_LIFECYCLE_STATE: "Document lifecycle state is not export ready.",
    ExportReadinessIssueCode.VALIDATION_NOT_PASSED: "Document validation has blocking issues.",
    ExportReadinessIssueCode.MATCHING_NOT_COMPLETED: "Required matching is incomplete.",
    ExportReadinessIssueCode.REVIEW_NOT_APPROVED: "Required review is not approved.",
    ExportReadinessIssueCode.REQUIRED_ENTITIES_MISSING: "Required export entities are unavailable.",
    ExportReadinessIssueCode.EXPORT_TARGET_MISSING: "Export target is unavailable.",
    ExportReadinessIssueCode.DUPLICATE_EXPORT_ACTIVE: "An equivalent export is already active.",
    ExportReadinessIssueCode.PAYLOAD_INVALID: "Export payload could not be prepared safely.",
    ExportReadinessIssueCode.ADAPTER_UNAVAILABLE: "Export adapter is unavailable.",
    ExportReadinessIssueCode.INTERNAL_ERROR: "Export readiness could not be evaluated.",
}


@dataclass(frozen=True, slots=True)
class ExportReadinessIssue(JsonContract):
    code: ExportReadinessIssueCode | str
    field: str | None = None
    message: str = dc_field(init=False)

    def __post_init__(self) -> None:
        try:
            code = self.code if isinstance(self.code, ExportReadinessIssueCode) else ExportReadinessIssueCode(self.code)
        except (TypeError, ValueError):
            raise ValueError("readiness issue code is invalid") from None
        object.__setattr__(self, "code", code.value)
        object.__setattr__(self, "field", None if self.field is None else safe_code(self.field, "field"))
        object.__setattr__(self, "message", _ISSUE_MESSAGES[code])


@dataclass(frozen=True, slots=True)
class ExportReadinessResult(JsonContract):
    document_id: str
    target: ExportTarget | None
    blocking_issues: tuple[ExportReadinessIssue, ...] = ()
    warning_issues: tuple[ExportReadinessIssue, ...] = ()
    ready: bool = dc_field(init=False)
    status: str = dc_field(init=False)
    safe_summary: str = dc_field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        if self.target is not None and not isinstance(self.target, ExportTarget):
            raise ValueError("target must be an ExportTarget")
        blockers = contract_tuple(self.blocking_issues, ExportReadinessIssue, "blocking_issues")
        warnings = contract_tuple(self.warning_issues, ExportReadinessIssue, "warning_issues")
        if self.target is None and not any(issue.code == ExportReadinessIssueCode.EXPORT_TARGET_MISSING.value for issue in blockers):
            raise ValueError("a missing target requires export_target_missing")
        object.__setattr__(self, "blocking_issues", blockers)
        object.__setattr__(self, "warning_issues", warnings)
        ready = not blockers
        object.__setattr__(self, "ready", ready)
        object.__setattr__(self, "status", ExportStatus.READY.value if ready else ExportStatus.NOT_READY.value)
        summary = "Export is not ready." if blockers else ("Export is ready with warnings." if warnings else "Export is ready.")
        object.__setattr__(self, "safe_summary", summary)


def readiness_result(
    *,
    document_id: str,
    target: ExportTarget | None,
    blocking_issues: tuple[ExportReadinessIssue, ...] = (),
    warning_issues: tuple[ExportReadinessIssue, ...] = (),
) -> ExportReadinessResult:
    """Pure convenience constructor; it performs no authorization or external work."""

    return ExportReadinessResult(document_id, target, blocking_issues, warning_issues)
