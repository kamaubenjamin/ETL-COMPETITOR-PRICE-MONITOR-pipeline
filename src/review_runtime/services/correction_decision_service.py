"""Field correction and reviewer decision service for Review Runtime v1."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from typing import Any
from uuid import uuid4

from src.review_runtime.contracts._validation import (
    check_keys,
    identifier,
    mapping,
    positive_version,
)
from src.review_runtime.contracts.audit import ReviewAuditEvent
from src.review_runtime.contracts.correction import ControlledValue, FieldCorrection
from src.review_runtime.contracts.decision import ReviewerDecision
from src.review_runtime.contracts.enums import (
    CorrectionOperation,
    ReviewStatus,
    ReviewerDecisionType,
)
from src.review_runtime.contracts.reprocess import ReprocessRequest
from src.review_runtime.errors import (
    INVALID_TRANSITION,
    INVALID_VALUE,
    ReviewCaseVersionConflictError,
    ReviewCorrectionLineageConflictError,
    ReviewCorrectionNotFoundError,
    ReviewReviewerConflictError,
    ReviewRuntimeError,
)
from src.review_runtime.repositories.base import ReviewCaseRepository
from src.review_runtime.state_machine import (
    status_for_decision,
    transition_review_case,
    utc_now_iso,
)

Clock = Callable[[], str]
IdFactory = Callable[[str], str]

CORRECTION_SPEC_REQUIRED = {"field_path", "new_value", "reason_code"}
CORRECTION_SPEC_OPTIONAL = {
    "correction_id",
    "operation",
    "old_value_reference",
    "source_runtime",
    "source_stage",
    "source_artifact_id",
    "source_artifact_version",
    "metadata",
}


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


class CorrectionDecisionService:
    """Record immutable corrections and transition cases through decisions."""

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

    def submit_correction(
        self,
        review_case_id: str,
        *,
        field_path: str,
        new_value: ControlledValue | Mapping[str, Any],
        reason_code: str,
        corrected_by: str,
        expected_version: int,
        operation: CorrectionOperation | str = CorrectionOperation.REPLACE,
        old_value_reference: str | None = None,
        source_runtime: str | None = None,
        source_stage: str | None = None,
        source_artifact_id: str | None = None,
        source_artifact_version: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        correction_id: str | None = None,
        occurred_at: str | None = None,
    ) -> FieldCorrection:
        corrections = self.submit_corrections(
            review_case_id,
            [
                {
                    "correction_id": correction_id,
                    "field_path": field_path,
                    "new_value": new_value,
                    "reason_code": reason_code,
                    "operation": operation,
                    "old_value_reference": old_value_reference,
                    "source_runtime": source_runtime,
                    "source_stage": source_stage,
                    "source_artifact_id": source_artifact_id,
                    "source_artifact_version": source_artifact_version,
                    "metadata": metadata or {},
                }
            ],
            corrected_by=corrected_by,
            expected_version=expected_version,
            occurred_at=occurred_at,
        )
        return corrections[0]

    def submit_corrections(
        self,
        review_case_id: str,
        corrections: Iterable[FieldCorrection | Mapping[str, Any]],
        *,
        corrected_by: str,
        expected_version: int,
        occurred_at: str | None = None,
    ) -> tuple[FieldCorrection, ...]:
        case, normalized_version = self._load_for_action(review_case_id, expected_version)
        self._require_correction_state(case.status)
        actor_id = identifier(corrected_by, ("corrected_by",))
        self._require_assigned_reviewer(case.assigned_reviewer_id, actor_id)
        timestamp = occurred_at or self._clock()
        records = self._build_corrections(case, corrections, actor_id, timestamp)

        updated = replace(
            case,
            version=case.version + 1,
            updated_at=timestamp,
        )
        first_sequence = self._repository.next_audit_sequence(case.review_case_id)
        event = self._audit_event(
            case,
            updated,
            event_type="correction_submitted",
            actor_id=actor_id,
            sequence=first_sequence,
            metadata={"field_count": len(records)},
            new_status=case.status,
        )
        self._repository.commit_action(
            updated,
            (event,),
            expected_version=normalized_version,
            corrections=records,
        )
        return tuple(FieldCorrection.from_dict(item.to_dict()) for item in records)

    def list_corrections(self, review_case_id: str) -> tuple[FieldCorrection, ...]:
        return self._repository.list_corrections(identifier(review_case_id, ("review_case_id",)))

    def submit_decision(
        self,
        review_case_id: str,
        decision: ReviewerDecisionType | str,
        *,
        reviewer_id: str,
        expected_version: int,
        reason_code: str | None = None,
        correction_ids: tuple[str, ...] = (),
        reprocess_request: ReprocessRequest | None = None,
        metadata: Mapping[str, Any] | None = None,
        decision_id: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: str | None = None,
    ):
        case, normalized_version = self._load_for_action(review_case_id, expected_version)
        actor_id = identifier(reviewer_id, ("reviewer_id",))
        self._require_assigned_reviewer(case.assigned_reviewer_id, actor_id)
        target_status = status_for_decision(decision)
        timestamp = occurred_at or self._clock()
        updated = transition_review_case(case, target_status, occurred_at=timestamp)

        normalized_correction_ids = tuple(correction_ids)
        if target_status is ReviewStatus.CORRECTED:
            self._require_existing_corrections(case.review_case_id, normalized_correction_ids)
        if target_status is ReviewStatus.REPROCESS_REQUESTED and reprocess_request is None:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "request_reprocess requires a declarative reprocess request.",
                ("reprocess_request",),
            )
        if target_status is not ReviewStatus.REPROCESS_REQUESTED and reprocess_request is not None:
            raise ReviewRuntimeError(
                INVALID_VALUE,
                "Reprocess intent requires request_reprocess decision.",
                ("reprocess_request",),
            )
        if reprocess_request is not None and reprocess_request.review_case_id != case.review_case_id:
            raise ReviewCorrectionLineageConflictError()

        decision_record = ReviewerDecision(
            decision_id=decision_id or self._id_factory("review-decision"),
            review_case_id=case.review_case_id,
            decision=decision,
            reviewer_id=actor_id,
            occurred_at=timestamp,
            expected_case_version=normalized_version,
            idempotency_key=idempotency_key or self._id_factory("decision-idem"),
            reason_code=reason_code,
            correction_ids=normalized_correction_ids,
            reprocess_request_id=reprocess_request.request_id if reprocess_request else None,
            metadata=metadata or {},
        )
        events = self._decision_audit_events(
            case,
            updated,
            decision_record,
            reprocess_request,
        )
        return self._repository.commit_action(
            updated,
            events,
            expected_version=normalized_version,
            decision=decision_record,
            reprocess_request=reprocess_request,
        )

    def approve_case(self, review_case_id: str, **kwargs):
        return self.submit_decision(review_case_id, ReviewerDecisionType.APPROVE, **kwargs)

    def reject_case(self, review_case_id: str, **kwargs):
        return self.submit_decision(review_case_id, ReviewerDecisionType.REJECT, **kwargs)

    def skip_case(self, review_case_id: str, **kwargs):
        return self.submit_decision(review_case_id, ReviewerDecisionType.SKIP, **kwargs)

    def request_reprocess(
        self,
        review_case_id: str,
        *,
        requested_target_stage: str,
        reason_code: str,
        reviewer_id: str,
        expected_version: int,
        requested_from_stage: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        request_id: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: str | None = None,
    ):
        case, normalized_version = self._load_for_action(review_case_id, expected_version)
        timestamp = occurred_at or self._clock()
        request = ReprocessRequest(
            request_id=request_id or self._id_factory("reprocess-request"),
            review_case_id=case.review_case_id,
            requested_from_stage=requested_from_stage or case.source_stage,
            requested_target_stage=requested_target_stage,
            reason_code=reason_code,
            requested_by=reviewer_id,
            created_at=timestamp,
            metadata=metadata or {},
            expected_case_version=normalized_version,
            idempotency_key=idempotency_key,
        )
        return self.submit_decision(
            case.review_case_id,
            ReviewerDecisionType.REQUEST_REPROCESS,
            reviewer_id=reviewer_id,
            expected_version=normalized_version,
            reason_code=reason_code,
            reprocess_request=request,
            metadata=metadata,
            idempotency_key=idempotency_key,
            occurred_at=timestamp,
        )

    def correct_case(
        self,
        review_case_id: str,
        corrections: Iterable[FieldCorrection | Mapping[str, Any]],
        *,
        reviewer_id: str,
        expected_version: int,
        reason_code: str,
        metadata: Mapping[str, Any] | None = None,
        decision_id: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: str | None = None,
    ):
        case, normalized_version = self._load_for_action(review_case_id, expected_version)
        self._require_correction_state(case.status)
        actor_id = identifier(reviewer_id, ("reviewer_id",))
        self._require_assigned_reviewer(case.assigned_reviewer_id, actor_id)
        timestamp = occurred_at or self._clock()
        records = self._build_corrections(case, corrections, actor_id, timestamp)
        updated = transition_review_case(case, ReviewStatus.CORRECTED, occurred_at=timestamp)
        decision = ReviewerDecision(
            decision_id=decision_id or self._id_factory("review-decision"),
            review_case_id=case.review_case_id,
            decision=ReviewerDecisionType.CORRECT,
            reviewer_id=actor_id,
            occurred_at=timestamp,
            expected_case_version=normalized_version,
            idempotency_key=idempotency_key or self._id_factory("decision-idem"),
            reason_code=reason_code,
            correction_ids=tuple(item.correction_id for item in records),
            metadata=metadata or {},
        )
        sequence = self._repository.next_audit_sequence(case.review_case_id)
        correction_event = self._audit_event(
            case,
            updated,
            event_type="correction_submitted",
            actor_id=actor_id,
            sequence=sequence,
            metadata={"field_count": len(records)},
            new_status=case.status,
        )
        decision_event = self._audit_event(
            case,
            updated,
            event_type="decision_submitted",
            actor_id=actor_id,
            sequence=sequence + 1,
            metadata={"reason_code": reason_code},
            new_status=case.status,
        )
        status_event = self._audit_event(
            case,
            updated,
            event_type="status_changed",
            actor_id=actor_id,
            sequence=sequence + 2,
            metadata={},
            new_status=updated.status,
        )
        return self._repository.commit_action(
            updated,
            (correction_event, decision_event, status_event),
            expected_version=normalized_version,
            corrections=records,
            decision=decision,
        )

    def _load_for_action(self, review_case_id: str, expected_version: int):
        case_id = identifier(review_case_id, ("review_case_id",))
        normalized_version = positive_version(expected_version, ("expected_version",))
        case = self._repository.get_case(case_id)
        if case.version != normalized_version:
            raise ReviewCaseVersionConflictError()
        if case.status is ReviewStatus.RESOLVED:
            raise ReviewRuntimeError(
                INVALID_TRANSITION,
                "Resolved review cases are immutable.",
                ("status",),
            )
        return case, normalized_version

    @staticmethod
    def _require_correction_state(status: ReviewStatus) -> None:
        if status is not ReviewStatus.IN_REVIEW:
            raise ReviewRuntimeError(
                INVALID_TRANSITION,
                "Corrections may only be submitted while a case is in_review.",
                ("status",),
            )

    @staticmethod
    def _require_assigned_reviewer(assigned_reviewer_id: str | None, reviewer_id: str) -> None:
        if assigned_reviewer_id is not None and assigned_reviewer_id != reviewer_id:
            raise ReviewReviewerConflictError()

    def _build_corrections(
        self,
        case,
        corrections: Iterable[FieldCorrection | Mapping[str, Any]],
        corrected_by: str,
        occurred_at: str,
    ) -> tuple[FieldCorrection, ...]:
        items = tuple(corrections)
        if not items:
            raise ReviewRuntimeError(INVALID_VALUE, "At least one correction is required.", ("corrections",))
        records = tuple(
            item
            if isinstance(item, FieldCorrection)
            else self._correction_from_spec(case, item, corrected_by, occurred_at, index)
            for index, item in enumerate(items)
        )
        for item in records:
            if item.corrected_by != corrected_by:
                raise ReviewReviewerConflictError()
            self._validate_correction_lineage(case, item)
        if len({item.correction_id for item in records}) != len(records):
            raise ReviewRuntimeError(INVALID_VALUE, "Correction identifiers must be unique.", ("corrections",))
        return records

    def _correction_from_spec(self, case, spec, corrected_by, occurred_at, index):
        data = mapping(spec, ("corrections", index))
        check_keys(
            data,
            allowed=CORRECTION_SPEC_REQUIRED | CORRECTION_SPEC_OPTIONAL,
            required=CORRECTION_SPEC_REQUIRED,
            path=("corrections", index),
        )
        raw_value = data["new_value"]
        controlled_value = (
            raw_value if isinstance(raw_value, ControlledValue) else ControlledValue.from_dict(raw_value)
        )
        return FieldCorrection(
            correction_id=data.get("correction_id") or self._id_factory("field-correction"),
            review_case_id=case.review_case_id,
            field_path=data["field_path"],
            new_value=controlled_value,
            reason_code=data["reason_code"],
            corrected_by=corrected_by,
            created_at=occurred_at,
            source_runtime=data.get("source_runtime") or case.source_runtime,
            source_stage=data.get("source_stage") or case.source_stage,
            source_artifact_id=data.get("source_artifact_id") or case.source_artifact_id,
            operation=data.get("operation", CorrectionOperation.REPLACE),
            old_value_reference=data.get("old_value_reference"),
            source_artifact_version=data.get("source_artifact_version") or case.source_artifact_version,
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _validate_correction_lineage(case, correction: FieldCorrection) -> None:
        if (
            correction.review_case_id != case.review_case_id
            or correction.source_runtime != case.source_runtime
            or correction.source_stage != case.source_stage
            or correction.source_artifact_id != case.source_artifact_id
            or correction.source_artifact_version != case.source_artifact_version
        ):
            raise ReviewCorrectionLineageConflictError()

    def _require_existing_corrections(self, review_case_id: str, correction_ids: tuple[str, ...]) -> None:
        existing_ids = {item.correction_id for item in self._repository.list_corrections(review_case_id)}
        if not correction_ids or any(item not in existing_ids for item in correction_ids):
            raise ReviewCorrectionNotFoundError()

    def _decision_audit_events(self, case, updated, decision, reprocess_request):
        sequence = self._repository.next_audit_sequence(case.review_case_id)
        events = [
            self._audit_event(
                case,
                updated,
                event_type="decision_submitted",
                actor_id=decision.reviewer_id,
                sequence=sequence,
                metadata={"reason_code": decision.reason_code} if decision.reason_code else {},
                new_status=case.status,
            )
        ]
        if reprocess_request is not None:
            events.append(
                self._audit_event(
                    case,
                    updated,
                    event_type="reprocess_requested",
                    actor_id=decision.reviewer_id,
                    sequence=sequence + len(events),
                    metadata={"reason_code": reprocess_request.reason_code},
                    new_status=case.status,
                )
            )
        events.append(
            self._audit_event(
                case,
                updated,
                event_type="status_changed",
                actor_id=decision.reviewer_id,
                sequence=sequence + len(events),
                metadata={},
                new_status=updated.status,
            )
        )
        return tuple(events)

    def _audit_event(
        self,
        case,
        updated,
        *,
        event_type,
        actor_id,
        sequence,
        metadata,
        new_status,
    ):
        return ReviewAuditEvent(
            event_id=self._id_factory("review-event"),
            review_case_id=case.review_case_id,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=updated.updated_at,
            previous_status=case.status,
            new_status=new_status,
            sequence=sequence,
            case_version=updated.version,
            metadata=metadata,
        )
