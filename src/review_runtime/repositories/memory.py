"""Deterministic in-memory Review Case repository."""

from __future__ import annotations

from threading import RLock

from src.review_runtime.contracts.audit import ReviewAuditEvent
from src.review_runtime.contracts.correction import FieldCorrection
from src.review_runtime.contracts.decision import ReviewerDecision
from src.review_runtime.contracts.reprocess import ReprocessRequest
from src.review_runtime.contracts.review_case import ReviewCase
from src.review_runtime.errors import (
    ReviewAuditConflictError,
    ReviewCaseAlreadyExistsError,
    ReviewCaseIdempotencyConflictError,
    ReviewCaseNotFoundError,
    ReviewCaseVersionConflictError,
)

from .base import CaseCreateResult, ReviewCaseRepository


def _copy_case(review_case: ReviewCase) -> ReviewCase:
    return ReviewCase.from_dict(review_case.to_dict())


def _copy_event(event: ReviewAuditEvent) -> ReviewAuditEvent:
    return ReviewAuditEvent.from_dict(event.to_dict())


def _copy_correction(correction: FieldCorrection) -> FieldCorrection:
    return FieldCorrection.from_dict(correction.to_dict())


def _copy_decision(decision: ReviewerDecision) -> ReviewerDecision:
    return ReviewerDecision.from_dict(decision.to_dict())


def _copy_reprocess_request(request: ReprocessRequest) -> ReprocessRequest:
    return ReprocessRequest.from_dict(request.to_dict())


class InMemoryReviewCaseRepository(ReviewCaseRepository):
    """Thread-safe process-local repository for tests and local execution."""

    def __init__(self) -> None:
        self._cases: dict[str, ReviewCase] = {}
        self._audit_events: dict[str, list[ReviewAuditEvent]] = {}
        self._corrections: dict[str, list[FieldCorrection]] = {}
        self._decisions: dict[str, list[ReviewerDecision]] = {}
        self._reprocess_requests: dict[str, list[ReprocessRequest]] = {}
        self._idempotency: dict[str, tuple[str, str]] = {}
        self._lock = RLock()

    def create_case(
        self,
        review_case: ReviewCase,
        audit_event: ReviewAuditEvent,
        *,
        idempotency_key: str,
        creation_fingerprint: str,
    ) -> CaseCreateResult:
        with self._lock:
            existing_idempotency = self._idempotency.get(idempotency_key)
            if existing_idempotency is not None:
                existing_fingerprint, existing_case_id = existing_idempotency
                if existing_fingerprint != creation_fingerprint:
                    raise ReviewCaseIdempotencyConflictError()
                return CaseCreateResult(
                    review_case=_copy_case(self._cases[existing_case_id]),
                    created=False,
                )

            if review_case.review_case_id in self._cases:
                raise ReviewCaseAlreadyExistsError()
            self._validate_create_audit(review_case, audit_event)

            stored_case = _copy_case(review_case)
            stored_event = _copy_event(audit_event)
            self._cases[stored_case.review_case_id] = stored_case
            self._audit_events[stored_case.review_case_id] = [stored_event]
            self._corrections[stored_case.review_case_id] = []
            self._decisions[stored_case.review_case_id] = []
            self._reprocess_requests[stored_case.review_case_id] = []
            self._idempotency[idempotency_key] = (
                creation_fingerprint,
                stored_case.review_case_id,
            )
            return CaseCreateResult(review_case=_copy_case(stored_case), created=True)

    def get_case(self, review_case_id: str) -> ReviewCase:
        with self._lock:
            review_case = self._cases.get(review_case_id)
            if review_case is None:
                raise ReviewCaseNotFoundError()
            return _copy_case(review_case)

    def list_cases(self) -> tuple[ReviewCase, ...]:
        with self._lock:
            return tuple(_copy_case(item) for item in self._cases.values())

    def update_case(
        self,
        review_case: ReviewCase,
        audit_event: ReviewAuditEvent,
        *,
        expected_version: int,
    ) -> ReviewCase:
        with self._lock:
            current = self._cases.get(review_case.review_case_id)
            if current is None:
                raise ReviewCaseNotFoundError()
            if current.version != expected_version:
                raise ReviewCaseVersionConflictError()
            if review_case.version != expected_version + 1:
                raise ReviewCaseVersionConflictError()

            events = self._audit_events[review_case.review_case_id]
            self._validate_update_audit(current, review_case, audit_event, len(events) + 1)
            stored_case = _copy_case(review_case)
            self._cases[stored_case.review_case_id] = stored_case
            events.append(_copy_event(audit_event))
            return _copy_case(stored_case)

    def list_audit_events(self, review_case_id: str) -> tuple[ReviewAuditEvent, ...]:
        with self._lock:
            if review_case_id not in self._cases:
                raise ReviewCaseNotFoundError()
            return tuple(
                _copy_event(item)
                for item in sorted(
                    self._audit_events[review_case_id],
                    key=lambda event: event.sequence,
                )
            )

    def next_audit_sequence(self, review_case_id: str) -> int:
        with self._lock:
            if review_case_id not in self._cases:
                raise ReviewCaseNotFoundError()
            return len(self._audit_events[review_case_id]) + 1

    def commit_action(
        self,
        review_case: ReviewCase,
        audit_events: tuple[ReviewAuditEvent, ...],
        *,
        expected_version: int,
        corrections: tuple[FieldCorrection, ...] = (),
        decision: ReviewerDecision | None = None,
        reprocess_request: ReprocessRequest | None = None,
    ) -> ReviewCase:
        with self._lock:
            current = self._cases.get(review_case.review_case_id)
            if current is None:
                raise ReviewCaseNotFoundError()
            if current.version != expected_version or review_case.version != expected_version + 1:
                raise ReviewCaseVersionConflictError()
            if not audit_events:
                raise ReviewAuditConflictError()

            existing_events = self._audit_events[review_case.review_case_id]
            existing_event_ids = {item.event_id for item in existing_events}
            new_event_ids = [item.event_id for item in audit_events]
            if (
                len(set(new_event_ids)) != len(new_event_ids)
                or any(item in existing_event_ids for item in new_event_ids)
            ):
                raise ReviewAuditConflictError()
            self._validate_action_audit(
                current,
                review_case,
                audit_events,
                len(existing_events) + 1,
            )
            self._validate_action_records(
                review_case.review_case_id,
                corrections,
                decision,
                reprocess_request,
            )

            stored_case = _copy_case(review_case)
            stored_events = tuple(_copy_event(item) for item in audit_events)
            stored_corrections = tuple(_copy_correction(item) for item in corrections)
            stored_decision = _copy_decision(decision) if decision else None
            stored_request = _copy_reprocess_request(reprocess_request) if reprocess_request else None

            self._cases[stored_case.review_case_id] = stored_case
            existing_events.extend(stored_events)
            self._corrections[stored_case.review_case_id].extend(stored_corrections)
            if stored_decision:
                self._decisions[stored_case.review_case_id].append(stored_decision)
            if stored_request:
                self._reprocess_requests[stored_case.review_case_id].append(stored_request)
            return _copy_case(stored_case)

    def list_corrections(self, review_case_id: str) -> tuple[FieldCorrection, ...]:
        with self._lock:
            if review_case_id not in self._cases:
                raise ReviewCaseNotFoundError()
            return tuple(
                _copy_correction(item)
                for item in sorted(
                    self._corrections[review_case_id],
                    key=lambda item: (item.created_at, item.correction_id),
                )
            )

    def list_decisions(self, review_case_id: str) -> tuple[ReviewerDecision, ...]:
        with self._lock:
            if review_case_id not in self._cases:
                raise ReviewCaseNotFoundError()
            return tuple(
                _copy_decision(item)
                for item in sorted(
                    self._decisions[review_case_id],
                    key=lambda item: (item.occurred_at, item.decision_id),
                )
            )

    def list_reprocess_requests(self, review_case_id: str) -> tuple[ReprocessRequest, ...]:
        with self._lock:
            if review_case_id not in self._cases:
                raise ReviewCaseNotFoundError()
            return tuple(
                _copy_reprocess_request(item)
                for item in sorted(
                    self._reprocess_requests[review_case_id],
                    key=lambda item: (item.created_at, item.request_id),
                )
            )

    @staticmethod
    def _validate_create_audit(
        review_case: ReviewCase,
        audit_event: ReviewAuditEvent,
    ) -> None:
        if (
            review_case.version != 1
            or audit_event.review_case_id != review_case.review_case_id
            or audit_event.event_type != "case_created"
            or audit_event.previous_status is not None
            or audit_event.new_status != review_case.status
            or audit_event.sequence != 1
            or audit_event.case_version != 1
        ):
            raise ReviewAuditConflictError()

    @staticmethod
    def _validate_update_audit(
        current: ReviewCase,
        updated: ReviewCase,
        audit_event: ReviewAuditEvent,
        expected_sequence: int,
    ) -> None:
        if (
            audit_event.review_case_id != updated.review_case_id
            or audit_event.previous_status != current.status
            or audit_event.new_status != updated.status
            or audit_event.sequence != expected_sequence
            or audit_event.case_version != updated.version
        ):
            raise ReviewAuditConflictError()

    @staticmethod
    def _validate_action_audit(
        current: ReviewCase,
        updated: ReviewCase,
        audit_events: tuple[ReviewAuditEvent, ...],
        first_sequence: int,
    ) -> None:
        prior_status = current.status
        for offset, event in enumerate(audit_events):
            if (
                event.review_case_id != updated.review_case_id
                or event.previous_status != prior_status
                or event.sequence != first_sequence + offset
                or event.case_version != updated.version
            ):
                raise ReviewAuditConflictError()
            prior_status = event.new_status
        if prior_status != updated.status:
            raise ReviewAuditConflictError()

    def _validate_action_records(
        self,
        review_case_id: str,
        corrections: tuple[FieldCorrection, ...],
        decision: ReviewerDecision | None,
        reprocess_request: ReprocessRequest | None,
    ) -> None:
        existing_correction_ids = {
            item.correction_id for item in self._corrections[review_case_id]
        }
        new_correction_ids: set[str] = set()
        for correction in corrections:
            if (
                correction.review_case_id != review_case_id
                or correction.correction_id in existing_correction_ids
                or correction.correction_id in new_correction_ids
            ):
                raise ReviewAuditConflictError()
            new_correction_ids.add(correction.correction_id)

        if decision is not None:
            if decision.review_case_id != review_case_id or any(
                item.decision_id == decision.decision_id
                or item.idempotency_key == decision.idempotency_key
                for item in self._decisions[review_case_id]
            ):
                raise ReviewAuditConflictError()
        if reprocess_request is not None:
            if reprocess_request.review_case_id != review_case_id or any(
                item.request_id == reprocess_request.request_id
                or item.idempotency_key == reprocess_request.idempotency_key
                for item in self._reprocess_requests[review_case_id]
            ):
                raise ReviewAuditConflictError()
