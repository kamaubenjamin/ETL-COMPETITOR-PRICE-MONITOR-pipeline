"""Internal review, correction, and reprocess Document State writer."""

from __future__ import annotations

from ..errors import DocumentStateError
from ..lifecycle import LifecycleAdvancementService
from ..records import CorrectionSummaryRecord, ReprocessPlanRecord, ReviewReferenceRecord
from ..repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
from ._service_support import append_audit, append_lifecycle, invalid, repository_failure, result
from .commands import (
    AppendLifecycleEventCommand,
    WriteAuditEventCommand,
    WriteCorrectionSummaryCommand,
    WriteReprocessPlanCommand,
    WriteReviewSummaryCommand,
)
from .errors import DocumentStateWriterError
from .idempotency import make_idempotency_key


_REVIEW_AUDIT_TYPES = frozenset({"review_required", "correction_submitted", "reprocess_planned"})


class ReviewDocumentStateWriter:
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

    def write_review_summary(self, command: WriteReviewSummaryCommand):
        operation = "write_review_summary"
        if not isinstance(command, WriteReviewSummaryCommand):
            return invalid(operation)
        try:
            version = 1 if command.expected_version is None else command.expected_version + 1
            record = ReviewReferenceRecord(
                command.review_case_id,
                command.document_id,
                command.reason_code,
                command.priority,
                command.status,
                command.created_at,
                command.updated_at,
                command.assigned_reviewer_id,
                command.correction_count,
                command.decision_code,
                command.reprocess_state,
                version,
                command.metadata,
            )
            if command.expected_version is None:
                self.__writer.create_review_reference(record)
            else:
                self.__writer.update_review_reference(record, expected_version=command.expected_version)
            return result("success", operation, record_ids=(record.review_case_id,))
        except DocumentStateError as error:
            if error.code != "conflict":
                return repository_failure(error, operation, versioned=command.expected_version is not None)
            try:
                existing = self.__reader.get_review_reference(command.review_case_id)
            except DocumentStateError as read_error:
                return repository_failure(read_error, operation, versioned=command.expected_version is not None)
            if existing == record:
                return result("skipped_idempotent", operation, record_ids=(record.review_case_id,))
            return result("conflict", operation, error_code="version_conflict" if command.expected_version is not None else "invalid_command")
        except (DocumentStateWriterError, TypeError, ValueError):
            return invalid(operation)
        except Exception:
            return result("failed", operation, error_code="internal_error")

    def write_correction_summary(self, command: WriteCorrectionSummaryCommand):
        operation = "write_correction_summary"
        if not isinstance(command, WriteCorrectionSummaryCommand):
            return invalid(operation)
        try:
            record = CorrectionSummaryRecord(
                command.correction_id,
                command.review_case_id,
                command.document_id,
                command.field_path,
                command.operation,
                command.reason_code,
                command.actor_id,
                command.occurred_at,
                command.source_stage,
                command.metadata,
            )
            key = make_idempotency_key("correction", command.review_case_id, command.correction_id, command.source_event_id)
            self.__writer.append_correction_summary(record, idempotency_key=key)
            return result("success", operation, record_ids=(record.correction_id,))
        except DocumentStateError as error:
            return repository_failure(error, operation)
        except (DocumentStateWriterError, TypeError, ValueError):
            return invalid(operation)
        except Exception:
            return result("failed", operation, error_code="internal_error")

    def write_reprocess_plan(self, command: WriteReprocessPlanCommand):
        operation = "write_reprocess_plan"
        if not isinstance(command, WriteReprocessPlanCommand):
            return invalid(operation)
        try:
            record = ReprocessPlanRecord(
                command.plan_id,
                command.review_case_id,
                command.document_id,
                command.requested_from_stage,
                command.requested_target_stage,
                command.invalidated_artifact_count,
                command.retained_artifact_count,
                command.reason_code,
                command.requested_by,
                command.created_at,
                command.mode,
                command.metadata,
            )
            key = make_idempotency_key("reprocess", command.review_case_id, command.plan_id, command.source_event_id)
            self.__writer.append_reprocess_plan(record, idempotency_key=key)
            return result("success", operation, record_ids=(record.plan_id,))
        except DocumentStateError as error:
            return repository_failure(error, operation)
        except (DocumentStateWriterError, TypeError, ValueError):
            return invalid(operation)
        except Exception:
            return result("failed", operation, error_code="internal_error")

    def append_lifecycle_event(self, command: AppendLifecycleEventCommand):
        return append_lifecycle(
            self.__reader,
            self.__writer,
            command,
            allowed_statuses=frozenset({"review_required", "approved"}),
            lifecycle_service=self.__lifecycle_service,
        )

    def write_audit_event(self, command: WriteAuditEventCommand):
        return append_audit(self.__writer, command, allowed_event_types=_REVIEW_AUDIT_TYPES)
