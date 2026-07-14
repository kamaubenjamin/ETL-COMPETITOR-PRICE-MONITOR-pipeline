import json

from src.export_runtime import (
    ExportPayloadBuildCommand,
    ExportPayloadLine,
    ExportRuntimeCommand,
    ExportRuntimeService,
    ExportTarget,
    InMemoryExportStore,
    SuccessfulPlaceholderAdapter,
    create_export_audit_intent,
    readiness_result,
)


NOW = "2026-07-14T10:00:00Z"


def command():
    target = ExportTarget("erp-main", "erp", "Main ERP")
    payload = ExportPayloadBuildCommand(
        "doc-001", "tenant-001", target, "KES", (ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),)
    )
    return ExportRuntimeCommand(
        "tenant-001",
        "actor-001",
        "doc-001",
        target,
        payload,
        readiness_result(document_id="doc-001", target=target),
        requested_at=NOW,
        correlation_id="corr-001",
        request_id="req-001",
    )


def test_audit_intent_contains_only_safe_bounded_context():
    intent = create_export_audit_intent(
        command(), event_type="export_requested", outcome_code="accepted", occurred_at=NOW, result_status="exporting"
    )
    projected = intent.to_dict()

    assert projected["document_id"] == "doc-001"
    assert projected["target_id"] == "erp-main"
    assert projected["metadata"] == {
        "tenant_id": "tenant-001",
        "target_type": "erp",
        "target_label": "Main ERP",
        "correlation_id": "corr-001",
        "request_id": "req-001",
        "result_status": "exporting",
    }


def test_success_audit_sequence_serializes_without_payload_or_adapter_body():
    store = InMemoryExportStore()
    result = ExportRuntimeService(
        reader=store.reader, writer=store.writer, adapter=SuccessfulPlaceholderAdapter()
    ).export(command())
    serialized = json.dumps([intent.to_dict() for intent in result.audit_intents]).lower()

    assert [intent.event_type for intent in result.audit_intents] == [
        "export_requested",
        "export_attempt_started",
        "export_succeeded",
    ]
    for forbidden in ("raw_document", "raw_rows", "artifact_payload", "adapter_response", "credential", "token", "stack_trace"):
        assert forbidden not in serialized

