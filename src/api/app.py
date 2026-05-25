"""
FastAPI app exposing the ETL execution plane through stable API contracts.

FastAPI is imported lazily so the ETL engine remains usable in worker/runtime
contexts where only the execution modules are installed.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from src.contracts.api import (
    ConnectorTestRequest,
    SourceSyncRequest,
    WorkflowCreateRequest,
    WorkflowRunRequest,
)
from src.contracts.payloads import alert_payload, execution_history_payload, report_payload, telemetry_run_payload


def create_app():
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install fastapi and uvicorn to run the FlowSync ETL API"
        ) from exc

    from src.services.workflow_execution_service import workflow_execution_service
    from src.telemetry.telemetry_manager import telemetry_manager

    app = FastAPI(
        title="FlowSync ETL Intelligence Engine API",
        version="1.0.0",
        description="API boundary between FlowSync control plane and ETL execution plane.",
    )

    # ---------------------------------------------------------
    # CORS CONFIGURATION
    # ---------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------
    # HEALTH
    # ---------------------------------------------------------
    @app.get("/health")
    def health() -> Dict[str, Any]:
        telemetry = telemetry_manager.validate_connection()

        return {
            "status": "ok",
            "telemetry_ready": not telemetry.skipped and telemetry.ok,
            "telemetry_message": telemetry.error,
        }

    # ---------------------------------------------------------
    # WORKFLOW EXECUTION
    # ---------------------------------------------------------
    @app.post("/workflows/run")
    def run_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = workflow_execution_service.run_workflow(
                WorkflowRunRequest.from_dict(payload)
            )

            return asdict(response)

        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Missing field: {exc}",
            ) from exc

    @app.post("/workflows/create")
    def create_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return workflow_execution_service.create_workflow(
                WorkflowCreateRequest.from_dict(payload)
            )

        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Missing field: {exc}",
            ) from exc

    # ---------------------------------------------------------
    # WORKFLOW HISTORY
    # ---------------------------------------------------------
    @app.get("/workflows/history")
    def workflow_history(
        workflow_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:

        return {
            "history": [
                execution_history_payload(entry)
                for entry in workflow_execution_service.get_workflow_history(workflow_id, run_id, limit)
            ]
        }

    # ---------------------------------------------------------
    # WORKFLOW STATUS
    # ---------------------------------------------------------
    @app.get("/workflows/status/{run_id}")
    def workflow_status(run_id: str) -> Dict[str, Any]:
        status = workflow_execution_service.get_run_status(run_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} not found",
            )

        return status

    # ---------------------------------------------------------
    # TELEMETRY
    # ---------------------------------------------------------
    @app.get("/telemetry/runs")
    def telemetry_runs(
        workflow_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:

        return {
            "runs": [
                telemetry_run_payload(record)
                for record in workflow_execution_service.list_run_statuses(workflow_id, limit)
            ]
        }

    # ---------------------------------------------------------
    # ALERTS
    # ---------------------------------------------------------
    @app.get("/alerts")
    def alerts(limit: int = 50) -> Dict[str, Any]:
        history = workflow_execution_service.get_workflow_history(limit=limit)

        flattened = []

        for entry in history:
            for alert in entry.get("alerts", []) or []:
                flattened.append(alert_payload(entry, alert))

        return {
            "alerts": flattened[:limit]
        }

    # ---------------------------------------------------------
    # CONNECTOR TEST
    # ---------------------------------------------------------
    @app.post("/connectors/test")
    def connector_test(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return workflow_execution_service.test_connector(
                ConnectorTestRequest.from_dict(payload)
            )

        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Missing field: {exc}",
            ) from exc

    # ---------------------------------------------------------
    # SOURCE SYNC
    # ---------------------------------------------------------
    @app.post("/sources/sync")
    def source_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
        return workflow_execution_service.sync_source(
            SourceSyncRequest.from_dict(payload)
        )

    # ---------------------------------------------------------
    # SOURCE HEALTH
    # ---------------------------------------------------------
    @app.get("/sources/health")
    def source_health() -> Dict[str, Any]:
        return {
            "sources": workflow_execution_service.get_source_health()
        }

    # ---------------------------------------------------------
    # REPORTS
    # ---------------------------------------------------------
    @app.get("/reports/latest")
    def latest_reports(limit: int = 10) -> Dict[str, Any]:
        return {
            "reports": [
                report_payload(report)
                for report in workflow_execution_service.get_latest_reports(limit)
            ]
        }

    return app


try:
    app = create_app()

except RuntimeError:
    # Keeps non-API ETL workers importable when FastAPI is not installed.
    # API deployments should install `fastapi` and `uvicorn`.
    app = None
