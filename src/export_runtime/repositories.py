"""Structural read/write ports for export attempt and result storage."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .attempts import ExportAttempt
from .idempotency import ExportIdempotencyKey
from .queries import ExportAttemptQuery, ExportPage, ExportPageRequest
from .results import ExportResult
from .statuses import ExportOperationStatus


@runtime_checkable
class ExportAttemptReadRepository(Protocol):
    def get_attempt(self, attempt_id: str) -> ExportAttempt: ...
    def get_attempt_by_idempotency_key(self, idempotency_key: ExportIdempotencyKey | str) -> ExportAttempt: ...
    def list_attempts(self, query: ExportAttemptQuery | None = None, page: ExportPageRequest | None = None) -> ExportPage[ExportAttempt]: ...
    def list_attempts_by_document(self, document_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportAttempt]: ...
    def list_attempts_by_tenant(self, tenant_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportAttempt]: ...
    def list_attempts_by_target(self, target_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportAttempt]: ...
    def has_active_duplicate(self, *, tenant_id: str, document_id: str, target_id: str, idempotency_key: ExportIdempotencyKey | str) -> bool: ...
    def has_active_document_target(self, *, tenant_id: str, document_id: str, target_id: str) -> bool: ...


@runtime_checkable
class ExportResultReadRepository(Protocol):
    def list_results_by_attempt(self, attempt_id: str, page: ExportPageRequest | None = None) -> ExportPage[ExportResult]: ...


@runtime_checkable
class ExportAttemptWriteRepository(Protocol):
    def save_attempt(self, attempt: ExportAttempt) -> ExportAttempt: ...
    def update_attempt_status(
        self,
        attempt_id: str,
        status: ExportOperationStatus | str,
        *,
        expected_version: int,
        updated_at: str,
    ) -> ExportAttempt: ...


@runtime_checkable
class ExportResultWriteRepository(Protocol):
    def save_result(self, result: ExportResult) -> ExportResult: ...


@runtime_checkable
class ExportRepositoryReader(ExportAttemptReadRepository, ExportResultReadRepository, Protocol):
    pass


@runtime_checkable
class ExportRepositoryWriter(ExportAttemptWriteRepository, ExportResultWriteRepository, Protocol):
    pass
