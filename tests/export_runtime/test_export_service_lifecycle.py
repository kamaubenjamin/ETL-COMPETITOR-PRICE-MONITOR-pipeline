from src.export_runtime import (
    ExportPayloadBuildCommand,
    ExportPayloadLine,
    ExportRuntimeCommand,
    ExportRuntimeService,
    ExportTarget,
    FailingPlaceholderAdapter,
    InMemoryExportStore,
    UnavailablePlaceholderAdapter,
    export_lifecycle_decision,
    readiness_result,
)


NOW = "2026-07-14T10:00:00Z"


def command():
    target = ExportTarget("erp-main", "erp", "Main ERP")
    payload = ExportPayloadBuildCommand(
        "doc-001", "tenant-001", target, "KES", (ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),), document_version=4
    )
    return ExportRuntimeCommand(
        "tenant-001", "actor-001", "doc-001", target, payload, readiness_result(document_id="doc-001", target=target), requested_at=NOW
    )


def run(adapter):
    store = InMemoryExportStore()
    result = ExportRuntimeService(reader=store.reader, writer=store.writer, adapter=adapter).export(command())
    return result, store


def test_failed_adapter_never_returns_exported_lifecycle_intent():
    result, store = run(FailingPlaceholderAdapter())

    assert result.status == "failed"
    assert result.result.status == "failed"
    assert store.reader.get_attempt(result.attempt_id).status == "failed"
    assert result.lifecycle_decision.permitted is False
    assert result.lifecycle_decision.target_status == "unchanged"
    assert result.lifecycle_decision.reason_code == "export_failed"


def test_unavailable_adapter_returns_safe_failure_and_no_lifecycle_change():
    result, store = run(UnavailablePlaceholderAdapter())

    assert result.status == "adapter_unavailable"
    assert result.error_code == "adapter_unavailable"
    assert store.reader.get_attempt(result.attempt_id).status == "failed"
    assert result.lifecycle_decision.permitted is False
    assert result.lifecycle_decision.reason_code == "adapter_unavailable"


def test_lifecycle_policy_is_pure_and_deterministic():
    assert export_lifecycle_decision(outcome="exported", document_version=2).to_dict() == {
        "permitted": True,
        "target_status": "exported",
        "expected_document_version": 2,
        "reason_code": "export_confirmed",
        "projection_pending": False,
    }
    assert export_lifecycle_decision(outcome="duplicate_prevented", document_version=2).target_status == "unchanged"

