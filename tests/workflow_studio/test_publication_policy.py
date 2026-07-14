from dataclasses import replace

import pytest

from src.workflow_studio import (
    ActionDefinition, InMemoryWorkflowOperationCatalog, InMemoryWorkflowStudioStore,
    PublicationCommand, RuleDefinition, WorkflowChangeSummary, WorkflowDefinition,
    WorkflowOwnership, WorkflowPublicationService, WorkflowValidationService, WorkflowVersion,
    evaluate_publication_policy,
)


NOW = "2026-07-14T10:00:00+00:00"


def setup() -> tuple[InMemoryWorkflowStudioStore, WorkflowVersion, object]:
    store = InMemoryWorkflowStudioStore()
    definition = WorkflowDefinition("workflow-1", "tenant-1", "Flow", "", "finance", None, "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW)
    store.create_definition(definition)
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    rule = RuleDefinition("rule-1", "Rule", "process", "", (), 0, True, False, None, (action,))
    version = WorkflowVersion("version-1", "workflow-1", 1, "approved", (rule,), None, WorkflowChangeSummary("Approved"), "author-1", "reviewer-1", "approver-1", NOW, NOW, None, None)
    stored = store.create_version("tenant-1", version)
    validation = WorkflowValidationService(InMemoryWorkflowOperationCatalog()).validate(version)
    return store, version, validation


def command(validation: object, **changes: object) -> PublicationCommand:
    values = dict(
        tenant_id="tenant-1", workflow_id="workflow-1", version_id="version-1",
        publication_id="publication-1", environment="production", actor_id="publisher-1",
        expected_version_revision=1, expected_definition_revision=1,
        validation_result=validation, test_evidence_present=True, approval_evidence_present=True,
        publication_permission_granted=True, required_features_available=True,
        unresolved_legacy_review=False, supersede_previous=False, occurred_at=NOW,
    )
    values.update(changes)
    return PublicationCommand(**values)


def test_fully_eligible_approved_version_passes_policy() -> None:
    store, _, validation = setup()
    result = evaluate_publication_policy(command(validation), store.get_definition("tenant-1", "workflow-1"), store.get_version("tenant-1", "version-1"), None)
    assert result.allowed and result.issues == ()


@pytest.mark.parametrize(("field", "code"), [
    ("test_evidence_present", "test_evidence_required"),
    ("approval_evidence_present", "approval_evidence_required"),
    ("publication_permission_granted", "publication_permission_required"),
    ("required_features_available", "required_feature_unavailable"),
])
def test_missing_caller_supplied_facts_block_publication(field: str, code: str) -> None:
    store, _, validation = setup()
    result = evaluate_publication_policy(command(validation, **{field: False}), store.get_definition("tenant-1", "workflow-1"), store.get_version("tenant-1", "version-1"), None)
    assert not result.allowed
    assert code in {issue.code.value for issue in result.issues}


def test_invalid_validation_legacy_review_and_revision_conflict_are_blocked() -> None:
    store, _, validation = setup()
    invalid = replace(validation, publication_eligible=False)
    result = evaluate_publication_policy(
        command(invalid, unresolved_legacy_review=True, expected_version_revision=2),
        store.get_definition("tenant-1", "workflow-1"), store.get_version("tenant-1", "version-1"), None,
    )
    assert {item.code.value for item in result.issues}.issuperset({"publication_ineligible", "legacy_review_unresolved", "version_conflict"})


def test_policy_does_not_mutate_repository() -> None:
    store, version, validation = setup()
    evaluate_publication_policy(command(validation), store.get_definition("tenant-1", "workflow-1"), store.get_version("tenant-1", "version-1"), None)
    assert store.get_version("tenant-1", "version-1").value == version
