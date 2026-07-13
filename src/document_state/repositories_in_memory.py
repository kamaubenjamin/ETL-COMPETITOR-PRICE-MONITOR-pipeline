"""Deterministic in-memory implementations of Document State repositories."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Iterable, TypeVar

from .contracts import (
    AuditQuery,
    DocumentQuery,
    LifecycleQuery,
    MatchingQuery,
    OrderingSpec,
    ProcessingQuery,
    ReviewQuery,
    ValidationQuery,
    WorkflowRunQuery,
)
from .errors import DocumentStateError
from .pagination import PageRequest, PageResult
from .privacy import positive_version, stable_id
from .records import (
    AuditEventRecord,
    CorrectionSummaryRecord,
    DocumentLifecycleEvent,
    DocumentRecord,
    MatchingSummaryRecord,
    PersistentRecord,
    ProcessingSnapshot,
    ReprocessPlanRecord,
    ReviewReferenceRecord,
    ValidationIssueRecord,
    WorkflowRunRecord,
)


RecordT = TypeVar("RecordT", bound=PersistentRecord)
QueryT = TypeVar("QueryT")


@dataclass(slots=True)
class _State:
    available: bool = True
    lock: RLock = field(default_factory=RLock)
    documents: dict[str, DocumentRecord] = field(default_factory=dict)
    lifecycle: dict[str, DocumentLifecycleEvent] = field(default_factory=dict)
    processing: dict[str, ProcessingSnapshot] = field(default_factory=dict)
    validation: dict[str, ValidationIssueRecord] = field(default_factory=dict)
    matching: dict[str, MatchingSummaryRecord] = field(default_factory=dict)
    reviews: dict[str, ReviewReferenceRecord] = field(default_factory=dict)
    corrections: dict[str, CorrectionSummaryRecord] = field(default_factory=dict)
    reprocess: dict[str, ReprocessPlanRecord] = field(default_factory=dict)
    workflow_runs: dict[str, WorkflowRunRecord] = field(default_factory=dict)
    audit: dict[str, AuditEventRecord] = field(default_factory=dict)
    idempotency: dict[str, dict[str, str]] = field(default_factory=dict)


def _ensure_available(state: _State) -> None:
    if not state.available:
        raise DocumentStateError("source_unavailable")


def _read_id(value: Any, field_name: str) -> str:
    try:
        return stable_id(value, field_name)
    except ValueError:
        raise DocumentStateError("invalid_query", field=field_name) from None


def _write_id(value: Any, field_name: str) -> str:
    try:
        return stable_id(value, field_name)
    except ValueError:
        raise DocumentStateError("invalid_record", field=field_name) from None


def _ensure_page(page: Any) -> PageRequest:
    if not isinstance(page, PageRequest):
        raise DocumentStateError("invalid_query", field="page")
    return page


def _ensure_query(query: Any, expected: type[QueryT]) -> QueryT:
    if not isinstance(query, expected):
        raise DocumentStateError("invalid_query", field="query")
    return query


def _ensure_record(record: Any, expected: type[RecordT]) -> RecordT:
    if type(record) is not expected:
        raise DocumentStateError("invalid_record", field="record")
    try:
        return expected(**record.to_dict())
    except (TypeError, ValueError):
        raise DocumentStateError("invalid_record", field="record") from None


def _ordered(records: Iterable[RecordT], ordering: OrderingSpec) -> list[RecordT]:
    result = list(records)
    for field_name, direction in reversed(tuple(zip(ordering.fields, ordering.directions))):
        result.sort(key=lambda item, name=field_name: getattr(item, name), reverse=direction == "desc")
    return result


def _page(records: Iterable[RecordT], page: PageRequest, ordering: OrderingSpec) -> PageResult[RecordT]:
    safe_page = _ensure_page(page)
    ordered = _ordered(records, ordering)
    return PageResult(
        items=tuple(ordered[safe_page.offset : safe_page.offset + safe_page.limit]),
        total=len(ordered),
        limit=safe_page.limit,
        offset=safe_page.offset,
    )


def _get(state: _State, records: dict[str, RecordT], record_id: Any, field_name: str) -> RecordT:
    safe_id = _read_id(record_id, field_name)
    with state.lock:
        _ensure_available(state)
        try:
            return records[safe_id]
        except KeyError:
            raise DocumentStateError("not_found") from None


def _create(
    state: _State,
    records: dict[str, RecordT],
    record: Any,
    expected_type: type[RecordT],
    id_field: str,
) -> RecordT:
    safe_record = _ensure_record(record, expected_type)
    record_id = getattr(safe_record, id_field)
    if getattr(safe_record, "version", 1) != 1:
        raise DocumentStateError("invalid_record", field="version")
    with state.lock:
        _ensure_available(state)
        if record_id in records:
            raise DocumentStateError("conflict")
        records[record_id] = safe_record
        return safe_record


def _update(
    state: _State,
    records: dict[str, RecordT],
    record: Any,
    expected_type: type[RecordT],
    id_field: str,
    expected_version: Any,
) -> RecordT:
    safe_record = _ensure_record(record, expected_type)
    try:
        safe_version = positive_version(expected_version)
    except ValueError:
        raise DocumentStateError("invalid_record", field="expected_version") from None
    record_id = getattr(safe_record, id_field)
    with state.lock:
        _ensure_available(state)
        current = records.get(record_id)
        if current is None:
            raise DocumentStateError("not_found")
        if getattr(current, "version") != safe_version or getattr(safe_record, "version") != safe_version + 1:
            raise DocumentStateError("conflict")
        records[record_id] = safe_record
        return safe_record


def _append(
    state: _State,
    collection_name: str,
    records: dict[str, RecordT],
    record: Any,
    expected_type: type[RecordT],
    id_field: str,
    idempotency_key: Any,
) -> RecordT:
    safe_record = _ensure_record(record, expected_type)
    safe_key = _write_id(idempotency_key, "idempotency_key")
    record_id = getattr(safe_record, id_field)
    with state.lock:
        _ensure_available(state)
        key_index = state.idempotency.setdefault(collection_name, {})
        existing_id = key_index.get(safe_key)
        if existing_id is not None:
            existing = records[existing_id]
            if existing_id == record_id and existing == safe_record:
                return existing
            raise DocumentStateError("conflict")
        if record_id in records:
            raise DocumentStateError("conflict")
        records[record_id] = safe_record
        key_index[safe_key] = record_id
        return safe_record


class InMemoryDocumentStateReader:
    """Read-only view over deterministic in-memory document state."""

    def __init__(self, state: _State) -> None:
        self.__state = state

    def get_document(self, document_id: str, *, tenant_id: str | None = None) -> DocumentRecord:
        record = _get(self.__state, self.__state.documents, document_id, "document_id")
        if tenant_id is not None:
            try:
                safe_tenant = stable_id(tenant_id, "tenant_id")
            except ValueError:
                raise DocumentStateError("invalid_query", field="tenant_id") from None
            if record.tenant_id != safe_tenant:
                raise DocumentStateError("not_found")
        return record

    def list_documents(self, query: DocumentQuery, page: PageRequest) -> PageResult[DocumentRecord]:
        safe_query = _ensure_query(query, DocumentQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.documents.values())
        records = tuple(
            item for item in records
            if (safe_query.status is None or item.status == safe_query.status)
            and (safe_query.document_type is None or item.document_type == safe_query.document_type)
            and (safe_query.tenant_id is None or item.tenant_id == safe_query.tenant_id)
        )
        return _page(records, page, DocumentRecord.ORDERING)

    def list_lifecycle_events(self, document_id: str, query: LifecycleQuery, page: PageRequest) -> PageResult[DocumentLifecycleEvent]:
        safe_id = _read_id(document_id, "document_id")
        safe_query = _ensure_query(query, LifecycleQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.lifecycle.values())
        records = tuple(item for item in records if item.document_id == safe_id and (safe_query.status is None or item.status == safe_query.status))
        return _page(records, page, DocumentLifecycleEvent.ORDERING)

    def get_processing_snapshot(self, snapshot_id: str) -> ProcessingSnapshot:
        return _get(self.__state, self.__state.processing, snapshot_id, "snapshot_id")

    def list_processing_snapshots(self, document_id: str, query: ProcessingQuery, page: PageRequest) -> PageResult[ProcessingSnapshot]:
        safe_id = _read_id(document_id, "document_id")
        safe_query = _ensure_query(query, ProcessingQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.processing.values())
        records = tuple(
            item for item in records
            if item.document_id == safe_id
            and (safe_query.status is None or item.status == safe_query.status)
            and (safe_query.workflow_run_id is None or item.workflow_run_id == safe_query.workflow_run_id)
        )
        return _page(records, page, ProcessingSnapshot.ORDERING)

    def get_validation_issue(self, issue_id: str) -> ValidationIssueRecord:
        return _get(self.__state, self.__state.validation, issue_id, "issue_id")

    def list_validation_issues(self, document_id: str, query: ValidationQuery, page: PageRequest) -> PageResult[ValidationIssueRecord]:
        safe_id = _read_id(document_id, "document_id")
        safe_query = _ensure_query(query, ValidationQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.validation.values())
        records = tuple(
            item for item in records
            if item.document_id == safe_id
            and (safe_query.severity is None or item.severity == safe_query.severity)
            and (safe_query.rule_id is None or item.rule_id == safe_query.rule_id)
        )
        return _page(records, page, ValidationIssueRecord.ORDERING)

    def get_matching_summary(self, match_id: str) -> MatchingSummaryRecord:
        return _get(self.__state, self.__state.matching, match_id, "match_id")

    def list_matching_summaries(self, document_id: str, query: MatchingQuery, page: PageRequest) -> PageResult[MatchingSummaryRecord]:
        safe_id = _read_id(document_id, "document_id")
        safe_query = _ensure_query(query, MatchingQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.matching.values())
        records = tuple(
            item for item in records
            if item.document_id == safe_id
            and (safe_query.status is None or item.status == safe_query.status)
            and (safe_query.entity_type is None or item.entity_type == safe_query.entity_type)
        )
        return _page(records, page, MatchingSummaryRecord.ORDERING)

    def get_review_reference(self, review_case_id: str) -> ReviewReferenceRecord:
        return _get(self.__state, self.__state.reviews, review_case_id, "review_case_id")

    def list_review_references(self, query: ReviewQuery, page: PageRequest) -> PageResult[ReviewReferenceRecord]:
        safe_query = _ensure_query(query, ReviewQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.reviews.values())
        records = tuple(
            item for item in records
            if (safe_query.status is None or item.status == safe_query.status)
            and (safe_query.priority is None or item.priority == safe_query.priority)
        )
        return _page(records, page, ReviewReferenceRecord.ORDERING)

    def get_correction_summary(self, correction_id: str) -> CorrectionSummaryRecord:
        return _get(self.__state, self.__state.corrections, correction_id, "correction_id")

    def list_correction_summaries(self, review_case_id: str, page: PageRequest) -> PageResult[CorrectionSummaryRecord]:
        safe_id = _read_id(review_case_id, "review_case_id")
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(item for item in self.__state.corrections.values() if item.review_case_id == safe_id)
        return _page(records, page, CorrectionSummaryRecord.ORDERING)

    def get_reprocess_plan(self, plan_id: str) -> ReprocessPlanRecord:
        return _get(self.__state, self.__state.reprocess, plan_id, "plan_id")

    def list_reprocess_plans(self, review_case_id: str | None, page: PageRequest) -> PageResult[ReprocessPlanRecord]:
        safe_id = None if review_case_id is None else _read_id(review_case_id, "review_case_id")
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.reprocess.values())
        if safe_id is not None:
            records = tuple(item for item in records if item.review_case_id == safe_id)
        return _page(records, page, ReprocessPlanRecord.ORDERING)

    def get_workflow_run(self, run_id: str) -> WorkflowRunRecord:
        return _get(self.__state, self.__state.workflow_runs, run_id, "run_id")

    def list_workflow_runs(self, query: WorkflowRunQuery, page: PageRequest) -> PageResult[WorkflowRunRecord]:
        safe_query = _ensure_query(query, WorkflowRunQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.workflow_runs.values())
        records = tuple(
            item for item in records
            if (safe_query.status is None or item.status == safe_query.status)
            and (safe_query.workflow_name is None or item.workflow_name == safe_query.workflow_name)
        )
        return _page(records, page, WorkflowRunRecord.ORDERING)

    def get_audit_event(self, event_id: str) -> AuditEventRecord:
        return _get(self.__state, self.__state.audit, event_id, "event_id")

    def list_audit_events(self, query: AuditQuery, page: PageRequest) -> PageResult[AuditEventRecord]:
        safe_query = _ensure_query(query, AuditQuery)
        with self.__state.lock:
            _ensure_available(self.__state)
            records = tuple(self.__state.audit.values())
        records = tuple(
            item for item in records
            if (safe_query.event_type is None or item.event_type == safe_query.event_type)
            and (safe_query.document_id is None or item.document_id == safe_query.document_id)
            and (safe_query.review_case_id is None or item.review_case_id == safe_query.review_case_id)
        )
        return _page(records, page, AuditEventRecord.ORDERING)


class InMemoryDocumentStateWriter:
    """Write-only view over deterministic in-memory document state."""

    def __init__(self, state: _State) -> None:
        self.__state = state

    def create_document(self, record: DocumentRecord) -> DocumentRecord:
        return _create(self.__state, self.__state.documents, record, DocumentRecord, "document_id")

    def update_document(self, record: DocumentRecord, *, expected_version: int) -> DocumentRecord:
        return _update(self.__state, self.__state.documents, record, DocumentRecord, "document_id", expected_version)

    def append_lifecycle_event(self, record: DocumentLifecycleEvent, *, idempotency_key: str) -> DocumentLifecycleEvent:
        return _append(self.__state, "lifecycle", self.__state.lifecycle, record, DocumentLifecycleEvent, "event_id", idempotency_key)

    def create_processing_snapshot(self, record: ProcessingSnapshot) -> ProcessingSnapshot:
        return _create(self.__state, self.__state.processing, record, ProcessingSnapshot, "snapshot_id")

    def update_processing_snapshot(self, record: ProcessingSnapshot, *, expected_version: int) -> ProcessingSnapshot:
        return _update(self.__state, self.__state.processing, record, ProcessingSnapshot, "snapshot_id", expected_version)

    def append_validation_issue(self, record: ValidationIssueRecord, *, idempotency_key: str) -> ValidationIssueRecord:
        return _append(self.__state, "validation", self.__state.validation, record, ValidationIssueRecord, "issue_id", idempotency_key)

    def append_matching_summary(self, record: MatchingSummaryRecord, *, idempotency_key: str) -> MatchingSummaryRecord:
        return _append(self.__state, "matching", self.__state.matching, record, MatchingSummaryRecord, "match_id", idempotency_key)

    def create_review_reference(self, record: ReviewReferenceRecord) -> ReviewReferenceRecord:
        return _create(self.__state, self.__state.reviews, record, ReviewReferenceRecord, "review_case_id")

    def update_review_reference(self, record: ReviewReferenceRecord, *, expected_version: int) -> ReviewReferenceRecord:
        return _update(self.__state, self.__state.reviews, record, ReviewReferenceRecord, "review_case_id", expected_version)

    def append_correction_summary(self, record: CorrectionSummaryRecord, *, idempotency_key: str) -> CorrectionSummaryRecord:
        return _append(self.__state, "corrections", self.__state.corrections, record, CorrectionSummaryRecord, "correction_id", idempotency_key)

    def append_reprocess_plan(self, record: ReprocessPlanRecord, *, idempotency_key: str) -> ReprocessPlanRecord:
        return _append(self.__state, "reprocess", self.__state.reprocess, record, ReprocessPlanRecord, "plan_id", idempotency_key)

    def create_workflow_run(self, record: WorkflowRunRecord) -> WorkflowRunRecord:
        return _create(self.__state, self.__state.workflow_runs, record, WorkflowRunRecord, "run_id")

    def update_workflow_run(self, record: WorkflowRunRecord, *, expected_version: int) -> WorkflowRunRecord:
        return _update(self.__state, self.__state.workflow_runs, record, WorkflowRunRecord, "run_id", expected_version)

    def append_audit_event(self, record: AuditEventRecord, *, idempotency_key: str) -> AuditEventRecord:
        return _append(self.__state, "audit", self.__state.audit, record, AuditEventRecord, "event_id", idempotency_key)


class InMemoryDocumentStateRepositories:
    """Own shared state while exposing strictly separated read and write views."""

    def __init__(self, *, source_available: bool = True) -> None:
        if not isinstance(source_available, bool):
            raise ValueError("source_available must be a boolean")
        state = _State(available=source_available)
        self.reader = InMemoryDocumentStateReader(state)
        self.writer = InMemoryDocumentStateWriter(state)
