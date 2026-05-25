"""Standard API payload shapes for telemetry, alerts, reports, and history."""

from __future__ import annotations

from typing import Any, Dict


def execution_history_payload(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": entry.get("run_id"),
        "workflow_id": entry.get("workflow_id"),
        "status": entry.get("status"),
        "started_at": entry.get("started_at") or entry.get("start_time"),
        "completed_at": entry.get("completed_at") or entry.get("end_time"),
        "duration_ms": entry.get("duration_ms"),
        "records_processed": entry.get("records_processed", 0),
        "alerts_generated": entry.get("alerts_generated", 0),
        "reports_generated": entry.get("reports_generated", len(entry.get("report_paths", []) or [])),
        "connector_type": entry.get("connector_type"),
        "error": entry.get("error"),
        "steps": entry.get("steps", []),
        "alerts": entry.get("alerts", []),
        "report_paths": entry.get("report_paths", []),
        "metadata": entry.get("metadata", {}),
    }


def alert_payload(entry: Dict[str, Any], alert: Any) -> Dict[str, Any]:
    if isinstance(alert, dict):
        message = alert.get("message") or str(alert)
        alert_type = alert.get("alert_type", "workflow_alert")
        severity = alert.get("severity", "warning")
    else:
        message = str(alert)
        alert_type = "workflow_alert"
        severity = "warning"
    return {
        "run_id": entry.get("run_id"),
        "workflow_id": entry.get("workflow_id"),
        "workflow_name": entry.get("workflow_name"),
        "alert_type": alert_type,
        "severity": severity,
        "alert": message,
        "message": message,
        "timestamp": entry.get("completed_at") or entry.get("end_time") or entry.get("start_time"),
    }


def report_payload(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": report.get("name"),
        "path": report.get("path"),
        "size_bytes": report.get("size_bytes"),
        "updated_at": report.get("updated_at"),
        "report_type": report.get("report_type") or _infer_report_type(report.get("name", "")),
    }


def telemetry_run_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": record.get("run_id"),
        "workflow_id": record.get("workflow_id"),
        "status": record.get("status"),
        "submitted_at": record.get("submitted_at"),
        "started_at": record.get("started_at"),
        "completed_at": record.get("completed_at"),
        "duration_ms": record.get("duration_ms"),
        "records_processed": record.get("records_processed", 0),
        "alerts_generated": record.get("alerts_generated", 0),
        "reports_generated": record.get("reports_generated", 0),
        "connector_type": record.get("connector_type"),
        "error": record.get("error"),
        "metadata": record.get("metadata", {}),
    }


def _infer_report_type(name: str) -> str:
    lowered = name.lower()
    if "alert" in lowered:
        return "alerts"
    if "comparison" in lowered:
        return "comparison"
    return "report"
