import json
from datetime import datetime

import pandas as pd
import pandas.testing as pdt
import pytest

from src.transforms.errors import ConfigurationError
from src.transforms.regex_registry import RegexRegistry
from src.transforms.validation import TabularDataValidator, validate_data


def _plan(rules, *, failure_policy="fail_stage", issue_limit=100):
    return {
        "contract_version": 1,
        "failure_policy": failure_policy,
        "issue_limit": issue_limit,
        "rules": rules,
    }


def _regex_registry():
    return RegexRegistry.from_dicts(
        [{"id": "sku", "pattern": r"(?P<sku>[A-Z]{2}-\d{3})", "flags": ["IGNORECASE"]}]
    )


def test_required_rule_rejects_null_and_blank_text():
    result = validate_data(
        pd.DataFrame({"name": ["Acme", None, "  "]}),
        _plan([{"id": "name-required", "type": "required", "field": "name"}]),
    )
    assert result.error_count == 2
    assert result.invalid_rows == 2
    assert [issue.row_index for issue in result.issues] == [1, 2]
    assert {issue.code for issue in result.issues} == {"required_missing"}


@pytest.mark.parametrize(
    ("expected", "values", "failing_positions"),
    [
        ("string", ["a", 1, None], [1]),
        ("int", [1, 1.0, True, None], [1, 2]),
        ("float", [1.5, 1, None], []),
        ("number", [1, 1.5, True, None], [2]),
        ("bool", [True, False, 1, None], [2]),
        ("datetime", [datetime(2026, 1, 1), "2026-01-01", None], [1]),
    ],
)
def test_type_rule_boundaries(expected, values, failing_positions):
    result = validate_data(
        pd.DataFrame({"value": values}),
        _plan([{"id": "type", "type": "type", "field": "value", "value": expected}]),
    )
    assert [issue.row_index for issue in result.issues] == failing_positions
    assert all(issue.code == "type_mismatch" for issue in result.issues)


def test_regex_rule_uses_named_registry_and_skips_null():
    result = validate_data(
        pd.DataFrame({"sku": ["AB-123", "invalid", None]}),
        _plan([{"id": "sku-format", "type": "regex", "field": "sku", "pattern_id": "sku"}]),
        regex_registry=_regex_registry(),
    )
    assert result.error_count == 1
    assert result.issues[0].row_index == 1
    assert result.issues[0].code == "regex_mismatch"


def test_min_and_max_rules():
    result = validate_data(
        pd.DataFrame({"price": [-1, 10, 101, None]}),
        _plan(
            [
                {"id": "minimum", "type": "min", "field": "price", "value": 0},
                {"id": "maximum", "type": "max", "field": "price", "value": 100},
            ]
        ),
    )
    assert [(issue.rule_id, issue.row_index, issue.code) for issue in result.issues] == [
        ("minimum", 0, "min_violation"),
        ("maximum", 2, "max_violation"),
    ]


def test_allowed_values_rule():
    result = validate_data(
        pd.DataFrame({"currency": ["KES", "EUR", None]}),
        _plan([{"id": "currency", "type": "allowed_values", "field": "currency", "values": ["KES", "USD"]}]),
    )
    assert result.error_count == 1
    assert result.issues[0].code == "value_not_allowed"


def test_unique_rule_marks_every_duplicate_and_skips_null():
    result = validate_data(
        pd.DataFrame({"external_id": ["A", "B", "A", None, "B"]}),
        _plan([{"id": "unique-id", "type": "unique", "field": "external_id"}]),
    )
    assert [issue.row_index for issue in result.issues] == [0, 1, 2, 4]
    assert result.error_count == 4
    assert result.invalid_rows == 4


def test_warning_failures_do_not_make_result_invalid():
    result = validate_data(
        pd.DataFrame({"currency": ["EUR"]}),
        _plan([{"id": "currency", "type": "allowed_values", "field": "currency", "values": ["KES"], "severity": "warning"}]),
    )
    assert result.valid is True
    assert result.error_count == 0
    assert result.warning_count == 1
    assert result.valid_rows == 1


def test_issue_order_is_rule_order_then_row_position():
    frame = pd.DataFrame({"name": [None, None], "price": [-1, -2]}, index=[20, 10])
    plan = _plan(
        [
            {"id": "required", "type": "required", "field": "name"},
            {"id": "minimum", "type": "min", "field": "price", "value": 0},
        ]
    )
    first = validate_data(frame, plan).to_dict()
    second = validate_data(frame, plan).to_dict()
    assert first == second
    assert [(issue["rule_id"], issue["row_index"]) for issue in first["issues"]] == [
        ("required", 0), ("required", 1), ("minimum", 0), ("minimum", 1)
    ]


def test_issue_limit_retains_complete_counts():
    result = validate_data(
        pd.DataFrame({"name": [None] * 8}),
        _plan([{"id": "required", "type": "required", "field": "name"}], issue_limit=3),
    )
    payload = result.to_dict()
    assert result.error_count == 8
    assert result.invalid_rows == 8
    assert len(result.issues) == 3
    assert result.truncated is True
    assert payload["total_issue_count"] == 8
    assert payload["detail_count"] == 3


def test_missing_column_fails_before_row_evaluation():
    with pytest.raises(ConfigurationError) as caught:
        validate_data(
            pd.DataFrame({"present": ["private-value"]}),
            _plan([{"id": "missing", "type": "required", "field": "absent"}]),
        )
    assert caught.value.code == "missing_column"
    assert caught.value.path == "$.rules[0].field"
    assert "private-value" not in str(caught.value)


def test_invalid_type_config_is_rejected():
    with pytest.raises(ConfigurationError) as caught:
        validate_data(
            pd.DataFrame({"value": [1]}),
            _plan([{"id": "type", "type": "type", "field": "value", "value": "decimal128"}]),
        )
    assert caught.value.path == "$.rules[0].value"


def test_invalid_numeric_threshold_is_rejected_before_rows():
    with pytest.raises(ConfigurationError) as caught:
        validate_data(
            pd.DataFrame({"value": [1, 2]}),
            _plan([{"id": "minimum", "type": "min", "field": "value", "value": "zero"}]),
        )
    assert caught.value.path == "$.rules[0].value"


def test_unknown_regex_definition_is_rejected():
    with pytest.raises(ConfigurationError) as caught:
        validate_data(
            pd.DataFrame({"sku": ["AB-123"]}),
            _plan([{"id": "regex", "type": "regex", "field": "sku", "pattern_id": "missing"}]),
        )
    assert caught.value.code == "unknown_pattern"


def test_empty_dataframe_is_valid_when_schema_exists():
    result = validate_data(
        pd.DataFrame({"name": pd.Series(dtype="object")}),
        _plan([{"id": "required", "type": "required", "field": "name"}]),
    )
    assert result.valid is True
    assert result.total_rows == 0
    assert result.to_dict()["total_issue_count"] == 0


def test_validation_does_not_mutate_input():
    source = pd.DataFrame({"value": [1, -1]})
    original = source.copy(deep=True)
    validate_data(source, _plan([{"id": "minimum", "type": "min", "field": "value", "value": 0}]))
    pdt.assert_frame_equal(source, original)


def test_results_are_json_compatible_and_privacy_safe():
    secret = "customer-private-value"
    result = validate_data(
        pd.DataFrame({"customer": [secret]}),
        _plan([{"id": "format", "type": "regex", "field": "customer", "pattern_id": "sku"}]),
        regex_registry=_regex_registry(),
    )
    serialized = json.dumps(result.to_dict())
    assert secret not in serialized
    assert "Field does not match the required pattern." in serialized


def test_validation_plan_values_must_be_array():
    with pytest.raises(ConfigurationError) as caught:
        validate_data(
            pd.DataFrame({"currency": ["KES"]}),
            _plan([{"id": "allowed", "type": "allowed_values", "field": "currency", "values": "KES"}]),
        )
    assert caught.value.path == "$.rules[0].values"
