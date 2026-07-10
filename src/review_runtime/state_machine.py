"""Pure deterministic lifecycle transitions for Review Runtime v1."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from src.review_runtime.contracts.enums import ReviewStatus, ReviewerDecisionType
from src.review_runtime.contracts._validation import timestamp as validate_timestamp
from src.review_runtime.contracts._validation import review_status
from src.review_runtime.contracts.review_case import ReviewCase
from src.review_runtime.errors import INVALID_TRANSITION, ReviewRuntimeError

ALLOWED_TRANSITIONS: dict[ReviewStatus, frozenset[ReviewStatus]] = {
    ReviewStatus.REVIEW_REQUIRED: frozenset({ReviewStatus.IN_REVIEW, ReviewStatus.SKIPPED}),
    ReviewStatus.IN_REVIEW: frozenset(
        {
            ReviewStatus.CORRECTED,
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.SKIPPED,
            ReviewStatus.REPROCESS_REQUESTED,
        }
    ),
    ReviewStatus.CORRECTED: frozenset(
        {ReviewStatus.APPROVED, ReviewStatus.IN_REVIEW, ReviewStatus.REPROCESS_REQUESTED}
    ),
    ReviewStatus.APPROVED: frozenset({ReviewStatus.RESOLVED}),
    ReviewStatus.REJECTED: frozenset({ReviewStatus.RESOLVED}),
    ReviewStatus.SKIPPED: frozenset({ReviewStatus.RESOLVED}),
    ReviewStatus.REPROCESS_REQUESTED: frozenset({ReviewStatus.RESOLVED}),
    ReviewStatus.RESOLVED: frozenset(),
}

DECISION_TARGET_STATUS: dict[ReviewerDecisionType, ReviewStatus] = {
    ReviewerDecisionType.APPROVE: ReviewStatus.APPROVED,
    ReviewerDecisionType.REJECT: ReviewStatus.REJECTED,
    ReviewerDecisionType.CORRECT: ReviewStatus.CORRECTED,
    ReviewerDecisionType.SKIP: ReviewStatus.SKIPPED,
    ReviewerDecisionType.REQUEST_REPROCESS: ReviewStatus.REPROCESS_REQUESTED,
}


@dataclass(frozen=True, slots=True)
class ReviewTransition:
    previous_status: ReviewStatus
    new_status: ReviewStatus
    previous_version: int
    new_version: int
    occurred_at: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "previous_status": self.previous_status.value,
            "new_status": self.new_status.value,
            "previous_version": self.previous_version,
            "new_version": self.new_version,
            "occurred_at": self.occurred_at,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status(value: ReviewStatus | str, field_name: str) -> ReviewStatus:
    try:
        return review_status(value, (field_name,))
    except ReviewRuntimeError as exc:
        raise ReviewRuntimeError(
            INVALID_TRANSITION,
            f"Unknown {field_name} code.",
            (field_name,),
        ) from exc


def can_transition(current_status: ReviewStatus | str, new_status: ReviewStatus | str) -> bool:
    current = _status(current_status, "current_status")
    target = _status(new_status, "new_status")
    return target in ALLOWED_TRANSITIONS[current]


def transition_status(
    current_status: ReviewStatus | str,
    new_status: ReviewStatus | str,
    current_version: int,
    *,
    occurred_at: str | None = None,
) -> ReviewTransition:
    """Validate and describe a transition without mutating runtime state."""

    current = _status(current_status, "current_status")
    target = _status(new_status, "new_status")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ReviewRuntimeError(
            INVALID_TRANSITION,
            f"Transition from '{current.value}' to '{target.value}' is not allowed.",
            ("status",),
        )
    if not isinstance(current_version, int) or isinstance(current_version, bool) or current_version < 1:
        raise ReviewRuntimeError(
            INVALID_TRANSITION,
            "Current version must be a positive integer.",
            ("version",),
        )
    timestamp = validate_timestamp(occurred_at or utc_now_iso(), ("occurred_at",))
    return ReviewTransition(
        previous_status=current,
        new_status=target,
        previous_version=current_version,
        new_version=current_version + 1,
        occurred_at=timestamp,
    )


def transition_review_case(
    review_case: ReviewCase,
    new_status: ReviewStatus | str,
    *,
    occurred_at: str | None = None,
) -> ReviewCase:
    """Return a new case projection with incremented version and timestamp."""

    if not isinstance(review_case, ReviewCase):
        raise ReviewRuntimeError(INVALID_TRANSITION, "Expected a ReviewCase.", ("review_case",))
    transition = transition_status(
        review_case.status,
        new_status,
        review_case.version,
        occurred_at=occurred_at,
    )
    return replace(
        review_case,
        status=transition.new_status,
        version=transition.new_version,
        updated_at=transition.occurred_at,
    )


def status_for_decision(decision: ReviewerDecisionType | str) -> ReviewStatus:
    try:
        normalized = decision if isinstance(decision, ReviewerDecisionType) else ReviewerDecisionType(decision)
    except (TypeError, ValueError) as exc:
        raise ReviewRuntimeError(
            INVALID_TRANSITION,
            "Unknown reviewer decision code.",
            ("decision",),
        ) from exc
    return DECISION_TARGET_STATUS[normalized]
