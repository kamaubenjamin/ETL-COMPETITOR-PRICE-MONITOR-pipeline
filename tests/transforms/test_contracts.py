import json

import pytest

from src.transforms.contracts import (
    AggregationPlan,
    DataValidationResult,
    FieldMapping,
    RegexDefinition,
    SortPlan,
    TransformationPlan,
    ValidationIssue,
    ValidationPlan,
    ValidationResult,
)
from src.transforms.errors import ConfigurationError


def test_transformation_plan_round_trips_as_json_compatible_dict():
    plan = TransformationPlan.from_dict(
        {
            "contract_version": 1,
            "operations": [
                {"id": "map", "type": "field_map", "options": {"mappings": []}},
                {"id": "dedupe", "type": "deduplicate", "options": {"subset": ["sku"]}},
            ],
        }
    )
    payload = plan.to_dict()
    assert payload["operations"][0]["id"] == "map"
    assert json.loads(json.dumps(payload)) == payload


def test_transformation_plan_rejects_unsupported_version():
    with pytest.raises(ConfigurationError) as caught:
        TransformationPlan.from_dict({"contract_version": 2, "operations": []})
    assert caught.value.code == "unsupported_version"
    assert caught.value.path == "$.contract_version"


def test_operation_error_is_path_aware():
    with pytest.raises(ConfigurationError) as caught:
        TransformationPlan.from_dict(
            {"contract_version": 1, "operations": [{"id": "bad", "type": "execute_python"}]}
        )
    assert caught.value.code == "invalid_value"
    assert caught.value.path == "$.operations[0].type"
    assert caught.value.to_dict()["message"].startswith("Unsupported value")


def test_transformation_plan_rejects_duplicate_operation_ids():
    with pytest.raises(ConfigurationError) as caught:
        TransformationPlan.from_dict(
            {
                "contract_version": 1,
                "operations": [
                    {"id": "same", "type": "rename"},
                    {"id": "same", "type": "drop_nulls"},
                ],
            }
        )
    assert caught.value.code == "duplicate_id"
    assert caught.value.path == "$.operations[1].id"


def test_contracts_reject_unknown_fields():
    with pytest.raises(ConfigurationError) as caught:
        TransformationPlan.from_dict({"contract_version": 1, "operations": [], "callback": "x"})
    assert caught.value.code == "unknown_field"
    assert caught.value.path == "$.callback"


def test_operation_options_must_be_json_compatible():
    with pytest.raises(ConfigurationError, match="JSON-compatible"):
        TransformationPlan.from_dict(
            {"contract_version": 1, "operations": [{"id": "x", "type": "rename", "options": {"bad": object()}}]}
        )


def test_field_mapping_contract():
    mapping = FieldMapping.from_dict(
        {
            "source": "Supplier Price",
            "target": "price",
            "required": True,
            "coerce": "float",
            "transforms": ["trim"],
            "on_error": "null",
        }
    )
    assert mapping.source == "Supplier Price"
    assert mapping.to_dict()["transforms"] == ["trim"]
    assert json.loads(json.dumps(mapping.to_dict())) == mapping.to_dict()


def test_field_mapping_rejects_arbitrary_transform():
    with pytest.raises(ConfigurationError) as caught:
        FieldMapping.from_dict({"source": "a", "target": "b", "transforms": ["eval"]})
    assert caught.value.path == "$.transforms[0]"


def test_regex_definition_requires_python_named_capture_group():
    definition = RegexDefinition.from_dict(
        {"id": "sku_v1", "pattern": r"(?P<sku>[A-Z]+-\d+)", "flags": ["IGNORECASE"]}
    )
    assert definition.group_names == ("sku",)
    assert json.loads(json.dumps(definition.to_dict())) == definition.to_dict()


@pytest.mark.parametrize("pattern", [r"(?<sku>[A-Z]+)", r"[unterminated", r"[A-Z]+"])
def test_regex_definition_rejects_invalid_or_unnamed_patterns(pattern):
    with pytest.raises(ConfigurationError) as caught:
        RegexDefinition.from_dict({"id": "bad", "pattern": pattern})
    assert caught.value.code == "invalid_regex"
    assert caught.value.path == "$.pattern"


def test_validation_plan_and_result_contracts():
    plan = ValidationPlan.from_dict(
        {
            "contract_version": 1,
            "failure_policy": "report_only",
            "issue_limit": 25,
            "rules": [
                {"id": "required-price", "type": "required", "field": "price"},
                {"id": "min-price", "type": "min", "field": "price", "value": 0},
                {"id": "currency", "type": "allowed_values", "field": "currency", "values": ["KES", "USD"], "severity": "warning"},
            ],
        }
    )
    issue = ValidationIssue(row_index=3, rule_id="required-price", field="price", severity="error", message="Required field is missing.")
    result = DataValidationResult(
        valid=False, total_rows=4, valid_rows=3, invalid_rows=1,
        error_count=1, warning_count=0, issues=(issue,), truncated=False,
    )
    assert plan.to_dict()["failure_policy"] == "report_only"
    assert result.to_dict()["issues"][0]["row_index"] == 3
    json.dumps(plan.to_dict())
    json.dumps(result.to_dict())
    assert isinstance(result, ValidationResult)


def test_validation_plan_rejects_duplicate_rules_with_path():
    with pytest.raises(ConfigurationError) as caught:
        ValidationPlan.from_dict(
            {
                "contract_version": 1,
                "rules": [
                    {"id": "same", "type": "required", "field": "a"},
                    {"id": "same", "type": "required", "field": "b"},
                ],
            }
        )
    assert caught.value.path == "$.rules[1].id"


def test_sort_plan_contract():
    plan = SortPlan.from_dict(
        {
            "contract_version": 1,
            "keys": [
                {"field": "supplier", "direction": "asc", "nulls": "last"},
                {"field": "price", "direction": "desc", "nulls": "first"},
            ],
            "stable": True,
        }
    )
    assert plan.to_dict()["keys"][1]["direction"] == "desc"
    json.dumps(plan.to_dict())


def test_sort_plan_requires_a_key():
    with pytest.raises(ConfigurationError) as caught:
        SortPlan.from_dict({"contract_version": 1, "keys": []})
    assert caught.value.path == "$.keys"


def test_aggregation_plan_contract():
    plan = AggregationPlan.from_dict(
        {
            "contract_version": 1,
            "group_by": ["supplier"],
            "aggregations": [
                {"field": "price", "function": "avg", "output": "avg_price"},
                {"field": "product", "function": "count", "output": "product_count"},
            ],
            "drop_null_groups": False,
        }
    )
    assert plan.to_dict()["aggregations"][0]["function"] == "avg"
    json.dumps(plan.to_dict())


def test_aggregation_plan_rejects_duplicate_outputs():
    with pytest.raises(ConfigurationError) as caught:
        AggregationPlan.from_dict(
            {
                "contract_version": 1,
                "aggregations": [
                    {"field": "price", "function": "min", "output": "price"},
                    {"field": "price", "function": "max", "output": "price"},
                ],
            }
        )
    assert caught.value.code == "duplicate_output"
    assert caught.value.path == "$.aggregations[1].output"
