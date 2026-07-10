import pandas as pd
import pandas.testing as pdt
import pytest

from src.transforms.errors import ConfigurationError
from src.transforms.executor import TransformationExecutor
from src.transforms.regex_registry import RegexRegistry
from src.transforms.registry import OperationRegistry
from src.workflow_runtime.operations.tabular_artifact_adapter import (
    UnsupportedTabularArtifactError,
    to_dataframe,
)


def test_executor_applies_operations_in_declared_order():
    source = pd.DataFrame({"Raw Name": ["  ACME  ", " Beta "]})
    plan = {
        "contract_version": 1,
        "operations": [
            {"id": "rename", "type": "rename", "options": {"columns": {"Raw Name": "name"}}},
            {
                "id": "map",
                "type": "field_map",
                "options": {"mappings": [{"source": "name", "target": "canonical", "transforms": ["trim", "lower"]}]},
            },
            {"id": "source", "type": "add_constant", "options": {"column": "source", "value": "fixture"}},
        ],
    }
    result = TransformationExecutor().execute(source, plan)
    assert result.columns.tolist() == ["name", "canonical", "source"]
    assert result["canonical"].tolist() == ["acme", "beta"]


def test_executor_repeated_output_is_deterministic():
    source = pd.DataFrame({"sku": ["A", "A", "B"], "price": [2, 2, 1]})
    plan = {
        "contract_version": 1,
        "operations": [
            {"id": "dedupe", "type": "deduplicate", "options": {"subset": ["sku", "price"]}},
            {"id": "constant", "type": "add_constant", "options": {"column": "currency", "value": "KES"}},
        ],
    }
    executor = TransformationExecutor()
    pdt.assert_frame_equal(executor.execute(source, plan), executor.execute(source, plan))


def test_versioned_normalize_does_not_inject_wall_clock_timestamp():
    source = pd.DataFrame({"name": ["Omo 1kg"]})
    plan = {
        "contract_version": 1,
        "operations": [{"id": "normalize", "type": "normalize", "options": {"source": "fixture"}}],
    }
    executor = TransformationExecutor()
    first = executor.execute(source, plan)
    second = executor.execute(source, plan)
    pdt.assert_frame_equal(first, second)
    assert first["timestamp"].isna().all()


def test_executor_copies_input_dataframe():
    source = pd.DataFrame({"old": [1, 2]})
    original = source.copy(deep=True)
    result = TransformationExecutor().execute(
        source,
        {"contract_version": 1, "operations": [{"id": "rename", "type": "rename", "options": {"columns": {"old": "new"}}}]},
    )
    pdt.assert_frame_equal(source, original)
    assert result is not source


def test_complete_preflight_fails_before_any_operation_is_applied():
    source = pd.DataFrame({"old": [1]})
    original = source.copy(deep=True)
    plan = {
        "contract_version": 1,
        "operations": [
            {"id": "rename", "type": "rename", "options": {"columns": {"old": "new"}}},
            {"id": "bad", "type": "drop_nulls", "options": {"subset": ["missing"]}},
        ],
    }
    with pytest.raises(ConfigurationError) as caught:
        TransformationExecutor().execute(source, plan)
    assert caught.value.code == "missing_column"
    assert caught.value.path == "$.operations[1].options.subset[0]"
    pdt.assert_frame_equal(source, original)


def test_executor_uses_named_regex_registry():
    registry = RegexRegistry.from_dicts(
        [{"id": "sku", "pattern": r"(?P<sku>[A-Z]{2}-\d{3})", "flags": ["IGNORECASE"]}]
    )
    plan = {
        "contract_version": 1,
        "operations": [
            {
                "id": "extract",
                "type": "regex_map",
                "options": {"source": "description", "target": "sku", "pattern_id": "sku", "group": "sku", "on_no_match": "null"},
            }
        ],
    }
    result = TransformationExecutor(regex_registry=registry).execute(
        pd.DataFrame({"description": ["Product AB-123", "unknown"]}), plan
    )
    assert result["sku"].iloc[0] == "AB-123"
    assert pd.isna(result["sku"].iloc[1])


def test_executor_rejects_operation_missing_from_injected_allowlist():
    plan = {
        "contract_version": 1,
        "operations": [{"id": "constant", "type": "add_constant", "options": {"column": "x", "value": 1}}],
    }
    with pytest.raises(ConfigurationError) as caught:
        TransformationExecutor(operation_registry=OperationRegistry(["rename"])).execute(pd.DataFrame(), plan)
    assert caught.value.code == "unknown_operation"


def test_new_plan_does_not_accept_legacy_filter_operation():
    with pytest.raises(ConfigurationError) as caught:
        TransformationExecutor().execute(
            pd.DataFrame({"price": [1]}),
            {"contract_version": 1, "operations": [{"id": "filter", "type": "filter", "options": {"condition": "price > 0"}}]},
        )
    assert caught.value.code == "invalid_value"


@pytest.mark.parametrize(
    "operation",
    [
        {"id": "coerce", "type": "type_coercion", "options": {"columns": {"value": ["float"]}}},
        {"id": "dedupe", "type": "deduplicate", "options": {"keep": ["first"]}},
        {
            "id": "regex", "type": "regex_map",
            "options": {"source": "value", "target": "match", "pattern_id": "missing", "group": "value", "on_no_match": ["null"]},
        },
    ],
)
def test_malformed_operation_options_raise_configuration_error(operation):
    with pytest.raises(ConfigurationError):
        TransformationExecutor().execute(
            pd.DataFrame({"value": ["1"]}),
            {"contract_version": 1, "operations": [operation]},
        )


def test_dataframe_adapter_copies_dataframe():
    source = pd.DataFrame({"value": [1]})
    adapted = to_dataframe(source)
    adapted.loc[0, "value"] = 2
    assert source.loc[0, "value"] == 1


def test_list_of_dicts_adapter_isolated_from_source():
    source = [{"value": 1}, {"value": 2}]
    adapted = to_dataframe(source)
    adapted.loc[0, "value"] = 99
    assert source == [{"value": 1}, {"value": 2}]


@pytest.mark.parametrize("artifact", [None, {}, [1, 2], "rows"])
def test_adapter_rejects_unsupported_artifact(artifact):
    with pytest.raises(UnsupportedTabularArtifactError):
        to_dataframe(artifact)
