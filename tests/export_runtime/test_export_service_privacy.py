import json

from src.export_runtime import (
    ExportPayloadBuildCommand,
    ExportPayloadLine,
    ExportRuntimeCommand,
    ExportRuntimeService,
    ExportTarget,
    InMemoryExportStore,
    readiness_result,
)


NOW = "2026-07-14T10:00:00Z"


class ExplodingAdapter:
    def export(self, payload):
        raise RuntimeError(r"ERP response secret token at C:\private\response.json")


def command(*, payload_metadata=None, command_metadata=None):
    target = ExportTarget("erp-main", "erp", "Main ERP")
    payload = ExportPayloadBuildCommand(
        "doc-001",
        "tenant-001",
        target,
        "KES",
        (ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),),
        metadata={} if payload_metadata is None else payload_metadata,
    )
    return ExportRuntimeCommand(
        "tenant-001",
        "actor-001",
        "doc-001",
        target,
        payload,
        readiness_result(document_id="doc-001", target=target),
        requested_at=NOW,
        metadata={} if command_metadata is None else command_metadata,
    )


def test_adapter_exception_is_converted_without_raw_exception_leakage():
    store = InMemoryExportStore()
    result = ExportRuntimeService(reader=store.reader, writer=store.writer, adapter=ExplodingAdapter()).export(command())
    serialized = json.dumps(result.to_dict()).lower()

    assert result.status == "failed"
    assert result.error_code == "adapter_failed"
    assert "secret token" not in serialized
    assert "private" not in serialized
    assert "response.json" not in serialized
    assert store.reader.get_attempt(result.attempt_id).status == "failed"


def test_unsafe_payload_metadata_is_rejected_before_attempt_or_adapter():
    store = InMemoryExportStore()
    adapter = ExplodingAdapter()
    result = ExportRuntimeService(reader=store.reader, writer=store.writer, adapter=adapter).export(
        command(payload_metadata={"backend_config": "private"})
    )

    assert result.status == "invalid_payload"
    assert store.reader.list_attempts().total == 0
    assert "private" not in json.dumps(result.to_dict()).lower()


def test_command_metadata_rejects_nested_or_sensitive_values_at_contract_boundary():
    for metadata in ({"token": "private"}, {"safe": {"nested": "value"}}):
        try:
            command(command_metadata=metadata)
        except ValueError as error:
            assert "private" not in str(error).lower()
        else:
            raise AssertionError("unsafe metadata was accepted")

