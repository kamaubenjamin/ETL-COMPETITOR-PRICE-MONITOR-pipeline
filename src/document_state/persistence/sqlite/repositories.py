"""SQLite implementations of the persistence-neutral Document State ports."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, TypeVar

from ...contracts import (
    AuditQuery, DocumentQuery, LifecycleQuery, MatchingQuery, OrderingSpec,
    ProcessingQuery, ReviewQuery, ValidationQuery, WorkflowRunQuery, query_to_dict,
)
from ...errors import DocumentStateError
from ...pagination import PageRequest, PageResult
from ...privacy import positive_version, stable_id
from ...records import (
    AuditEventRecord, CorrectionSummaryRecord, DocumentLifecycleEvent,
    DocumentRecord, MatchingSummaryRecord, PersistentRecord, ProcessingSnapshot,
    ReprocessPlanRecord, ReviewReferenceRecord, ValidationIssueRecord,
    WorkflowRunRecord,
)
from ..config import PersistenceConfig
from ..errors import PersistenceError
from .connection import SQLiteConnectionFactory
from .mappers import record_columns, record_hash, record_values, row_to_record, validate_record
from .migrations import apply_migrations


RecordT = TypeVar("RecordT", bound=PersistentRecord)
QueryT = TypeVar("QueryT")


@dataclass(frozen=True, slots=True)
class _Table:
    name: str
    record_type: type[PersistentRecord]
    id_field: str
    mutable: bool = False


DOCUMENTS = _Table("documents", DocumentRecord, "document_id", True)
LIFECYCLE = _Table("document_lifecycle_events", DocumentLifecycleEvent, "event_id")
PROCESSING = _Table("processing_snapshots", ProcessingSnapshot, "snapshot_id", True)
VALIDATION = _Table("validation_issues", ValidationIssueRecord, "issue_id")
MATCHING = _Table("matching_summaries", MatchingSummaryRecord, "match_id")
REVIEWS = _Table("review_summaries", ReviewReferenceRecord, "review_case_id", True)
CORRECTIONS = _Table("correction_summaries", CorrectionSummaryRecord, "correction_id")
REPROCESS = _Table("reprocess_plans", ReprocessPlanRecord, "plan_id")
WORKFLOWS = _Table("workflow_runs", WorkflowRunRecord, "run_id", True)
AUDIT = _Table("audit_events", AuditEventRecord, "event_id")


def _read_id(value: Any, field: str) -> str:
    try:
        return stable_id(value, field)
    except ValueError:
        raise DocumentStateError("invalid_query", field=field) from None


def _idempotency_key(value: Any) -> str:
    try:
        return stable_id(value, "idempotency_key")
    except ValueError:
        raise DocumentStateError("invalid_record", field="idempotency_key") from None


def _page(value: Any) -> PageRequest:
    if not isinstance(value, PageRequest):
        raise DocumentStateError("invalid_query", field="page")
    return value


def _query(value: Any, expected: type[QueryT]) -> QueryT:
    if not isinstance(value, expected):
        raise DocumentStateError("invalid_query", field="query")
    return value


def _where(filters: dict[str, Any]) -> tuple[str, tuple[Any, ...]]:
    active = tuple((key, value) for key, value in filters.items() if value is not None)
    if not active:
        return "", ()
    return " WHERE " + " AND ".join(f"{key} = ?" for key, _ in active), tuple(value for _, value in active)


def _order(ordering: OrderingSpec) -> str:
    return ", ".join(
        f"{field} {'DESC' if direction == 'desc' else 'ASC'}"
        for field, direction in zip(ordering.fields, ordering.directions)
    )


class SQLiteDocumentStateReader:
    """Read-only SQLite view implementing all Document State read ports."""

    def __init__(self, factory: SQLiteConnectionFactory) -> None:
        self.__factory = factory

    def _get(self, table: _Table, value: Any, *, tenant_id: str | None = None) -> Any:
        safe_id = _read_id(value, table.id_field)
        safe_tenant = None if tenant_id is None else _read_id(tenant_id, "tenant_id")
        tenant_clause = "" if safe_tenant is None else " AND tenant_id = ?"
        parameters = (safe_id,) if safe_tenant is None else (safe_id, safe_tenant)
        try:
            with self.__factory.transaction() as connection:
                row = connection.execute(
                    f"SELECT * FROM {table.name} WHERE {table.id_field} = ?{tenant_clause}", parameters
                ).fetchone()
        except PersistenceError:
            raise DocumentStateError("source_unavailable") from None
        if row is None:
            raise DocumentStateError("not_found")
        return row_to_record(row, table.record_type)

    def _list(
        self,
        table: _Table,
        page: PageRequest,
        filters: dict[str, Any],
    ) -> PageResult[Any]:
        safe_page = _page(page)
        where, parameters = _where(filters)
        ordering = table.record_type.ORDERING
        try:
            with self.__factory.transaction() as connection:
                total = connection.execute(
                    f"SELECT COUNT(*) FROM {table.name}{where}", parameters
                ).fetchone()[0]
                rows = connection.execute(
                    f"SELECT * FROM {table.name}{where} ORDER BY {_order(ordering)} LIMIT ? OFFSET ?",
                    parameters + (safe_page.limit, safe_page.offset),
                ).fetchall()
        except PersistenceError:
            raise DocumentStateError("source_unavailable") from None
        return PageResult(
            items=tuple(row_to_record(row, table.record_type) for row in rows),
            total=total,
            limit=safe_page.limit,
            offset=safe_page.offset,
        )

    def get_document(self, document_id: str, *, tenant_id: str | None = None) -> DocumentRecord:
        return self._get(DOCUMENTS, document_id, tenant_id=tenant_id)

    def list_documents(self, query: DocumentQuery, page: PageRequest) -> PageResult[DocumentRecord]:
        return self._list(DOCUMENTS, page, query_to_dict(_query(query, DocumentQuery)))

    def list_lifecycle_events(self, document_id: str, query: LifecycleQuery, page: PageRequest) -> PageResult[DocumentLifecycleEvent]:
        filters = query_to_dict(_query(query, LifecycleQuery))
        filters["document_id"] = _read_id(document_id, "document_id")
        return self._list(LIFECYCLE, page, filters)

    def get_processing_snapshot(self, snapshot_id: str) -> ProcessingSnapshot:
        return self._get(PROCESSING, snapshot_id)

    def list_processing_snapshots(self, document_id: str, query: ProcessingQuery, page: PageRequest) -> PageResult[ProcessingSnapshot]:
        filters = query_to_dict(_query(query, ProcessingQuery))
        filters["document_id"] = _read_id(document_id, "document_id")
        return self._list(PROCESSING, page, filters)

    def get_validation_issue(self, issue_id: str) -> ValidationIssueRecord:
        return self._get(VALIDATION, issue_id)

    def list_validation_issues(self, document_id: str, query: ValidationQuery, page: PageRequest) -> PageResult[ValidationIssueRecord]:
        filters = query_to_dict(_query(query, ValidationQuery))
        filters["document_id"] = _read_id(document_id, "document_id")
        return self._list(VALIDATION, page, filters)

    def get_matching_summary(self, match_id: str) -> MatchingSummaryRecord:
        return self._get(MATCHING, match_id)

    def list_matching_summaries(self, document_id: str, query: MatchingQuery, page: PageRequest) -> PageResult[MatchingSummaryRecord]:
        filters = query_to_dict(_query(query, MatchingQuery))
        filters["document_id"] = _read_id(document_id, "document_id")
        return self._list(MATCHING, page, filters)

    def get_review_reference(self, review_case_id: str) -> ReviewReferenceRecord:
        return self._get(REVIEWS, review_case_id)

    def list_review_references(self, query: ReviewQuery, page: PageRequest) -> PageResult[ReviewReferenceRecord]:
        return self._list(REVIEWS, page, query_to_dict(_query(query, ReviewQuery)))

    def get_correction_summary(self, correction_id: str) -> CorrectionSummaryRecord:
        return self._get(CORRECTIONS, correction_id)

    def list_correction_summaries(self, review_case_id: str, page: PageRequest) -> PageResult[CorrectionSummaryRecord]:
        return self._list(CORRECTIONS, page, {"review_case_id": _read_id(review_case_id, "review_case_id")})

    def get_reprocess_plan(self, plan_id: str) -> ReprocessPlanRecord:
        return self._get(REPROCESS, plan_id)

    def list_reprocess_plans(self, review_case_id: str | None, page: PageRequest) -> PageResult[ReprocessPlanRecord]:
        safe_id = None if review_case_id is None else _read_id(review_case_id, "review_case_id")
        return self._list(REPROCESS, page, {"review_case_id": safe_id})

    def get_workflow_run(self, run_id: str) -> WorkflowRunRecord:
        return self._get(WORKFLOWS, run_id)

    def list_workflow_runs(self, query: WorkflowRunQuery, page: PageRequest) -> PageResult[WorkflowRunRecord]:
        return self._list(WORKFLOWS, page, query_to_dict(_query(query, WorkflowRunQuery)))

    def get_audit_event(self, event_id: str) -> AuditEventRecord:
        return self._get(AUDIT, event_id)

    def list_audit_events(self, query: AuditQuery, page: PageRequest) -> PageResult[AuditEventRecord]:
        return self._list(AUDIT, page, query_to_dict(_query(query, AuditQuery)))


class SQLiteDocumentStateWriter:
    """Write-only SQLite view implementing all Document State write ports."""

    def __init__(self, factory: SQLiteConnectionFactory) -> None:
        self.__factory = factory

    def _insert(self, table: _Table, record: Any) -> Any:
        safe = validate_record(record, table.record_type)
        if table.mutable and getattr(safe, "version") != 1:
            raise DocumentStateError("invalid_record", field="version")
        columns = record_columns(table.record_type)
        placeholders = ", ".join("?" for _ in columns)
        try:
            with self.__factory.transaction(write=True) as connection:
                connection.execute(
                    f"INSERT INTO {table.name} ({', '.join(columns)}) VALUES ({placeholders})",
                    record_values(safe),
                )
        except PersistenceError:
            raise DocumentStateError("source_unavailable") from None
        except sqlite3.IntegrityError:
            raise DocumentStateError("conflict") from None
        return safe

    def _update(self, table: _Table, record: Any, expected_version: Any) -> Any:
        safe = validate_record(record, table.record_type)
        try:
            expected = positive_version(expected_version)
        except ValueError:
            raise DocumentStateError("invalid_record", field="expected_version") from None
        if safe.version != expected + 1:
            raise DocumentStateError("conflict")
        columns = record_columns(table.record_type)
        assignments = ", ".join(f"{column} = ?" for column in columns if column != table.id_field)
        values = tuple(
            value for column, value in zip(columns, record_values(safe)) if column != table.id_field
        )
        record_id = getattr(safe, table.id_field)
        try:
            with self.__factory.transaction(write=True) as connection:
                cursor = connection.execute(
                    f"UPDATE {table.name} SET {assignments} WHERE {table.id_field} = ? AND version = ?",
                    values + (record_id, expected),
                )
                if cursor.rowcount == 0:
                    exists = connection.execute(
                        f"SELECT 1 FROM {table.name} WHERE {table.id_field} = ?", (record_id,)
                    ).fetchone()
                    raise DocumentStateError("conflict" if exists else "not_found")
        except DocumentStateError:
            raise
        except PersistenceError:
            raise DocumentStateError("source_unavailable") from None
        return safe

    def _append(self, table: _Table, record: Any, idempotency_key: Any) -> Any:
        safe = validate_record(record, table.record_type)
        key = _idempotency_key(idempotency_key)
        digest = record_hash(safe)
        columns = record_columns(table.record_type) + ("idempotency_key", "content_hash")
        placeholders = ", ".join("?" for _ in columns)
        try:
            with self.__factory.transaction(write=True) as connection:
                previous = connection.execute(
                    f"SELECT * FROM {table.name} WHERE idempotency_key = ?", (key,)
                ).fetchone()
                if previous is not None:
                    if previous[table.id_field] == getattr(safe, table.id_field) and previous["content_hash"] == digest:
                        return row_to_record(previous, table.record_type)
                    raise DocumentStateError("conflict")
                connection.execute(
                    f"INSERT INTO {table.name} ({', '.join(columns)}) VALUES ({placeholders})",
                    record_values(safe) + (key, digest),
                )
        except DocumentStateError:
            raise
        except sqlite3.IntegrityError:
            raise DocumentStateError("conflict") from None
        except PersistenceError:
            raise DocumentStateError("source_unavailable") from None
        return safe

    def create_document(self, record: DocumentRecord) -> DocumentRecord:
        return self._insert(DOCUMENTS, record)

    def update_document(self, record: DocumentRecord, *, expected_version: int) -> DocumentRecord:
        return self._update(DOCUMENTS, record, expected_version)

    def append_lifecycle_event(self, record: DocumentLifecycleEvent, *, idempotency_key: str) -> DocumentLifecycleEvent:
        return self._append(LIFECYCLE, record, idempotency_key)

    def create_processing_snapshot(self, record: ProcessingSnapshot) -> ProcessingSnapshot:
        return self._insert(PROCESSING, record)

    def update_processing_snapshot(self, record: ProcessingSnapshot, *, expected_version: int) -> ProcessingSnapshot:
        return self._update(PROCESSING, record, expected_version)

    def append_validation_issue(self, record: ValidationIssueRecord, *, idempotency_key: str) -> ValidationIssueRecord:
        return self._append(VALIDATION, record, idempotency_key)

    def append_matching_summary(self, record: MatchingSummaryRecord, *, idempotency_key: str) -> MatchingSummaryRecord:
        return self._append(MATCHING, record, idempotency_key)

    def create_review_reference(self, record: ReviewReferenceRecord) -> ReviewReferenceRecord:
        return self._insert(REVIEWS, record)

    def update_review_reference(self, record: ReviewReferenceRecord, *, expected_version: int) -> ReviewReferenceRecord:
        return self._update(REVIEWS, record, expected_version)

    def append_correction_summary(self, record: CorrectionSummaryRecord, *, idempotency_key: str) -> CorrectionSummaryRecord:
        return self._append(CORRECTIONS, record, idempotency_key)

    def append_reprocess_plan(self, record: ReprocessPlanRecord, *, idempotency_key: str) -> ReprocessPlanRecord:
        return self._append(REPROCESS, record, idempotency_key)

    def create_workflow_run(self, record: WorkflowRunRecord) -> WorkflowRunRecord:
        return self._insert(WORKFLOWS, record)

    def update_workflow_run(self, record: WorkflowRunRecord, *, expected_version: int) -> WorkflowRunRecord:
        return self._update(WORKFLOWS, record, expected_version)

    def append_audit_event(self, record: AuditEventRecord, *, idempotency_key: str) -> AuditEventRecord:
        return self._append(AUDIT, record, idempotency_key)


class SQLiteDocumentStateRepositories:
    """Own configuration while exposing separate durable read and write views."""

    def __init__(self, config: PersistenceConfig, *, apply_schema: bool = True) -> None:
        factory = SQLiteConnectionFactory(config)
        if apply_schema:
            apply_migrations(factory)
        self.reader = SQLiteDocumentStateReader(factory)
        self.writer = SQLiteDocumentStateWriter(factory)
