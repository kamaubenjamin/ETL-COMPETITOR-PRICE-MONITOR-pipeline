from dataclasses import FrozenInstanceError

import pytest

from src.export_runtime import (
    ExportPayloadBuildCommand,
    ExportPayloadLine,
    ExportAttempt,
    ExportIdempotencyPolicy,
    ExportReadinessIssue,
    ExportRuntimeCommand,
    ExportRuntimeService,
    ExportTarget,
    InMemoryExportStore,
    SuccessfulPlaceholderAdapter,
    build_export_payload,
    fingerprint_export_payload,
    readiness_result,
)


NOW = "2026-07-14T10:00:00Z"


def command(*, ready=True, lines=None, target=None):
    target = target or ExportTarget("erp-main", "erp", "Main ERP")
    payload = ExportPayloadBuildCommand(
        "doc-001",
        "tenant-001",
        target,
        "KES",
        (ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),) if lines is None else lines,
        document_version=3,
    )
    blockers = () if ready else (ExportReadinessIssue("validation_not_passed", field="validation"),)
    return ExportRuntimeCommand(
        "tenant-001",
        "actor-001",
        "doc-001",
        target,
        payload,
        readiness_result(document_id="doc-001", target=target, blocking_issues=blockers),
        requested_at=NOW,
        correlation_id="corr-001",
        request_id="req-001",
        metadata={"source": "internal"},
    )


class CountingAdapter:
    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = 0

    def export(self, payload):
        self.calls += 1
        return self.delegate.export(payload)


def service(adapter=None, store=None):
    store = store or InMemoryExportStore()
    adapter = adapter or SuccessfulPlaceholderAdapter()
    return ExportRuntimeService(reader=store.reader, writer=store.writer, adapter=adapter), store


def test_readiness_block_creates_safe_audit_and_no_attempt_or_adapter_call():
    adapter = CountingAdapter(SuccessfulPlaceholderAdapter())
    runtime, store = service(adapter)

    result = runtime.export(command(ready=False))

    assert result.status == "blocked_not_ready"
    assert result.attempt_id is None
    assert result.result is None
    assert adapter.calls == 0
    assert store.reader.list_attempts().total == 0
    assert [event.event_type for event in result.audit_intents] == ["export_blocked_not_ready"]
    assert result.lifecycle_decision.permitted is False
    assert result.lifecycle_decision.target_status == "unchanged"


def test_successful_export_persists_attempt_and_result_and_returns_safe_intents():
    runtime, store = service()
    source = command()

    result = runtime.export(source)

    assert result.succeeded
    assert result.result_status == "exported"
    assert store.reader.get_attempt(result.attempt_id).status == "exported"
    assert store.reader.get_attempt(result.attempt_id).version == 3
    assert store.reader.list_results_by_attempt(result.attempt_id).items == (result.result,)
    assert result.lifecycle_decision.permitted is True
    assert result.lifecycle_decision.target_status == "exported"
    assert [event.event_type for event in result.audit_intents] == [
        "export_requested",
        "export_attempt_started",
        "export_succeeded",
    ]
    assert source.payload_command.lines[0].item_code == "SKU-001"
    with pytest.raises(FrozenInstanceError):
        source.document_id = "doc-002"


def test_invalid_payload_returns_safe_failure_without_attempt_or_adapter_call():
    adapter = CountingAdapter(SuccessfulPlaceholderAdapter())
    runtime, store = service(adapter)

    result = runtime.export(command(lines=({"raw": "row"},)))

    assert result.status == "invalid_payload"
    assert result.error_code == "invalid_payload"
    assert adapter.calls == 0
    assert store.reader.list_attempts().total == 0
    assert result.lifecycle_decision.reason_code == "payload_invalid"


def test_non_command_input_is_rejected_without_reflecting_input():
    runtime, store = service()
    result = runtime.export({"raw_document": "private invoice text"})

    assert result.status == "invalid_command"
    assert result.audit_intents == ()
    assert "private" not in result.message
    assert store.reader.list_attempts().total == 0


def test_exact_duplicate_prevents_second_adapter_call_and_preserves_terminal_result():
    adapter = CountingAdapter(SuccessfulPlaceholderAdapter())
    runtime, store = service(adapter)

    first = runtime.export(command())
    duplicate = runtime.export(command())

    assert first.status == "exported"
    assert duplicate.status == "duplicate_prevented"
    assert duplicate.attempt_id == first.attempt_id
    assert duplicate.result.status == "duplicate_prevented"
    assert adapter.calls == 1
    assert store.reader.list_attempts().total == 1
    assert store.reader.list_results_by_attempt(first.attempt_id).items == (first.result,)


def test_active_document_target_lock_blocks_changed_payload_before_adapter_call():
    adapter = CountingAdapter(SuccessfulPlaceholderAdapter())
    runtime, store = service(adapter)
    active_command = command()
    build = build_export_payload(active_command.payload_command)
    payload = build.payload
    policy = ExportIdempotencyPolicy()
    key = policy.key_for_payload(payload)

    store.writer.save_attempt(
        ExportAttempt(
            "attempt-active",
            "tenant-001",
            "doc-001",
            active_command.target,
            key,
            fingerprint_export_payload(payload),
            "preparing",
            "export",
            "actor-001",
            NOW,
            NOW,
        )
    )
    changed = command(lines=(ExportPayloadLine("line-002", "SKU-002", 1, 20, 20),))

    result = runtime.export(changed)

    assert result.status == "duplicate_prevented"
    assert result.attempt_id == "attempt-active"
    assert adapter.calls == 0
    assert store.reader.list_attempts().total == 1
