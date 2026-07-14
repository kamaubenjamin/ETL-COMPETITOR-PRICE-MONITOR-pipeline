from src.workflow_studio import (
    ActionDefinition,
    InMemoryWorkflowOperationCatalog,
    OperationArgumentDefinition,
    OperationArgumentType,
    OperationAvailabilityStatus,
    OperationCategory,
    OperationDeterminism,
    OperationExecutionMode,
    StudioOperationDefinition,
    validate_action_compatibility,
)


def custom_catalog() -> InMemoryWorkflowOperationCatalog:
    operation = StudioOperationDefinition(
        "custom", "2", OperationCategory.TRANSFORMATION, "Custom operation",
        OperationAvailabilityStatus.AVAILABLE, OperationDeterminism.DETERMINISTIC,
        OperationExecutionMode.RUNTIME, "transform", True, True, True,
        ("custom_port",),
        (OperationArgumentDefinition("mode", OperationArgumentType.STRING, True),),
        requires_source_path=True, requires_target_path=True,
    )
    return InMemoryWorkflowOperationCatalog((operation,))


def test_known_available_operation_is_eligible() -> None:
    action = ActionDefinition("action-1", "runtime", "filter", "1")
    result = validate_action_compatibility("rule-1", action)
    assert result.structurally_valid and result.preview_eligible and result.publication_eligible


def test_unknown_and_wrong_version_operations_are_rejected() -> None:
    unknown = ActionDefinition("action-1", "runtime", "unknown", "1")
    wrong = ActionDefinition("action-2", "runtime", "filter", "2")
    assert validate_action_compatibility("rule-1", unknown).issues[0].code == "operation_not_found"
    assert validate_action_compatibility("rule-1", wrong).issues[0].code == "operation_version_not_found"


def test_unavailable_operation_is_structural_but_not_ready() -> None:
    action = ActionDefinition("action-1", "runtime", "trim", "1")
    result = validate_action_compatibility("rule-1", action, available_features=("workflow_operation_compiler",))
    assert result.structurally_valid
    assert not result.preview_eligible
    assert not result.publication_eligible
    assert "operation_unavailable" in {issue.code for issue in result.issues}


def test_argument_path_and_feature_contracts_are_checked() -> None:
    missing = ActionDefinition("action-1", "runtime", "custom", "2")
    result = validate_action_compatibility("rule-1", missing, custom_catalog())
    assert {item.code for item in result.issues}.issuperset({
        "missing_argument", "source_path_required", "target_path_required", "required_feature_unavailable",
    })
    valid = ActionDefinition(
        "action-2", "runtime", "custom", "2", "input.value", "output.value", {"mode": "strict"},
    )
    ready = validate_action_compatibility("rule-1", valid, custom_catalog(), available_features=("custom_port",))
    assert ready.structurally_valid and ready.preview_eligible and ready.publication_eligible


def test_unknown_and_incompatible_arguments_are_rejected() -> None:
    unknown = ActionDefinition("action-1", "runtime", "custom", "2", "a", "b", {"mode": "x", "extra": 1})
    wrong = ActionDefinition("action-2", "runtime", "custom", "2", "a", "b", {"mode": 1})
    assert "unknown_argument" in {item.code for item in validate_action_compatibility("rule-1", unknown, custom_catalog()).issues}
    assert "invalid_argument_type" in {item.code for item in validate_action_compatibility("rule-1", wrong, custom_catalog()).issues}
