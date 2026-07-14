from dataclasses import replace

import pytest

from src.workflow_studio import (
    ActionDefinition, DraftLifecycleService, InMemoryWorkflowStudioStore, RuleDefinition,
    WorkflowChangeSummary, WorkflowDefinition, WorkflowOwnership, WorkflowRepositoryError,
    WorkflowVersion,
)


NOW = "2026-07-14T10:00:00+00:00"
T2 = "2026-07-14T11:00:00+00:00"


def setup() -> tuple[InMemoryWorkflowStudioStore, DraftLifecycleService, WorkflowVersion]:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(WorkflowDefinition("workflow-1", "tenant-1", "Flow", "", "finance", None, "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW))
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    rule = RuleDefinition("rule-1", "Rule", "process", "", (), 0, True, False, None, (action,))
    draft = WorkflowVersion("version-1", "workflow-1", 1, "draft", (rule,), None, WorkflowChangeSummary("Initial"), "author-1", None, None, NOW, NOW, None, None)
    return store, DraftLifecycleService(store), draft


def test_create_initial_draft_and_enforce_one_current_draft() -> None:
    store, service, draft = setup()
    result = service.create_initial_draft("tenant-1", draft, actor_id="author-1")
    assert result.succeeded and result.audit_intents[0].event_type.value == "draft_created"
    with pytest.raises(WorkflowRepositoryError) as error:
        service.create_initial_draft("tenant-1", replace(draft, version_id="version-2", version=2), actor_id="author-1")
    assert error.value.code == "current_draft_exists"


def test_valid_lifecycle_uses_caller_supplied_evidence() -> None:
    _, service, draft = setup()
    created = service.create_initial_draft("tenant-1", draft, actor_id="author-1")
    validated = service.mark_validated("tenant-1", "version-1", created.version.revision, validation_passed=True, actor_id="reviewer-1", timestamp=T2)
    tested = service.mark_test_passed("tenant-1", "version-1", validated.version.revision, test_passed=True, actor_id="reviewer-1", timestamp=T2)
    submitted = service.submit_for_approval("tenant-1", "version-1", actor_id="author-1", timestamp=T2)
    approved = service.approve_draft("tenant-1", "version-1", tested.version.revision, approver_id="approver-1", timestamp=T2)
    assert validated.version.value.status.value == "validated"
    assert tested.version.value.status.value == "test_passed"
    assert submitted.audit_intents[0].event_type.value == "draft_submitted"
    assert approved.version.value.status.value == "approved"


def test_failed_or_invalid_transition_is_denied_without_mutation() -> None:
    store, service, draft = setup()
    created = service.create_initial_draft("tenant-1", draft, actor_id="author-1")
    denied = service.mark_validated("tenant-1", "version-1", created.version.revision, validation_passed=False, actor_id="reviewer-1", timestamp=T2)
    approve = service.approve_draft("tenant-1", "version-1", created.version.revision, approver_id="approver-1", timestamp=T2)
    assert not denied.succeeded and not approve.succeeded
    assert store.get_version("tenant-1", "version-1").value.status.value == "draft"


def test_rejection_returns_tested_draft_to_editing() -> None:
    _, service, draft = setup()
    current = service.create_initial_draft("tenant-1", draft, actor_id="author-1")
    current = service.mark_validated("tenant-1", "version-1", current.version.revision, validation_passed=True, actor_id="reviewer-1", timestamp=T2)
    current = service.mark_test_passed("tenant-1", "version-1", current.version.revision, test_passed=True, actor_id="reviewer-1", timestamp=T2)
    rejected = service.reject_draft("tenant-1", "version-1", current.version.revision, reviewer_id="reviewer-1", timestamp=T2)
    assert rejected.version.value.status.value == "draft"
    assert rejected.audit_intents[0].event_type.value == "draft_rejected"


def test_archive_abandoned_draft_retains_record() -> None:
    store, service, draft = setup()
    created = service.create_initial_draft("tenant-1", draft, actor_id="author-1")
    archived = service.archive_draft("tenant-1", "version-1", created.version.revision, actor_id="author-1", timestamp=T2)
    assert archived.version.value.status.value == "archived"
    assert store.get_version("tenant-1", "version-1") == archived.version
