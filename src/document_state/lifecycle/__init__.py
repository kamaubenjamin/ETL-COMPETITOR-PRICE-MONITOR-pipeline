"""Public contracts and pure policy for Document State lifecycle advancement."""

from .contracts import (
    LifecyclePolicyDecision,
    LifecyclePolicyOutcome,
    LifecycleRecoveryPolicy,
    LifecycleTransitionRequest,
)
from .errors import LifecycleErrorCode, LifecyclePolicyError
from .policy import evaluate_transition, order_transition_candidates, transition_order_key
from .results import LifecycleResultStatus, LifecycleTransitionResult
from .states import (
    ALLOWED_TRANSITIONS,
    LIFECYCLE_STATES,
    NON_TERMINAL_STATES,
    RECOVERY_TARGETS,
    STATE_PRIORITY,
    STRUCTURED_EQUIVALENT,
    TERMINAL_STATES,
    lifecycle_priority,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "LIFECYCLE_STATES",
    "LifecycleErrorCode",
    "LifecyclePolicyDecision",
    "LifecyclePolicyError",
    "LifecyclePolicyOutcome",
    "LifecycleRecoveryPolicy",
    "LifecycleResultStatus",
    "LifecycleTransitionRequest",
    "LifecycleTransitionResult",
    "NON_TERMINAL_STATES",
    "RECOVERY_TARGETS",
    "STATE_PRIORITY",
    "STRUCTURED_EQUIVALENT",
    "TERMINAL_STATES",
    "evaluate_transition",
    "lifecycle_priority",
    "order_transition_candidates",
    "transition_order_key",
]
