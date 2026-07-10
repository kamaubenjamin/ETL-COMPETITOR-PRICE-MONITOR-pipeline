"""Declarative reprocess request contract; execution is out of scope."""

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
    identifier,
    mapping,
    positive_version,
    stage_name,
    timestamp,
)


@dataclass(frozen=True, slots=True)
class ReprocessRequest:
    request_id: str
    review_case_id: str
    requested_from_stage: str
    requested_target_stage: str
    reason_code: str
    requested_by: str
    created_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    expected_case_version: int = 1
    idempotency_key: str | None = None
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", identifier(self.request_id, ("request_id",)))
        object.__setattr__(self, "review_case_id", identifier(self.review_case_id, ("review_case_id",)))
        object.__setattr__(
            self,
            "requested_from_stage",
            stage_name(self.requested_from_stage, ("requested_from_stage",)),
        )
        object.__setattr__(
            self,
            "requested_target_stage",
            stage_name(self.requested_target_stage, ("requested_target_stage",)),
        )
        object.__setattr__(self, "reason_code", code(self.reason_code, ("reason_code",)))
        object.__setattr__(self, "requested_by", identifier(self.requested_by, ("requested_by",)))
        object.__setattr__(self, "created_at", timestamp(self.created_at, ("created_at",)))
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
        object.__setattr__(
            self,
            "expected_case_version",
            positive_version(self.expected_case_version, ("expected_case_version",)),
        )
        object.__setattr__(
            self,
            "idempotency_key",
            identifier(self.idempotency_key or self.request_id, ("idempotency_key",)),
        )
        object.__setattr__(self, "contract_version", contract_version(self.contract_version, ("contract_version",)))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReprocessRequest":
        data = mapping(payload)
        required = {
            "request_id", "review_case_id", "requested_from_stage", "requested_target_stage",
            "reason_code", "requested_by", "created_at", "metadata",
        }
        allowed = required | {"expected_case_version", "idempotency_key", "contract_version"}
        check_keys(data, allowed=allowed, required=required)
        return cls(
            request_id=data["request_id"],
            review_case_id=data["review_case_id"],
            requested_from_stage=data["requested_from_stage"],
            requested_target_stage=data["requested_target_stage"],
            reason_code=data["reason_code"],
            requested_by=data["requested_by"],
            created_at=data["created_at"],
            metadata=data["metadata"],
            expected_case_version=data.get("expected_case_version", 1),
            idempotency_key=data.get("idempotency_key"),
            contract_version=data.get("contract_version", CONTRACT_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "request_id": self.request_id,
            "review_case_id": self.review_case_id,
            "requested_from_stage": self.requested_from_stage,
            "requested_target_stage": self.requested_target_stage,
            "reason_code": self.reason_code,
            "requested_by": self.requested_by,
            "created_at": self.created_at,
            "expected_case_version": self.expected_case_version,
            "idempotency_key": self.idempotency_key,
            "metadata": metadata_to_dict(self.metadata),
        }

