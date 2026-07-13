"""Internal workflow-run Document State writer."""

from __future__ import annotations

from ..errors import DocumentStateError
from ..records import WorkflowRunRecord
from ..repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
from ._service_support import append_audit, invalid, repository_failure, result
from .commands import WriteAuditEventCommand, WriteWorkflowRunCommand
from .errors import DocumentStateWriterError


_WORKFLOW_AUDIT_TYPES = frozenset({"workflow_run_completed", "workflow_run_failed"})
_FINAL_WORKFLOW_STATUSES = frozenset({"succeeded", "failed"})


class WorkflowDocumentStateWriter:
    def __init__(self, reader: DocumentStateReadRepositories, writer: DocumentStateWriteRepositories) -> None:
        self.__reader = reader
        self.__writer = writer

    def write_workflow_run(self, command: WriteWorkflowRunCommand):
        operation = "write_workflow_run"
        if not isinstance(command, WriteWorkflowRunCommand) or command.status not in _FINAL_WORKFLOW_STATUSES:
            return invalid(operation)
        try:
            version = 1 if command.expected_version is None else command.expected_version + 1
            record = WorkflowRunRecord(
                command.run_id,
                command.workflow_name,
                command.status,
                command.started_at,
                command.created_at,
                command.updated_at,
                command.completed_at,
                command.duration_ms,
                command.current_stage,
                command.stage_count,
                command.succeeded_stage_count,
                command.failed_stage_count,
                version,
                command.metadata,
            )
            if command.expected_version is None:
                self.__writer.create_workflow_run(record)
            else:
                self.__writer.update_workflow_run(record, expected_version=command.expected_version)
            return result("success", operation, record_ids=(record.run_id,))
        except DocumentStateError as error:
            if error.code != "conflict":
                return repository_failure(error, operation, versioned=command.expected_version is not None)
            try:
                existing = self.__reader.get_workflow_run(command.run_id)
            except DocumentStateError as read_error:
                return repository_failure(read_error, operation, versioned=command.expected_version is not None)
            if existing == record:
                return result("skipped_idempotent", operation, record_ids=(record.run_id,))
            return result("conflict", operation, error_code="version_conflict" if command.expected_version is not None else "invalid_command")
        except (DocumentStateWriterError, TypeError, ValueError):
            return invalid(operation)
        except Exception:
            return result("failed", operation, error_code="internal_error")

    def write_audit_event(self, command: WriteAuditEventCommand):
        return append_audit(self.__writer, command, allowed_event_types=_WORKFLOW_AUDIT_TYPES)
