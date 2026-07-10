"""Append-only review audit event contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.review_runtime.privacy import metadata_to_dict, validate_safe_metadata

from ._validation import (
    CONTRACT_VERSION,
    check_keys,
    code,
    contract_version,
    enum_value,
    identifier,
    mapping,
    positive_version,
    review_status,
    timestamp,
)
from .enums import ReviewStatus


@dataclass(frozen=True, slots=True)
class ReviewAuditEvent:
    event_id: str
    review_case_id: str
    event_type: str
    actor_id: str
    occurred_at: str
    previous_status: ReviewStatus | str | None
    new_status: ReviewStatus | str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    sequence: int = 1
    case_version: int = 1
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", identifier(self.event_id, ("event_id",)))
        object.__setattr__(self, "review_case_id", identifier(self.review_case_id, ("review_case_id",)))
        object.__setattr__(self, "event_type", code(self.event_type, ("event_type",)))
        object.__setattr__(self, "actor_id", identifier(self.actor_id, ("actor_id",)))
        object.__setattr__(self, "occurred_at", timestamp(self.occurred_at, ("occurred_at",)))
        if self.previous_status is not None:
            object.__setattr__(
                self,
                "previous_status",
                review_status(self.previous_status, ("previous_status",)),
            )
        object.__setattr__(self, "new_status", review_status(self.new_status, ("new_status",)))
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
        object.__setattr__(self, "sequence", positive_version(self.sequence, ("sequence",)))
        object.__setattr__(self, "case_version", positive_version(self.case_version, ("case_version",)))
        object.__setattr__(self, "contract_version", contract_version(self.contract_version, ("contract_version",)))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReviewAuditEvent":
        data = mapping(payload)
        required = {
            "event_id", "review_case_id", "event_type", "actor_id", "occurred_at",
            "previous_status", "new_status", "metadata",
        }
        allowed = required | {"sequence", "case_version", "contract_version"}
        check_keys(data, allowed=allowed, required=required)
        return cls(
            event_id=data["event_id"],
            review_case_id=data["review_case_id"],
            event_type=data["event_type"],
            actor_id=data["actor_id"],
            occurred_at=data["occurred_at"],
            previous_status=data["previous_status"],
            new_status=data["new_status"],
            metadata=data["metadata"],
            sequence=data.get("sequence", 1),
            case_version=data.get("case_version", 1),
            contract_version=data.get("contract_version", CONTRACT_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "event_id": self.event_id,
            "review_case_id": self.review_case_id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at,
            "previous_status": self.previous_status.value if self.previous_status else None,
            "new_status": self.new_status.value,
            "sequence": self.sequence,
            "case_version": self.case_version,
            "metadata": metadata_to_dict(self.metadata),
        }
