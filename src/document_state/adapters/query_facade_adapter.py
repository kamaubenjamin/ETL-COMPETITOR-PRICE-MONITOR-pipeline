"""Read-only adapter from Document State repositories to Workflow Query Facade."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from src.document_state import (
    AuditQuery as StateAuditQuery,
    DocumentQuery as StateDocumentQuery,
    DocumentStateError,
    DocumentStateReadRepositories,
    MAX_PAGE_LIMIT as STATE_MAX_PAGE_LIMIT,
    MatchingQuery as StateMatchingQuery,
    PageRequest as StatePageRequest,
    ProcessingQuery as StateProcessingQuery,
    ReviewQuery as StateReviewQuery,
    ValidationQuery as StateValidationQuery,
    WorkflowRunQuery as StateWorkflowRunQuery,
)
from src.workflow_runtime.query_facade import (
    AuditEventQuery,
    AuditEventSummary,
    CorrectionHistorySummary,
    DocumentDetail,
    DocumentInboxItem,
    DocumentQuery,
    MatchingResult,
    PageRequest,
    PageResult,
    ProcessingStatus,
    QueryFacadeError,
    ReprocessPlanSummary,
    ReviewCaseQuery,
    ReviewCaseSummary,
    ValidationIssue,
    WorkflowQueryFacadePort,
    WorkflowRunQuery,
    WorkflowRunSummary,
)


StateRecord = TypeVar("StateRecord")
FacadeRecord = TypeVar("FacadeRecord")

_MATCH_STATUS = {
    "matched": "matched",
    "ambiguous": "ambiguous",
    "unmatched": "no_match",
    "review_required": "ambiguous",
}
_WORKFLOW_STATUS = {
    "queued": "queued",
    "running": "running",
    "succeeded": "succeeded",
    "failed": "failed",
    "cancelled": "failed",
}
_REPROCESS_STATE = {
    None: "not_requested",
    "not_requested": "not_requested",
    "requested": "requested",
    "reprocess_requested": "requested",
    "planned": "planned",
}
_AUDIT_METADATA_KEYS = frozenset(
    {
        "attempt",
        "correlation_id",
        "correction_count",
        "issue_count",
        "match_count",
        "mode",
        "operation_count",
        "plan_count",
        "reason_code",
        "source_runtime",
        "source_stage",
        "stage_count",
        "status",
        "trace_id",
        "workflow_name",
    }
)


def _facade_error(error: DocumentStateError) -> QueryFacadeError:
    code = {
        "invalid_query": "invalid_query",
        "not_found": "not_found",
        "source_unavailable": "source_unavailable",
        "invalid_record": "internal_error",
        "conflict": "internal_error",
        "internal_error": "internal_error",
    }[error.code]
    field = error.field if code == "invalid_query" else None
    return QueryFacadeError(code, field=field)


def _validate_page(page: Any) -> PageRequest:
    if not isinstance(page, PageRequest):
        raise QueryFacadeError("invalid_query", field="page")
    return page


def _validate_query(query: Any, expected: type[FacadeRecord]) -> FacadeRecord:
    if not isinstance(query, expected):
        raise QueryFacadeError("invalid_query", field="query")
    return query


def _ordered(records: Iterable[FacadeRecord]) -> tuple[FacadeRecord, ...]:
    result = list(records)
    if not result:
        return ()
    ordering = result[0].ORDERING
    for field_name, direction in reversed(tuple(zip(ordering.fields, ordering.directions))):
        direction_value = getattr(direction, "value", direction)
        result.sort(key=lambda item, name=field_name: getattr(item, name), reverse=direction_value == "desc")
    return tuple(result)


class DocumentStateQueryFacadeAdapter:
    """Workflow Query Facade port backed by injected Document State reads."""

    __slots__ = ("__repositories", "__snapshot_at")

    def __init__(self, repositories: DocumentStateReadRepositories, *, snapshot_at: str) -> None:
        if not isinstance(repositories, DocumentStateReadRepositories):
            raise ValueError("repositories must implement DocumentStateReadRepositories")
        try:
            PageResult(items=(), total=0, limit=1, offset=0, snapshot_at=snapshot_at)
        except (TypeError, ValueError) as exc:
            raise ValueError("snapshot_at must be a valid facade timestamp") from exc
        self.__repositories = repositories
        self.__snapshot_at = snapshot_at

    def _all(self, read: Callable[[StatePageRequest], Any]) -> tuple[Any, ...]:
        records: list[Any] = []
        offset = 0
        try:
            while True:
                result = read(StatePageRequest(limit=STATE_MAX_PAGE_LIMIT, offset=offset))
                records.extend(result.items)
                if len(records) >= result.total:
                    return tuple(records)
                if not result.items:
                    raise QueryFacadeError("internal_error")
                offset += len(result.items)
        except DocumentStateError as error:
            raise _facade_error(error) from None
        except ValueError:
            raise QueryFacadeError("internal_error") from None

    def _page(
        self,
        records: Iterable[StateRecord],
        page: PageRequest,
        project: Callable[[StateRecord], FacadeRecord],
    ) -> PageResult[FacadeRecord]:
        safe_page = _validate_page(page)
        try:
            projected = _ordered(project(record) for record in records)
            return PageResult(
                items=projected[safe_page.offset : safe_page.offset + safe_page.limit],
                total=len(projected),
                limit=safe_page.limit,
                offset=safe_page.offset,
                snapshot_at=self.__snapshot_at,
            )
        except QueryFacadeError:
            raise
        except (KeyError, TypeError, ValueError):
            raise QueryFacadeError("internal_error") from None

    def list_documents(self, query: DocumentQuery, page: PageRequest) -> PageResult[DocumentInboxItem]:
        safe_query = _validate_query(query, DocumentQuery)
        try:
            state_query = StateDocumentQuery(
                status=safe_query.status,
                document_type=safe_query.document_type,
                tenant_id=safe_query.tenant_id,
            )
        except ValueError:
            raise QueryFacadeError("invalid_query", field="query") from None
        records = self._all(lambda state_page: self.__repositories.list_documents(state_query, state_page))
        return self._page(records, page, self._document_item)

    def get_document(self, document_id: str, *, tenant_id: str | None = None) -> DocumentDetail:
        try:
            record = self.__repositories.get_document(document_id, tenant_id=tenant_id)
            workflow_name = record.metadata.get("workflow_name")
            return DocumentDetail(
                record.document_id,
                record.filename,
                record.document_type,
                record.status,
                record.confidence,
                record.current_stage,
                record.received_at,
                record.updated_at,
                workflow_name if isinstance(workflow_name, str) else None,
                record.tenant_id,
            )
        except DocumentStateError as error:
            raise _facade_error(error) from None
        except (TypeError, ValueError):
            raise QueryFacadeError("internal_error") from None

    @staticmethod
    def _document_item(record: Any) -> DocumentInboxItem:
        return DocumentInboxItem(
            record.document_id,
            record.filename,
            record.document_type,
            record.status,
            record.confidence,
            record.current_stage,
            record.received_at,
            record.tenant_id,
        )

    def list_processing(self, document_id: str, page: PageRequest) -> PageResult[ProcessingStatus]:
        records = self._all(
            lambda state_page: self.__repositories.list_processing_snapshots(
                document_id, StateProcessingQuery(), state_page
            )
        )
        return self._page(
            records,
            page,
            lambda record: ProcessingStatus(record.document_id, record.stage, record.status, record.updated_at),
        )

    def list_validation_issues(self, document_id: str, page: PageRequest) -> PageResult[ValidationIssue]:
        records = self._all(
            lambda state_page: self.__repositories.list_validation_issues(
                document_id, StateValidationQuery(), state_page
            )
        )
        return self._page(
            records,
            page,
            lambda record: ValidationIssue(
                record.issue_id,
                record.document_id,
                record.severity,
                record.field,
                record.rule_id,
                record.code,
                record.message,
            ),
        )

    def list_matching_results(self, document_id: str, page: PageRequest) -> PageResult[MatchingResult]:
        records = self._all(
            lambda state_page: self.__repositories.list_matching_summaries(
                document_id, StateMatchingQuery(), state_page
            )
        )
        return self._page(
            records,
            page,
            lambda record: MatchingResult(
                record.match_id,
                record.document_id,
                record.entity_type,
                record.candidate_id,
                record.confidence,
                _MATCH_STATUS[record.status],
            ),
        )

    def list_review_cases(self, query: ReviewCaseQuery, page: PageRequest) -> PageResult[ReviewCaseSummary]:
        safe_query = _validate_query(query, ReviewCaseQuery)
        try:
            state_query = StateReviewQuery(status=safe_query.status, priority=safe_query.priority)
        except ValueError:
            raise QueryFacadeError("invalid_query", field="query") from None
        records = self._all(lambda state_page: self.__repositories.list_review_references(state_query, state_page))
        return self._page(records, page, self._review_summary)

    def get_review_case(self, review_case_id: str) -> ReviewCaseSummary:
        try:
            return self._review_summary(self.__repositories.get_review_reference(review_case_id))
        except DocumentStateError as error:
            raise _facade_error(error) from None
        except (KeyError, TypeError, ValueError):
            raise QueryFacadeError("internal_error") from None

    @staticmethod
    def _review_summary(record: Any) -> ReviewCaseSummary:
        return ReviewCaseSummary(
            record.review_case_id,
            record.document_id,
            record.reason_code,
            record.priority,
            record.status,
            record.assigned_reviewer_id,
            record.correction_count,
            record.decision_code,
            _REPROCESS_STATE[record.reprocess_state],
            record.created_at,
            record.updated_at,
        )

    def list_correction_history(self, review_case_id: str, page: PageRequest) -> PageResult[CorrectionHistorySummary]:
        records = self._all(
            lambda state_page: self.__repositories.list_correction_summaries(review_case_id, state_page)
        )
        return self._page(
            records,
            page,
            lambda record: CorrectionHistorySummary(
                record.correction_id,
                record.review_case_id,
                record.field_path,
                record.operation,
                record.reason_code,
                record.actor_id,
                record.occurred_at,
                record.source_stage,
            ),
        )

    def list_reprocess_plans(self, review_case_id: str | None, page: PageRequest) -> PageResult[ReprocessPlanSummary]:
        records = self._all(
            lambda state_page: self.__repositories.list_reprocess_plans(review_case_id, state_page)
        )
        return self._page(
            records,
            page,
            lambda record: ReprocessPlanSummary(
                record.plan_id,
                record.review_case_id,
                record.requested_from_stage,
                record.requested_target_stage,
                record.invalidated_artifact_count,
                record.retained_artifact_count,
                record.reason_code,
                record.requested_by,
                record.created_at,
                record.mode,
            ),
        )

    def list_workflow_runs(self, query: WorkflowRunQuery, page: PageRequest) -> PageResult[WorkflowRunSummary]:
        safe_query = _validate_query(query, WorkflowRunQuery)
        try:
            state_query = StateWorkflowRunQuery(workflow_name=safe_query.workflow_name)
        except ValueError:
            raise QueryFacadeError("invalid_query", field="query") from None
        records = self._all(lambda state_page: self.__repositories.list_workflow_runs(state_query, state_page))
        projected = tuple(self._workflow_summary(record) for record in records)
        if safe_query.status is not None:
            projected = tuple(record for record in projected if record.status == safe_query.status)
        return self._page(projected, page, lambda record: record)

    @staticmethod
    def _workflow_summary(record: Any) -> WorkflowRunSummary:
        return WorkflowRunSummary(
            record.run_id,
            record.workflow_name,
            _WORKFLOW_STATUS[record.status],
            record.started_at,
            record.completed_at,
            record.duration_ms,
            record.stage_count,
            record.succeeded_stage_count,
            record.failed_stage_count,
        )

    def list_audit_events(self, query: AuditEventQuery, page: PageRequest) -> PageResult[AuditEventSummary]:
        safe_query = _validate_query(query, AuditEventQuery)
        try:
            state_query = StateAuditQuery(event_type=safe_query.event_type)
        except ValueError:
            raise QueryFacadeError("invalid_query", field="query") from None
        records = self._all(lambda state_page: self.__repositories.list_audit_events(state_query, state_page))
        return self._page(records, page, self._audit_summary)

    @staticmethod
    def _audit_summary(record: Any) -> AuditEventSummary:
        metadata = {
            key: value
            for key, value in record.metadata.items()
            if key in _AUDIT_METADATA_KEYS and (value is None or isinstance(value, (str, int, bool)))
        }
        return AuditEventSummary(
            record.event_id,
            record.event_type,
            record.actor_id,
            record.occurred_at,
            record.document_id,
            record.review_case_id,
            metadata,
        )
