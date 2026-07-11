"""Review Runtime service for storing dry-run reprocess plans."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any
from uuid import uuid4

from src.review_runtime.contracts._validation import identifier, positive_version
from src.review_runtime.contracts.audit import ReviewAuditEvent
from src.review_runtime.contracts.enums import ReviewStatus
from src.review_runtime.errors import (
    INVALID_TRANSITION,
    ReviewCaseVersionConflictError,
    ReviewReprocessRequestNotFoundError,
    ReviewRuntimeError,
)
from src.review_runtime.repositories.base import ReviewCaseRepository
from src.review_runtime.reprocess.contracts import ReprocessPlan
from src.review_runtime.reprocess.planner import ReprocessPlanner

IdFactory = Callable[[str], str]


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


class ReprocessService:
    """Create and persist plans without invoking Workflow Runtime."""

    def __init__(
        self,
        repository: ReviewCaseRepository,
        planner: ReprocessPlanner,
        *,
        id_factory: IdFactory = _default_id_factory,
    ) -> None:
        self._repository = repository
        self._planner = planner
        self._id_factory = id_factory

    def create_plan(
        self,
        review_case_id: str,
        request_id: str,
        *,
        invalidated_artifacts: Iterable[str],
        retained_artifacts: Iterable[str] = (),
        expected_version: int,
        metadata: Mapping[str, Any] | None = None,
        plan_id: str | None = None,
        created_at: str | None = None,
    ) -> ReprocessPlan:
        case_id = identifier(review_case_id, ("review_case_id",))
        normalized_request_id = identifier(request_id, ("request_id",))
        normalized_version = positive_version(expected_version, ("expected_version",))
        review_case = self._repository.get_case(case_id)
        if review_case.version != normalized_version:
            raise ReviewCaseVersionConflictError()
        if review_case.status is not ReviewStatus.REPROCESS_REQUESTED:
            raise ReviewRuntimeError(
                INVALID_TRANSITION,
                "Reprocess plans require a reprocess_requested review case.",
                ("status",),
            )
        request = next(
            (
                item
                for item in self._repository.list_reprocess_requests(case_id)
                if item.request_id == normalized_request_id
            ),
            None,
        )
        if request is None:
            raise ReviewReprocessRequestNotFoundError()

        plan = self._planner.create_plan(
            request,
            invalidated_artifacts=invalidated_artifacts,
            retained_artifacts=retained_artifacts,
            metadata=metadata,
            plan_id=plan_id,
            created_at=created_at,
        )
        audit_event = ReviewAuditEvent(
            event_id=self._id_factory("review-event"),
            review_case_id=case_id,
            event_type="reprocess_plan_created",
            actor_id=request.requested_by,
            occurred_at=plan.created_at,
            previous_status=review_case.status,
            new_status=review_case.status,
            sequence=self._repository.next_audit_sequence(case_id),
            case_version=review_case.version,
            metadata={
                "requested_from_stage": plan.requested_from_stage,
                "requested_target_stage": plan.requested_target_stage,
                "invalidated_count": len(plan.invalidated_artifacts),
                "retained_count": len(plan.retained_artifacts),
                "dry_run": True,
            },
        )
        return self._repository.store_reprocess_plan(
            plan,
            audit_event,
            expected_version=normalized_version,
        )

    def list_plans(self, review_case_id: str) -> tuple[ReprocessPlan, ...]:
        return self._repository.list_reprocess_plans(
            identifier(review_case_id, ("review_case_id",))
        )
