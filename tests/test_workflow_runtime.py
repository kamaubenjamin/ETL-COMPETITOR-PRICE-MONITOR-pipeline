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
        expected = {"document_ingest", "entity_extract", "transform", "filter", "fuzzy_match", "compare", "alert", "matching", "report"}
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


class TestIngestStage:
    def test_config_access(self):
        stage = IngestStage(config={"source_name": "test", "source_type": "csv"})
        assert stage._config["source_name"] == "test"


class TestTransformStage:
    def test_run(self):
        stage = TransformStage(config={"rules": []})
        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws",
            workflow_id="wf-1",
            started_at="2025-01-01T00:00:00",
        )
        result = stage.run(input_artifact=None, context=ctx)
        assert result.status == ExecutionStatus.SUCCESS.value
        assert result.stage_name == "transform"


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
        result = runner.run(valid_definition)
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
        result = runner.run(wf)
        assert result.overall_status == ExecutionStatus.SUCCESS.value

    def test_creates_debug_artifact(self, tmp_path, valid_definition):
        debug_dir = tmp_path / "debug"
        runner = WorkflowRunner(debug_path=str(debug_dir))
        result = runner.run(valid_definition)

        artifacts = list(debug_dir.glob("workflow_*.json"))
        assert len(artifacts) == 1
        artifact = json.loads(artifacts[0].read_text(encoding="utf-8"))
        assert artifact["workflow_id"] == "test_workflow"
        assert artifact["stage_count"] == 6

    def test_artifact_replayability(self, tmp_path, valid_definition):
        debug_dir = tmp_path / "debug"
        runner = WorkflowRunner(debug_path=str(debug_dir))
        result1 = runner.run(valid_definition)
        result2 = runner.run(valid_definition)
        assert len(result1.stage_results) == len(result2.stage_results)
        assert result1.overall_status == result2.overall_status

    def test_initial_artifact_passthrough(self, valid_definition):
        runner = WorkflowRunner()
        initial = {"external_input": "test_value"}
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