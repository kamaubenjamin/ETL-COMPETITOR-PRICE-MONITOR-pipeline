import json

import pytest

from src.workflow_studio import (
    LegacyActionDescriptor,
    RuleDependencyNode,
    ValidationIssueCode,
    validate_dependencies,
)
from src.workflow_studio.validation_errors import validation_issue
from src.workflow_studio.validation_results import ValidationLayer, ValidationSeverity


def test_validation_issues_use_fixed_summaries_without_reflection() -> None:
    unsafe = "../../secret?token=value"
    issue = validation_issue(ValidationIssueCode.INVALID_PATH, ValidationSeverity.BLOCKING, ValidationLayer.PATH)
    assert unsafe not in json.dumps(issue.to_dict())
    assert issue.summary == "Logical field path is invalid."


def test_dependency_diagnostic_does_not_dump_raw_nodes() -> None:
    result = validate_dependencies([RuleDependencyNode("rule-safe", ("missing-safe",))])
    payload = result.to_dict()
    assert "missing-safe" not in json.dumps(payload)
    assert payload["issues"][0]["rule_id"] == "rule-safe"


@pytest.mark.parametrize("arguments", [
    {"token": "secret"}, {"credentials": "secret"}, {"raw_rows": "values"},
    {"script": "print(1)"}, {"payload": {"nested": True}},
])
def test_legacy_arguments_reject_sensitive_or_nested_values(arguments: object) -> None:
    with pytest.raises(ValueError):
        LegacyActionDescriptor("action-1", "function", arguments)
