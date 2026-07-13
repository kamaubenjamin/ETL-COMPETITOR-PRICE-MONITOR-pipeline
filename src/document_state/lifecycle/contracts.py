"""Immutable contracts for lifecycle transition policy and future advancement."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any

from ..contracts import DocumentStatus
from ..privacy import (
    JsonScalar,
    bounded_string,
    enum_value,
    json_value,
    optional_string,
    positive_version,
    stable_id,
    utc_timestamp,
    validate_safe_metadata,
)
from .states import RECOVERY_TARGETS


def _contract_value(value: Any) -> Any:
    if isinstance(value, LifecycleContract):
        return value.to_dict()
    return json_value(value)


class LifecycleContract:
    def to_dict(self) -> dict[str, Any]:
        return {item.name: _contract_value(getattr(self, item.name)) for item in fields(self)}


class LifecyclePolicyOutcome(str, Enum):
    ALLOWED = "allowed"
    NO_OP = "no_op"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class LifecycleRecoveryPolicy(LifecycleContract):
    target_status: DocumentStatus | str
    reprocess_plan_id: str | None = None
    governed_reason_code: str | None = None

    def __post_init__(self) -> None:
        target = enum_value(self.target_status, DocumentStatus, "target_status")
        if target not in RECOVERY_TARGETS:
            raise ValueError("target_status is not an approved recovery target")
        object.__setattr__(self, "target_status", target)
        plan_id = None if self.reprocess_plan_id is None else stable_id(self.reprocess_plan_id, "reprocess_plan_id")
        reason = optional_string(self.governed_reason_code, "governed_reason_code", maximum=128)
        if plan_id is None and reason is None:
            raise ValueError("recovery policy requires a reprocess plan or governed reason")
        object.__setattr__(self, "reprocess_plan_id", plan_id)
        object.__setattr__(self, "governed_reason_code", reason)


@dataclass(frozen=True, slots=True)
class LifecycleTransitionRequest(LifecycleContract):
    document_id: str
    source_status: DocumentStatus | str
    target_status: DocumentStatus | str
    lifecycle_event_id: str
    expected_version: int
    reason_code: str
    actor_id: str
    occurred_at: str
    source_stage: str | None = None
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict, repr=False)
    recovery_policy: LifecycleRecoveryPolicy | None = None

    def __post_init__(self) -> None:
        for name in ("document_id", "lifecycle_event_id", "actor_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        for name in ("source_status", "target_status"):
            object.__setattr__(self, name, enum_value(getattr(self, name), DocumentStatus, name))
        object.__setattr__(self, "expected_version", positive_version(self.expected_version))
        object.__setattr__(self, "reason_code", bounded_string(self.reason_code, "reason_code", maximum=128))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "source_stage", optional_string(self.source_stage, "source_stage", maximum=128))
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
        if self.recovery_policy is not None:
            if not isinstance(self.recovery_policy, LifecycleRecoveryPolicy):
                raise ValueError("recovery_policy must be a LifecycleRecoveryPolicy")
            if self.recovery_policy.target_status != self.target_status:
                raise ValueError("recovery target must match target_status")


@dataclass(frozen=True, slots=True)
class LifecyclePolicyDecision(LifecycleContract):
    outcome: LifecyclePolicyOutcome | str
    document_id: str
    lifecycle_event_id: str
    source_status: DocumentStatus | str
    target_status: DocumentStatus | str
    reason_code: str
    expected_version: int

    def __post_init__(self) -> None:
        try:
            outcome = self.outcome.value if isinstance(self.outcome, LifecyclePolicyOutcome) else LifecyclePolicyOutcome(self.outcome).value
        except (TypeError, ValueError) as exc:
            raise ValueError("outcome is invalid") from exc
        object.__setattr__(self, "outcome", outcome)
        for name in ("document_id", "lifecycle_event_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        for name in ("source_status", "target_status"):
            object.__setattr__(self, name, enum_value(getattr(self, name), DocumentStatus, name))
        object.__setattr__(self, "reason_code", bounded_string(self.reason_code, "reason_code", maximum=128))
        object.__setattr__(self, "expected_version", positive_version(self.expected_version))
