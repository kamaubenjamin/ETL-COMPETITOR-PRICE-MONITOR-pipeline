"""Deterministic process-local export attempt/result repositories."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from typing import Any

from .attempts import ExportAttempt
from .contracts import positive_integer, utc_timestamp
from .idempotency import ExportIdempotencyKey
from .queries import ExportAttemptQuery, ExportPage, ExportPageRequest, validate_page, validate_query_id
from .repository_errors import ExportRepositoryError
from .repositories import ExportRepositoryReader, ExportRepositoryWriter
from .results import ExportResult
from .statuses import ExportOperationStatus


ACTIVE_EXPORT_STATUSES = frozenset(
    {
        ExportOperationStatus.PREPARING.value,
        ExportOperationStatus.QUEUED.value,
        ExportOperationStatus.EXPORTING.value,
    }
)
TERMINAL_EXPORT_STATUSES = frozenset(
    {
        ExportOperationStatus.NOT_READY.value,
        ExportOperationStatus.EXPORTED.value,
        ExportOperationStatus.FAILED.value,
        ExportOperationStatus.CANCELLED.value,
        ExportOperationStatus.DUPLICATE_PREVENTED.value,
    }
)
_ALLOWED_STATUS_TRANSITIONS = {
    ExportOperationStatus.READY.value: frozenset(
        {
            ExportOperationStatus.PREPARING.value,
            ExportOperationStatus.CANCELLED.value,
            ExportOperationStatus.DUPLICATE_PREVENTED.value,
        }
    ),
    ExportOperationStatus.PREPARING.value: frozenset(
        {
            ExportOperationStatus.QUEUED.value,
            ExportOperationStatus.EXPORTING.value,
            ExportOperationStatus.FAILED.value,
            ExportOperationStatus.CANCELLED.value,
            ExportOperationStatus.DUPLICATE_PREVENTED.value,
        }
    ),
    ExportOperationStatus.QUEUED.value: frozenset(
        {
            ExportOperationStatus.EXPORTING.value,
            ExportOperationStatus.FAILED.value,
            ExportOperationStatus.CANCELLED.value,
            ExportOperationStatus.DUPLICATE_PREVENTED.value,
        }
    ),
    ExportOperationStatus.EXPORTING.value: frozenset(
        {
            ExportOperationStatus.EXPORTED.value,
            ExportOperationStatus.FAILED.value,
            ExportOperationStatus.CANCELLED.value,
        }
    ),
}


@dataclass(slots=True)
class _ExportStoreState:
    attempts: dict[str, ExportAttempt] = field(default_factory=dict)
    attempt_by_idempotency_key: dict[str, str] = field(default_factory=dict)
    results: dict[str, ExportResult] = field(default_factory=dict)
    result_by_attempt: dict[str, str] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)


def _idempotency_value(value: Any) -> str:
    if isinstance(value, ExportIdempotencyKey):
        return value.value
    try:
        return ExportIdempotencyKey(value).value
    except (TypeError, ValueError):
        raise ExportRepositoryError("invalid_query", field="idempotency_key") from None


def _page(items: list[Any], page: ExportPageRequest) -> ExportPage[Any]:
    total = len(items)
    return ExportPage(tuple(items[page.offset : page.offset + page.limit]), total, page.limit, page.offset)


class InMemoryExportRepositoryReader:
    def __init__(self, state: _ExportStoreState) -> None:
        self.__state = state

    def get_attempt(self, attempt_id: str) -> ExportAttempt:
        safe_id = validate_query_id(attempt_id, "attempt_id")
        with self.__state.lock:
            try:
                return self.__state.attempts[safe_id]
            except KeyError:
                raise ExportRepositoryError("not_found", field="attempt_id") from None

    def get_attempt_by_idempotency_key(self, idempotency_key: ExportIdempotencyKey | str) -> ExportAttempt:
        safe_key = _idempotency_value(idempotency_key)
        with self.__state.lock:
            attempt_id = self.__state.attempt_by_idempotency_key.get(safe_key)
            if attempt_id is None:
                raise ExportRepositoryError("not_found", field="idempotency_key")
            return self.__state.attempts[attempt_id]

    def list_attempts(
        self,
        query: ExportAttemptQuery | None = None,
        page: ExportPageRequest | None = None,
    ) -> ExportPage[ExportAttempt]:
        if query is None:
            query = ExportAttemptQuery()
        if not isinstance(query, ExportAttemptQuery):
            raise ExportRepositoryError("invalid_query", field="query")
        safe_page = validate_page(page)
        with self.__state.lock:
            items = [
                attempt
                for attempt in self.__state.attempts.values()
                if (query.document_id is None or attempt.document_id == query.document_id)
                and (query.tenant_id is None or attempt.tenant_id == query.tenant_id)
                and (query.target_id is None or attempt.target.target_id == query.target_id)
                and (query.status is None or attempt.status == query.status)
            ]
            items.sort(key=lambda item: (item.created_at, item.attempt_id))
            return _page(items, safe_page)

    def list_attempts_by_document(self, document_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportAttempt]:
        return self.list_attempts(ExportAttemptQuery(document_id=validate_query_id(document_id, "document_id")), page)

    def list_attempts_by_tenant(self, tenant_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportAttempt]:
        return self.list_attempts(ExportAttemptQuery(tenant_id=validate_query_id(tenant_id, "tenant_id")), page)

    def list_attempts_by_target(self, target_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportAttempt]:
        return self.list_attempts(ExportAttemptQuery(target_id=validate_query_id(target_id, "target_id")), page)

    def list_results_by_attempt(self, attempt_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportResult]:
        safe_id = validate_query_id(attempt_id, "attempt_id")
        safe_page = validate_page(page)
        with self.__state.lock:
            items = [result for result in self.__state.results.values() if result.attempt_id == safe_id]
            items.sort(key=lambda item: (item.occurred_at, item.result_id))
            return _page(items, safe_page)

    def has_active_duplicate(
        self,
        *,
        tenant_id: str,
        document_id: str,
        target_id: str,
        idempotency_key: ExportIdempotencyKey | str,
    ) -> bool:
        safe_tenant = validate_query_id(tenant_id, "tenant_id")
        safe_document = validate_query_id(document_id, "document_id")
        safe_target = validate_query_id(target_id, "target_id")
        safe_key = _idempotency_value(idempotency_key)
        with self.__state.lock:
            attempt_id = self.__state.attempt_by_idempotency_key.get(safe_key)
            if attempt_id is None:
                return False
            attempt = self.__state.attempts[attempt_id]
            return (
                attempt.tenant_id == safe_tenant
                and attempt.document_id == safe_document
                and attempt.target.target_id == safe_target
                and attempt.status in ACTIVE_EXPORT_STATUSES
            )

    def has_active_document_target(self, *, tenant_id: str, document_id: str, target_id: str) -> bool:
        safe_tenant = validate_query_id(tenant_id, "tenant_id")
        safe_document = validate_query_id(document_id, "document_id")
        safe_target = validate_query_id(target_id, "target_id")
        with self.__state.lock:
            return any(
                attempt.tenant_id == safe_tenant
                and attempt.document_id == safe_document
                and attempt.target.target_id == safe_target
                and attempt.status in ACTIVE_EXPORT_STATUSES
                for attempt in self.__state.attempts.values()
            )


class InMemoryExportRepositoryWriter:
    def __init__(self, state: _ExportStoreState) -> None:
        self.__state = state

    def save_attempt(self, attempt: ExportAttempt) -> ExportAttempt:
        if not isinstance(attempt, ExportAttempt):
            raise ExportRepositoryError("invalid_record", field="attempt")
        with self.__state.lock:
            if attempt.attempt_id in self.__state.attempts:
                raise ExportRepositoryError("duplicate_attempt", field="attempt_id")
            if attempt.idempotency_key.value in self.__state.attempt_by_idempotency_key:
                raise ExportRepositoryError("duplicate_idempotency_key", field="idempotency_key")
            self.__state.attempts[attempt.attempt_id] = attempt
            self.__state.attempt_by_idempotency_key[attempt.idempotency_key.value] = attempt.attempt_id
            return attempt

    def save_result(self, result: ExportResult) -> ExportResult:
        if not isinstance(result, ExportResult):
            raise ExportRepositoryError("invalid_record", field="result")
        with self.__state.lock:
            attempt = self.__state.attempts.get(result.attempt_id)
            if attempt is None:
                raise ExportRepositoryError("missing_attempt", field="attempt_id")
            if result.document_id != attempt.document_id or result.target_id != attempt.target.target_id:
                raise ExportRepositoryError("invalid_record", field="result")
            if result.result_id in self.__state.results:
                raise ExportRepositoryError("conflict", field="result_id")
            if result.attempt_id in self.__state.result_by_attempt:
                raise ExportRepositoryError("terminal_result_exists", field="attempt_id")
            self.__state.results[result.result_id] = result
            self.__state.result_by_attempt[result.attempt_id] = result.result_id
            return result

    def update_attempt_status(
        self,
        attempt_id: str,
        status: ExportOperationStatus | str,
        *,
        expected_version: int,
        updated_at: str,
    ) -> ExportAttempt:
        safe_id = validate_query_id(attempt_id, "attempt_id")
        try:
            safe_status = ExportOperationStatus(status).value
            safe_version = positive_integer(expected_version, "expected_version")
            safe_updated_at = utc_timestamp(updated_at, "updated_at")
        except (TypeError, ValueError):
            raise ExportRepositoryError("invalid_record", field="status") from None
        with self.__state.lock:
            current = self.__state.attempts.get(safe_id)
            if current is None:
                raise ExportRepositoryError("not_found", field="attempt_id")
            if current.version != safe_version:
                raise ExportRepositoryError("version_conflict", field="expected_version")
            if safe_status == current.status:
                return current
            if current.status in TERMINAL_EXPORT_STATUSES or safe_status not in _ALLOWED_STATUS_TRANSITIONS.get(current.status, frozenset()):
                raise ExportRepositoryError("invalid_transition", field="status")
            updated = replace(current, status=safe_status, version=current.version + 1, updated_at=safe_updated_at)
            self.__state.attempts[safe_id] = updated
            return updated


class InMemoryExportStore:
    """Explicit in-memory composition with separate reader and writer views."""

    def __init__(self) -> None:
        state = _ExportStoreState()
        self.reader: ExportRepositoryReader = InMemoryExportRepositoryReader(state)
        self.writer: ExportRepositoryWriter = InMemoryExportRepositoryWriter(state)
