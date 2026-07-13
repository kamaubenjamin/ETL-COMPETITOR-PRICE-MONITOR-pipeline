"""Internal processing, validation, and matching Document State writer."""

from __future__ import annotations

from ..errors import DocumentStateError
from ..lifecycle import LifecycleAdvancementService
from ..records import MatchingSummaryRecord, ProcessingSnapshot, ValidationIssueRecord
from ..repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
from ._service_support import append_audit, append_lifecycle, invalid, repository_failure, result, with_committed
from .commands import (
    AppendLifecycleEventCommand,
    WriteAuditEventCommand,
    WriteMatchingSummariesCommand,
    WriteProcessingSnapshotCommand,
    WriteValidationIssuesCommand,
)
from .errors import DocumentStateWriterError
from .idempotency import make_idempotency_key


_PROCESSING_STAGES = frozenset({"parsing_structure", "validate_data", "matching"})
_PROCESSING_AUDIT_TYPES = frozenset({"parsing_structure_completed", "validation_completed", "matching_completed"})


class ProcessingDocumentStateWriter:
    def __init__(
        self,
        reader: DocumentStateReadRepositories,
        writer: DocumentStateWriteRepositories,
        lifecycle_service: LifecycleAdvancementService | None = None,
    ) -> None:
        if lifecycle_service is not None and not isinstance(lifecycle_service, LifecycleAdvancementService):
            raise ValueError("lifecycle_service must be a LifecycleAdvancementService")
        self.__reader = reader
        self.__writer = writer
        self.__lifecycle_service = lifecycle_service

    def append_lifecycle_event(self, command: AppendLifecycleEventCommand):
        return append_lifecycle(
            self.__reader,
            self.__writer,
            command,
            allowed_statuses=frozenset({"parsed", "validated", "matched"}),
            lifecycle_service=self.__lifecycle_service,
        )

    def write_processing_snapshot(self, command: WriteProcessingSnapshotCommand):
        operation = "write_processing_snapshot"
        if not isinstance(command, WriteProcessingSnapshotCommand) or command.stage not in _PROCESSING_STAGES:
            return invalid(operation)
        try:
            version = 1 if command.expected_version is None else command.expected_version + 1
            record = ProcessingSnapshot(
                command.snapshot_id,
                command.document_id,
                command.workflow_run_id,
                command.stage,
                command.status,
                command.started_at,
                command.updated_at,
                command.completed_at,
                command.duration_ms,
                version,
                command.metadata,
            )
            if command.expected_version is None:
                self.__writer.create_processing_snapshot(record)
            else:
                self.__writer.update_processing_snapshot(record, expected_version=command.expected_version)
            return result("success", operation, record_ids=(record.snapshot_id,))
        except DocumentStateError as error:
            if error.code != "conflict":
                return repository_failure(error, operation, versioned=command.expected_version is not None)
            try:
                existing = self.__reader.get_processing_snapshot(command.snapshot_id)
            except DocumentStateError as read_error:
                return repository_failure(read_error, operation, versioned=command.expected_version is not None)
            if existing == record:
                return result("skipped_idempotent", operation, record_ids=(record.snapshot_id,))
            return result("conflict", operation, error_code="version_conflict")
        except (DocumentStateWriterError, TypeError, ValueError):
            return invalid(operation)
        except Exception:
            return result("failed", operation, error_code="internal_error")

    def write_validation_issues(self, command: WriteValidationIssuesCommand):
        operation = "write_validation_issues"
        if not isinstance(command, WriteValidationIssuesCommand):
            return invalid(operation)
        committed: list[str] = []
        for issue in command.issues:
            try:
                record = ValidationIssueRecord(
                    issue.issue_id,
                    command.document_id,
                    command.validation_run_id,
                    issue.severity,
                    issue.field,
                    issue.rule_id,
                    issue.code,
                    issue.message,
                    issue.occurred_at,
                    issue.metadata,
                )
                key = make_idempotency_key("validation", command.validation_run_id, issue.issue_id, command.source_event_id)
                self.__writer.append_validation_issue(record, idempotency_key=key)
                committed.append(record.issue_id)
            except DocumentStateError as error:
                return with_committed(repository_failure(error, operation), operation, committed)
            except (DocumentStateWriterError, TypeError, ValueError):
                return with_committed(invalid(operation), operation, committed)
            except Exception:
                return with_committed(result("failed", operation, error_code="internal_error"), operation, committed)
        return result("success", operation, record_ids=tuple(committed))

    def write_matching_summaries(self, command: WriteMatchingSummariesCommand):
        operation = "write_matching_summaries"
        if not isinstance(command, WriteMatchingSummariesCommand):
            return invalid(operation)
        committed: list[str] = []
        for item in command.summaries:
            try:
                record = MatchingSummaryRecord(
                    item.match_id,
                    command.document_id,
                    command.matching_run_id,
                    item.entity_type,
                    item.candidate_id,
                    item.confidence,
                    item.status,
                    item.occurred_at,
                    item.metadata,
                )
                key = make_idempotency_key("matching", command.matching_run_id, item.match_id, command.source_event_id)
                self.__writer.append_matching_summary(record, idempotency_key=key)
                committed.append(record.match_id)
            except DocumentStateError as error:
                return with_committed(repository_failure(error, operation), operation, committed)
            except (DocumentStateWriterError, TypeError, ValueError):
                return with_committed(invalid(operation), operation, committed)
            except Exception:
                return with_committed(result("failed", operation, error_code="internal_error"), operation, committed)
        return result("success", operation, record_ids=tuple(committed))

    def write_audit_event(self, command: WriteAuditEventCommand):
        return append_audit(self.__writer, command, allowed_event_types=_PROCESSING_AUDIT_TYPES)
