import pytest

from src.workflow_studio import (
    ActionDefinition, InMemoryWorkflowStudioStore, RepositoryErrorCode, RuleDefinition,
    WorkflowChangeSummary, WorkflowDefinition, WorkflowOwnership, WorkflowRepositoryError,
    WorkflowVersion,
)


NOW = "2026-07-14T10:00:00+00:00"


def definition(tenant: str = "tenant-1", workflow: str = "workflow-1") -> WorkflowDefinition:
    return WorkflowDefinition(workflow, tenant, "Invoice flow", "", "finance", "invoice", "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW)


def version(version_id: str = "version-1", workflow: str = "workflow-1", label: int | str = 1) -> WorkflowVersion:
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    rule = RuleDefinition("rule-1", "Rule", "process", "", (), 0, True, False, None, (action,))
    return WorkflowVersion(version_id, workflow, label, "draft", (rule,), None, WorkflowChangeSummary("Initial"), "actor-1", None, None, NOW, NOW, None, None)


def test_create_read_and_duplicate_workflow_policy() -> None:
    store = InMemoryWorkflowStudioStore()
    stored = store.create_definition(definition())
    assert stored.revision == 1
    assert store.get_definition("tenant-1", "workflow-1") == stored
    with pytest.raises(WorkflowRepositoryError) as error:
        store.create_definition(definition())
    assert error.value.code == RepositoryErrorCode.DUPLICATE_WORKFLOW.value


def test_same_workflow_id_is_allowed_in_different_tenants() -> None:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(definition("tenant-1"))
    store.create_definition(definition("tenant-2"))
    assert store.get_definition("tenant-1", "workflow-1").value.tenant_id == "tenant-1"
    assert store.get_definition("tenant-2", "workflow-1").value.tenant_id == "tenant-2"


def test_versions_require_matching_workflow_and_unique_identity_and_label() -> None:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(definition())
    store.create_version("tenant-1", version())
    with pytest.raises(WorkflowRepositoryError) as duplicate:
        store.create_version("tenant-1", version())
    assert duplicate.value.code == "duplicate_version"
    with pytest.raises(WorkflowRepositoryError) as label:
        store.create_version("tenant-1", version("version-2", label=1))
    assert label.value.code == "duplicate_version_label"
    with pytest.raises(WorkflowRepositoryError) as mismatch:
        store.create_version("tenant-1", version("version-3", "workflow-other", 2))
    assert mismatch.value.code == "not_found"


def test_listing_is_tenant_scoped_stable_and_bounded() -> None:
    store = InMemoryWorkflowStudioStore()
    for workflow in ("workflow-c", "workflow-a", "workflow-b"):
        store.create_definition(definition("tenant-1", workflow))
    store.create_definition(definition("tenant-2", "workflow-hidden"))
    page = store.list_definitions("tenant-1", limit=2, offset=1)
    assert [item.value.workflow_id for item in page.items] == ["workflow-b", "workflow-c"]
    assert page.total == 3
    with pytest.raises(ValueError):
        store.list_definitions("tenant-1", limit=101)


def test_optimistic_definition_conflict_is_safe() -> None:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(definition())
    with pytest.raises(WorkflowRepositoryError) as error:
        store.update_definition(definition(), expected_revision=2)
    assert error.value.to_dict() == {"code": "version_conflict", "message": "Workflow record changed before the requested update."}
