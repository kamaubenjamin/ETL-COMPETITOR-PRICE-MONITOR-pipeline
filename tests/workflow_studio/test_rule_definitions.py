import pytest

from src.workflow_studio import ActionDefinition, ConditionDefinition, RuleDefinition


def action() -> ActionDefinition:
    return ActionDefinition("action-1", "runtime", "filter", "1", arguments={"category": "invoice"})


def rule(**changes: object) -> RuleDefinition:
    values = dict(
        rule_id="rule-1", name="Invoice rule", stage="normalize", description="Safe rule",
        dependencies=("rule-0",), order=1, enabled=True, skip=False,
        condition=ConditionDefinition("invoice.total", "greater_than", 0), actions=(action(),),
        input_contract_hints=("invoice.total",), output_contract_hints=("invoice.accepted",),
    )
    values.update(changes)
    return RuleDefinition(**values)


def test_rule_accepts_stable_dependencies_and_modeled_actions() -> None:
    value = rule()
    assert value.dependencies == ("rule-0",)
    assert value.to_dict()["actions"][0]["operation_name"] == "filter"


@pytest.mark.parametrize("dependencies", [("rule-1",), ("rule-0", "rule-0"), (lambda: None,)])
def test_rule_rejects_invalid_dependencies(dependencies: object) -> None:
    with pytest.raises(ValueError):
        rule(dependencies=dependencies)


def test_rule_rejects_unmodeled_or_callable_actions() -> None:
    with pytest.raises(ValueError):
        rule(actions=(lambda: None,))
    with pytest.raises(ValueError):
        rule(actions=({"operation": "filter"},))
