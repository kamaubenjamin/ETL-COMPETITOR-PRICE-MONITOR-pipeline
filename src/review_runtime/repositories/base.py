"""Repository boundary for Review Case projections and audit events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.review_runtime.contracts.audit import ReviewAuditEvent
from src.review_runtime.contracts.correction import FieldCorrection
from src.review_runtime.contracts.decision import ReviewerDecision
from src.review_runtime.contracts.reprocess import ReprocessRequest
from src.review_runtime.contracts.review_case import ReviewCase
from src.review_runtime.reprocess.contracts import ReprocessPlan


@dataclass(frozen=True, slots=True)
class CaseCreateResult:
    review_case: ReviewCase
    created: bool


class ReviewCaseRepository(ABC):
    """Storage-neutral compare-version and append-only audit boundary."""

    @abstractmethod
    def create_case(
        self,
        review_case: ReviewCase,
        audit_event: ReviewAuditEvent,
        *,
        idempotency_key: str,
        creation_fingerprint: str,
    ) -> CaseCreateResult:
        """Atomically create a case and its first audit event."""

    @abstractmethod
    def get_case(self, review_case_id: str) -> ReviewCase:
        """Return a defensive case copy or raise ReviewCaseNotFoundError."""

    @abstractmethod
    def list_cases(self) -> tuple[ReviewCase, ...]:
        """Return defensive copies without exposing repository state."""

    @abstractmethod
    def update_case(
        self,
        review_case: ReviewCase,
        audit_event: ReviewAuditEvent,
        *,
        expected_version: int,
    ) -> ReviewCase:
        """Atomically compare version, update the projection, and append audit."""

    @abstractmethod
    def list_audit_events(self, review_case_id: str) -> tuple[ReviewAuditEvent, ...]:
        """Return append-only audit events ordered by sequence."""

    @abstractmethod
    def next_audit_sequence(self, review_case_id: str) -> int:
        """Return the next sequence for an atomic action on the case."""

    @abstractmethod
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
        """Atomically update a case and append immutable action records."""

    @abstractmethod
    def list_corrections(self, review_case_id: str) -> tuple[FieldCorrection, ...]:
        """Return append-only corrections in deterministic order."""

    @abstractmethod
    def list_decisions(self, review_case_id: str) -> tuple[ReviewerDecision, ...]:
        """Return append-only reviewer decisions in deterministic order."""

    @abstractmethod
    def list_reprocess_requests(self, review_case_id: str) -> tuple[ReprocessRequest, ...]:
        """Return declarative reprocess intents without executing them."""

    @abstractmethod
    def store_reprocess_plan(
        self,
        plan: ReprocessPlan,
        audit_event: ReviewAuditEvent,
        *,
        expected_version: int,
    ) -> ReprocessPlan:
        """Atomically append a dry-run plan and its audit event."""

    @abstractmethod
    def list_reprocess_plans(self, review_case_id: str) -> tuple[ReprocessPlan, ...]:
        """Return dry-run plans in deterministic order."""
