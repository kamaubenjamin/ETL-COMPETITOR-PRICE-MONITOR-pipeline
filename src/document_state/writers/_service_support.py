"""Shared privacy-safe mechanics for internal writer services."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import DocumentStateError
from ..records import AuditEventRecord, DocumentLifecycleEvent
from ..repositories import DocumentStateWriteRepositories
from .commands import AppendLifecycleEventCommand, WriteAuditEventCommand
from .errors import DocumentStateWriterError
from .idempotency import make_idempotency_key
from .results import WriterResult


def result(
    status: str,
    operation: str,
    *,
    record_ids: tuple[str, ...] = (),
    error_code: str | None = None,
) -> WriterResult:
    message = DocumentStateWriterError(error_code).message if error_code else None
    return WriterResult(status, operation, record_ids, len(record_ids), error_code=error_code, message=message)


def invalid(operation: str) -> WriterResult:
    return result("invalid_input", operation, error_code="invalid_command")


def repository_failure(error: DocumentStateError, operation: str, *, versioned: bool = False) -> WriterResult:
    if error.code in {"invalid_record", "invalid_query", "not_found"}:
        if versioned and error.code == "not_found":
            return result("conflict", operation, error_code="version_conflict")
        return invalid(operation)
    if error.code == "conflict":
        return result("conflict", operation, error_code="version_conflict" if versioned else "invalid_command")
    if error.code == "source_unavailable":
        return result("failed", operation, error_code="repository_unavailable")
    return result("failed", operation, error_code="internal_error")


def with_committed(failure: WriterResult, operation: str, record_ids: list[str]) -> WriterResult:
    return WriterResult(
        failure.status,
        operation,
        tuple(record_ids),
        len(record_ids),
        error_code=failure.error_code,
        message=failure.message,
    )


def run_steps(operation: str, steps: tuple[Callable[[], WriterResult], ...]) -> WriterResult:
    record_ids: list[str] = []
    all_skipped = True
    for step in steps:
        step_result = step()
        if step_result.status not in {"success", "skipped_idempotent"}:
            return with_committed(step_result, operation, record_ids)
        record_ids.extend(step_result.record_ids)
        all_skipped = all_skipped and step_result.status == "skipped_idempotent"
    return result("skipped_idempotent" if all_skipped else "success", operation, record_ids=tuple(record_ids))


def append_lifecycle(
    writer: DocumentStateWriteRepositories,
    command: AppendLifecycleEventCommand,
    *,
    allowed_statuses: frozenset[str],
) -> WriterResult:
    operation = "append_lifecycle_event"
    if not isinstance(command, AppendLifecycleEventCommand) or command.status not in allowed_statuses:
        return invalid(operation)
    try:
        record = DocumentLifecycleEvent(
            command.event_id,
            command.document_id,
            command.status,
            command.occurred_at,
            command.source_runtime,
            command.source_stage,
            command.reason_code,
            command.metadata,
        )
        key = make_idempotency_key("lifecycle", command.document_id, command.source_event_id, command.status)
        writer.append_lifecycle_event(record, idempotency_key=key)
        return result("success", operation, record_ids=(record.event_id,))
    except DocumentStateError as error:
        return repository_failure(error, operation)
    except (DocumentStateWriterError, TypeError, ValueError):
        return invalid(operation)
    except Exception:
        return result("failed", operation, error_code="internal_error")


def append_audit(
    writer: DocumentStateWriteRepositories,
    command: WriteAuditEventCommand,
    *,
    allowed_event_types: frozenset[str],
) -> WriterResult:
    operation = "write_audit_event"
    if not isinstance(command, WriteAuditEventCommand) or command.event_type not in allowed_event_types:
        return invalid(operation)
    try:
        record = AuditEventRecord(
            command.event_id,
            command.event_type,
            command.actor_id,
            command.occurred_at,
            command.document_id,
            command.review_case_id,
            command.workflow_run_id,
            command.metadata,
        )
        key = make_idempotency_key("audit", command.event_id, command.source_event_id)
        writer.append_audit_event(record, idempotency_key=key)
        return result("success", operation, record_ids=(record.event_id,))
    except DocumentStateError as error:
        return repository_failure(error, operation)
    except (DocumentStateWriterError, TypeError, ValueError):
        return invalid(operation)
    except Exception:
        return result("failed", operation, error_code="internal_error")
