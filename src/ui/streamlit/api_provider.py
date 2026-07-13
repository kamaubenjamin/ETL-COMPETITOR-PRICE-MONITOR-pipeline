"""View-friendly read-only provider backed by the Document Intelligence API."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .api_client import APIClientError, DocumentIntelligenceAPIClient


Record = dict[str, Any]

_SAFE_ERROR_MESSAGES = {
    "authentication_required": "Authentication is required for this API preview.",
    "authorization_denied": "This identity is not permitted to view the requested data.",
    "resource_not_found": "The requested resource is not available in this scope.",
    "not_found": "The requested resource is not available in this scope.",
    "api_unavailable": "Document Intelligence API is unavailable.",
    "identity_provider_unavailable": "Identity resolution is temporarily unavailable.",
    "invalid_response": "Document Intelligence API returned an invalid response.",
}


def safe_api_preview_error(code: str) -> str:
    """Return a fixed operator-safe message without reflecting backend detail."""

    return _SAFE_ERROR_MESSAGES.get(code, "Document Intelligence API request could not be completed.")


class DocumentIntelligenceAPIProvider:
    """Maps consumer-neutral API projections to operator-console records."""

    def __init__(self, client: DocumentIntelligenceAPIClient | None, *, initial_error: str | None = None) -> None:
        self.client = client
        self.last_error: str | None = initial_error
        self.last_error_code: str | None = "invalid_configuration" if initial_error else None

    def _safe(self, read: Callable[[], list[Record]]) -> list[Record]:
        if self.client is None:
            return []
        try:
            rows = read()
        except APIClientError as exc:
            self.last_error_code = exc.code
            self.last_error = safe_api_preview_error(exc.code)
            return []
        self.last_error_code = None
        self.last_error = None
        return deepcopy(rows)

    def documents(self, *, document_type: str | None = None, status: str | None = None) -> list[Record]:
        def read() -> list[Record]:
            rows = self.client.get("/api/v1/documents", params={"status": status})
            if not isinstance(rows, list):
                raise APIClientError("invalid_response", "API document data is invalid.")
            if document_type:
                expected = document_type.lower().replace(" ", "_")
                rows = [row for row in rows if row.get("document_type") == expected]
            return rows
        return self._safe(read)

    def processing_statuses(self, *, status: str | None = None) -> list[Record]:
        def read() -> list[Record]:
            rows = []
            for document in self.client.get("/api/v1/documents"):
                for item in self.client.get(f"/api/v1/documents/{document['document_id']}/processing"):
                    record = dict(item)
                    record.update({"document_id": document["document_id"], "started_at": item.get("occurred_at", ""), "elapsed": "-"})
                    rows.append(record)
            return [row for row in rows if status is None or row.get("status") == status]
        return self._safe(read)

    def validation_issues(self) -> list[Record]:
        def read() -> list[Record]:
            rows = []
            for document in self.client.get("/api/v1/documents"):
                for item in self.client.get(f"/api/v1/documents/{document['document_id']}/validation"):
                    rows.append({"document_id": document["document_id"], "severity": item["severity"], "field": item["field"], "rule": item["rule_id"], "message": item["message"]})
            return rows
        return self._safe(read)

    def matching_results(self) -> list[Record]:
        def read() -> list[Record]:
            rows = []
            for document in self.client.get("/api/v1/documents"):
                for item in self.client.get(f"/api/v1/documents/{document['document_id']}/matching"):
                    rows.append({"document_id": document["document_id"], "entity": item["entity_type"], "candidate_match": item["candidate_id"], "confidence": item["confidence"], "match_status": item["status"]})
            return rows
        return self._safe(read)

    def review_cases(self, *, status: str | None = None) -> list[Record]:
        def read() -> list[Record]:
            rows = self.client.get("/api/v1/review-cases", params={"status": status})
            return [{**row, "decision": row.get("decision_code") or "pending"} for row in rows]
        return self._safe(read)

    def workflow_runs(self, *, workflow_name: str | None = None) -> list[Record]:
        def read() -> list[Record]:
            rows = self.client.get("/api/v1/workflow-runs")
            if workflow_name:
                expected = workflow_name.lower().replace(" ", "_")
                rows = [row for row in rows if row.get("workflow_name") == expected]
            return [{**row, "duration": _duration(row.get("duration_ms"))} for row in rows]
        return self._safe(read)

    def audit_events(self) -> list[Record]:
        def read() -> list[Record]:
            rows = self.client.get("/api/v1/audit-events")
            return [{"timestamp": row["occurred_at"], "event_type": row["event_type"], "actor": row["actor_id"], "safe_metadata": _safe_metadata(row.get("metadata", {}))} for row in rows]
        return self._safe(read)

    def summary_metrics(self, *, documents: list[Record] | None = None) -> Record:
        rows = deepcopy(documents) if documents is not None else self.documents()
        processed = {"validated", "matched", "review_required", "approved", "export_ready", "exported"}
        return {"documents_received": len(rows), "processed": sum(row["status"] in processed for row in rows), "review_required": sum(row["status"] == "review_required" for row in rows), "failed": sum(row["status"] == "failed" for row in rows), "export_ready": sum(row["status"] == "export_ready" for row in rows)}


def _duration(duration_ms: int | None) -> str:
    if duration_ms is None:
        return "Running"
    seconds = duration_ms // 1000
    return f"00:00:{seconds:02d}"


def _safe_metadata(metadata: dict[str, Any]) -> str:
    return "; ".join(f"{key}={metadata[key]}" for key in sorted(metadata))
