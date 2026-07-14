from dataclasses import replace

import pytest

from src.workflow_studio import (
    ActionDefinition, InMemoryWorkflowStudioStore, RuleDefinition, WorkflowChangeSummary,
    WorkflowDefinition, WorkflowOwnership, WorkflowRepositoryError, WorkflowVersion,
)


NOW = "2026-07-14T10:00:00+00:00"


@pytest.mark.parametrize("status", ["approved", "published", "superseded", "archived"])
def test_non_draft_version_content_cannot_be_edited(status: str) -> None:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(WorkflowDefinition("workflow-1", "tenant-1", "Flow", "", "finance", None, "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW))
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    rule = RuleDefinition("rule-1", "Rule", "process", "", (), 0, True, False, None, (action,))
    value = WorkflowVersion("version-1", "workflow-1", 1, status, (rule,), None, WorkflowChangeSummary("Snapshot"), "author-1", None, "approver-1" if status != "archived" else None, NOW, NOW, NOW if status in {"published", "superseded", "archived"} else None, None)
    store.create_version("tenant-1", value)
    changed_rule = replace(rule, name="Changed")
    with pytest.raises(WorkflowRepositoryError) as error:
        store.update_draft("tenant-1", replace(value, rules=(changed_rule,)), 1)
    assert error.value.code == "immutable_version"


def test_status_transition_cannot_rewrite_published_content() -> None:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(WorkflowDefinition("workflow-1", "tenant-1", "Flow", "", "finance", None, "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW))
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    original = RuleDefinition("rule-1", "Rule", "process", "", (), 0, True, False, None, (action,))
    value = WorkflowVersion("version-1", "workflow-1", 1, "published", (original,), None, WorkflowChangeSummary("Snapshot"), "author-1", "reviewer-1", "approver-1", NOW, NOW, NOW, None)
    store.create_version("tenant-1", value)
    with pytest.raises(WorkflowRepositoryError):
        store.transition_version("tenant-1", replace(value, status="superseded", rules=(replace(original, name="Changed"),)), 1)


def test_store_rejects_direct_published_to_draft_transition() -> None:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(WorkflowDefinition("workflow-1", "tenant-1", "Flow", "", "finance", None, "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW))
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    rule = RuleDefinition("rule-1", "Rule", "process", "", (), 0, True, False, None, (action,))
    value = WorkflowVersion("version-1", "workflow-1", 1, "published", (rule,), None, WorkflowChangeSummary("Snapshot"), "author-1", "reviewer-1", "approver-1", NOW, NOW, NOW, None)
    store.create_version("tenant-1", value)
    with pytest.raises(WorkflowRepositoryError) as error:
        store.transition_version("tenant-1", replace(value, status="draft", published_at=None), 1)
    assert error.value.code == "invalid_state"
