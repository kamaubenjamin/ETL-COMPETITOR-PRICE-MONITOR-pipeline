"""
Workflow Runner - Orchestration engine for declarative workflow execution.
Loads workflow definitions from JSON and executes them end-to-end.
"""
import json
import os
import threading
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, Any, Optional, List
from uuid import uuid4
import pandas as pd

from src.scheduler import scheduler
from src.core.execution.status import ExecutionStatus
from src.contracts.execution import ExecutionError
from src.reporter import reporter
from src.workflows import WorkflowConfig, SourceConfig, registry
from src.pipeline.multi_source_pipeline import run_multi_source_pipeline
from src.storage.history_store import save_snapshot, detect_price_changes
from src.storage.workflow_history import workflow_history_store
from src.alerts.alert_engine import AlertEngine, generate_alerts
from src.services.alert_manager import AlertManager
from src.telemetry.pipeline_logger import PipelineLogger
from src.transform.comparison_engine import (
    combine_datasets,
    match_products,
    build_comparison_table,
    compare_supplier_vs_market,
    detect_supplier_undercut,
)
import src.config as config


class WorkflowRunner:
    """Execute workflows from declarative JSON definitions."""

    def __init__(self, workflows_dir: str = "workflows"):
        self.workflows_dir = workflows_dir
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.alert_manager = AlertManager()
        self._active_workflows: set[str] = set()
        self._active_lock = threading.RLock()
        self.load_workflows()

    def load_workflows(self):
        """Load all workflow definitions from JSON files."""
        if not os.path.isdir(self.workflows_dir):
            os.makedirs(self.workflows_dir, exist_ok=True)
            return

        for filename in os.listdir(self.workflows_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.workflows_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        workflow_def = json.load(f)
                    workflow_id = workflow_def.get("workflow_id", filename.replace(".json", ""))
                    self.workflows[workflow_id] = workflow_def
                except Exception as e:
                    print(f"❌ Failed to load workflow {filename}: {e}")

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a workflow definition by ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[str]:
        """List all available workflow IDs."""
        return list(self.workflows.keys())

    def workflow_to_config(self, workflow_def: Dict[str, Any]) -> WorkflowConfig:
        """Convert a workflow definition to a WorkflowConfig object."""
        sources = []

        # Handle internal sources
        for src in workflow_def.get("internal_sources", []):
            sources.append(SourceConfig(
                name=src["name"],
                source_type="internal",
                url=src.get("file_path"),  # Use url field for file path
                selector=None,
                keyword=None,
                match_threshold=src.get("match_threshold", 70),
                mode="internal",
                max_pages=src.get("max_pages", 1),
                scroll_depth=src.get("scroll_depth", 0),
                category=src.get("category"),
            ))

        # Handle external sources
        for src in workflow_def.get("external_sources", []):
            sources.append(SourceConfig(
                name=src["name"],
                source_type=src["source_type"],
                url=src.get("url"),
                selector=src.get("selector"),
                keyword=src.get("keyword"),
                match_threshold=src.get("match_threshold", 70),
                mode="Auto Detect",
                max_pages=src.get("max_pages", 3),
                scroll_depth=src.get("scroll_depth", 4),
                category=src.get("category"),
            ))

        # Legacy support for "sources" field
        for src in workflow_def.get("sources", []):
            sources.append(SourceConfig(
                name=src["name"],
                source_type=src["source_type"],
                url=src.get("url"),
                selector=src.get("selector"),
                keyword=src.get("keyword"),
                match_threshold=src.get("match_threshold", 70),
                mode="Auto Detect",
                max_pages=src.get("max_pages", 3),
                scroll_depth=src.get("scroll_depth", 4),
                category=src.get("category"),
            ))

        return WorkflowConfig(
            workflow_id=workflow_def.get("workflow_id"),
            name=workflow_def.get("workflow_name", workflow_def.get("workflow_id")),
            description=workflow_def.get("description", ""),
            sources=sources,
            transformation_rules=workflow_def.get("transformation_rules", []),
            alert_rules=workflow_def.get("alert_rules", {}),
            global_match_threshold=workflow_def.get("global_match_threshold", 70),
            enabled=workflow_def.get("enabled", True),
        )

    def execute_workflow(
        self,
        workflow_id: str,
        run_id: Optional[str] = None,
        triggered_by: str = "manual",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a complete workflow from definition to reporting."""
        workflow_def = self.get_workflow(workflow_id)
        if not workflow_def:
            return {
                "status": ExecutionStatus.FAILED.value,
                "error": f"Workflow {workflow_id} not found",
                "execution_time": 0,
            }
        with self._active_lock:
            if workflow_id in self._active_workflows:
                return {
                    "run_id": run_id or str(uuid4()),
                    "workflow_id": workflow_id,
                    "status": ExecutionStatus.CANCELLED.value,
                    "error": f"Workflow {workflow_id} already has an active run",
                    "execution_time": 0,
                }
            self._active_workflows.add(workflow_id)

        start_time = datetime.now()
        run_id = run_id or str(uuid4())
        metadata = metadata or {}
        pipeline_logger = PipelineLogger(
            workflow_def.get("workflow_name", workflow_id),
            run_id=run_id,
        )
        pipeline_logger.start(
            metadata={
                "workflow_id": workflow_id,
                "triggered_by": triggered_by,
                # Future Airflow DAG integration can pass dag_run_id here and
                # use this FlowSync run_id as the external task correlation key.
                "orchestrator": "WorkflowRunner.execute_workflow",
                **metadata,
            },
            triggered_by=triggered_by,
        )
        execution_log = {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "workflow_name": workflow_def.get("workflow_name"),
            "start_time": start_time.isoformat(),
            "started_at": start_time.isoformat(),
            "status": ExecutionStatus.RUNNING.value,
            "error": None,
            "errors": [],
            "steps": [],
            "alerts_generated": 0,
            "report_paths": [],
            "reports_generated": 0,
            "comparison_shape": None,
            "records_processed": 0,
            "connector_type": None,
            "triggered_by": triggered_by,
            "metadata": metadata,
        }

        try:
            workflow_config = self.workflow_to_config(workflow_def)
            execution_config = self._make_execution_config()
            execution_log["connector_type"] = ",".join(sorted({source.source_type for source in workflow_config.sources}))
            max_step_retries = int(workflow_def.get("max_retries", metadata.get("max_retries", 0)) or 0)

            # Execute each step
            for step in workflow_def.get("steps", []):
                step_start = datetime.now()
                step_log = {
                    "name": step,
                    "status": ExecutionStatus.RUNNING.value,
                    "duration": 0,
                    "duration_ms": 0,
                    "message": "",
                    "attempts": 0,
                }

                try:
                    step_error = None
                    for attempt in range(max_step_retries + 1):
                        step_log["attempts"] = attempt + 1
                        try:
                            self._execute_step(
                                step,
                                workflow_def,
                                workflow_config,
                                execution_config,
                                execution_log,
                                run_id,
                            )
                            step_error = None
                            break
                        except Exception as e:
                            step_error = e
                            if attempt >= max_step_retries:
                                raise

                    if step_error is None:
                        step_log["status"] = ExecutionStatus.SUCCESS.value
                        step_log["message"] = self._step_message(step, workflow_config, execution_log, workflow_def)
                    step_log["duration"] = (datetime.now() - step_start).total_seconds()
                    step_log["duration_ms"] = int(step_log["duration"] * 1000)
                    execution_log["steps"].append(step_log)

                except Exception as e:
                    step_log["status"] = ExecutionStatus.FAILED.value
                    step_log["message"] = str(e)
                    step_log["duration"] = (datetime.now() - step_start).total_seconds()
                    step_log["duration_ms"] = int(step_log["duration"] * 1000)
                    execution_log["steps"].append(step_log)
                    execution_log["status"] = ExecutionStatus.PARTIAL_SUCCESS.value
                    error_payload = ExecutionError(
                        message=str(e),
                        error_type=type(e).__name__,
                        step=step,
                        retryable=max_step_retries > 0,
                    ).to_payload()
                    execution_log["errors"].append(error_payload)
                    if execution_log["error"] is None:
                        execution_log["error"] = f"Step '{step}' failed: {e}"

            if execution_log["status"] == ExecutionStatus.RUNNING.value:
                execution_log["status"] = ExecutionStatus.SUCCESS.value

            # Record execution in history
            completed_at = datetime.now()
            execution_log["end_time"] = completed_at.isoformat()
            execution_log["completed_at"] = completed_at.isoformat()
            execution_log["total_duration"] = (completed_at - start_time).total_seconds()
            execution_log["duration_ms"] = int(execution_log["total_duration"] * 1000)
            execution_log["reports_generated"] = len(execution_log["report_paths"])
            if execution_log.get("comparison_shape"):
                execution_log["records_processed"] = execution_log["comparison_shape"][0]
            workflow_history_store.record_execution(execution_log)
            self.execution_history.append(execution_log)
            pipeline_logger.finalize(
                execution_log["status"],
                records_processed=execution_log["records_processed"],
                error_message=execution_log.get("error"),
                metadata={
                    "workflow_id": workflow_id,
                    "alerts_generated": execution_log["alerts_generated"],
                    "reports_generated": execution_log["reports_generated"],
                    "report_paths": execution_log["report_paths"],
                    "duration_ms": execution_log["duration_ms"],
                    "connector_type": execution_log["connector_type"],
                },
            )

            # Update scheduler
            schedule = scheduler.get_schedule(workflow_id)
            if schedule:
                scheduler.record_run(workflow_id)

            with self._active_lock:
                self._active_workflows.discard(workflow_id)
            return execution_log

        except Exception as e:
            completed_at = datetime.now()
            execution_log["status"] = ExecutionStatus.FAILED.value
            execution_log["error"] = str(e)
            execution_log["errors"].append(
                ExecutionError(
                    message=str(e),
                    error_type=type(e).__name__,
                    retryable=False,
                ).to_payload()
            )
            execution_log["end_time"] = completed_at.isoformat()
            execution_log["completed_at"] = completed_at.isoformat()
            execution_log["total_duration"] = (completed_at - start_time).total_seconds()
            execution_log["duration_ms"] = int(execution_log["total_duration"] * 1000)
            workflow_history_store.record_execution(execution_log)
            self.execution_history.append(execution_log)
            pipeline_logger.failure(
                e,
                metadata={
                    "workflow_id": workflow_id,
                    "total_duration": execution_log["total_duration"],
                    "duration_ms": execution_log["duration_ms"],
                },
            )
            with self._active_lock:
                self._active_workflows.discard(workflow_id)
            return execution_log

    def _execute_step(self, step, workflow_def, workflow_config, execution_config, execution_log, run_id):
                    if step == "extract":
                        pipeline_result = run_multi_source_pipeline(workflow_config, execution_config)
                        if isinstance(pipeline_result, tuple):
                            matched, comparison = pipeline_result
                            execution_log["matched"] = matched
                            execution_log["comparison"] = comparison
                        else:
                            # Fallback for older pipeline versions
                            execution_log["comparison"] = pipeline_result
                        if hasattr(comparison, "shape"):
                            execution_log["comparison_shape"] = list(comparison.shape)
                            execution_log["records_processed"] = comparison.shape[0]
                        source_failures = getattr(comparison, "attrs", {}).get("source_failures", [])
                        if source_failures:
                            execution_log["errors"].extend(source_failures)
                            execution_log["status"] = ExecutionStatus.PARTIAL_SUCCESS.value

                    elif step == "normalize":
                        return

                    elif step == "fuzzy_match":
                        return

                    elif step == "compare":
                        return

                    elif step == "compare_supplier_vs_market":
                        if "matched" in execution_log:
                            supplier_analysis = compare_supplier_vs_market(execution_log["matched"])
                            execution_log["supplier_analysis"] = supplier_analysis
                        return

                    elif step == "detect_undercut":
                        if "supplier_analysis" in execution_log:
                            undercut_threshold = workflow_def.get("alert_rules", {}).get("undercut_threshold", 2000)
                            undercut_opportunities = detect_supplier_undercut(
                                execution_log["supplier_analysis"],
                                threshold=undercut_threshold
                            )
                            execution_log["undercut_opportunities"] = undercut_opportunities
                        else:
                            execution_log["undercut_opportunities"] = pd.DataFrame()
                        history_file = "price_history.csv"
                        if os.path.exists(history_file):
                            df_history = pd.read_csv(history_file)
                            changes = detect_price_changes(df_history)
                            execution_log["changes"] = changes
                        return

                    elif step == "generate_alerts":
                        structured_alerts = []
                        if "comparison" in execution_log:
                            alert_rules = workflow_def.get("alert_rules", {})
                            structured_rules = []
                            if isinstance(alert_rules, dict):
                                if alert_rules.get("abnormal_discount_threshold") is not None:
                                    structured_rules.append({"type": "abnormal_discount", "threshold_percent": alert_rules.get("abnormal_discount_threshold", 35)})
                                if alert_rules.get("sudden_spike_percentage") is not None:
                                    structured_rules.append({"type": "abnormal_spike", "threshold_percent": alert_rules.get("sudden_spike_percentage", 25)})
                                if alert_rules.get("supplier_variance_threshold") is not None:
                                    structured_rules.append({"type": "supplier_pricing_variance", "threshold": alert_rules.get("supplier_variance_threshold", 10)})
                                structured_rules.extend([
                                    {"type": "missing_product"},
                                    {"type": "stock_disappearance"},
                                ])
                            structured_alerts = AlertEngine(structured_rules).evaluate(execution_log["comparison"])
                        if "changes" in execution_log:
                            alert_rules = workflow_def.get("alert_rules", {})
                            alerts = generate_alerts(
                                execution_log["changes"],
                                [alert_rules] if alert_rules else []
                            )
                            alerts = alerts + structured_alerts
                            execution_log["alerts"] = alerts
                            execution_log["alerts_generated"] = len(alerts) if isinstance(alerts, list) else 0
                            for alert in alerts:
                                alert_message = alert.get("message") if isinstance(alert, dict) else alert
                                if isinstance(alert_message, str) and not alert_message.lower().startswith("no "):
                                    self.alert_manager.publish(
                                        alert_message,
                                        alert_type="price_monitoring",
                                        severity=alert.get("severity", "warning") if isinstance(alert, dict) else "warning",
                                        pipeline_name=workflow_def.get("workflow_name", workflow_id),
                                        pipeline_run_id=run_id,
                                        metadata={"workflow_id": workflow_id},
                                    )
                        else:
                            execution_log["alerts"] = structured_alerts
                            execution_log["alerts_generated"] = len(structured_alerts)
                        return

                    elif step == "generate_reports":
                        if "comparison" in execution_log:
                            csv_file = reporter.export_comparison_csv(
                                execution_log["comparison"],
                                workflow_def.get("workflow_name", workflow_id),
                            )
                            execution_log["report_file"] = csv_file
                            execution_log["report_paths"].append(csv_file)

                            if workflow_def.get("reporting", {}).get("export_pdf"):
                                pdf_file = reporter.export_comparison_pdf(
                                    execution_log["comparison"],
                                    workflow_def.get("workflow_name", workflow_id),
                                )
                                if pdf_file:
                                    execution_log["pdf_file"] = pdf_file
                                    execution_log["report_paths"].append(pdf_file)
                        execution_log["reports_generated"] = len(execution_log["report_paths"])
                        return

    def _step_message(self, step, workflow_config, execution_log, workflow_def):
        if step == "extract":
            return f"Extracted from {len(workflow_config.sources)} sources"
        if step == "compare_supplier_vs_market" and "supplier_analysis" in execution_log:
            return f"Analyzed {len(execution_log['supplier_analysis'])} supplier vs market comparisons"
        if step == "detect_undercut" and "changes" in execution_log:
            return f"Detected {len(execution_log['changes'])} price changes"
        if step == "generate_alerts":
            return f"Generated {execution_log.get('alerts_generated', 0)} alerts"
        if step == "generate_reports":
            return f"Generated {len(execution_log.get('report_paths', []))} reports"
        return f"Completed {step}"

    def execute_due_workflows(self) -> List[Dict[str, Any]]:
        """Execute all workflows that are due to run."""
        results = []
        due_schedules = [s for s in scheduler.list_enabled() if scheduler.is_due(s)]

        for schedule in due_schedules:
            result = self.execute_workflow(schedule.workflow_id)
            results.append(result)

        return results

    def get_execution_history(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get execution history, optionally filtered by workflow ID."""
        if workflow_id:
            return [e for e in self.execution_history if e["workflow_id"] == workflow_id]
        return self.execution_history

    def register_workflow_to_registry(self, workflow_id: str) -> bool:
        """Register a workflow definition to the global registry."""
        workflow_def = self.get_workflow(workflow_id)
        if not workflow_def:
            return False

        config = self.workflow_to_config(workflow_def)
        registry.register(config)
        return True

    def _make_execution_config(self):
        """
        Create a run-scoped config snapshot.

        Existing connectors mutate config.url/keyword while processing sources.
        Keeping those mutations inside a per-run namespace preserves run_id
        isolation today and prepares the engine for async workers later.
        """
        return SimpleNamespace(
            **{
                key: value
                for key, value in vars(config).items()
                if not key.startswith("__")
            }
        )


# Global runner instance
runner = WorkflowRunner()
