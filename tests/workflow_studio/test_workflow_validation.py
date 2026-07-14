from src.workflow_studio import (
    ActionDefinition,
    InMemoryWorkflowOperationCatalog,
    RuleDefinition,
    ValidationPolicyFacts,
    WorkflowChangeSummary,
    WorkflowValidationService,
    WorkflowVersion,
)


NOW = "2026-07-14T10:00:00+00:00"


def rule(rule_id: str = "rule-1", *, operation: str = "filter", order: int = 0, dependencies: tuple[str, ...] = ()) -> RuleDefinition:
    action = ActionDefinition(f"action-{rule_id}", "runtime", operation, "1")
    return RuleDefinition(rule_id, "Rule", "process", "", dependencies, order, True, False, None, (action,))


def version(rules: tuple[RuleDefinition, ...]) -> WorkflowVersion:
    return WorkflowVersion(
        "version-1", "workflow-1", 1, "draft", rules, None,
        WorkflowChangeSummary("Initial"), "actor-1", None, None, NOW, NOW, None, None,
    )


def validator() -> WorkflowValidationService:
    return WorkflowValidationService(InMemoryWorkflowOperationCatalog())


def test_valid_workflow_passes_and_serializes_safely() -> None:
    result = validator().validate(version((rule(),)))
    assert result.structurally_valid
    assert result.preview_eligible
    assert result.test_ready
    assert result.publication_eligible
    assert result.to_dict()["ordered_rule_ids"] == ["rule-1"]


def test_empty_workflow_is_structurally_invalid() -> None:
    result = validator().validate(version(()))
    assert not result.structurally_valid
    assert result.issues[0].code == "empty_workflow"


def test_duplicate_order_is_rejected_deterministically() -> None:
    result = validator().validate(version((rule("rule-a"), rule("rule-b"))))
    assert not result.structurally_valid
    assert "duplicate_rule_order" in {item.code for item in result.issues}


def test_duplicate_rule_ids_are_defensively_rejected() -> None:
    workflow = version((rule(),))
    object.__setattr__(workflow, "rules", (workflow.rules[0], workflow.rules[0]))
    result = validator().validate(workflow)
    assert not result.structurally_valid
    assert "duplicate_rule_id" in {item.code for item in result.issues}


def test_structural_preview_and_publication_outcomes_remain_distinct() -> None:
    result = validator().validate(
        version((rule(operation="trim"),)),
        policy=ValidationPolicyFacts(available_features=("workflow_operation_compiler",)),
    )
    assert result.structurally_valid
    assert not result.preview_eligible
    assert not result.publication_eligible
    assert result.publication_blocked


def test_caller_supplied_test_and_approval_policy_blocks_publication_only() -> None:
    result = validator().validate(
        version((rule(),)),
        policy=ValidationPolicyFacts(require_test_evidence=True, require_approval_evidence=True),
    )
    assert result.structurally_valid and result.preview_eligible
    assert not result.publication_eligible
    assert {item.code for item in result.issues}.issuperset({"test_evidence_required", "approval_evidence_required"})
