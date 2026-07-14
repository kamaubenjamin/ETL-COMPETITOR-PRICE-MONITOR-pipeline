import pytest

from src.workflow_studio.conditions import (
    BooleanOperator,
    ConditionDefinition,
    ConditionGroup,
    ConditionOperator,
    NullPolicy,
)


def test_all_required_condition_operators_are_available() -> None:
    assert {item.value for item in ConditionOperator} == {
        "exists", "not_exists", "equals", "not_equals", "contains", "not_contains",
        "starts_with", "ends_with", "in", "not_in", "greater_than",
        "greater_than_or_equal", "less_than", "less_than_or_equal", "matches_regex",
        "is_null", "is_not_null",
    }


def test_condition_and_group_serialize_as_structured_values() -> None:
    condition = ConditionDefinition("invoice.total", "greater_than", 100, NullPolicy.REJECT)
    group = ConditionGroup(BooleanOperator.ALL, (condition, ConditionDefinition("invoice.currency", "in", ["KES", "USD"])))
    assert group.to_dict()["conditions"][1]["value"] == ["KES", "USD"]


@pytest.mark.parametrize("value", [{"nested": "value"}, object(), lambda: None])
def test_condition_rejects_unrestricted_values(value: object) -> None:
    with pytest.raises(ValueError):
        ConditionDefinition("invoice.total", ConditionOperator.EQUALS, value)


def test_condition_operator_value_shape_is_enforced() -> None:
    with pytest.raises(ValueError):
        ConditionDefinition("invoice.total", "exists", 1)
    with pytest.raises(ValueError):
        ConditionDefinition("invoice.total", "in", "KES")
    with pytest.raises(ValueError):
        ConditionGroup("not", (ConditionDefinition("invoice.total", "exists"), ConditionDefinition("invoice.id", "exists")))


@pytest.mark.parametrize("value", ["__import__('os')", "select secret from records", "powershell -Command whoami"])
def test_condition_rejects_code_sql_and_shell_like_values(value: str) -> None:
    with pytest.raises(ValueError):
        ConditionDefinition("invoice.reference", "equals", value)
