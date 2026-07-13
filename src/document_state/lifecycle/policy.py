"""Pure deterministic lifecycle transition policy."""

from __future__ import annotations

from collections.abc import Iterable

from ..contracts import DocumentStatus
from .contracts import LifecyclePolicyDecision, LifecyclePolicyOutcome, LifecycleTransitionRequest
from .states import ALLOWED_TRANSITIONS, RECOVERY_TARGETS, lifecycle_priority


def _decision(request: LifecycleTransitionRequest, outcome: LifecyclePolicyOutcome, reason_code: str) -> LifecyclePolicyDecision:
    return LifecyclePolicyDecision(
        outcome=outcome,
        document_id=request.document_id,
        lifecycle_event_id=request.lifecycle_event_id,
        source_status=request.source_status,
        target_status=request.target_status,
        reason_code=reason_code,
        expected_version=request.expected_version,
    )


def evaluate_transition(request: LifecycleTransitionRequest) -> LifecyclePolicyDecision:
    if not isinstance(request, LifecycleTransitionRequest):
        raise ValueError("request must be a LifecycleTransitionRequest")
    if request.source_status == request.target_status:
        return _decision(request, LifecyclePolicyOutcome.NO_OP, "already_applied")
    if request.source_status == DocumentStatus.EXPORTED.value:
        return _decision(request, LifecyclePolicyOutcome.REJECTED, "terminal_state")
    if request.source_status == DocumentStatus.FAILED.value:
        if request.recovery_policy is None:
            return _decision(request, LifecyclePolicyOutcome.REJECTED, "recovery_required")
        if request.target_status not in RECOVERY_TARGETS:
            return _decision(request, LifecyclePolicyOutcome.REJECTED, "invalid_recovery_target")
        return _decision(request, LifecyclePolicyOutcome.ALLOWED, "recovery_allowed")
    if request.recovery_policy is not None:
        return _decision(request, LifecyclePolicyOutcome.REJECTED, "recovery_not_applicable")
    if request.target_status in ALLOWED_TRANSITIONS[request.source_status]:
        return _decision(request, LifecyclePolicyOutcome.ALLOWED, "transition_allowed")
    return _decision(request, LifecyclePolicyOutcome.REJECTED, "invalid_transition")


def transition_order_key(request: LifecycleTransitionRequest) -> tuple[str, int, str]:
    if not isinstance(request, LifecycleTransitionRequest):
        raise ValueError("request must be a LifecycleTransitionRequest")
    return (request.occurred_at, lifecycle_priority(request.target_status), request.lifecycle_event_id)


def order_transition_candidates(requests: Iterable[LifecycleTransitionRequest]) -> tuple[LifecycleTransitionRequest, ...]:
    candidates = tuple(requests)
    if any(not isinstance(request, LifecycleTransitionRequest) for request in candidates):
        raise ValueError("candidates must contain LifecycleTransitionRequest values")
    return tuple(sorted(candidates, key=transition_order_key))
