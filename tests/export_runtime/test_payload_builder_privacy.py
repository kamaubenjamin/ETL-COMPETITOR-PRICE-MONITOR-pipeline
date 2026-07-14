import pytest

from src.export_runtime import (
    ExportPayloadBuildCommand,
    ExportPayloadBuildStatus,
    ExportPayloadLine,
    ExportTarget,
    build_export_payload,
)


@pytest.mark.parametrize(
    "candidate",
    [
        {"raw_document": "invoice contents"},
        {"raw_rows": [{"account": "secret"}]},
        {"artifact_payload": {"content": "secret"}},
        {"raw_file": b"file bytes"},
        {"backend_config": {"dsn": "secret"}},
        {"credential": "secret"},
        {"token": "secret"},
        {"claim": "raw claim"},
        {"stack_trace": "traceback"},
    ],
)
def test_raw_or_sensitive_command_shapes_are_privacy_rejected(candidate):
    result = build_export_payload(candidate)

    assert result.status == ExportPayloadBuildStatus.PRIVACY_REJECTED.value
    assert result.error_code == "privacy_rejected"
    assert result.payload is None
    assert all(str(value) not in result.message for value in candidate.values())


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_document": "content"},
        {"backend_config": "private"},
        {"safe": {"nested": "object"}},
        {"safe": ["raw", "row"]},
    ],
)
def test_unsafe_or_nested_metadata_is_privacy_rejected(metadata):
    result = build_export_payload(
        ExportPayloadBuildCommand(
            "doc-001",
            "tenant-001",
            ExportTarget("erp-main", "erp", "Main ERP"),
            "KES",
            (ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),),
            metadata=metadata,
        )
    )

    assert result.status == ExportPayloadBuildStatus.PRIVACY_REJECTED.value
    assert result.message == "Export payload input violates privacy requirements."


def test_oversized_metadata_is_rejected_without_echoing_values():
    metadata = {f"key_{index}": f"private-{index}" for index in range(21)}
    result = build_export_payload(
        ExportPayloadBuildCommand(
            "doc-001",
            "tenant-001",
            ExportTarget("erp-main", "erp", "Main ERP"),
            "KES",
            (ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),),
            metadata=metadata,
        )
    )

    assert result.status == ExportPayloadBuildStatus.INVALID_PAYLOAD.value
    assert "private" not in result.message

