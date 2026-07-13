"""Internal ingestion writer backed by injected Document State repositories."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..errors import DocumentStateError
from ..lifecycle import LifecycleAdvancementService
from ..records import AuditEventRecord, DocumentRecord, ProcessingSnapshot
from ..repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
from .commands import (
    AppendLifecycleEventCommand,
    CreateDocumentCommand,
    WriteAuditEventCommand,
    WriteProcessingSnapshotCommand,
)
from ._service_support import append_lifecycle
from .errors import DocumentStateWriterError
from .idempotency import make_idempotency_key
from .mappings import get_writer_mapping
from .results import WriterResult


_INGESTION_AUDIT_TYPES = frozenset({"ingestion_received", "ingestion_classified"})


def _safe_message(code: str) -> str:
    return DocumentStateWriterError(code).message


def _result(
    status: str,
    operation: str,
    *,
    record_ids: tuple[str, ...] = (),
    error_code: str | None = None,
) -> WriterResult:
    return WriterResult(
        status,
        operation,
        record_ids,
        len(record_ids),
        error_code=error_code,
        message=_safe_message(error_code) if error_code else None,
    )


def _repository_failure(error: DocumentStateError, operation: str, *, versioned: bool = False) -> WriterResult:
    if error.code in {"invalid_record", "invalid_query", "not_found"}:
        if versioned and error.code == "not_found":
            return _result("conflict", operation, error_code="version_conflict")
        return _result("invalid_input", operation, error_code="invalid_command")
    if error.code == "conflict":
        return _result("conflict", operation, error_code="version_conflict" if versioned else "invalid_command")
    if error.code == "source_unavailable":
        return _result("failed", operation, error_code="repository_unavailable")
    return _result("failed", operation, error_code="internal_error")


def _invalid(operation: str) -> WriterResult:
    return _result("invalid_input", operation, error_code="invalid_command")


class IngestionDocumentStateWriter:
    """Maps ingestion commands to records without selecting a repository backend."""

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

    def create_document(self, command: CreateDocumentCommand) -> WriterResult:
        operation = "create_document"
        if not isinstance(command, CreateDocumentCommand):
            return _invalid(operation)
        try:
            mapping = get_writer_mapping("ingestion_received")
            if "document_record" not in mapping.record_targets:
                return _invalid(operation)
            record = DocumentRecord(
                document_id=command.document_id,
                filename=command.filename,
                document_type=command.document_type,
                status=mapping.lifecycle_status,
                confidence=command.confidence,
                current_stage=mapping.lifecycle_status,
                received_at=command.received_at,
                created_at=command.created_at,
                updated_at=command.created_at,
                version=1,
                metadata={**dict(command.metadata), "source_runtime": command.producer},
            )
            self.__writer.create_document(record)
            return _result("success", operation, record_ids=(record.document_id,))
        except DocumentStateError as error:
            if error.code != "conflict":
                return _repository_failure(error, operation)
            try:
                existing = self.__reader.get_document(command.document_id)
            except DocumentStateError as read_error:
                return _repository_failure(read_error, operation)
            if existing == record:
                return _result("skipped_idempotent", operation, record_ids=(record.document_id,))
            return _result("conflict", operation, error_code="invalid_command")
        except (DocumentStateWriterError, TypeError, ValueError):
            return _invalid(operation)
        except Exception:
            return _result("failed", operation, error_code="internal_error")

    def append_lifecycle_event(self, command: AppendLifecycleEventCommand) -> WriterResult:
        allowed = frozenset(
            mapping.lifecycle_status
            for name in ("ingestion_received", "ingestion_classified")
            if (mapping := get_writer_mapping(name)).lifecycle_status is not None
        )
        return append_lifecycle(
            self.__reader,
            self.__writer,
            command,
            allowed_statuses=allowed,
            lifecycle_service=self.__lifecycle_service,
        )

    def write_processing_snapshot(self, command: WriteProcessingSnapshotCommand) -> WriterResult:
        operation = "write_processing_snapshot"
        if not isinstance(command, WriteProcessingSnapshotCommand):
            return _invalid(operation)
        try:
            mapping = get_writer_mapping("ingestion_classified")
            if command.stage != mapping.processing_stage:
                return _invalid(operation)
            version = 1 if command.expected_version is None else command.expected_version + 1
            record = ProcessingSnapshot(
                snapshot_id=command.snapshot_id,
                document_id=command.document_id,
                workflow_run_id=command.workflow_run_id,
                stage=command.stage,
                status=command.status,
                started_at=command.started_at,
                updated_at=command.updated_at,
                completed_at=command.completed_at,
                duration_ms=command.duration_ms,
                version=version,
                metadata=command.metadata,
            )
            if command.expected_version is None:
                self.__writer.create_processing_snapshot(record)
            else:
                self.__writer.update_processing_snapshot(record, expected_version=command.expected_version)
            return _result("success", operation, record_ids=(record.snapshot_id,))
        except DocumentStateError as error:
            if error.code != "conflict":
                return _repository_failure(error, operation, versioned=command.expected_version is not None)
            try:
                existing = self.__reader.get_processing_snapshot(command.snapshot_id)
            except DocumentStateError as read_error:
                return _repository_failure(read_error, operation, versioned=command.expected_version is not None)
            if existing == record:
                return _result("skipped_idempotent", operation, record_ids=(record.snapshot_id,))
            return _result("conflict", operation, error_code="version_conflict")
        except (DocumentStateWriterError, TypeError, ValueError):
            return _invalid(operation)
        except Exception:
            return _result("failed", operation, error_code="internal_error")

    def write_audit_event(self, command: WriteAuditEventCommand) -> WriterResult:
        operation = "write_audit_event"
        if not isinstance(command, WriteAuditEventCommand) or command.event_type not in _INGESTION_AUDIT_TYPES:
            return _invalid(operation)
        try:
            record = AuditEventRecord(
                event_id=command.event_id,
                event_type=command.event_type,
                actor_id=command.actor_id,
                occurred_at=command.occurred_at,
                document_id=command.document_id,
                review_case_id=command.review_case_id,
                workflow_run_id=command.workflow_run_id,
                metadata=command.metadata,
            )
            key = make_idempotency_key("audit", command.event_id, command.source_event_id)
            self.__writer.append_audit_event(record, idempotency_key=key)
            return _result("success", operation, record_ids=(record.event_id,))
        except DocumentStateError as error:
            return _repository_failure(error, operation)
        except (DocumentStateWriterError, TypeError, ValueError):
            return _invalid(operation)
        except Exception:
            return _result("failed", operation, error_code="internal_error")

    def write_ingestion_received(
        self,
        document: CreateDocumentCommand,
        lifecycle: AppendLifecycleEventCommand,
        audit: WriteAuditEventCommand | None = None,
    ) -> WriterResult:
        operation = "write_ingestion_received"
        if (
            not isinstance(document, CreateDocumentCommand)
            or not isinstance(lifecycle, AppendLifecycleEventCommand)
            or lifecycle.document_id != document.document_id
            or lifecycle.status != "received"
            or (audit is not None and (not isinstance(audit, WriteAuditEventCommand) or audit.document_id != document.document_id))
        ):
            return _invalid(operation)
        steps: tuple[Callable[[], WriterResult], ...] = (
            lambda: self.create_document(document),
            lambda: self.append_lifecycle_event(lifecycle),
        ) + ((lambda: self.write_audit_event(audit)),) if audit is not None else (
            lambda: self.create_document(document),
            lambda: self.append_lifecycle_event(lifecycle),
        )
        return self.__run_steps(operation, steps)

    def write_ingestion_classified(
        self,
        lifecycle: AppendLifecycleEventCommand,
        processing: WriteProcessingSnapshotCommand,
        audit: WriteAuditEventCommand | None = None,
    ) -> WriterResult:
        operation = "write_ingestion_classified"
        if (
            not isinstance(lifecycle, AppendLifecycleEventCommand)
            or not isinstance(processing, WriteProcessingSnapshotCommand)
            or lifecycle.document_id != processing.document_id
            or lifecycle.status != "classified"
            or processing.stage != "classification"
            or (audit is not None and (not isinstance(audit, WriteAuditEventCommand) or audit.document_id != lifecycle.document_id))
        ):
            return _invalid(operation)
        steps: tuple[Callable[[], WriterResult], ...] = (
            lambda: self.append_lifecycle_event(lifecycle),
            lambda: self.write_processing_snapshot(processing),
        ) + ((lambda: self.write_audit_event(audit)),) if audit is not None else (
            lambda: self.append_lifecycle_event(lifecycle),
            lambda: self.write_processing_snapshot(processing),
        )
        return self.__run_steps(operation, steps)

    @staticmethod
    def __run_steps(operation: str, steps: tuple[Callable[[], WriterResult], ...]) -> WriterResult:
        record_ids: list[str] = []
        all_skipped = True
        for step in steps:
            result = step()
            if result.status not in {"success", "skipped_idempotent"}:
                return WriterResult(
                    result.status,
                    operation,
                    tuple(record_ids),
                    len(record_ids),
                    error_code=result.error_code,
                    message=result.message,
                )
            record_ids.extend(result.record_ids)
            all_skipped = all_skipped and result.status == "skipped_idempotent"
        return _result("skipped_idempotent" if all_skipped else "success", operation, record_ids=tuple(record_ids))
