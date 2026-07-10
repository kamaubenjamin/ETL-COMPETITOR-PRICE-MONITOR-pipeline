"""Reviewer decision contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.review_runtime.errors import INVALID_VALUE, ReviewRuntimeError
from src.review_runtime.privacy import metadata_to_dict, validate_safe_metadata

from ._validation import (
    CONTRACT_VERSION,
    check_keys,
    contract_version,
    enum_value,
    identifier,
    mapping,
    optional_code,
    optional_identifier,
    positive_version,
    string_tuple,
    timestamp,
)
from .enums import ReviewerDecisionType


@dataclass(frozen=True, slots=True)
class ReviewerDecision:
    decision_id: str
    review_case_id: str
    decision: ReviewerDecisionType | str
    reviewer_id: str
    occurred_at: str
    expected_case_version: int
    idempotency_key: str
    reason_code: str | None = None
    correction_ids: tuple[str, ...] = ()
    reprocess_request_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", identifier(self.decision_id, ("decision_id",)))
        object.__setattr__(self, "review_case_id", identifier(self.review_case_id, ("review_case_id",)))
        decision = enum_value(self.decision, ReviewerDecisionType, ("decision",))
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "reviewer_id", identifier(self.reviewer_id, ("reviewer_id",)))
        object.__setattr__(self, "occurred_at", timestamp(self.occurred_at, ("occurred_at",)))
        object.__setattr__(
            self,
            "expected_case_version",
            positive_version(self.expected_case_version, ("expected_case_version",)),
        )
        object.__setattr__(self, "idempotency_key", identifier(self.idempotency_key, ("idempotency_key",)))
        object.__setattr__(self, "reason_code", optional_code(self.reason_code, ("reason_code",)))
        correction_ids = string_tuple(self.correction_ids, ("correction_ids",))
        object.__setattr__(self, "correction_ids", correction_ids)
        object.__setattr__(
            self,
            "reprocess_request_id",
            optional_identifier(self.reprocess_request_id, ("reprocess_request_id",)),
        )
        if decision is ReviewerDecisionType.CORRECT and not correction_ids:
            raise ReviewRuntimeError(INVALID_VALUE, "correct requires at least one correction id.", ("correction_ids",))
        if decision is ReviewerDecisionType.SKIP and self.reason_code is None:
            raise ReviewRuntimeError(INVALID_VALUE, "skip requires a reason code.", ("reason_code",))
        if decision is ReviewerDecisionType.REQUEST_REPROCESS and self.reprocess_request_id is None:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "request_reprocess requires a reprocess request id.",
                ("reprocess_request_id",),
            )
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
        object.__setattr__(self, "contract_version", contract_version(self.contract_version, ("contract_version",)))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReviewerDecision":
        data = mapping(payload)
        required = {
            "decision_id", "review_case_id", "decision", "reviewer_id", "occurred_at",
            "expected_case_version", "idempotency_key",
        }
        allowed = required | {
            "reason_code", "correction_ids", "reprocess_request_id", "metadata", "contract_version",
        }
        check_keys(data, allowed=allowed, required=required)
        return cls(
            decision_id=data["decision_id"],
            review_case_id=data["review_case_id"],
            decision=data["decision"],
            reviewer_id=data["reviewer_id"],
            occurred_at=data["occurred_at"],
            expected_case_version=data["expected_case_version"],
            idempotency_key=data["idempotency_key"],
            reason_code=data.get("reason_code"),
            correction_ids=tuple(data.get("correction_ids", ())),
            reprocess_request_id=data.get("reprocess_request_id"),
            metadata=data.get("metadata", {}),
            contract_version=data.get("contract_version", CONTRACT_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "decision_id": self.decision_id,
            "review_case_id": self.review_case_id,
            "decision": self.decision.value,
            "reviewer_id": self.reviewer_id,
            "occurred_at": self.occurred_at,
            "expected_case_version": self.expected_case_version,
            "idempotency_key": self.idempotency_key,
            "reason_code": self.reason_code,
            "correction_ids": list(self.correction_ids),
            "reprocess_request_id": self.reprocess_request_id,
            "metadata": metadata_to_dict(self.metadata),
        }

