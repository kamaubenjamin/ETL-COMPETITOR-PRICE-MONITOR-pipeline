import json

import pytest

from src.export_runtime import (
    PAYLOAD_FINGERPRINT_DOMAIN,
    ExportPayload,
    ExportPayloadLine,
    ExportTarget,
    canonical_payload_json,
    fingerprint_export_payload,
)


def payload(**changes):
    values = {
        "payload_id": "payload-001",
        "document_id": "doc-001",
        "tenant_id": "tenant-001",
        "export_target": ExportTarget("erp-main", "erp", "Main ERP"),
        "currency": "KES",
        "lines": (ExportPayloadLine("line-001", "SKU-001", 2, 10.5, 21),),
        "external_reference": "ref-001",
        "subtotal": 21,
        "total": 21,
        "metadata": {"zeta": "last", "alpha": "first"},
    }
    values.update(changes)
    return ExportPayload(**values)


def test_payload_fingerprint_is_domain_separated_deterministic_and_opaque():
    contract = payload()
    fingerprint = fingerprint_export_payload(contract)

    assert fingerprint == fingerprint_export_payload(contract)
    assert len(fingerprint) == 64
    assert "doc-001" not in fingerprint
    assert "SKU-001" not in fingerprint
    assert PAYLOAD_FINGERPRINT_DOMAIN in json.loads(canonical_payload_json(contract))


def test_payload_fingerprint_is_stable_across_metadata_ordering():
    first = payload(metadata={"alpha": "first", "zeta": "last"})
    second = payload(metadata={"zeta": "last", "alpha": "first"})

    assert fingerprint_export_payload(first) == fingerprint_export_payload(second)


@pytest.mark.parametrize(
    "change",
    [
        {"external_reference": "ref-002"},
        {"total": 22},
        {"lines": (ExportPayloadLine("line-001", "SKU-002", 2, 10.5, 21),)},
        {"export_target": ExportTarget("erp-secondary", "erp", "Secondary ERP")},
    ],
)
def test_payload_fingerprint_changes_with_export_content(change):
    assert fingerprint_export_payload(payload()) != fingerprint_export_payload(payload(**change))


@pytest.mark.parametrize("candidate", [None, {}, "raw payload", object()])
def test_fingerprint_rejects_non_payload_values(candidate):
    with pytest.raises(ValueError, match="ExportPayload"):
        canonical_payload_json(candidate)

