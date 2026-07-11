"""Deterministic Review Case lifecycle service."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.review_runtime.contracts._validation import (
    check_keys,
    code,
    enum_value,
    identifier,
    mapping,
    positive_version,
    review_status,
    stage_name,
)
from src.review_runtime.contracts.audit import ReviewAuditEvent
from src.review_runtime.contracts.enums import (
    ReviewCaseType,
    ReviewPriority,
    ReviewStatus,
    SourceRuntime,
)
from src.review_runtime.contracts.review_case import ReviewCase
from src.review_runtime.errors import (
    INVALID_VALUE,
    ReviewCaseVersionConflictError,
    ReviewRuntimeError,
)
from src.review_runtime.repositories.base import ReviewCaseRepository
from src.review_runtime.state_machine import transition_review_case, utc_now_iso

Clock = Callable[[], str]
IdFactory = Callable[[str], str]

TRIGGER_REQUIRED_FIELDS = {
    "source_runtime",
    "source_stage",
    "source_artifact_id",
    "reason_code",
}
TRIGGER_OPTIONAL_FIELDS = {
    "review_case_id",
    "case_type",
    "source_artifact_version",
    "parent_review_case_id",
    "correlation_id",
    "priority",
    "status",
    "metadata",
    "idempotency_key",
}


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


def _created_at_sort_key(review_case: ReviewCase) -> tuple[datetime, str]:
    parsed = datetime.fromisoformat(review_case.created_at.replace("Z", "+00:00"))
    return parsed, review_case.review_case_id


class ReviewCaseService:
    """Create and transition Review Cases through the canonical state machine."""

    def __init__(
        self,
        repository: ReviewCaseRepository,
        *,
        clock: Clock = utc_now_iso,
        id_factory: IdFactory = _default_id_factory,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._id_factory = id_factory

    def create_case(
        self,
        *,
        source_runtime: SourceRuntime | str,
        source_stage: str,
        source_artifact_id: str,
        reason_code: str,
        priority: ReviewPriority | str = ReviewPriority.NORMAL,
        case_type: ReviewCaseType | str = ReviewCaseType.MANUAL_ESCALATION,
        metadata: Mapping[str, Any] | None = None,
        status: ReviewStatus | str = ReviewStatus.REVIEW_REQUIRED,
        review_case_id: str | None = None,
        source_artifact_version: str | None = None,
        parent_review_case_id: str | None = None,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
        actor_id: str = "system",
    ) -> ReviewCase:
        now = self._clock()
        requested_case_id = review_case_id
        case_id = review_case_id or self._id_factory("review-case")
        review_case = ReviewCase(
            review_case_id=case_id,
            source_runtime=source_runtime,
            source_stage=source_stage,
            source_artifact_id=source_artifact_id,
            status=status,
            reason_code=reason_code,
            priority=priority,
            created_at=now,
            updated_at=now,
            version=1,
            metadata=metadata or {},
            case_type=case_type,
            source_artifact_version=source_artifact_version,
            parent_review_case_id=parent_review_case_id,
            correlation_id=correlation_id,
        )
        if review_case.status is not ReviewStatus.REVIEW_REQUIRED:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "New review cases must start in review_required.",
                ("status",),
            )

        normalized_actor_id = identifier(actor_id, ("actor_id",))
        normalized_idempotency_key = identifier(
            idempotency_key or f"create-{review_case.review_case_id}",
            ("idempotency_key",),
        )
        audit_event = ReviewAuditEvent(
            event_id=self._id_factory("review-event"),
            review_case_id=review_case.review_case_id,
            event_type="case_created",
            actor_id=normalized_actor_id,
            occurred_at=now,
            previous_status=None,
            new_status=review_case.status,
            sequence=1,
            case_version=1,
            metadata={
                "reason_code": review_case.reason_code,
                "source": review_case.source_runtime.value,
            },
        )
        result = self._repository.create_case(
            review_case,
            audit_event,
            idempotency_key=normalized_idempotency_key,
            creation_fingerprint=self._creation_fingerprint(review_case, requested_case_id),
        )
        return result.review_case

    def create_case_from_trigger(
        self,
        trigger_metadata: Mapping[str, Any],
        *,
        actor_id: str = "system",
    ) -> ReviewCase:
        data = mapping(trigger_metadata, ("trigger",))
        check_keys(
            data,
            allowed=TRIGGER_REQUIRED_FIELDS | TRIGGER_OPTIONAL_FIELDS,
            required=TRIGGER_REQUIRED_FIELDS,
            path=("trigger",),
        )
        return self.create_case(
            source_runtime=data["source_runtime"],
            source_stage=data["source_stage"],
            source_artifact_id=data["source_artifact_id"],
            reason_code=data["reason_code"],
            priority=data.get("priority", ReviewPriority.NORMAL.value),
            case_type=data.get("case_type", ReviewCaseType.MANUAL_ESCALATION.value),
            metadata=data.get("metadata", {}),
            status=data.get("status", ReviewStatus.REVIEW_REQUIRED.value),
            review_case_id=data.get("review_case_id"),
            source_artifact_version=data.get("source_artifact_version"),
            parent_review_case_id=data.get("parent_review_case_id"),
            correlation_id=data.get("correlation_id"),
            idempotency_key=data.get("idempotency_key"),
            actor_id=actor_id,
        )

    def escalate_case(
        self,
        trigger_metadata: Mapping[str, Any],
        *,
        actor_id: str = "system",
    ) -> ReviewCase:
        data = dict(mapping(trigger_metadata, ("trigger",)))
        data["case_type"] = ReviewCaseType.MANUAL_ESCALATION.value
        data.setdefault("priority", ReviewPriority.HIGH.value)
        return self.create_case_from_trigger(data, actor_id=actor_id)

    def get_case(self, review_case_id: str) -> ReviewCase:
        return self._repository.get_case(identifier(review_case_id, ("review_case_id",)))

    def list_cases(
        self,
        *,
        status: ReviewStatus | str | None = None,
        reason_code: str | None = None,
        source_runtime: SourceRuntime | str | None = None,
        source_stage: str | None = None,
        priority: ReviewPriority | str | None = None,
    ) -> tuple[ReviewCase, ...]:
        normalized_status = review_status(status, ("status",)) if status is not None else None
        normalized_reason = code(reason_code, ("reason_code",)) if reason_code is not None else None
        normalized_runtime = (
            enum_value(source_runtime, SourceRuntime, ("source_runtime",))
            if source_runtime is not None
            else None
        )
        normalized_stage = stage_name(source_stage, ("source_stage",)) if source_stage is not None else None
        normalized_priority = (
            enum_value(priority, ReviewPriority, ("priority",))
            if priority is not None
            else None
        )
        cases = (
            item
            for item in self._repository.list_cases()
            if (normalized_status is None or item.status is normalized_status)
            and (normalized_reason is None or item.reason_code == normalized_reason)
            and (normalized_runtime is None or item.source_runtime is normalized_runtime)
            and (normalized_stage is None or item.source_stage == normalized_stage)
            and (normalized_priority is None or item.priority is normalized_priority)
        )
        return tuple(sorted(cases, key=_created_at_sort_key))

    def transition_case(
        self,
        review_case_id: str,
        new_status: ReviewStatus | str,
        *,
        expected_version: int,
        actor_id: str,
        metadata: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> ReviewCase:
        return self._transition_case(
            review_case_id,
            new_status,
            expected_version=expected_version,
            actor_id=actor_id,
            metadata=metadata,
            occurred_at=occurred_at,
            event_type="status_changed",
            assign_reviewer=new_status == ReviewStatus.IN_REVIEW or new_status == ReviewStatus.IN_REVIEW.value,
        )

    def mark_in_review(
        self,
        review_case_id: str,
        *,
        reviewer_id: str,
        expected_version: int,
        metadata: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> ReviewCase:
        return self._transition_case(
            review_case_id,
            ReviewStatus.IN_REVIEW,
            expected_version=expected_version,
            actor_id=reviewer_id,
            metadata=metadata,
            occurred_at=occurred_at,
            event_type="status_changed",
            assign_reviewer=True,
        )

    def resolve_case(
        self,
        review_case_id: str,
        *,
        expected_version: int,
        actor_id: str,
        metadata: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> ReviewCase:
        return self._transition_case(
            review_case_id,
            ReviewStatus.RESOLVED,
            expected_version=expected_version,
            actor_id=actor_id,
            metadata=metadata,
            occurred_at=occurred_at,
            event_type="case_resolved",
        )

    def list_audit_events(self, review_case_id: str) -> tuple[ReviewAuditEvent, ...]:
        return self._repository.list_audit_events(identifier(review_case_id, ("review_case_id",)))

    def _transition_case(
        self,
        review_case_id: str,
        new_status: ReviewStatus | str,
        *,
        expected_version: int,
        actor_id: str,
        metadata: Mapping[str, Any] | None,
        occurred_at: str | None,
        event_type: str,
        assign_reviewer: bool = False,
    ) -> ReviewCase:
        normalized_version = positive_version(expected_version, ("expected_version",))
        current = self.get_case(review_case_id)
        if current.version != normalized_version:
            raise ReviewCaseVersionConflictError()
        normalized_actor_id = identifier(actor_id, ("actor_id",))
        updated = transition_review_case(
            current,
            new_status,
            occurred_at=occurred_at or self._clock(),
        )
        if assign_reviewer:
            updated = replace(updated, assigned_reviewer_id=normalized_actor_id)
        audit_event = ReviewAuditEvent(
            event_id=self._id_factory("review-event"),
            review_case_id=updated.review_case_id,
            event_type=event_type,
            actor_id=normalized_actor_id,
            occurred_at=updated.updated_at,
            previous_status=current.status,
            new_status=updated.status,
            sequence=self._repository.next_audit_sequence(updated.review_case_id),
            case_version=updated.version,
            metadata=metadata or {},
        )
        return self._repository.update_case(
            updated,
            audit_event,
            expected_version=normalized_version,
        )

    @staticmethod
    def _creation_fingerprint(
        review_case: ReviewCase,
        requested_case_id: str | None,
    ) -> str:
        payload = review_case.to_dict()
        for key in ("review_case_id", "created_at", "updated_at", "version"):
            payload.pop(key)
        payload["requested_review_case_id"] = requested_case_id
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
