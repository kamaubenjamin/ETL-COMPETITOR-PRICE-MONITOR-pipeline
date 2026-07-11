"""Pure display shaping for the Document Intelligence operator console."""

from __future__ import annotations

from typing import Any, Iterable


Record = dict[str, Any]


def _rows(records: Iterable[Record], fields: tuple[str, ...]) -> list[Record]:
    return [{field: record[field] for field in fields} for record in records]


def summary_metrics(metrics: Record) -> list[Record]:
    return [
        {"label": "Documents received", "value": metrics["documents_received"]},
        {"label": "Processed", "value": metrics["processed"]},
        {"label": "Review required", "value": metrics["review_required"]},
        {"label": "Failed", "value": metrics["failed"]},
        {"label": "Export ready", "value": metrics["export_ready"]},
    ]


def inbox_rows(records: Iterable[Record]) -> list[Record]:
    return _rows(records, ("document_id", "filename", "document_type", "status", "confidence", "current_stage"))


def validation_rows(records: Iterable[Record]) -> list[Record]:
    return _rows(records, ("document_id", "severity", "field", "rule", "message"))


def matching_rows(records: Iterable[Record]) -> list[Record]:
    return _rows(records, ("document_id", "entity", "candidate_match", "confidence", "match_status"))


def review_queue_rows(records: Iterable[Record]) -> list[Record]:
    return _rows(records, ("review_case_id", "reason", "priority", "status", "assigned_reviewer"))


def workflow_run_rows(records: Iterable[Record]) -> list[Record]:
    return _rows(records, ("run_id", "workflow_name", "status", "started_at", "duration"))


def audit_log_rows(records: Iterable[Record]) -> list[Record]:
    return _rows(records, ("timestamp", "event_type", "actor", "safe_metadata"))

