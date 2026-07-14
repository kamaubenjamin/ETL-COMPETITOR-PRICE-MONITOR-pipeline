from datetime import date

from src.export_runtime import (
    ExportPayloadBuildCommand,
    ExportPayloadBuildStatus,
    ExportPayloadBuilder,
    ExportPayloadLine,
    ExportPayloadParty,
    ExportTarget,
    build_export_payload,
)


def command(**changes):
    values = {
        "document_id": "doc-001",
        "tenant_id": "tenant-001",
        "export_target": ExportTarget("erp-main", "erp", "Main ERP"),
        "currency": " kes ",
        "lines": (
            ExportPayloadLine(
                "line-001",
                "SKU-001",
                2,
                "10.50",
                "21.00",
                description="  Service   fee  ",
            ),
        ),
        "parties": (ExportPayloadParty("supplier", "  Example   Supplier  "),),
        "document_type": "invoice",
        "document_date": date(2026, 7, 14),
        "subtotal": "21.00",
        "tax_total": "0",
        "total": "21.00",
        "metadata": {"batch": "B-001", "approved": True},
    }
    values.update(changes)
    return ExportPayloadBuildCommand(**values)


def test_valid_command_builds_normalized_payload():
    result = build_export_payload(command())

    assert result.succeeded
    assert result.status == ExportPayloadBuildStatus.SUCCESS.value
    assert result.payload.currency == "KES"
    assert result.payload.document_date == "2026-07-14"
    assert result.payload.lines[0].description == "Service fee"
    assert result.payload.parties[0].display_name == "Example Supplier"
    assert result.payload.payload_id.startswith("payload-")
    assert result.readiness_issue is None


def test_builder_is_deterministic_and_does_not_mutate_inputs():
    metadata = {"batch": "B-001"}
    source = command(metadata=metadata)
    original_line = source.lines[0]

    first = ExportPayloadBuilder().build(source)
    second = ExportPayloadBuilder().build(source)

    assert first == second
    assert first.payload.to_dict() == second.payload.to_dict()
    assert metadata == {"batch": "B-001"}
    assert source.lines[0] is original_line
    assert source.lines[0].description == "Service   fee"


def test_missing_document_id_rejects_safely():
    result = build_export_payload(command(document_id=None))

    assert result.status == ExportPayloadBuildStatus.INVALID_PAYLOAD.value
    assert result.payload is None
    assert result.error_code == "invalid_payload"
    assert result.readiness_issue.code == "payload_invalid"
    assert "None" not in result.message


def test_missing_target_rejects_safely():
    result = build_export_payload(command(export_target=None))

    assert result.status == ExportPayloadBuildStatus.INVALID_PAYLOAD.value
    assert result.payload is None


def test_invalid_line_item_rejects_without_silent_conversion():
    result = build_export_payload(command(lines=({"line_id": "line-001"},)))

    assert result.status == ExportPayloadBuildStatus.INVALID_PAYLOAD.value
    assert result.payload is None

