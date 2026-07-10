"""End-to-end verification for v0.6 deterministic tabular workflow stages."""

import json

import pandas as pd
import pandas.testing as pdt

import src.workflow_runtime.operations  # noqa: F401 - populate stage registry
from src.core.execution.status import ExecutionStatus
from src.transforms.pipeline import TransformationPipeline
from src.workflow_runtime.contracts.workflow_definition import StageDefinition, WorkflowDefinition
from src.workflow_runtime.dsl.workflow_validator import WorkflowValidator
from src.workflow_runtime.operations.base import STAGE_REGISTRY
from src.workflow_runtime.operations.stage_catalog import IMPLEMENTED_STAGE_TYPES
from src.workflow_runtime.runtime.workflow_runner import WorkflowRunner


def _workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="v06-integration",
        name="v0.6 deterministic integration",
        version="1.0.0",
        workspace_id="test-workspace",
        enabled=True,
        stages=[
            StageDefinition(
                name="transform",
                type="transform",
                config={
                    "plan": {
                        "contract_version": 1,
                        "operations": [
                            {
                                "id": "canonical-fields",
                                "type": "field_map",
                                "options": {
                                    "mappings": [
                                        {"source": "Supplier Name", "target": "supplier", "required": True, "transforms": ["trim"]},
                                        {"source": "Raw Price", "target": "price", "required": True, "coerce": "float"},
                                        {"source": "Currency", "target": "currency", "required": True, "transforms": ["trim", "upper"]},
                                        {"source": "Product", "target": "product", "required": True, "transforms": ["trim"]},
                                    ]
                                },
                            }
                        ],
                    }
                },
            ),
            StageDefinition(
                name="validate",
                type="validate_data",
                depends_on=["transform"],
                config={
                    "plan": {
                        "contract_version": 1,
                        "failure_policy": "report_only",
                        "rules": [
                            {"id": "supplier-required", "type": "required", "field": "supplier"},
                            {"id": "price-type", "type": "type", "field": "price", "value": "float"},
                            {"id": "price-positive", "type": "min", "field": "price", "value": 0},
                            {
                                "id": "currency-known",
                                "type": "allowed_values",
                                "field": "currency",
                                "values": ["KES", "USD"],
                                "severity": "warning",
                            },
                        ],
                    }
                },
            ),
            StageDefinition(
                name="sort",
                type="sort",
                depends_on=["validate"],
                config={
                    "plan": {
                        "contract_version": 1,
                        "stable": True,
                        "keys": [
                            {"field": "supplier", "direction": "asc", "nulls": "last"},
                            {"field": "price", "direction": "asc", "nulls": "last"},
                        ],
                    }
                },
            ),
            StageDefinition(
                name="aggregate",
                type="aggregate",
                depends_on=["sort"],
                config={
                    "plan": {
                        "contract_version": 1,
                        "group_by": ["supplier"],
                        "aggregations": [
                            {"function": "count", "output": "row_count"},
                            {"field": "price", "function": "sum", "output": "total_price"},
                            {"field": "price", "function": "avg", "output": "average_price"},
                        ],
                        "drop_null_groups": False,
                    }
                },
            ),
        ],
    )


def _source() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Supplier Name": [" Beta ", " Acme ", "Acme"],
            "Raw Price": ["20", "30", "10"],
            "Currency": [" eur ", "kes", " KES "],
            "Product": ["Private Item B", "Private Item C", "Private Item A"],
            "sensitive_note": ["customer-secret-1", "customer-secret-2", "customer-secret-3"],
        }
    )


def test_transform_validate_sort_aggregate_workflow_is_deterministic_and_private():
    source = _source()
    original = source.copy(deep=True)
    definition = _workflow()

    assert WorkflowValidator.validate(definition).all_passed is True
    first = WorkflowRunner().run(definition, initial_artifact=source)
    second = WorkflowRunner().run(definition, initial_artifact=source)

    assert first.overall_status == ExecutionStatus.SUCCESS.value
    assert [result.stage_name for result in first.stage_results] == [
        "transform", "validate_data", "sort", "aggregate"
    ]

    transformed = first.stage_results[0].output_artifact
    assert transformed[["supplier", "price", "currency", "product"]].to_dict("records") == [
        {"supplier": "Beta", "price": 20.0, "currency": "EUR", "product": "Private Item B"},
        {"supplier": "Acme", "price": 30.0, "currency": "KES", "product": "Private Item C"},
        {"supplier": "Acme", "price": 10.0, "currency": "KES", "product": "Private Item A"},
    ]

    validation_metadata = first.stage_results[1].metadata["validation"]
    assert validation_metadata["valid"] is True
    assert validation_metadata["error_count"] == 0
    assert validation_metadata["warning_count"] == 1
    assert validation_metadata["issues"][0]["code"] == "value_not_allowed"

    sorted_output = first.stage_results[2].output_artifact
    assert list(zip(sorted_output["supplier"], sorted_output["price"])) == [
        ("Acme", 10.0), ("Acme", 30.0), ("Beta", 20.0)
    ]

    aggregated = first.stage_results[3].output_artifact
    expected = pd.DataFrame(
        {
            "supplier": ["Acme", "Beta"],
            "row_count": [2, 1],
            "total_price": [40.0, 20.0],
            "average_price": [20.0, 20.0],
        }
    )
    pdt.assert_frame_equal(aggregated.reset_index(drop=True), expected)
    pdt.assert_frame_equal(
        second.stage_results[3].output_artifact.reset_index(drop=True), expected
    )

    metadata_json = json.dumps([result.metadata for result in first.stage_results])
    for sensitive_value in source["sensitive_note"]:
        assert sensitive_value not in metadata_json
    assert "Private Item" not in metadata_json
    pdt.assert_frame_equal(source, original)


def test_legacy_transformation_rules_remain_compatible():
    source = pd.DataFrame({"old_name": ["A", "A", None], "price": ["10", "10", "30"]})
    original = source.copy(deep=True)
    result = TransformationPipeline(source).apply(
        [
            {"type": "rename", "columns": {"old_name": "name"}},
            {"type": "drop_nulls", "subset": ["name"]},
            {"type": "filter", "condition": "price == '10'"},
            {"type": "type_coercion", "columns": {"price": "float"}},
            {"type": "deduplicate", "subset": ["name", "price"]},
            {"type": "add_column", "column": "source", "value": "legacy"},
        ]
    )
    assert result.to_dict("records") == [{"name": "A", "price": 10.0, "source": "legacy"}]
    pdt.assert_frame_equal(source, original)


def test_stage_catalog_and_validator_are_consistent():
    assert frozenset(STAGE_REGISTRY) == IMPLEMENTED_STAGE_TYPES
    for stage_type in sorted(IMPLEMENTED_STAGE_TYPES):
        definition = WorkflowDefinition(
            workflow_id=f"catalog-{stage_type}",
            name="Catalog consistency",
            version="1.0.0",
            workspace_id="test-workspace",
            enabled=True,
            stages=[StageDefinition(name="stage", type=stage_type)],
        )
        assert WorkflowValidator.validate(definition).all_passed is True

