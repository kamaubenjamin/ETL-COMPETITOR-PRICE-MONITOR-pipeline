from dataclasses import FrozenInstanceError
import json

import pytest

from src.export_runtime import (
    ExportPayload,
    ExportPayloadLine,
    ExportPayloadParty,
    ExportTarget,
    payload_fingerprint,
)


def payload(*, item_code: str = "SKU-001", metadata=None) -> ExportPayload:
    target = ExportTarget("erp-main", "erp", "Main ERP")
    party = ExportPayloadParty("supplier", "Example Supplier", party_id="party-001")
    line = ExportPayloadLine("line-001", item_code, 2, "10.50", "21.00", description="Service fee")
    return ExportPayload(
        payload_id="payload-001",
        document_id="doc-001",
        tenant_id="tenant-001",
        export_target=target,
        currency="kes",
        lines=(line,),
        document_type="invoice",
        parties=(party,),
        document_date="2026-07-14",
        subtotal="21.00",
        tax_total="0",
        total="21.00",
        metadata={} if metadata is None else metadata,
    )


def test_payload_is_structured_immutable_and_json_safe():
    contract = payload()
    projected = contract.to_dict()

    assert projected["currency"] == "KES"
    assert projected["lines"][0]["quantity"] == "2"
    assert projected["parties"][0]["display_name"] == "Example Supplier"
    assert json.loads(json.dumps(projected))["document_id"] == "doc-001"
    with pytest.raises(FrozenInstanceError):
        contract.document_id = "doc-002"


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_document": "content"},
        {"raw_rows": "content"},
        {"artifact_payload": "content"},
        {"credential": "content"},
        {"safe": {"nested": "value"}},
        {"safe": ["row"]},
    ],
)
def test_payload_metadata_rejects_unsafe_or_non_scalar_values(metadata):
    with pytest.raises(ValueError):
        payload(metadata=metadata)


def test_payload_requires_typed_lines_not_raw_rows():
    target = ExportTarget("erp-main", "erp", "Main ERP")
    with pytest.raises(ValueError, match="invalid items"):
        ExportPayload("payload-001", "doc-001", "tenant-001", target, "KES", ({"raw": "row"},))


def test_payload_fingerprint_is_deterministic_and_content_sensitive():
    first = payload()
    assert payload_fingerprint(first) == payload_fingerprint(first)
    assert payload_fingerprint(first) != payload_fingerprint(payload(item_code="SKU-002"))
    assert len(payload_fingerprint(first)) == 64

