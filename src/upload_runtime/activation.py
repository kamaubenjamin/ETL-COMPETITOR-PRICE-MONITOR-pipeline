"""Deterministic upload activation orchestration over injected intent ports."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Callable

from .activation_errors import UploadActivationReason
from .commands import UploadCommand
from .contracts import UploadArtifactReference
from .idempotency import upload_idempotency_key
from .integration import (
    DocumentStateWriteReceipt,
    IngestionActivationReceipt,
    UploadDocumentStateWriterPort,
    UploadIngestionActivationPort,
)
from .processing import (
    UploadActivationResult,
    UploadDocumentStateWriteIntent,
    UploadIngestionActivationIntent,
)
from .staging import ValidatedStagedUpload
from .validation import UploadValidationResult


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(f"idp.upload.activation.v1\x1f{prefix}\x1f{value}".encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:24]}"


class UploadActivationService:
    def __init__(
        self,
        *,
        ingestion: UploadIngestionActivationPort,
        document_state: UploadDocumentStateWriterPort,
        clock: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(ingestion, UploadIngestionActivationPort):
            raise ValueError("ingestion must satisfy UploadIngestionActivationPort")
        if not isinstance(document_state, UploadDocumentStateWriterPort):
            raise ValueError("document_state must satisfy UploadDocumentStateWriterPort")
        self.__ingestion = ingestion
        self.__document_state = document_state
        self.__clock = _utc_now if clock is None else clock

    def activate(
        self,
        command: UploadCommand,
        validation: UploadValidationResult,
        artifact_reference: UploadArtifactReference | None,
    ) -> UploadActivationResult:
        if not isinstance(command, UploadCommand) or not isinstance(validation, UploadValidationResult) or not validation.valid:
            return UploadActivationResult(None, None, "failed", UploadActivationReason.VALIDATION_REQUIRED.value)
        try:
            key = upload_idempotency_key(command)
        except ValueError:
            return UploadActivationResult(command.upload_id, None, "failed", UploadActivationReason.VALIDATION_REQUIRED.value)
        upload_id = command.upload_id or _stable_id("upload", key.value)
        if artifact_reference is None:
            return UploadActivationResult(upload_id, None, "deferred_staging_required", UploadActivationReason.STAGING_REQUIRED.value)
        try:
            staged = ValidatedStagedUpload(command, validation, artifact_reference)
        except ValueError:
            return UploadActivationResult(upload_id, None, "unsupported_activation", UploadActivationReason.ARTIFACT_MISMATCH.value)
        if command.tenant_id is None or command.actor_id is None:
            return UploadActivationResult(upload_id, None, "failed", UploadActivationReason.VALIDATION_REQUIRED.value)
        occurred_at = command.requested_at or self.__clock()
        document_id = _stable_id("document", key.value)
        source_event_id = _stable_id("upload-event", key.value)
        state_intent = UploadDocumentStateWriteIntent(
            upload_id=upload_id,
            document_id=document_id,
            tenant_id=command.tenant_id,
            actor_id=command.actor_id,
            source_event_id=source_event_id,
            filename=command.original_filename,
            document_type_hint=command.document_type_hint,
            received_at=occurred_at,
            artifact_reference_id=staged.artifact_reference.reference_id,
        )
        try:
            state_receipt = self.__document_state.record_received(state_intent)
            if not isinstance(state_receipt, DocumentStateWriteReceipt) or not state_receipt.recorded or state_receipt.document_id != document_id:
                return UploadActivationResult(upload_id, document_id, "failed", UploadActivationReason.DOCUMENT_STATE_REJECTED.value)
            ingestion_intent = UploadIngestionActivationIntent(
                upload_id=upload_id,
                document_id=document_id,
                tenant_id=command.tenant_id,
                actor_id=command.actor_id,
                source=command.source,
                file_type=command.file_type,
                artifact_reference=artifact_reference,
                requested_at=occurred_at,
            )
            ingestion_receipt = self.__ingestion.request_ingestion(ingestion_intent)
            if not isinstance(ingestion_receipt, IngestionActivationReceipt) or not ingestion_receipt.accepted:
                return UploadActivationResult(
                    upload_id, document_id, "failed", UploadActivationReason.INGESTION_REJECTED.value,
                    lifecycle_stage="received", document_state_recorded=True,
                )
        except Exception:
            return UploadActivationResult(
                upload_id, document_id, "failed", UploadActivationReason.ACTIVATION_FAILED.value,
                lifecycle_stage="received" if "state_receipt" in locals() else None,
                document_state_recorded="state_receipt" in locals(),
            )
        return UploadActivationResult(
            upload_id, document_id, "ingestion_requested", UploadActivationReason.INGESTION_ACCEPTED.value,
            lifecycle_stage="received", document_state_recorded=True,
        )

