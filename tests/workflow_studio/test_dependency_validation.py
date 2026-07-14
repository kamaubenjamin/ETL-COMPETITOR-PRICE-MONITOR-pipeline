from src.workflow_studio import RuleDependencyNode, validate_dependencies


def codes(result: object) -> list[str]:
    return [issue.code for issue in result.issues]


def test_valid_graph_has_stable_topological_order() -> None:
    rules = [
        RuleDependencyNode("rule-c", ("rule-a", "rule-b")),
        RuleDependencyNode("rule-b", ("rule-a",)),
        RuleDependencyNode("rule-a"),
    ]
    assert validate_dependencies(rules).ordered_rule_ids == ("rule-a", "rule-b", "rule-c")


def test_missing_dependency_is_rejected() -> None:
    result = validate_dependencies([RuleDependencyNode("rule-a", ("missing",))])
    assert not result.valid
    assert codes(result) == ["missing_dependency"]


def test_self_and_duplicate_dependencies_are_rejected() -> None:
    result = validate_dependencies([RuleDependencyNode("rule-a", ("rule-a", "rule-a"))])
    assert codes(result) == ["duplicate_dependency", "self_dependency"]


def test_duplicate_rule_ids_are_rejected() -> None:
    result = validate_dependencies([RuleDependencyNode("rule-a"), RuleDependencyNode("rule-a")])
    assert codes(result) == ["duplicate_rule_id"]


def test_cycle_members_are_deterministic_and_exclude_downstream_nodes() -> None:
    result = validate_dependencies([
        RuleDependencyNode("rule-a", ("rule-b",)),
        RuleDependencyNode("rule-b", ("rule-a",)),
        RuleDependencyNode("rule-c", ("rule-a",)),
    ])
    assert result.cycle_member_ids == ("rule-a", "rule-b")
    assert codes(result) == ["dependency_cycle"]
