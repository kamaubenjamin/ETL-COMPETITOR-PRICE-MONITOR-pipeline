"""Controlled editable-draft lifecycle; no validation or test success is inferred."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .audit import WorkflowStudioAuditEventType, WorkflowStudioAuditIntent
from .contracts import StudioContract
from .definitions import WorkflowChangeSummary, WorkflowVersion
from .policy_errors import PolicyErrorCode, PolicyIssue, policy_issue
from .repositories import StoredWorkflowVersion
from .statuses import WorkflowVersionStatus
from .store import InMemoryWorkflowStudioStore
from .versioning import clone_version_to_draft


_ALLOWED_TRANSITIONS = {
    WorkflowVersionStatus.DRAFT: {WorkflowVersionStatus.VALIDATED, WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.VALIDATED: {WorkflowVersionStatus.DRAFT, WorkflowVersionStatus.TEST_PASSED, WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.TEST_PASSED: {WorkflowVersionStatus.DRAFT, WorkflowVersionStatus.APPROVED, WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.APPROVED: {WorkflowVersionStatus.PUBLISHED},
    WorkflowVersionStatus.PUBLISHED: {WorkflowVersionStatus.SUPERSEDED, WorkflowVersionStatus.INACTIVE},
    WorkflowVersionStatus.SUPERSEDED: {WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.INACTIVE: {WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.ARCHIVED: set(),
}


@dataclass(frozen=True, slots=True)
class DraftLifecycleResult(StudioContract):
    succeeded: bool
    version: StoredWorkflowVersion | None
    issues: tuple[PolicyIssue, ...]
    audit_intents: tuple[WorkflowStudioAuditIntent, ...]


class DraftLifecycleService:
    def __init__(self, store: InMemoryWorkflowStudioStore) -> None:
        self._store = store

    def create_initial_draft(self, tenant_id: str, version: WorkflowVersion, *, actor_id: str, correlation_id: str | None = None) -> DraftLifecycleResult:
        if version.status is not WorkflowVersionStatus.DRAFT or version.derived_from_version_id is not None:
            return _denied()
        stored = self._store.create_version(tenant_id, version)
        audit = _audit(WorkflowStudioAuditEventType.DRAFT_CREATED, tenant_id, version, actor_id, "initial_draft", version.created_at, correlation_id)
        return DraftLifecycleResult(True, stored, (), (audit,))

    def derive_draft(
        self,
        tenant_id: str,
        source_version_id: str,
        *,
        new_version_id: str,
        authored_by: str,
        change_summary: WorkflowChangeSummary,
        timestamp: str,
        version: int | str | None = None,
        rollback: bool = False,
        correlation_id: str | None = None,
    ) -> DraftLifecycleResult:
        draft = clone_version_to_draft(
            self._store, tenant_id, source_version_id, new_version_id=new_version_id,
            authored_by=authored_by, change_summary=change_summary, timestamp=timestamp, version=version,
        )
        stored = self._store.create_version(tenant_id, draft)
        event = WorkflowStudioAuditEventType.ROLLBACK_DRAFT_CREATED if rollback else WorkflowStudioAuditEventType.DRAFT_CREATED
        audit = _audit(event, tenant_id, draft, authored_by, "derived_draft", timestamp, correlation_id)
        return DraftLifecycleResult(True, stored, (), (audit,))

    def update_draft(self, tenant_id: str, version: WorkflowVersion, expected_revision: int, *, actor_id: str, timestamp: str, correlation_id: str | None = None) -> DraftLifecycleResult:
        updated = replace(version, updated_at=timestamp, authored_by=actor_id)
        stored = self._store.update_draft(tenant_id, updated, expected_revision)
        audit = _audit(WorkflowStudioAuditEventType.DRAFT_UPDATED, tenant_id, updated, actor_id, "draft_content_updated", timestamp, correlation_id)
        return DraftLifecycleResult(True, stored, (), (audit,))

    def mark_validated(self, tenant_id: str, version_id: str, expected_revision: int, *, validation_passed: bool, actor_id: str, timestamp: str) -> DraftLifecycleResult:
        if not validation_passed:
            return _denied()
        return self._transition(tenant_id, version_id, expected_revision, WorkflowVersionStatus.VALIDATED, actor_id, timestamp, WorkflowStudioAuditEventType.DRAFT_UPDATED, "validation_passed")

    def mark_test_passed(self, tenant_id: str, version_id: str, expected_revision: int, *, test_passed: bool, actor_id: str, timestamp: str) -> DraftLifecycleResult:
        if not test_passed:
            return _denied()
        return self._transition(tenant_id, version_id, expected_revision, WorkflowVersionStatus.TEST_PASSED, actor_id, timestamp, WorkflowStudioAuditEventType.DRAFT_UPDATED, "test_passed")

    def submit_for_approval(self, tenant_id: str, version_id: str, *, actor_id: str, timestamp: str, correlation_id: str | None = None) -> DraftLifecycleResult:
        current = self._store.get_version(tenant_id, version_id)
        if current is None or current.value.status is not WorkflowVersionStatus.TEST_PASSED:
            return _denied()
        audit = _audit(WorkflowStudioAuditEventType.DRAFT_SUBMITTED, tenant_id, current.value, actor_id, "approval_requested", timestamp, correlation_id)
        return DraftLifecycleResult(True, current, (), (audit,))

    def approve_draft(self, tenant_id: str, version_id: str, expected_revision: int, *, approver_id: str, timestamp: str) -> DraftLifecycleResult:
        return self._transition(tenant_id, version_id, expected_revision, WorkflowVersionStatus.APPROVED, approver_id, timestamp, WorkflowStudioAuditEventType.DRAFT_APPROVED, "approval_granted", approved_by=approver_id)

    def reject_draft(self, tenant_id: str, version_id: str, expected_revision: int, *, reviewer_id: str, timestamp: str, reason_code: str = "changes_requested") -> DraftLifecycleResult:
        return self._transition(tenant_id, version_id, expected_revision, WorkflowVersionStatus.DRAFT, reviewer_id, timestamp, WorkflowStudioAuditEventType.DRAFT_REJECTED, reason_code, reviewed_by=reviewer_id, approved_by=None)

    def archive_draft(self, tenant_id: str, version_id: str, expected_revision: int, *, actor_id: str, timestamp: str) -> DraftLifecycleResult:
        return self._transition(tenant_id, version_id, expected_revision, WorkflowVersionStatus.ARCHIVED, actor_id, timestamp, WorkflowStudioAuditEventType.DRAFT_ARCHIVED, "draft_abandoned")

    def _transition(
        self,
        tenant_id: str,
        version_id: str,
        expected_revision: int,
        target: WorkflowVersionStatus,
        actor_id: str,
        timestamp: str,
        event: WorkflowStudioAuditEventType,
        reason_code: str,
        **changes,
    ) -> DraftLifecycleResult:
        current = self._store.get_version(tenant_id, version_id)
        if current is None or target not in _ALLOWED_TRANSITIONS[current.value.status]:
            return _denied()
        transitioned = replace(current.value, status=target, updated_at=timestamp, **changes)
        stored = self._store.transition_version(tenant_id, transitioned, expected_revision)
        audit = _audit(event, tenant_id, transitioned, actor_id, reason_code, timestamp, None)
        return DraftLifecycleResult(True, stored, (), (audit,))


def _denied() -> DraftLifecycleResult:
    return DraftLifecycleResult(False, None, (policy_issue(PolicyErrorCode.INVALID_TRANSITION),), ())


def _audit(event: WorkflowStudioAuditEventType, tenant_id: str, version: WorkflowVersion, actor_id: str, reason_code: str, timestamp: str, correlation_id: str | None) -> WorkflowStudioAuditIntent:
    return WorkflowStudioAuditIntent(event, tenant_id, version.workflow_id, version.version_id, None, actor_id, version.status.value, reason_code, timestamp, correlation_id)
