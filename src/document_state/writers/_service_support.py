"""Shared privacy-safe mechanics for internal writer services."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import DocumentStateError
from ..lifecycle import (
    LifecycleAdvancementService,
    LifecyclePolicyOutcome,
    LifecycleTransitionRequest,
    evaluate_transition,
)
from ..records import AuditEventRecord, DocumentLifecycleEvent
from ..repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
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
    reader: DocumentStateReadRepositories,
    writer: DocumentStateWriteRepositories,
    command: AppendLifecycleEventCommand,
    *,
    allowed_statuses: frozenset[str],
    lifecycle_service: LifecycleAdvancementService | None = None,
) -> WriterResult:
    operation = "append_lifecycle_event"
    if not isinstance(command, AppendLifecycleEventCommand) or command.status not in allowed_statuses:
        return invalid(operation)
    try:
        request = None
        if lifecycle_service is not None:
            try:
                current = reader.get_document(command.document_id)
            except DocumentStateError as error:
                return repository_failure(error, operation)
            request = LifecycleTransitionRequest(
                document_id=command.document_id,
                source_status=current.status,
                target_status=command.status,
                lifecycle_event_id=command.event_id,
                expected_version=current.version,
                reason_code=command.reason_code or f"{command.status}_lifecycle",
                actor_id=command.source_runtime,
                occurred_at=command.occurred_at,
                source_stage=command.source_stage,
                metadata=command.metadata,
            )
            if evaluate_transition(request).outcome == LifecyclePolicyOutcome.REJECTED.value:
                return invalid(operation)
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
        if lifecycle_service is None:
            return result("success", operation, record_ids=(record.event_id,))
        assert request is not None
        advancement = lifecycle_service.advance(request, lifecycle_event_persisted=True)
        if advancement.status in {"advanced", "no_op"}:
            return result("success", operation, record_ids=(record.event_id,))
        if advancement.status == "projection_pending":
            return result(
                "projection_pending",
                operation,
                record_ids=(record.event_id,),
                error_code="version_conflict",
            )
        if advancement.status == "conflict":
            return result("conflict", operation, record_ids=(record.event_id,), error_code="version_conflict")
        if advancement.status == "rejected":
            return result("invalid_input", operation, record_ids=(record.event_id,), error_code="invalid_command")
        error_code = "repository_unavailable" if advancement.error_code == "repository_unavailable" else "internal_error"
        return result("failed", operation, record_ids=(record.event_id,), error_code=error_code)
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
