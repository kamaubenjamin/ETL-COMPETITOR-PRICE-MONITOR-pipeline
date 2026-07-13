"""Adapter from Workflow Query Facade read models to v0.9 API provider shapes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from src.workflow_runtime.query_facade import (
    AuditEventQuery,
    DocumentQuery,
    InMemoryWorkflowQueryFacade,
    MAX_PAGE_LIMIT,
    PageRequest,
    PageResult,
    QueryFacadeError,
    ReviewCaseQuery,
    WorkflowQueryFacadePort,
    WorkflowRunQuery,
)

from ..errors import DocumentIntelligenceAPIError


Record = dict[str, Any]
T = TypeVar("T")


def _api_error(error: QueryFacadeError) -> DocumentIntelligenceAPIError:
    status_codes = {
        "invalid_query": 400,
        "not_found": 404,
        "source_unavailable": 503,
        "internal_error": 500,
    }
    details = {"field": error.field} if error.field is not None else None
    return DocumentIntelligenceAPIError(
        error.code,
        error.message,
        status_code=status_codes[error.code],
        details=details,
    )


def _all_pages(read: Callable[[PageRequest], PageResult[T]]) -> tuple[T, ...]:
    try:
        items: list[T] = []
        offset = 0
        while True:
            page = read(PageRequest(limit=MAX_PAGE_LIMIT, offset=offset))
            items.extend(page.items)
            if len(items) >= page.total:
                return tuple(items)
            if not page.items:
                raise QueryFacadeError("internal_error")
            offset += len(page.items)
    except QueryFacadeError as error:
        raise _api_error(error) from None


class FacadeDocumentIntelligenceProvider:
    """Read-only API provider backed only by the facade public contract."""

    def __init__(self, facade: WorkflowQueryFacadePort) -> None:
        if not isinstance(facade, WorkflowQueryFacadePort):
            raise ValueError("facade must implement WorkflowQueryFacadePort")
        self._facade = facade

    def list_documents(self, *, status: str | None = None, document_type: str | None = None) -> list[Record]:
        query = DocumentQuery(status=status, document_type=document_type)
        models = _all_pages(lambda page: self._facade.list_documents(query, page))
        return [
            {
                "document_id": model.document_id,
                "filename": model.filename,
                "document_type": model.document_type,
                "status": model.status,
                "confidence": model.confidence,
                "current_stage": model.current_stage,
                "received_at": model.received_at,
            }
            for model in models
        ]

    def get_document(self, document_id: str) -> Record | None:
        try:
            model = self._facade.get_document(document_id)
        except QueryFacadeError as exc:
            if exc.code == "not_found":
                return None
            raise _api_error(exc) from None
        return {
            "document_id": model.document_id,
            "filename": model.filename,
            "document_type": model.document_type,
            "status": model.status,
            "confidence": model.confidence,
            "current_stage": model.current_stage,
            "received_at": model.received_at,
        }

    def list_processing(self, document_id: str) -> list[Record]:
        models = _all_pages(lambda page: self._facade.list_processing(document_id, page))
        return [{"stage": model.stage, "status": model.status, "occurred_at": model.occurred_at} for model in models]

    def list_validation(self, document_id: str) -> list[Record]:
        models = _all_pages(lambda page: self._facade.list_validation_issues(document_id, page))
        return [
            {
                "issue_id": model.issue_id,
                "severity": model.severity,
                "field": model.field,
                "rule_id": model.rule_id,
                "code": model.code,
                "message": model.message,
            }
            for model in models
        ]

    def list_matching(self, document_id: str) -> list[Record]:
        models = _all_pages(lambda page: self._facade.list_matching_results(document_id, page))
        return [
            {
                "match_id": model.match_id,
                "entity_type": model.entity_type,
                "candidate_id": model.candidate_id,
                "confidence": model.confidence,
                "status": model.status,
            }
            for model in models
        ]

    def list_review_cases(self, *, status: str | None = None, priority: str | None = None) -> list[Record]:
        query = ReviewCaseQuery(status=status, priority=priority)
        models = _all_pages(lambda page: self._facade.list_review_cases(query, page))
        return [self._review_case(model) for model in models]

    def get_review_case(self, review_case_id: str) -> Record | None:
        try:
            model = self._facade.get_review_case(review_case_id)
        except QueryFacadeError as exc:
            if exc.code == "not_found":
                return None
            raise _api_error(exc) from None
        return self._review_case(model)

    @staticmethod
    def _review_case(model: Any) -> Record:
        return {
            "review_case_id": model.review_case_id,
            "document_id": model.document_id,
            "reason_code": model.reason_code,
            "priority": model.priority,
            "status": model.status,
            "assigned_reviewer": model.assigned_reviewer_id,
            "correction_count": model.correction_count,
            "decision_code": model.decision_code,
            "reprocess_state": model.reprocess_state,
            "created_at": model.created_at,
        }

    def list_corrections(self, review_case_id: str) -> list[Record]:
        models = _all_pages(lambda page: self._facade.list_correction_history(review_case_id, page))
        return [model.to_dict() for model in models]

    def list_reprocess_plans(self) -> list[Record]:
        models = _all_pages(lambda page: self._facade.list_reprocess_plans(None, page))
        return [model.to_dict() for model in models]

    def list_workflow_runs(self, *, status: str | None = None) -> list[Record]:
        query = WorkflowRunQuery(status=status)
        models = _all_pages(lambda page: self._facade.list_workflow_runs(query, page))
        return [
            {
                "run_id": model.run_id,
                "workflow_name": model.workflow_name,
                "status": model.status,
                "started_at": model.started_at,
                "duration_ms": model.duration_ms,
            }
            for model in models
        ]

    def list_audit_events(self, *, event_type: str | None = None) -> list[Record]:
        query = AuditEventQuery(event_type=event_type)
        models = _all_pages(lambda page: self._facade.list_audit_events(query, page))
        return [
            {
                "event_id": model.event_id,
                "event_type": model.event_type,
                "actor_id": model.actor_id,
                "document_id": model.document_id,
                "review_case_id": model.review_case_id,
                "occurred_at": model.occurred_at,
                "metadata": dict(model.metadata),
            }
            for model in models
        ]


facade_provider = FacadeDocumentIntelligenceProvider(InMemoryWorkflowQueryFacade())
