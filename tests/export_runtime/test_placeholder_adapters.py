import pytest

from src.export_runtime import (
    ExportAdapterPort,
    ExportPayload,
    ExportPayloadLine,
    ExportTarget,
    FailingPlaceholderAdapter,
    SuccessfulPlaceholderAdapter,
    UnavailablePlaceholderAdapter,
)


def payload():
    return ExportPayload(
        "payload-001",
        "doc-001",
        "tenant-001",
        ExportTarget("erp-main", "erp", "Main ERP"),
        "KES",
        (ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),),
    )


@pytest.mark.parametrize(
    ("adapter", "status", "code", "retryable"),
    [
        (SuccessfulPlaceholderAdapter(), "exported", "placeholder_confirmed", False),
        (FailingPlaceholderAdapter(), "failed", "placeholder_failed", True),
        (UnavailablePlaceholderAdapter(), "failed", "adapter_unavailable", True),
    ],
)
def test_placeholders_satisfy_port_and_return_sanitized_results(adapter, status, code, retryable):
    assert isinstance(adapter, ExportAdapterPort)
    first = adapter.export(payload())
    second = adapter.export(payload())

    assert first == second
    assert first.status == status
    assert first.code == code
    assert first.retryable is retryable
    assert "credential" not in str(first.to_dict()).lower()
    assert "response_body" not in str(first.to_dict()).lower()


@pytest.mark.parametrize(
    "adapter",
    [SuccessfulPlaceholderAdapter(), FailingPlaceholderAdapter(), UnavailablePlaceholderAdapter()],
)
def test_placeholders_reject_non_payload_inputs(adapter):
    with pytest.raises(ValueError, match="ExportPayload"):
        adapter.export({"raw_document": "content"})

