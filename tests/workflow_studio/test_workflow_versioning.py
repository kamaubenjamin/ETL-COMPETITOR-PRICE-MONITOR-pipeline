from dataclasses import replace

import pytest

from src.workflow_studio import (
    ActionDefinition, InMemoryWorkflowStudioStore, RuleDefinition, WorkflowChangeSummary,
    WorkflowDefinition, WorkflowOwnership, WorkflowRepositoryError, WorkflowVersion,
    clone_version_to_draft, next_integer_version,
)


NOW = "2026-07-14T10:00:00+00:00"
LATER = "2026-07-15T10:00:00+00:00"


def setup_published() -> tuple[InMemoryWorkflowStudioStore, WorkflowVersion]:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(WorkflowDefinition("workflow-1", "tenant-1", "Flow", "", "finance", None, "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW))
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    rule = RuleDefinition("rule-1", "Rule", "process", "", (), 0, True, False, None, (action,))
    value = WorkflowVersion("version-1", "workflow-1", 1, "published", (rule,), None, WorkflowChangeSummary("Published"), "author-1", "reviewer-1", "approver-1", NOW, NOW, NOW, None)
    store.create_version("tenant-1", value)
    return store, value


def test_next_integer_version_is_deterministic() -> None:
    store, _ = setup_published()
    assert next_integer_version(store, "tenant-1", "workflow-1") == 2


def test_published_version_clones_to_new_derived_draft() -> None:
    store, published = setup_published()
    draft = clone_version_to_draft(store, "tenant-1", published.version_id, new_version_id="version-2", authored_by="author-2", change_summary=WorkflowChangeSummary("Rollback proposal"), timestamp=LATER)
    assert draft.status.value == "draft"
    assert draft.version == 2
    assert draft.derived_from_version_id == "version-1"
    assert draft.published_at is None and draft.approved_by is None


def test_clone_does_not_modify_source_history() -> None:
    store, published = setup_published()
    clone_version_to_draft(store, "tenant-1", published.version_id, new_version_id="version-2", authored_by="author-2", change_summary=WorkflowChangeSummary("New"), timestamp=LATER)
    assert store.get_version("tenant-1", "version-1").value == published


def test_editable_draft_cannot_be_used_as_rollback_source() -> None:
    store, published = setup_published()
    store.transition_version("tenant-1", replace(published, status="inactive"), 1)
    draft = clone_version_to_draft(store, "tenant-1", "version-1", new_version_id="version-2", authored_by="author-2", change_summary=WorkflowChangeSummary("New"), timestamp=LATER)
    store.create_version("tenant-1", draft)
    with pytest.raises(WorkflowRepositoryError):
        clone_version_to_draft(store, "tenant-1", "version-2", new_version_id="version-3", authored_by="author-3", change_summary=WorkflowChangeSummary("Invalid"), timestamp=LATER)
