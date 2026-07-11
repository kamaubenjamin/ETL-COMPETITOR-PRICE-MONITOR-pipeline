"""Stable errors for Review Runtime contracts and lifecycle transitions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

PathComponent = str | int


def format_path(path: Iterable[PathComponent]) -> str:
    formatted = "$"
    for component in path:
        if isinstance(component, int):
            formatted += f"[{component}]"
        elif component.isidentifier():
            formatted += f".{component}"
        else:
            escaped = component.replace("\\", "\\\\").replace("'", "\\'")
            formatted += f"['{escaped}']"
    return formatted


class ReviewRuntimeError(ValueError):
    """Path-aware error that never includes rejected payload values."""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        path: Iterable[PathComponent] = (),
    ) -> None:
        if message is None:
            message = code
            code = "review_runtime_error"
        self.code = code
        self.message = message
        self.path_components = tuple(path)
        self.path = format_path(self.path_components)
        super().__init__(f"{code} at {self.path}: {message}")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "path": self.path, "message": self.message}


INVALID_TYPE = "invalid_type"
INVALID_VALUE = "invalid_value"
MISSING_FIELD = "missing_field"
UNKNOWN_FIELD = "unknown_field"
UNSUPPORTED_VERSION = "unsupported_version"
UNSAFE_METADATA = "unsafe_metadata"
INVALID_TRANSITION = "invalid_transition"
NOT_FOUND = "not_found"
VERSION_CONFLICT = "version_conflict"
ALREADY_EXISTS = "already_exists"
IDEMPOTENCY_CONFLICT = "idempotency_conflict"
AUDIT_CONFLICT = "audit_conflict"
CORRECTION_NOT_FOUND = "correction_not_found"
CORRECTION_LINEAGE_CONFLICT = "correction_lineage_conflict"
REVIEWER_CONFLICT = "reviewer_conflict"
REPROCESS_REQUEST_NOT_FOUND = "reprocess_request_not_found"
REPROCESS_PLAN_CONFLICT = "reprocess_plan_conflict"


class ReviewCaseNotFoundError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(NOT_FOUND, "Review case was not found.", ("review_case_id",))


class ReviewCaseVersionConflictError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            VERSION_CONFLICT,
            "Review case version does not match the expected version.",
            ("version",),
        )


class ReviewCaseAlreadyExistsError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            ALREADY_EXISTS,
            "Review case identifier already exists.",
            ("review_case_id",),
        )


class ReviewCaseIdempotencyConflictError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            IDEMPOTENCY_CONFLICT,
            "Idempotency key was already used for a different case request.",
            ("idempotency_key",),
        )


class ReviewAuditConflictError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            AUDIT_CONFLICT,
            "Audit event is inconsistent with the review case update.",
            ("audit_event",),
        )


class ReviewCorrectionNotFoundError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            CORRECTION_NOT_FOUND,
            "Referenced correction was not found for this review case.",
            ("correction_ids",),
        )


class ReviewCorrectionLineageConflictError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            CORRECTION_LINEAGE_CONFLICT,
            "Correction lineage does not match the review case source.",
            ("correction",),
        )


class ReviewReviewerConflictError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            REVIEWER_CONFLICT,
            "Reviewer does not match the assigned review case owner.",
            ("reviewer_id",),
        )


class ReviewReprocessRequestNotFoundError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            REPROCESS_REQUEST_NOT_FOUND,
            "Reprocess request was not found for this review case.",
            ("request_id",),
        )


class ReviewReprocessPlanConflictError(ReviewRuntimeError):
    def __init__(self) -> None:
        super().__init__(
            REPROCESS_PLAN_CONFLICT,
            "Reprocess plan identifier already exists.",
            ("plan_id",),
        )
