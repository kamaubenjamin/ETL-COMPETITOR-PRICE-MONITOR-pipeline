"""
API-facing workflow execution service.

This service is the control-plane boundary for FlowSync. It owns run isolation,
status synchronization, async-safe execution, and error propagation. UI code
should call this through HTTP endpoints, while future Kafka consumers, Airflow
operators, or worker queues can reuse the same service methods.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.contracts.api import (
    ConnectorTestRequest,
    RunStatusRecord,
    SourceSyncRequest,
    WorkflowCreateRequest,
    WorkflowRunRequest,
    WorkflowRunResponse,
    public_dict,
    utc_now_iso,
)
from src.core.execution.status import ACTIVE_STATUSES, ExecutionStatus, normalize_status
from src.core.logging import ExecutionLogger
from src.extract.extract import run_extraction
from src.storage.workflow_history import workflow_history_store
from src.telemetry.pipeline_logger import PipelineLogger
from src.workflow_runner import WorkflowRunner, runner as global_runner
import src.config as config


class RunStatusStore:
    """Small persistent status store for API polling and async workers."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or os.path.join("src", "storage", "workflow_runs.json")
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def upsert(self, record: RunStatusRecord) -> RunStatusRecord:
        with self._lock:
            records = self._load()
            records[record.run_id] = public_dict(record)
            self._save(records)
        return record

    def update(self, run_id: str, **changes: Any) -> Optional[RunStatusRecord]:
        with self._lock:
            records = self._load()
            existing = records.get(run_id)
            if not existing:
                return None
            existing.update(changes)
            existing["updated_at"] = utc_now_iso()
            records[run_id] = existing
            self._save(records)
            return RunStatusRecord(**existing)

    def get(self, run_id: str) -> Optional[RunStatusRecord]:
        record = self._load().get(run_id)
        return RunStatusRecord(**record) if record else None

    def list(self, workflow_id: Optional[str] = None, limit: int = 50) -> List[RunStatusRecord]:
        records = list(self._load().values())
        if workflow_id:
            records = [record for record in records if record.get("workflow_id") == workflow_id]
        records = sorted(records, key=lambda item: item.get("updated_at", ""), reverse=True)
        return [RunStatusRecord(**record) for record in records[:limit]]

    def find_active_by_workflow(self, workflow_id: str) -> Optional[RunStatusRecord]:
        for record in self.list(workflow_id=workflow_id, limit=1000):
            if normalize_status(record.status) in ACTIVE_STATUSES:
                return record
        return None

    def mark_stale_running(self, stale_after_seconds: int = 7200) -> int:
        now = time.time()
        changed = 0
        with self._lock:
            records = self._load()
            for run_id, record in records.items():
                if normalize_status(record.get("status")) not in ACTIVE_STATUSES:
                    continue
                updated_at = record.get("updated_at") or record.get("submitted_at")
                try:
                    updated_ts = datetime_from_iso(updated_at)
                except ValueError:
                    continue
                if now - updated_ts > stale_after_seconds:
                    record["status"] = ExecutionStatus.TIMEOUT.value
                    record["completed_at"] = utc_now_iso()
                    record["error"] = "Execution state was stale and marked timeout"
                    changed += 1
            if changed:
                self._save(records)
        return changed

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return {}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, records: Dict[str, Dict[str, Any]]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)


class WorkflowExecutionService:
    """Public service used by API routes; keeps UI detached from internals."""

    def __init__(
        self,
        runner: WorkflowRunner = global_runner,
        status_store: Optional[RunStatusStore] = None,
        max_workers: int = 4,
    ):
        self.runner = runner
        self.status_store = status_store or RunStatusStore()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="flowsync-workflow")
        self._futures: Dict[str, Future] = {}
        self._futures_lock = threading.RLock()
        self.logger = ExecutionLogger()

    def run_workflow(self, request: WorkflowRunRequest) -> WorkflowRunResponse:
        self.status_store.mark_stale_running()
        if not self.runner.get_workflow(request.workflow_id):
            return WorkflowRunResponse(
                run_id=request.run_id or str(uuid4()),
                workflow_id=request.workflow_id,
                status=ExecutionStatus.FAILED.value,
                accepted=False,
                message=f"Workflow {request.workflow_id} not found",
                error=f"Workflow {request.workflow_id} not found",
            )

        run_id = request.run_id or str(uuid4())
        submitted_at = utc_now_iso()
        if request.prevent_overlap:
            active = self.status_store.find_active_by_workflow(request.workflow_id)
            if active and active.run_id != run_id:
                return WorkflowRunResponse(
                    run_id=active.run_id,
                    workflow_id=request.workflow_id,
                    status=active.status,
                    accepted=False,
                    message="Workflow already has an active run",
                    submitted_at=submitted_at,
                    error="overlapping_execution_prevented",
                )

        self.status_store.upsert(
            RunStatusRecord(
                run_id=run_id,
                workflow_id=request.workflow_id,
                status=ExecutionStatus.QUEUED.value if request.async_execution else ExecutionStatus.RUNNING.value,
                submitted_at=submitted_at,
                updated_at=submitted_at,
                triggered_by=request.triggered_by,
                metadata=request.metadata,
            )
        )

        if request.async_execution:
            future = self.executor.submit(self._execute_workflow, request, run_id)
            with self._futures_lock:
                self._futures[run_id] = future
            return WorkflowRunResponse(
                run_id=run_id,
                workflow_id=request.workflow_id,
                status=ExecutionStatus.QUEUED.value,
                accepted=True,
                message="Workflow execution queued",
                submitted_at=submitted_at,
            )

        sync_future = self.executor.submit(self._execute_workflow, request, run_id)
        try:
            result = sync_future.result(timeout=request.timeout_seconds)
        except TimeoutError:
            self.status_store.update(
                run_id,
                status=ExecutionStatus.TIMEOUT.value,
                completed_at=utc_now_iso(),
                error=f"Workflow timed out after {request.timeout_seconds}s",
            )
        except Exception as exc:
            return WorkflowRunResponse(
                run_id=run_id,
                workflow_id=request.workflow_id,
                status=ExecutionStatus.FAILED.value,
                accepted=False,
                message="Workflow execution failed",
                submitted_at=submitted_at,
                error=str(exc),
            )
            return WorkflowRunResponse(
                run_id=run_id,
                workflow_id=request.workflow_id,
                status=ExecutionStatus.TIMEOUT.value,
                accepted=False,
                message="Workflow execution timed out",
                submitted_at=submitted_at,
                error=f"Workflow timed out after {request.timeout_seconds}s",
            )
        status = normalize_status(result.get("status", "unknown"))
        return WorkflowRunResponse(
            run_id=run_id,
            workflow_id=request.workflow_id,
            status=status,
            accepted=normalize_status(status) != ExecutionStatus.FAILED.value,
            message="Workflow execution completed",
            submitted_at=submitted_at,
            result=self._summarize_result(result),
            error=result.get("error"),
        )

    def _execute_workflow(self, request: WorkflowRunRequest, run_id: str) -> Dict[str, Any]:
        started_at = utc_now_iso()
        start_perf = time.perf_counter()
        self.status_store.update(run_id, status=ExecutionStatus.RUNNING.value, started_at=started_at)
        max_retries = max(0, int(request.max_retries or 0))
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                if attempt:
                    self.logger.retry(
                        "workflow_retry",
                        attempt=attempt,
                        max_retries=max_retries,
                        run_id=run_id,
                        workflow_id=request.workflow_id,
                    )
                result = self.runner.execute_workflow(
                    request.workflow_id,
                    run_id=run_id,
                    triggered_by=request.triggered_by,
                    metadata={
                        **request.metadata,
                        "api_boundary": "WorkflowExecutionService",
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                    },
                )
                summary = self._summarize_result(result)
                status = normalize_status(result.get("status", ExecutionStatus.FAILED.value))
                completed_at = utc_now_iso()
                duration_ms = int((time.perf_counter() - start_perf) * 1000)
                self.status_store.update(
                    run_id,
                    status=status,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                    records_processed=summary.get("records_processed", 0),
                    alerts_generated=summary.get("alerts_generated", 0),
                    reports_generated=summary.get("reports_generated", 0),
                    connector_type=summary.get("connector_type"),
                    result=summary,
                    error=result.get("error"),
                )
                return result
            except Exception as exc:
                last_error = exc
                self.logger.error(
                    "workflow_execution_failed",
                    error=exc,
                    run_id=run_id,
                    workflow_id=request.workflow_id,
                    attempt=attempt + 1,
                )

        error = str(last_error) if last_error else "Unknown workflow failure"
        self.status_store.update(
            run_id,
            status=ExecutionStatus.FAILED.value,
            completed_at=utc_now_iso(),
            duration_ms=int((time.perf_counter() - start_perf) * 1000),
            error=error,
        )
        raise RuntimeError(error)

    def create_workflow(self, request: WorkflowCreateRequest) -> Dict[str, Any]:
        workflow_def = request.to_workflow_definition()
        workflow_path = Path(self.runner.workflows_dir) / f"{request.workflow_id}.json"
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        with open(workflow_path, "w", encoding="utf-8") as f:
            json.dump(workflow_def, f, indent=2)
        self.runner.load_workflows()
        return {
            "workflow_id": request.workflow_id,
            "status": "created",
            "path": str(workflow_path),
        }

    def get_workflow_history(
        self,
        workflow_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        history = workflow_history_store.get_history(workflow_id)
        if run_id:
            history = [entry for entry in history if entry.get("run_id") == run_id]
        return history[-limit:][::-1]

    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        record = self.status_store.get(run_id)
        return public_dict(record) if record else None

    def list_run_statuses(self, workflow_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return [public_dict(record) for record in self.status_store.list(workflow_id, limit)]

    def test_connector(self, request: ConnectorTestRequest) -> Dict[str, Any]:
        logger = PipelineLogger("connector_test")
        logger.start(
            metadata={
                "source_type": request.source_type,
                "url": request.url,
                "selector": request.selector,
                "api_boundary": "connectors/test",
            }
        )
        try:
            execution_config = self._make_execution_config(
                url=request.url,
                keyword=request.keyword,
            )
            df = run_extraction(
                source_type=request.source_type,
                config=execution_config,
                mode=request.mode,
                selector=request.selector,
            )
            rows = len(df)
            logger.success(records_processed=rows, metadata={"operation": "connector_test"})
            return {
                "status": "success",
                "source_type": request.source_type,
                "rows": rows,
                "columns": list(df.columns),
                "sample": df.head(request.sample_limit).to_dict(orient="records"),
            }
        except Exception as exc:
            logger.failure(exc, metadata={"operation": "connector_test"})
            return {"status": "failed", "source_type": request.source_type, "error": str(exc)}

    def sync_source(self, request: SourceSyncRequest) -> Dict[str, Any]:
        test_request = ConnectorTestRequest(
            source_type=request.source_type,
            url=request.url,
            selector=request.selector,
            mode=request.mode,
            keyword=request.keyword,
            sample_limit=0,
            metadata=request.metadata,
        )
        result = self.test_connector(test_request)
        result.update(
            {
                "run_id": request.run_id,
                "workflow_id": request.workflow_id,
                "source_name": request.source_name,
            }
        )
        return result

    def get_latest_reports(self, reports_dir: str = "reports", limit: int = 10) -> List[Dict[str, Any]]:
        if not os.path.isdir(reports_dir):
            return []
        files = []
        for path in Path(reports_dir).glob("*"):
            if not path.is_file():
                continue
            stat = path.stat()
            files.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "updated_at": stat.st_mtime,
                }
            )
        return sorted(files, key=lambda item: item["updated_at"], reverse=True)[:limit]

    def get_source_health(self) -> List[Dict[str, Any]]:
        health = []
        for workflow_id in self.runner.list_workflows():
            workflow = self.runner.get_workflow(workflow_id) or {}
            for source in workflow.get("internal_sources", []) + workflow.get("external_sources", []) + workflow.get("sources", []):
                health.append(
                    {
                        "workflow_id": workflow_id,
                        "source_name": source.get("name"),
                        "source_type": source.get("source_type") or source.get("type"),
                        "url": source.get("url") or source.get("file_path"),
                        "status": "configured",
                    }
                )
        return health

    def _summarize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "run_id": result.get("run_id"),
            "workflow_id": result.get("workflow_id"),
            "workflow_name": result.get("workflow_name"),
            "status": result.get("status"),
            "error": result.get("error"),
            "alerts_generated": result.get("alerts_generated", 0),
            "report_paths": result.get("report_paths", []),
            "reports_generated": len(result.get("report_paths", [])),
            "comparison_shape": result.get("comparison_shape"),
            "records_processed": result.get("records_processed", 0),
            "connector_type": result.get("connector_type"),
            "total_duration": result.get("total_duration"),
            "duration_ms": result.get("duration_ms"),
            "started_at": result.get("started_at") or result.get("start_time"),
            "completed_at": result.get("completed_at") or result.get("end_time"),
        }

    def _make_execution_config(self, **overrides: Any):
        values = {
            key: value
            for key, value in vars(config).items()
            if not key.startswith("__")
        }
        values.update({key: value for key, value in overrides.items() if value is not None})
        return SimpleNamespace(**values)


workflow_execution_service = WorkflowExecutionService()


def datetime_from_iso(value: str) -> float:
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
