import pytest

from src.workflow_studio import ConditionDefinition, ConditionGroup, validate_condition


def test_valid_condition_shapes_pass_validation() -> None:
    group = ConditionGroup("all", (
        ConditionDefinition("line_items[].amount", "greater_than", 0),
        ConditionDefinition("document.currency", "in", ("KES", "USD")),
        ConditionDefinition("document.reference", "matches_regex", "^[A-Z]+$"),
    ))
    assert validate_condition(group) == ()


def test_unmodeled_condition_is_rejected_safely() -> None:
    issues = validate_condition({"expression": "eval(value)"})
    assert [item.code for item in issues] == ["invalid_condition"]


def test_operator_value_compatibility_is_enforced_by_contract() -> None:
    with pytest.raises(ValueError):
        ConditionDefinition("field", "exists", "value")
    with pytest.raises(ValueError):
        ConditionDefinition("field", "in", "value")
    with pytest.raises(ValueError):
        ConditionDefinition("field", "equals", ["a", "b"])


def test_regex_requires_bounded_string() -> None:
    issues = validate_condition(ConditionDefinition("field", "matches_regex", 42))
    assert [item.code for item in issues] == ["invalid_condition_value"]


def test_excessive_group_width_and_depth_are_rejected() -> None:
    leaf = ConditionDefinition("field", "equals", "value")
    with pytest.raises(ValueError):
        ConditionGroup("all", tuple(leaf for _ in range(33)))
    nested = ConditionGroup("all", (leaf,))
    for _ in range(4):
        nested = ConditionGroup("all", (nested,))
    with pytest.raises(ValueError):
        ConditionGroup("all", (nested,))
