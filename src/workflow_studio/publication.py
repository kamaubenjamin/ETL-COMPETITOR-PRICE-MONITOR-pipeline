"""Pure publication policy and controlled governed-definition publication service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from .audit import WorkflowStudioAuditEventType, WorkflowStudioAuditIntent
from .contracts import StudioContract, safe_metadata, stable_id, utc_timestamp
from .definitions import WorkflowDefinition, WorkflowPublication, WorkflowReference, WorkflowVersion
from .policy_errors import PolicyErrorCode, PolicyIssue, policy_issue
from .repositories import StoredWorkflowDefinition, StoredWorkflowPublication, StoredWorkflowVersion
from .repository_errors import WorkflowRepositoryError
from .statuses import WorkflowDefinitionStatus, WorkflowPublicationStatus, WorkflowVersionStatus
from .store import InMemoryWorkflowStudioStore
from .validation_results import WorkflowValidationResult


@dataclass(frozen=True, slots=True)
class PublicationCommand(StudioContract):
    tenant_id: str
    workflow_id: str
    version_id: str
    publication_id: str
    environment: str
    actor_id: str
    expected_version_revision: int
    expected_definition_revision: int
    validation_result: WorkflowValidationResult
    test_evidence_present: bool
    approval_evidence_present: bool
    publication_permission_granted: bool
    required_features_available: bool
    unresolved_legacy_review: bool
    supersede_previous: bool
    occurred_at: str
    correlation_id: str | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for name in ("tenant_id", "workflow_id", "version_id", "publication_id", "environment", "actor_id"):
            object.__setattr__(self, name, stable_id(getattr(self, name), name))
        if not isinstance(self.expected_version_revision, int) or self.expected_version_revision < 1:
            raise ValueError("expected_version_revision must be positive")
        if not isinstance(self.expected_definition_revision, int) or self.expected_definition_revision < 1:
            raise ValueError("expected_definition_revision must be positive")
        if not isinstance(self.validation_result, WorkflowValidationResult):
            raise ValueError("validation_result must be modeled")
        for name in ("test_evidence_present", "approval_evidence_present", "publication_permission_granted", "required_features_available", "unresolved_legacy_review", "supersede_previous"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a boolean")
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        if self.correlation_id is not None:
            object.__setattr__(self, "correlation_id", stable_id(self.correlation_id, "correlation_id"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class PublicationPolicyResult(StudioContract):
    allowed: bool
    issues: tuple[PolicyIssue, ...]


@dataclass(frozen=True, slots=True)
class PublicationServiceResult(StudioContract):
    published: bool
    version: StoredWorkflowVersion | None
    publication: StoredWorkflowPublication | None
    definition: StoredWorkflowDefinition | None
    superseded_publication: StoredWorkflowPublication | None
    issues: tuple[PolicyIssue, ...]
    audit_intents: tuple[WorkflowStudioAuditIntent, ...]


def evaluate_publication_policy(
    command: PublicationCommand,
    definition: StoredWorkflowDefinition | None,
    version: StoredWorkflowVersion | None,
    active_publication: StoredWorkflowPublication | None,
    *,
    publication_identity_exists: bool = False,
) -> PublicationPolicyResult:
    issues = []
    if definition is None or version is None or definition.value.tenant_id != command.tenant_id or definition.value.workflow_id != command.workflow_id or version.tenant_id != command.tenant_id or version.value.workflow_id != command.workflow_id or version.value.version_id != command.version_id:
        issues.append(policy_issue(PolicyErrorCode.TENANT_WORKFLOW_MISMATCH))
    else:
        if version.value.status is not WorkflowVersionStatus.APPROVED:
            issues.append(policy_issue(PolicyErrorCode.VERSION_NOT_APPROVED))
        if version.revision != command.expected_version_revision or definition.revision != command.expected_definition_revision:
            issues.append(policy_issue(PolicyErrorCode.VERSION_CONFLICT))
    validation = command.validation_result
    if validation.workflow_id != command.workflow_id or validation.version_id != command.version_id or not validation.structurally_valid:
        issues.append(policy_issue(PolicyErrorCode.VALIDATION_REQUIRED))
    if not validation.dependency_result.valid:
        issues.append(policy_issue(PolicyErrorCode.DEPENDENCY_INVALID))
    if not validation.publication_eligible:
        issues.append(policy_issue(PolicyErrorCode.PUBLICATION_INELIGIBLE))
    if not command.test_evidence_present:
        issues.append(policy_issue(PolicyErrorCode.TEST_EVIDENCE_REQUIRED))
    if not command.approval_evidence_present:
        issues.append(policy_issue(PolicyErrorCode.APPROVAL_EVIDENCE_REQUIRED))
    if not command.publication_permission_granted:
        issues.append(policy_issue(PolicyErrorCode.PUBLICATION_PERMISSION_REQUIRED))
    if not command.required_features_available:
        issues.append(policy_issue(PolicyErrorCode.REQUIRED_FEATURE_UNAVAILABLE))
    if command.unresolved_legacy_review:
        issues.append(policy_issue(PolicyErrorCode.LEGACY_REVIEW_UNRESOLVED))
    if publication_identity_exists:
        issues.append(policy_issue(PolicyErrorCode.PUBLICATION_ALREADY_EXISTS))
    if active_publication is not None and not command.supersede_previous:
        issues.append(policy_issue(PolicyErrorCode.ACTIVE_PUBLICATION_CONFLICT))
    return PublicationPolicyResult(not issues, tuple(issues))


class WorkflowPublicationService:
    def __init__(self, store: InMemoryWorkflowStudioStore) -> None:
        self._store = store

    def publish(self, command: PublicationCommand) -> PublicationServiceResult:
        definition = self._store.get_definition(command.tenant_id, command.workflow_id)
        version = self._store.get_version(command.tenant_id, command.version_id)
        active = self._store.find_active_publication(command.tenant_id, command.workflow_id)
        existing = self._store.get_publication(command.tenant_id, command.publication_id) is not None
        requested = _audit(WorkflowStudioAuditEventType.PUBLICATION_REQUESTED, command, "publication_requested", WorkflowPublicationStatus.PENDING_APPROVAL.value)
        policy = evaluate_publication_policy(command, definition, version, active, publication_identity_exists=existing)
        if not policy.allowed or definition is None or version is None:
            return PublicationServiceResult(False, None, None, None, None, policy.issues, (requested,))

        published_version = replace(version.value, status=WorkflowVersionStatus.PUBLISHED, published_at=command.occurred_at, updated_at=command.occurred_at)
        publication = WorkflowPublication(
            command.publication_id, command.workflow_id, command.version_id,
            WorkflowPublicationStatus.ACTIVE, command.environment, command.actor_id,
            command.occurred_at, command.occurred_at, None, command.metadata,
        )
        definition_value = replace(
            definition.value,
            status=WorkflowDefinitionStatus.PUBLISHED,
            active_published_version=WorkflowReference(command.workflow_id, command.version_id, version.value.version),
            current_draft_version=None,
            updated_at=command.occurred_at,
        )
        previous_publication = None
        previous_version = None
        previous_publication_revision = None
        previous_version_revision = None
        if active is not None:
            previous_publication = replace(active.value, status=WorkflowPublicationStatus.SUPERSEDED, deactivated_at=command.occurred_at)
            previous_publication_revision = active.revision
            old_version = self._store.get_version(command.tenant_id, active.value.version_id)
            if old_version is None:
                return PublicationServiceResult(False, None, None, None, None, (policy_issue(PolicyErrorCode.TENANT_WORKFLOW_MISMATCH),), (requested,))
            previous_version = replace(old_version.value, status=WorkflowVersionStatus.SUPERSEDED, updated_at=command.occurred_at)
            previous_version_revision = old_version.revision
        try:
            stored_version, stored_publication, stored_definition, superseded, _ = self._store.commit_publication(
                command.tenant_id, published_version, command.expected_version_revision,
                publication, definition_value, command.expected_definition_revision,
                previous_publication=previous_publication, previous_version=previous_version,
                expected_previous_publication_revision=previous_publication_revision,
                expected_previous_version_revision=previous_version_revision,
            )
        except WorkflowRepositoryError:
            return PublicationServiceResult(False, None, None, None, None, (policy_issue(PolicyErrorCode.VERSION_CONFLICT),), (requested,))
        audits = [requested]
        if superseded is not None:
            audits.append(_audit(WorkflowStudioAuditEventType.PUBLICATION_SUPERSEDED, command, "replaced_by_new_publication", WorkflowPublicationStatus.SUPERSEDED.value, publication_id=superseded.value.publication_id, version_id=superseded.value.version_id))
        audits.append(_audit(WorkflowStudioAuditEventType.WORKFLOW_PUBLISHED, command, "governed_definition_published", WorkflowPublicationStatus.ACTIVE.value))
        return PublicationServiceResult(True, stored_version, stored_publication, stored_definition, superseded, (), tuple(audits))

    def deactivate(self, tenant_id: str, workflow_id: str, *, actor_id: str, occurred_at: str, expected_publication_revision: int, expected_definition_revision: int, correlation_id: str | None = None) -> PublicationServiceResult:
        active = self._store.find_active_publication(tenant_id, workflow_id)
        definition = self._store.get_definition(tenant_id, workflow_id)
        if active is None or definition is None:
            return PublicationServiceResult(False, None, None, definition, None, (policy_issue(PolicyErrorCode.ACTIVE_PUBLICATION_REQUIRED),), ())
        version = self._store.get_version(tenant_id, active.value.version_id)
        if version is None:
            return PublicationServiceResult(False, None, None, definition, None, (policy_issue(PolicyErrorCode.TENANT_WORKFLOW_MISMATCH),), ())
        timestamp = utc_timestamp(occurred_at, "occurred_at")
        inactive_publication = replace(active.value, status=WorkflowPublicationStatus.INACTIVE, deactivated_at=timestamp)
        inactive_version = replace(version.value, status=WorkflowVersionStatus.INACTIVE, updated_at=timestamp)
        inactive_definition = replace(definition.value, status=WorkflowDefinitionStatus.INACTIVE, active_published_version=None, updated_at=timestamp)
        try:
            stored_pub, stored_version, stored_definition = self._store.commit_deactivation(
                tenant_id, inactive_publication, expected_publication_revision, inactive_version, version.revision,
                inactive_definition, expected_definition_revision,
            )
        except WorkflowRepositoryError:
            return PublicationServiceResult(False, None, None, definition, None, (policy_issue(PolicyErrorCode.VERSION_CONFLICT),), ())
        command_stub = _AuditCommand(tenant_id, workflow_id, version.value.version_id, active.value.publication_id, actor_id, timestamp, correlation_id)
        audit = _audit(WorkflowStudioAuditEventType.WORKFLOW_DEACTIVATED, command_stub, "publication_deactivated", WorkflowPublicationStatus.INACTIVE.value)
        return PublicationServiceResult(False, stored_version, stored_pub, stored_definition, None, (), (audit,))

    def archive_definition(self, tenant_id: str, workflow_id: str, *, actor_id: str, occurred_at: str, expected_definition_revision: int) -> PublicationServiceResult:
        definition = self._store.get_definition(tenant_id, workflow_id)
        if definition is None:
            return PublicationServiceResult(False, None, None, None, None, (policy_issue(PolicyErrorCode.TENANT_WORKFLOW_MISMATCH),), ())
        if self._store.find_active_publication(tenant_id, workflow_id) is not None:
            return PublicationServiceResult(False, None, None, definition, None, (policy_issue(PolicyErrorCode.ARCHIVE_BLOCKED),), ())
        timestamp = utc_timestamp(occurred_at, "occurred_at")
        archived = replace(definition.value, status=WorkflowDefinitionStatus.ARCHIVED, updated_at=timestamp)
        try:
            stored = self._store.update_definition(archived, expected_definition_revision)
        except WorkflowRepositoryError:
            return PublicationServiceResult(False, None, None, definition, None, (policy_issue(PolicyErrorCode.VERSION_CONFLICT),), ())
        stub = _AuditCommand(tenant_id, workflow_id, None, None, actor_id, timestamp, None)
        audit = _audit(WorkflowStudioAuditEventType.WORKFLOW_ARCHIVED, stub, "workflow_archived", WorkflowDefinitionStatus.ARCHIVED.value)
        return PublicationServiceResult(False, None, None, stored, None, (), (audit,))


@dataclass(frozen=True, slots=True)
class _AuditCommand:
    tenant_id: str
    workflow_id: str
    version_id: str | None
    publication_id: str | None
    actor_id: str
    occurred_at: str
    correlation_id: str | None


def _audit(event: WorkflowStudioAuditEventType, command, reason: str, status: str, *, publication_id: str | None = None, version_id: str | None = None) -> WorkflowStudioAuditIntent:
    return WorkflowStudioAuditIntent(
        event, command.tenant_id, command.workflow_id,
        version_id if version_id is not None else command.version_id,
        publication_id if publication_id is not None else command.publication_id,
        command.actor_id, status, reason, command.occurred_at, command.correlation_id,
    )
