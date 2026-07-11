"""Deterministic in-memory Review Case repository."""

from __future__ import annotations

from threading import RLock

from src.review_runtime.contracts.audit import ReviewAuditEvent
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


class InMemoryReviewCaseRepository(ReviewCaseRepository):
    """Thread-safe process-local repository for tests and local execution."""

    def __init__(self) -> None:
        self._cases: dict[str, ReviewCase] = {}
        self._audit_events: dict[str, list[ReviewAuditEvent]] = {}
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

