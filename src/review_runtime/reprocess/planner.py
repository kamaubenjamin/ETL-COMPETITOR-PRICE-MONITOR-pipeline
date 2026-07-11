"""Pure conversion of reprocess requests into validated dry-run plans."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any
from uuid import uuid4

from src.review_runtime.contracts.reprocess import ReprocessRequest
from src.review_runtime.errors import INVALID_VALUE, ReviewRuntimeError
from src.review_runtime.state_machine import utc_now_iso

from .contracts import ReprocessPlan, SAFE_REPROCESS_STAGE_ORDER, SAFE_REPROCESS_STAGES

Clock = Callable[[], str]
IdFactory = Callable[[str], str]


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


class ReprocessPlanner:
    """Build deterministic plans without loading artifacts or running workflows."""

    def __init__(
        self,
        *,
        clock: Clock = utc_now_iso,
        id_factory: IdFactory = _default_id_factory,
    ) -> None:
        self._clock = clock
        self._id_factory = id_factory

    def create_plan(
        self,
        request: ReprocessRequest,
        *,
        invalidated_artifacts: Iterable[str],
        retained_artifacts: Iterable[str] = (),
        metadata: Mapping[str, Any] | None = None,
        plan_id: str | None = None,
        created_at: str | None = None,
    ) -> ReprocessPlan:
        if not isinstance(request, ReprocessRequest):
            raise ReviewRuntimeError(INVALID_VALUE, "Expected a ReprocessRequest.", ("request",))
        self._validate_stage_path(
            request.requested_from_stage,
            request.requested_target_stage,
        )
        return ReprocessPlan(
            plan_id=plan_id or self._id_factory("reprocess-plan"),
            review_case_id=request.review_case_id,
            requested_from_stage=request.requested_from_stage,
            requested_target_stage=request.requested_target_stage,
            invalidated_artifacts=tuple(invalidated_artifacts),
            retained_artifacts=tuple(retained_artifacts),
            reason_code=request.reason_code,
            requested_by=request.requested_by,
            created_at=created_at or self._clock(),
            metadata=metadata or {},
            dry_run=True,
        )

    @staticmethod
    def _validate_stage_path(from_stage: str, target_stage: str) -> None:
        if from_stage not in SAFE_REPROCESS_STAGES:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "Unknown requested_from_stage code.",
                ("requested_from_stage",),
            )
        if target_stage not in SAFE_REPROCESS_STAGES:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "Unknown requested_target_stage code.",
                ("requested_target_stage",),
            )
        order = {stage: index for index, stage in enumerate(SAFE_REPROCESS_STAGE_ORDER)}
        if order[target_stage] > order[from_stage]:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "Requested target stage must not be downstream of the source stage.",
                ("requested_target_stage",),
            )

