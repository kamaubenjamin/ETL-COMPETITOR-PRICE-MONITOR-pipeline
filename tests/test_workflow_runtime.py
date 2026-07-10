"""Comprehensive tests for Workflow Runtime v1.

Covers:
  - Contracts (serialization, immutability)
  - DSL parsing (JSON → typed definitions)
  - DAG builder (topological sort, cycle detection)
  - Workflow validator (field presence, stage types, dependencies)
  - Stage operations (all 7 types)
  - Workflow runner (sequential execution, fail-fast, debug artifacts)
  - Workspace registry (file-based loading)
"""

import json
import pandas as pd
import pytest

from src.core.execution.status import ExecutionStatus
from src.document_engine.contracts.document import Document, DocumentIngestionResult, DocumentSource
from src.document_engine.orchestration.ingestion_pipeline import IngestionPipelineResult
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_definition import (
    StageDefinition,
    WorkflowDefinition,
)
from src.workflow_runtime.contracts.workflow_result import StageResult, WorkflowResult
from src.workflow_runtime.dag.builder import DAGBuilder
from src.workflow_runtime.dsl.workflow_parser import WorkflowParser
from src.workflow_runtime.dsl.workflow_validator import WorkflowValidator
from src.workflow_runtime.operations.base import STAGE_REGISTRY
from src.workflow_runtime.operations.ingest_stage import IngestStage
from src.workflow_runtime.operations.transform_stage import TransformStage
from src.workflow_runtime.operations.validation_stage import ValidationStage
from src.workflow_runtime.operations.sort_stage import SortStage
from src.workflow_runtime.operations.aggregation_stage import AggregationStage
from src.workflow_runtime.operations.filter_stage import FilterStage
from src.workflow_runtime.operations.fuzzy_match_stage import FuzzyMatchStage
from src.workflow_runtime.operations.compare_stage import CompareStage
from src.workflow_runtime.operations.alert_stage import AlertStage
from src.workflow_runtime.operations.entity_extract_stage import EntityExtractStage
from src.workflow_runtime.operations.matching_stage import MatchingStage
from src.workflow_runtime.operations.report_stage import ReportStage
from src.workflow_runtime.runtime.workflow_runner import WorkflowRunner
from src.workflow_runtime.workspace.workspace_registry import WorkspaceRegistry


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def valid_workflow_dict():
    return {
        "workflow_id": "test_workflow",
        "name": "Test Workflow",
        "version": "1.0.0",
        "workspace_id": "test_workspace",
        "enabled": True,
        "description": "A test workflow",
        "stages": [
            {
                "name": "transform_1",
                "type": "transform",
                "depends_on": [],
                "config": {"rules": []},
            },
            {
                "name": "filter_1",
                "type": "filter",
                "depends_on": ["transform_1"],
                "config": {"category": "test", "keywords": []},
            },
            {
                "name": "fuzzy_match_1",
                "type": "fuzzy_match",
                "depends_on": ["filter_1"],
                "config": {"match_threshold": 78},
            },
            {
                "name": "compare_1",
                "type": "compare",
                "depends_on": ["fuzzy_match_1"],
                "config": {},
            },
            {
                "name": "alert_1",
                "type": "alert",
                "depends_on": ["compare_1"],
                "config": {"price_drop_percentage": 5},
            },
            {
                "name": "report_1",
                "type": "report",
                "depends_on": ["alert_1"],
                "config": {"export_csv": True},
            },
        ],
        "metadata": {},
    }


@pytest.fixture
def valid_definition(valid_workflow_dict):
    return WorkflowParser.parse_dict(valid_workflow_dict)


# ── Contract Tests ────────────────────────────────────────────────────


class TestStageDefinition:
    def test_create_minimal(self):
        stage = StageDefinition(name="test", type="transform")
        assert stage.name == "test"
        assert stage.type == "transform"
        assert stage.depends_on == []
        assert stage.config == {}

    def test_frozen_immutable(self):
        stage = StageDefinition(name="test", type="transform")
        with pytest.raises(AttributeError):
            stage.name = "changed"  # type: ignore[misc]

    def test_to_dict(self):
        stage = StageDefinition(
            name="ingest",
            type="document_ingest",
            depends_on=[],
            config={"source_name": "test"},
        )
        d = stage.to_dict()
        assert d["name"] == "ingest"
        assert d["type"] == "document_ingest"

    def test_to_json(self):
        stage = StageDefinition(name="test", type="transform")
        j = stage.to_json()
        parsed = json.loads(j)
        assert parsed["name"] == "test"


class TestWorkflowDefinition:
    def test_create_minimal(self):
        wf = WorkflowDefinition(
            workflow_id="test", name="Test", version="1.0.0", workspace_id="ws", enabled=True
        )
        assert wf.workflow_id == "test"
        assert wf.stages == []

    def test_to_dict(self, valid_definition):
        d = valid_definition.to_dict()
        assert d["workflow_id"] == "test_workflow"
        assert len(d["stages"]) == 6

    def test_to_json(self, valid_definition):
        j = valid_definition.to_json()
        parsed = json.loads(j)
        assert parsed["workflow_id"] == "test_workflow"
        assert parsed["version"] == "1.0.0"


class TestStageResult:
    def test_create_success(self):
        result = StageResult(
            stage_name="ingest",
            status=ExecutionStatus.SUCCESS.value,
            output_artifact={"key": "value"},
            duration_ms=100,
        )
        assert result.stage_name == "ingest"
        assert result.status == "success"
        assert result.error is None

    def test_create_failure(self):
        result = StageResult(
            stage_name="ingest",
            status=ExecutionStatus.FAILED.value,
            error="Something broke",
            duration_ms=50,
        )
        assert result.status == "failed"
        assert "broke" in result.error

    def test_to_dict(self):
        result = StageResult(stage_name="test", status=ExecutionStatus.SUCCESS.value)
        d = result.to_dict()
        assert d["stage_name"] == "test"
        assert d["has_output"] is False


class TestWorkflowResult:
    def test_create(self):
        result = WorkflowResult(
            workflow_id="test",
            pipeline_run_id="run-1",
            workspace_id="ws",
            overall_status=ExecutionStatus.SUCCESS.value,
        )
        assert result.stage_results == []

    def test_to_dict(self):
        result = WorkflowResult(
            workflow_id="test",
            pipeline_run_id="run-1",
            workspace_id="ws",
            overall_status=ExecutionStatus.SUCCESS.value,
        )
        d = result.to_dict()
        assert d["stage_count"] == 0


class TestExecutionContext:
    def test_create(self):
        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws",
            workflow_id="wf-1",
            started_at="2025-01-01T00:00:00",
        )
        assert ctx.pipeline_run_id == "run-1"


# ── DSL Parser Tests ──────────────────────────────────────────────────


class TestWorkflowParser:
    def test_parse_dict(self, valid_workflow_dict):
        wf = WorkflowParser.parse_dict(valid_workflow_dict)
        assert isinstance(wf, WorkflowDefinition)
        assert len(wf.stages) == 6
        assert wf.stages[0].type == "transform"
        assert wf.stages[1].depends_on == ["transform_1"]

    def test_parse_json(self, valid_workflow_dict):
        json_str = json.dumps(valid_workflow_dict)
        wf = WorkflowParser.parse_json(json_str)
        assert wf.workflow_id == "test_workflow"

    def test_parse_file(self, tmp_path, valid_workflow_dict):
        path = tmp_path / "workflow.json"
        path.write_text(json.dumps(valid_workflow_dict), encoding="utf-8")
        wf = WorkflowParser.parse_file(str(path))
        assert wf.workflow_id == "test_workflow"

    def test_parse_minimal(self):
        data = {"workflow_id": "minimal", "stages": []}
        wf = WorkflowParser.parse_dict(data)
        assert wf.workflow_id == "minimal"
        assert wf.version == "1.0.0"


# ── DAG Builder Tests ─────────────────────────────────────────────────


class TestDAGBuilder:
    def test_topological_sort_linear(self, valid_definition):
        stages = DAGBuilder.build(valid_definition)
        names = [s.name for s in stages]
        assert names == [
            "transform_1",
            "filter_1",
            "fuzzy_match_1",
            "compare_1",
            "alert_1",
            "report_1",
        ]

    def test_topological_sort_with_fork(self):
        wf = WorkflowDefinition(
            workflow_id="fork_test",
            name="Fork",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[
                StageDefinition(name="a", type="transform", depends_on=[]),
                StageDefinition(name="b", type="transform", depends_on=["a"]),
                StageDefinition(name="c", type="transform", depends_on=["a"]),
                StageDefinition(name="d", type="transform", depends_on=["b", "c"]),
            ],
        )
        stages = DAGBuilder.build(wf)
        names = [s.name for s in stages]
        assert names[0] == "a"
        assert names[3] == "d"
        assert set(names[1:3]) == {"b", "c"}

    def test_cycle_detection(self):
        wf = WorkflowDefinition(
            workflow_id="cycle_test",
            name="Cycle",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[
                StageDefinition(name="a", type="transform", depends_on=["b"]),
                StageDefinition(name="b", type="transform", depends_on=["a"]),
            ],
        )
        with pytest.raises(ValueError, match="DAG cycle detected"):
            DAGBuilder.build(wf)

    def test_empty_stages(self):
        wf = WorkflowDefinition(
            workflow_id="empty",
            name="Empty",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[],
        )
        stages = DAGBuilder.build(wf)
        assert stages == []


# ── Workflow Validator Tests ──────────────────────────────────────────


class TestWorkflowValidator:
    def test_validate_valid(self, valid_definition):
        result = WorkflowValidator.validate(valid_definition)
        assert result.all_passed is True

    def test_validate_missing_workflow_id(self):
        wf = WorkflowDefinition(
            workflow_id="", name="Test", version="1.0.0", workspace_id="ws", enabled=True, stages=[]
        )
        result = WorkflowValidator.validate(wf)
        assert result.all_passed is False

    def test_validate_no_stages(self):
        wf = WorkflowDefinition(
            workflow_id="test", name="Test", version="1.0.0", workspace_id="ws", enabled=True, stages=[]
        )
        result = WorkflowValidator.validate(wf)
        assert result.all_passed is False

    def test_validate_invalid_stage_type(self):
        wf = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[StageDefinition(name="bad", type="nonexistent")],
        )
        result = WorkflowValidator.validate(wf)
        assert result.all_passed is False

    def test_validate_duplicate_stage_name(self):
        wf = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[
                StageDefinition(name="dup", type="transform"),
                StageDefinition(name="dup", type="transform"),
            ],
        )
        result = WorkflowValidator.validate(wf)
        assert result.all_passed is False

    def test_validate_broken_dependency(self):
        wf = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[
                StageDefinition(name="a", type="transform", depends_on=[]),
                StageDefinition(name="b", type="transform", depends_on=["nonexistent"]),
            ],
        )
        result = WorkflowValidator.validate(wf)
        assert result.all_passed is False

    def test_validate_or_raise(self, valid_definition):
        assert WorkflowValidator.validate_or_raise(valid_definition) is valid_definition

    def test_validate_or_raise_failure(self):
        wf = WorkflowDefinition(
            workflow_id="", name="Test", version="1.0.0", workspace_id="ws", enabled=True, stages=[]
        )
        with pytest.raises(ValueError, match="Workflow validation failed"):
            WorkflowValidator.validate_or_raise(wf)


# ── Stage Operation Tests ─────────────────────────────────────────────


class TestStageRegistry:
    def test_all_stages_registered(self):
        expected = {"document_ingest", "entity_extract", "transform", "filter", "fuzzy_match", "compare", "alert", "matching", "report", "validate_data", "sort", "aggregate"}
        assert set(STAGE_REGISTRY.keys()) == expected

    def test_stage_class_types(self):
        assert STAGE_REGISTRY["document_ingest"] is IngestStage
        assert STAGE_REGISTRY["entity_extract"] is EntityExtractStage
        assert STAGE_REGISTRY["transform"] is TransformStage
        assert STAGE_REGISTRY["filter"] is FilterStage
        assert STAGE_REGISTRY["fuzzy_match"] is FuzzyMatchStage
        assert STAGE_REGISTRY["compare"] is CompareStage
        assert STAGE_REGISTRY["alert"] is AlertStage
        assert STAGE_REGISTRY["matching"] is MatchingStage
        assert STAGE_REGISTRY["report"] is ReportStage
        assert STAGE_REGISTRY["validate_data"] is ValidationStage
        assert STAGE_REGISTRY["sort"] is SortStage
        assert STAGE_REGISTRY["aggregate"] is AggregationStage


class TestIngestStage:
    def test_config_access(self):
        stage = IngestStage(config={"source_name": "test", "source_type": "csv"})
        assert stage._config["source_name"] == "test"


class TestTransformStage:
    def test_run(self):
        stage = TransformStage(config={
            "plan": {
                "contract_version": 1,
                "operations": [
                    {"id": "rename", "type": "rename", "options": {"columns": {"raw": "name"}}},
                    {"id": "source", "type": "add_constant", "options": {"column": "source", "value": "workflow"}},
                ],
            }
        })
        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws",
            workflow_id="wf-1",
            started_at="2025-01-01T00:00:00",
        )
        source = pd.DataFrame({"raw": ["A", "B"]})
        result = stage.run(input_artifact=source, context=ctx)
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.stage_name == "transform"
        assert isinstance(result.output_artifact, pd.DataFrame)
        assert result.output_artifact.columns.tolist() == ["name", "source"]
        assert result.output_artifact is not source
        assert result.metadata == {
            "operation_ids": ["rename", "source"],
            "operation_count": 2,
            "rows_in": 2,
            "rows_out": 2,
        }

    def test_run_accepts_list_of_row_dicts(self):
        stage = TransformStage(config={"rules": [{"type": "add_column", "column": "source", "value": "legacy"}]})
        ctx = ExecutionContext(
            pipeline_run_id="run-list", workspace_id="ws", workflow_id="wf-list",
            started_at="2025-01-01T00:00:00",
        )
        source = [{"name": "A"}, {"name": "B"}]
        result = stage.run(source, ctx)
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.output_artifact["source"].tolist() == ["legacy", "legacy"]
        assert source == [{"name": "A"}, {"name": "B"}]

    def test_legacy_identity_passes_through_dict_artifact(self):
        stage = TransformStage(config={"operation": "identity"})
        ctx = ExecutionContext(
            pipeline_run_id="run-identity", workspace_id="ws", workflow_id="wf-identity",
            started_at="2025-01-01T00:00:00",
        )
        source = {"data": 1}

        result = stage.run(source, ctx)

        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.output_artifact is source
        assert result.metadata == {
            "operation_ids": ["identity"],
            "operation_count": 1,
        }

    def test_non_identity_operation_does_not_bypass_artifact_validation(self):
        stage = TransformStage(config={"operation": "rename"})
        ctx = ExecutionContext(
            pipeline_run_id="run-non-identity", workspace_id="ws", workflow_id="wf-non-identity",
            started_at="2025-01-01T00:00:00",
        )

        result = stage.run({"data": 1}, ctx)

        assert result.status == ExecutionStatus.FAILED.value
        assert result.output_artifact is None
        assert "DataFrame or list[dict]" in result.error

    def test_invalid_plan_returns_failed_result(self):
        stage = TransformStage(config={"plan": {"contract_version": 1, "operations": [{"id": "bad", "type": "execute_python"}]}})
        ctx = ExecutionContext(
            pipeline_run_id="run-invalid", workspace_id="ws", workflow_id="wf-invalid",
            started_at="2025-01-01T00:00:00",
        )
        result = stage.run(pd.DataFrame({"name": ["private"]}), ctx)
        assert result.status == ExecutionStatus.FAILED.value
        assert result.output_artifact is None
        assert "execute_python" in result.error
        assert "private" not in result.error

    @pytest.mark.parametrize("artifact", [None, {}, [1, 2]])
    def test_unsupported_input_returns_failed_result(self, artifact):
        stage = TransformStage(config={"rules": []})
        ctx = ExecutionContext(
            pipeline_run_id="run-unsupported", workspace_id="ws", workflow_id="wf-unsupported",
            started_at="2025-01-01T00:00:00",
        )
        result = stage.run(artifact, ctx)
        assert result.status == ExecutionStatus.FAILED.value
        assert result.output_artifact is None
        assert "DataFrame or list[dict]" in result.error

    def test_metadata_does_not_include_source_values_or_rules(self):
        stage = TransformStage(config={"rules": [{"type": "add_column", "column": "secret", "value": "sensitive"}]})
        ctx = ExecutionContext(
            pipeline_run_id="run-private", workspace_id="ws", workflow_id="wf-private",
            started_at="2025-01-01T00:00:00",
        )
        result = stage.run(pd.DataFrame({"customer": ["private-name"]}), ctx)
        serialized_metadata = json.dumps(result.metadata)
        assert result.status == ExecutionStatus.SUCCESS.value
        assert "private-name" not in serialized_metadata
        assert "sensitive" not in serialized_metadata
        assert "rules" not in result.metadata


class TestValidationStage:
    @staticmethod
    def _context():
        return ExecutionContext(
            pipeline_run_id="run-validation",
            workspace_id="ws",
            workflow_id="wf-validation",
            started_at="2025-01-01T00:00:00",
        )

    def test_fail_stage_returns_failed_result_for_errors(self):
        stage = ValidationStage(config={
            "plan": {
                "contract_version": 1,
                "failure_policy": "fail_stage",
                "rules": [{"id": "required", "type": "required", "field": "name"}],
            }
        })
        result = stage.run(pd.DataFrame({"name": ["Acme", None]}), self._context())
        assert result.status == ExecutionStatus.FAILED.value
        assert result.output_artifact is None
        assert result.metadata["validation"]["error_count"] == 1
        assert result.error == "Data validation failed with 1 error issue(s)."

    def test_warning_only_fail_stage_succeeds_with_unchanged_dataframe(self):
        source = pd.DataFrame({"currency": ["EUR"]})
        stage = ValidationStage(config={
            "plan": {
                "contract_version": 1,
                "failure_policy": "fail_stage",
                "rules": [
                    {"id": "currency", "type": "allowed_values", "field": "currency", "values": ["KES"], "severity": "warning"}
                ],
            }
        })
        result = stage.run(source, self._context())
        assert result.status == ExecutionStatus.SUCCESS.value
        assert isinstance(result.output_artifact, pd.DataFrame)
        assert result.output_artifact is not source
        pd.testing.assert_frame_equal(result.output_artifact, source)
        assert result.metadata["validation"]["warning_count"] == 1
        assert result.metadata["validation"]["valid"] is True

    def test_report_only_succeeds_with_errors_and_preserves_list_artifact(self):
        source = [{"name": None}, {"name": "Acme"}]
        stage = ValidationStage(config={
            "plan": {
                "contract_version": 1,
                "failure_policy": "report_only",
                "rules": [{"id": "required", "type": "required", "field": "name"}],
            }
        })
        result = stage.run(source, self._context())
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.output_artifact == source
        assert result.output_artifact is not source
        assert result.metadata["validation"]["error_count"] == 1
        assert source == [{"name": None}, {"name": "Acme"}]

    def test_invalid_plan_returns_failed_result(self):
        stage = ValidationStage(config={
            "plan": {
                "contract_version": 1,
                "rules": [{"id": "missing", "type": "required", "field": "absent"}],
            }
        })
        result = stage.run(pd.DataFrame({"present": ["private-value"]}), self._context())
        assert result.status == ExecutionStatus.FAILED.value
        assert result.metadata == {}
        assert "private-value" not in result.error
        assert "$.rules[0].field" in result.error

    def test_unsupported_artifact_returns_failed_result(self):
        stage = ValidationStage(config={"plan": {"contract_version": 1, "rules": []}})
        result = stage.run({"name": "Acme"}, self._context())
        assert result.status == ExecutionStatus.FAILED.value
        assert "DataFrame or list[dict]" in result.error

    def test_metadata_is_bounded_and_privacy_safe(self):
        secret = "customer-secret-123"
        stage = ValidationStage(config={
            "plan": {
                "contract_version": 1,
                "failure_policy": "report_only",
                "issue_limit": 1,
                "rules": [{"id": "required", "type": "required", "field": "name"}],
            }
        })
        result = stage.run(pd.DataFrame({"name": [None, None], "other": [secret, secret]}), self._context())
        serialized = json.dumps(result.metadata)
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.metadata["validation"]["error_count"] == 2
        assert result.metadata["validation"]["detail_count"] == 1
        assert result.metadata["validation"]["truncated"] is True
        assert secret not in serialized


class TestSortAndAggregationStages:
    @staticmethod
    def _context():
        return ExecutionContext(
            pipeline_run_id="run-tabular",
            workspace_id="ws",
            workflow_id="wf-tabular",
            started_at="2025-01-01T00:00:00",
        )

    def test_sort_stage_success_and_metadata(self):
        source = pd.DataFrame({"price": [2, 1], "private": ["secret-b", "secret-a"]})
        stage = SortStage(config={
            "plan": {
                "contract_version": 1,
                "keys": [{"field": "price", "direction": "asc", "nulls": "last"}],
                "stable": True,
            }
        })
        result = stage.run(source, self._context())
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.output_artifact["price"].tolist() == [1, 2]
        assert source["price"].tolist() == [2, 1]
        assert result.metadata == {"sort_keys": ["price"], "operation_count": 1, "rows_in": 2, "rows_out": 2}
        assert "secret" not in json.dumps(result.metadata)

    def test_sort_stage_accepts_list_of_dicts(self):
        source = [{"price": 2}, {"price": 1}]
        stage = SortStage(config={
            "plan": {"contract_version": 1, "keys": [{"field": "price", "direction": "desc", "nulls": "last"}]}
        })
        result = stage.run(source, self._context())
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.output_artifact["price"].tolist() == [2, 1]
        assert source == [{"price": 2}, {"price": 1}]

    def test_sort_stage_invalid_plan_and_artifact_fail_safely(self):
        stage = SortStage(config={
            "plan": {"contract_version": 1, "keys": [{"field": "missing", "direction": "asc", "nulls": "last"}]}
        })
        missing = stage.run(pd.DataFrame({"present": ["private-value"]}), self._context())
        unsupported = stage.run({"present": 1}, self._context())
        assert missing.status == ExecutionStatus.FAILED.value
        assert missing.output_artifact is None
        assert "private-value" not in missing.error
        assert unsupported.status == ExecutionStatus.FAILED.value

    def test_aggregation_stage_success_and_metadata(self):
        source = pd.DataFrame({"supplier": ["B", "A", "B"], "price": [2, 3, 1], "private": ["x", "y", "z"]})
        stage = AggregationStage(config={
            "plan": {
                "contract_version": 1,
                "group_by": ["supplier"],
                "aggregations": [
                    {"function": "count", "output": "rows"},
                    {"field": "price", "function": "sum", "output": "total"},
                ],
                "drop_null_groups": False,
            }
        })
        result = stage.run(source, self._context())
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.output_artifact.to_dict("records") == [
            {"supplier": "A", "rows": 1, "total": 3},
            {"supplier": "B", "rows": 2, "total": 3},
        ]
        assert source.columns.tolist() == ["supplier", "price", "private"]
        assert result.metadata == {
            "aggregate_ids": ["rows", "total"],
            "group_by": ["supplier"],
            "operation_count": 2,
            "rows_in": 3,
            "rows_out": 2,
        }
        assert "private" not in json.dumps(result.metadata)

    def test_aggregation_stage_accepts_list_and_fails_invalid_inputs(self):
        stage = AggregationStage(config={
            "plan": {
                "contract_version": 1,
                "aggregations": [{"function": "count", "output": "rows"}],
            }
        })
        source = [{"value": 1}, {"value": 2}]
        success = stage.run(source, self._context())
        unsupported = stage.run({"value": 1}, self._context())
        assert success.status == ExecutionStatus.SUCCESS.value
        assert success.output_artifact.to_dict("records") == [{"rows": 2}]
        assert source == [{"value": 1}, {"value": 2}]
        assert unsupported.status == ExecutionStatus.FAILED.value


class TestFilterStage:
    def test_run_with_config(self):
        stage = FilterStage(config={"category": "detergents", "keywords": ["omo", "ariel"]})
        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws",
            workflow_id="wf-1",
            started_at="2025-01-01T00:00:00",
        )
        result = stage.run(input_artifact={}, context=ctx)
        assert result.status == ExecutionStatus.SUCCESS.value


class TestEntityExtractStage:
    def test_run_extracts_entities(self):
        document = Document(
            source=DocumentSource(path="/tmp/invoice.txt", source_type="text", media_type="text/plain"),
            content="Supplier: ABC Supplies\nCustomer: Quickmart Ltd.\nInvoice Number: INV-1001\nInvoice Date: 2026-05-01\nDue Date: 2026-05-15\nSubtotal: 65.00\nTax: 7.80\nGrand Total: 72.80\n",
            metadata={"source_name": "abc_supplies"},
        )
        ingestion_result = DocumentIngestionResult(
            document=document,
            classification={"document_type": "invoice"},
            normalized_document=document,
            ingestion_id="ingest-1",
        )
        parsing_result = ParsingResult(blocks=[], sections=[], tables=[])
        pipeline_result = IngestionPipelineResult(
            ingestion_result=ingestion_result,
            parsing_result=parsing_result,
            validation_result=None,
            quality_score=0.9,
            pipeline_run_id="run-1",
        )

        stage = EntityExtractStage(config={})
        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws",
            workflow_id="wf-1",
            started_at="2025-01-01T00:00:00",
        )
        result = stage.run(input_artifact=pipeline_result, context=ctx)

        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.output_artifact is not None
        assert hasattr(result.output_artifact, "references")
        assert len(result.output_artifact.references) == 1
        assert result.output_artifact.references[0].document_number == "INV-1001"


# ── Workflow Runner Tests ─────────────────────────────────────────────


class TestWorkflowRunner:
    def test_sequential_execution(self, valid_definition):
        runner = WorkflowRunner()
        result = runner.run(valid_definition, initial_artifact=pd.DataFrame({"value": [1]}))
        assert result.overall_status == ExecutionStatus.SUCCESS.value
        assert len(result.stage_results) == 6
        for stage_result in result.stage_results:
            assert stage_result.status == ExecutionStatus.SUCCESS.value, f"Stage {stage_result.stage_name} failed"

    def test_fail_fast_on_unknown_stage_raises_validation_error(self):
        wf = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[StageDefinition(name="bad", type="nonexistent")],
        )
        runner = WorkflowRunner()
        with pytest.raises(ValueError, match="stage_type_bad"):
            runner.run(wf)

    def test_fail_fast_on_stage_failure(self):
        wf = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[
                StageDefinition(name="fine", type="transform", depends_on=[]),
                StageDefinition(name="also_fine", type="alert", depends_on=["fine"]),
            ],
        )
        runner = WorkflowRunner()
        result = runner.run(wf, initial_artifact=pd.DataFrame({"value": [1]}))
        assert result.overall_status == ExecutionStatus.SUCCESS.value

    def test_creates_debug_artifact(self, tmp_path, valid_definition):
        debug_dir = tmp_path / "debug"
        runner = WorkflowRunner(debug_path=str(debug_dir))
        result = runner.run(valid_definition, initial_artifact=pd.DataFrame({"value": [1]}))

        artifacts = list(debug_dir.glob("workflow_*.json"))
        assert len(artifacts) == 1
        artifact = json.loads(artifacts[0].read_text(encoding="utf-8"))
        assert artifact["workflow_id"] == "test_workflow"
        assert artifact["stage_count"] == 6

    def test_artifact_replayability(self, tmp_path, valid_definition):
        debug_dir = tmp_path / "debug"
        runner = WorkflowRunner(debug_path=str(debug_dir))
        initial = pd.DataFrame({"value": [1]})
        result1 = runner.run(valid_definition, initial_artifact=initial)
        result2 = runner.run(valid_definition, initial_artifact=initial)
        assert len(result1.stage_results) == len(result2.stage_results)
        assert result1.overall_status == result2.overall_status

    def test_initial_artifact_passthrough(self, valid_definition):
        runner = WorkflowRunner()
        initial = [{"external_input": "test_value"}]
        result = runner.run(valid_definition, initial_artifact=initial)
        assert result.overall_status == ExecutionStatus.SUCCESS.value

    def test_empty_workflow_raises_validation_error(self):
        wf = WorkflowDefinition(
            workflow_id="empty",
            name="Empty",
            version="1.0.0",
            workspace_id="ws",
            enabled=True,
            stages=[],
        )
        runner = WorkflowRunner()
        with pytest.raises(ValueError, match="Workflow must have at least one stage"):
            runner.run(wf)


# ── Workspace Registry Tests ──────────────────────────────────────────


class TestWorkspaceRegistry:
    def test_list_workspaces(self, tmp_path):
        (tmp_path / "quickmart" / "workflows").mkdir(parents=True)
        (tmp_path / "naivas" / "workflows").mkdir(parents=True)
        (tmp_path / "_private").mkdir(parents=True)
        registry = WorkspaceRegistry(str(tmp_path))
        workspaces = registry.list_workspaces()
        assert "quickmart" in workspaces
        assert "naivas" in workspaces
        assert "_private" not in workspaces

    def test_load_workflow(self, tmp_path):
        workflow_dir = tmp_path / "test_ws" / "workflows"
        workflow_dir.mkdir(parents=True)
        workflow_path = workflow_dir / "test_wf.json"
        workflow_path.write_text(
            json.dumps({
                "workflow_id": "test_wf",
                "name": "Test",
                "version": "1.0.0",
                "workspace_id": "test_ws",
                "enabled": True,
                "stages": [{"name": "ingest", "type": "document_ingest", "depends_on": [], "config": {}}],
            }),
            encoding="utf-8",
        )
        registry = WorkspaceRegistry(str(tmp_path))
        wf = registry.load_workflow("test_ws", "test_wf")
        assert wf is not None
        assert wf.workflow_id == "test_wf"
        assert len(wf.stages) == 1

    def test_load_workflow_not_found(self):
        registry = WorkspaceRegistry("/nonexistent")
        wf = registry.load_workflow("nosuch", "nosuch")
        assert wf is None

    def test_list_workflows(self, tmp_path):
        workflow_dir = tmp_path / "test_ws" / "workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "wf_a.json").write_text(
            json.dumps({
                "workflow_id": "wf_a", "name": "A", "version": "1.0.0",
                "workspace_id": "test_ws", "enabled": True,
                "stages": [{"name": "t", "type": "transform", "depends_on": [], "config": {}}],
            }),
            encoding="utf-8",
        )
        (workflow_dir / "wf_b.json").write_text(
            json.dumps({
                "workflow_id": "wf_b", "name": "B", "version": "1.0.0",
                "workspace_id": "test_ws", "enabled": True,
                "stages": [{"name": "t", "type": "transform", "depends_on": [], "config": {}}],
            }),
            encoding="utf-8",
        )
        registry = WorkspaceRegistry(str(tmp_path))
        ids = registry.list_workflows("test_ws")
        assert "wf_a" in ids
        assert "wf_b" in ids

    def test_load_all_workflows(self, tmp_path):
        workflow_dir = tmp_path / "test_ws" / "workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "good.json").write_text(
            json.dumps({
                "workflow_id": "good", "name": "Good", "version": "1.0.0",
                "workspace_id": "test_ws", "enabled": True,
                "stages": [{"name": "t", "type": "transform", "depends_on": [], "config": {}}],
            }),
            encoding="utf-8",
        )
        (workflow_dir / "bad.json").write_text('{"invalid": true}', encoding="utf-8")
        registry = WorkspaceRegistry(str(tmp_path))
        definitions = registry.load_all_workflows("test_ws")
        assert len(definitions) == 1
        assert definitions[0].workflow_id == "good"
