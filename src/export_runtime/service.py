"""Internal deterministic export orchestration with injected safe boundaries."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib

from .attempts import ExportAttempt
from .audit import create_export_audit_intent
from .builder import ExportPayloadBuilder
from .commands import ExportRuntimeCommand
from .contracts import (
    ExportAuditIntent,
    ExportLifecycleDecision,
    JsonContract,
    contract_tuple,
    optional_id,
    positive_integer,
    safe_code,
    utc_timestamp,
)
from .fingerprints import fingerprint_export_payload
from .lifecycle import export_lifecycle_decision
from .policy import ExportIdempotencyPolicy
from .payloads import ExportPayload
from .ports import ExportAdapterPort
from .repository_errors import ExportRepositoryError
from .repositories import ExportRepositoryReader, ExportRepositoryWriter
from .results import ExportAdapterResult, ExportResult
from .service_errors import ExportServiceStatus, export_service_message
from .statuses import ExportStatus


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_runtime_id(prefix: str, *parts: str) -> str:
    canonical = "\x1f".join(("idp.export.runtime.v1", prefix, *parts))
    return f"{prefix}-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]}"


@dataclass(frozen=True, slots=True)
class ExportRuntimeServiceResult(JsonContract):
    status: ExportServiceStatus | str
    attempt_id: str | None = None
    result_id: str | None = None
    result_status: ExportStatus | str | None = None
    result: ExportResult | None = None
    error_code: str | None = None
    audit_intents: tuple[ExportAuditIntent, ...] = ()
    lifecycle_decision: ExportLifecycleDecision | None = None
    message: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            status = self.status if isinstance(self.status, ExportServiceStatus) else ExportServiceStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("service result status is invalid") from None
        object.__setattr__(self, "status", status.value)
        object.__setattr__(self, "attempt_id", optional_id(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "result_id", optional_id(self.result_id, "result_id"))
        if self.result_status is not None:
            try:
                object.__setattr__(self, "result_status", ExportStatus(self.result_status).value)
            except (TypeError, ValueError):
                raise ValueError("result_status is invalid") from None
        if self.result is not None and not isinstance(self.result, ExportResult):
            raise ValueError("result must be an ExportResult")
        object.__setattr__(self, "error_code", None if self.error_code is None else safe_code(self.error_code, "error_code"))
        object.__setattr__(self, "audit_intents", contract_tuple(self.audit_intents, ExportAuditIntent, "audit_intents"))
        if self.lifecycle_decision is not None and not isinstance(self.lifecycle_decision, ExportLifecycleDecision):
            raise ValueError("lifecycle_decision must be an ExportLifecycleDecision")
        if self.result is not None and (self.result_id != self.result.result_id or self.result_status != self.result.status):
            raise ValueError("service result identity is inconsistent")
        if status == ExportServiceStatus.EXPORTED and (self.result is None or not self.result.succeeded or self.error_code is not None):
            raise ValueError("successful service result is invalid")
        if status != ExportServiceStatus.EXPORTED and self.error_code is None:
            raise ValueError("non-success service result requires an error_code")
        object.__setattr__(self, "message", export_service_message(status))

    @property
    def succeeded(self) -> bool:
        return self.status == ExportServiceStatus.EXPORTED.value


class ExportRuntimeService:
    def __init__(
        self,
        *,
        reader: ExportRepositoryReader,
        writer: ExportRepositoryWriter,
        adapter: ExportAdapterPort,
        payload_builder: ExportPayloadBuilder | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(reader, ExportRepositoryReader):
            raise ValueError("reader must satisfy ExportRepositoryReader")
        if not isinstance(writer, ExportRepositoryWriter):
            raise ValueError("writer must satisfy ExportRepositoryWriter")
        if not isinstance(adapter, ExportAdapterPort):
            raise ValueError("adapter must satisfy ExportAdapterPort")
        self.__reader = reader
        self.__writer = writer
        self.__adapter = adapter
        self.__builder = ExportPayloadBuilder() if payload_builder is None else payload_builder
        if not isinstance(self.__builder, ExportPayloadBuilder):
            raise ValueError("payload_builder must be an ExportPayloadBuilder")
        self.__clock = _utc_now if clock is None else clock

    def export(self, command: object) -> ExportRuntimeServiceResult:
        if not isinstance(command, ExportRuntimeCommand):
            return ExportRuntimeServiceResult(status="invalid_command", error_code="invalid_command")
        try:
            occurred_at = command.requested_at or utc_timestamp(self.__clock(), "clock")
            document_version = positive_integer(command.payload_command.document_version, "document_version")
        except (TypeError, ValueError):
            return ExportRuntimeServiceResult(status="invalid_command", error_code="invalid_command")

        if not command.readiness.ready:
            lifecycle = export_lifecycle_decision(outcome="not_ready", document_version=document_version)
            audit = create_export_audit_intent(
                command,
                event_type="export_blocked_not_ready",
                outcome_code=command.readiness.blocking_issues[0].code if command.readiness.blocking_issues else "not_ready",
                occurred_at=occurred_at,
            )
            return ExportRuntimeServiceResult(
                status="blocked_not_ready",
                result_status="not_ready",
                error_code="not_ready",
                audit_intents=(audit,),
                lifecycle_decision=lifecycle,
            )

        build = self.__builder.build(command.payload_command)
        if not build.succeeded or build.payload is None:
            lifecycle = export_lifecycle_decision(outcome="invalid_payload", document_version=document_version)
            audit = create_export_audit_intent(
                command,
                event_type="export_failed",
                outcome_code=build.error_code or "invalid_payload",
                occurred_at=occurred_at,
                result_status="failed",
            )
            return ExportRuntimeServiceResult(
                status="invalid_payload",
                result_status="failed",
                error_code=build.error_code or "invalid_payload",
                audit_intents=(audit,),
                lifecycle_decision=lifecycle,
            )

        payload = build.payload
        payload_fingerprint = fingerprint_export_payload(payload)
        policy = ExportIdempotencyPolicy(command.operation_type, command.operation_version)
        idempotency_key = policy.key_for_payload(payload)

        try:
            duplicate = self.__find_exact_duplicate(idempotency_key.value)
        except ExportRepositoryError:
            return self.__repository_failure(command, occurred_at, document_version)
        if duplicate is not None:
            return self.__duplicate_result(command, duplicate, occurred_at, document_version, "duplicate_idempotency_key")
        try:
            if self.__reader.has_active_document_target(
                tenant_id=command.tenant_id,
                document_id=command.document_id,
                target_id=command.target.target_id,
            ):
                active = self.__reader.list_attempts_by_document(command.document_id).items
                existing = next(
                    item
                    for item in active
                    if item.tenant_id == command.tenant_id
                    and item.target.target_id == command.target.target_id
                    and item.status in {"preparing", "queued", "exporting"}
                )
                return self.__duplicate_result(command, existing, occurred_at, document_version, "active_document_target")
        except (ExportRepositoryError, StopIteration):
            return self.__repository_failure(command, occurred_at, document_version)

        attempt_id = _stable_runtime_id("attempt", idempotency_key.value, occurred_at)
        attempt = ExportAttempt(
            attempt_id=attempt_id,
            tenant_id=command.tenant_id,
            document_id=command.document_id,
            target=command.target,
            idempotency_key=idempotency_key,
            payload_fingerprint=payload_fingerprint,
            status="preparing",
            operation_type=command.operation_type,
            requested_by=command.actor_id,
            created_at=occurred_at,
            updated_at=occurred_at,
            operation_version=command.operation_version,
            metadata=command.metadata,
        )
        requested_audit = create_export_audit_intent(
            command, event_type="export_requested", outcome_code="accepted", occurred_at=occurred_at
        )
        try:
            self.__writer.save_attempt(attempt)
            attempt = self.__writer.update_attempt_status(
                attempt.attempt_id, "exporting", expected_version=attempt.version, updated_at=occurred_at
            )
        except ExportRepositoryError as error:
            if error.code in {"duplicate_attempt", "duplicate_idempotency_key"}:
                duplicate = self.__find_exact_duplicate(idempotency_key.value)
                if duplicate is not None:
                    return self.__duplicate_result(command, duplicate, occurred_at, document_version, error.code)
            return self.__repository_failure(command, occurred_at, document_version, attempt_id=attempt_id)

        started_audit = create_export_audit_intent(
            command,
            event_type="export_attempt_started",
            outcome_code="adapter_started",
            occurred_at=occurred_at,
            attempt_id=attempt.attempt_id,
            result_status="exporting",
        )
        adapter_result = self.__invoke_adapter(payload)
        terminal_status = "exported" if adapter_result.status == "exported" else "failed"
        result_id = _stable_runtime_id("result", attempt.attempt_id, terminal_status, adapter_result.code)
        result = ExportResult(
            result_id=result_id,
            attempt_id=attempt.attempt_id,
            document_id=command.document_id,
            target_id=command.target.target_id,
            status=terminal_status,
            code=adapter_result.code,
            occurred_at=occurred_at,
            adapter_result=adapter_result,
            metadata={"operation_version": command.operation_version},
        )
        try:
            self.__writer.save_result(result)
            self.__writer.update_attempt_status(
                attempt.attempt_id,
                terminal_status,
                expected_version=attempt.version,
                updated_at=occurred_at,
            )
        except ExportRepositoryError:
            return self.__repository_failure(
                command,
                occurred_at,
                document_version,
                attempt_id=attempt.attempt_id,
                result=result,
                prior_audits=(requested_audit, started_audit),
            )

        if terminal_status == "exported":
            service_status = ExportServiceStatus.EXPORTED
            error_code = None
            event_type = "export_succeeded"
            lifecycle_outcome = "exported"
        elif adapter_result.code == "adapter_unavailable":
            service_status = ExportServiceStatus.ADAPTER_UNAVAILABLE
            error_code = "adapter_unavailable"
            event_type = "export_adapter_unavailable"
            lifecycle_outcome = "adapter_unavailable"
        else:
            service_status = ExportServiceStatus.FAILED
            error_code = adapter_result.code
            event_type = "export_failed"
            lifecycle_outcome = "failed"
        final_audit = create_export_audit_intent(
            command,
            event_type=event_type,
            outcome_code=adapter_result.code,
            occurred_at=occurred_at,
            attempt_id=attempt.attempt_id,
            result_status=terminal_status,
        )
        lifecycle = export_lifecycle_decision(outcome=lifecycle_outcome, document_version=document_version)
        return ExportRuntimeServiceResult(
            status=service_status,
            attempt_id=attempt.attempt_id,
            result_id=result.result_id,
            result_status=result.status,
            result=result,
            error_code=error_code,
            audit_intents=(requested_audit, started_audit, final_audit),
            lifecycle_decision=lifecycle,
        )

    def __invoke_adapter(self, payload: ExportPayload) -> ExportAdapterResult:
        try:
            result = self.__adapter.export(payload)
            if not isinstance(result, ExportAdapterResult):
                raise TypeError("invalid adapter result")
            return result
        except Exception:
            return ExportAdapterResult(
                status="failed",
                code="adapter_failed",
                retryable=False,
                message="Export adapter did not confirm success.",
            )

    def __find_exact_duplicate(self, idempotency_key: str) -> ExportAttempt | None:
        try:
            return self.__reader.get_attempt_by_idempotency_key(idempotency_key)
        except ExportRepositoryError as error:
            if error.code == "not_found":
                return None
            raise

    def __duplicate_result(
        self,
        command: ExportRuntimeCommand,
        existing: ExportAttempt,
        occurred_at: str,
        document_version: int,
        reason_code: str,
    ) -> ExportRuntimeServiceResult:
        result = ExportResult(
            result_id=_stable_runtime_id("result", "duplicate", existing.attempt_id, reason_code),
            attempt_id=existing.attempt_id,
            document_id=existing.document_id,
            target_id=existing.target.target_id,
            status="duplicate_prevented",
            code="duplicate_export",
            occurred_at=occurred_at,
            duplicate_of_attempt_id=existing.attempt_id,
            metadata={"duplicate_reason": reason_code},
        )
        audit = create_export_audit_intent(
            command,
            event_type="export_duplicate_prevented",
            outcome_code=reason_code,
            occurred_at=occurred_at,
            attempt_id=existing.attempt_id,
            result_status="duplicate_prevented",
        )
        return ExportRuntimeServiceResult(
            status="duplicate_prevented",
            attempt_id=existing.attempt_id,
            result_id=result.result_id,
            result_status=result.status,
            result=result,
            error_code="duplicate_export",
            audit_intents=(audit,),
            lifecycle_decision=export_lifecycle_decision(
                outcome="duplicate_prevented", document_version=document_version
            ),
        )

    def __repository_failure(
        self,
        command: ExportRuntimeCommand,
        occurred_at: str,
        document_version: int,
        *,
        attempt_id: str | None = None,
        result: ExportResult | None = None,
        prior_audits: tuple[ExportAuditIntent, ...] = (),
    ) -> ExportRuntimeServiceResult:
        audit = create_export_audit_intent(
            command,
            event_type="export_failed",
            outcome_code="repository_error",
            occurred_at=occurred_at,
            attempt_id=attempt_id,
            result_status="failed",
        )
        return ExportRuntimeServiceResult(
            status="repository_error",
            attempt_id=attempt_id,
            result_id=None if result is None else result.result_id,
            result_status=None if result is None else result.status,
            result=result,
            error_code="repository_error",
            audit_intents=(*prior_audits, audit),
            lifecycle_decision=export_lifecycle_decision(
                outcome="repository_error", document_version=document_version
            ),
        )
