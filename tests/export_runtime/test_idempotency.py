import pytest

from src.export_runtime import ExportIdempotencyKey, generate_export_idempotency_key


def make_key(fingerprint: str = "a" * 64) -> ExportIdempotencyKey:
    return generate_export_idempotency_key(
        tenant_id="tenant-001",
        document_id="doc-001",
        export_target="erp-main",
        payload_fingerprint=fingerprint,
        operation_type="export",
        operation_version="v1",
    )


def test_idempotency_key_is_deterministic_and_opaque():
    first = make_key()
    second = make_key()
    assert first == second
    assert str(first).startswith("exp_v1_")
    assert "tenant-001" not in str(first)
    assert "doc-001" not in str(first)
    assert "erp-main" not in str(first)
    assert "a" * 64 not in str(first)


def test_changed_payload_fingerprint_changes_key():
    assert make_key("a" * 64) != make_key("b" * 64)


@pytest.mark.parametrize(
    "changes",
    [
        {"tenant_id": "tenant-002"},
        {"document_id": "doc-002"},
        {"export_target": "erp-secondary"},
        {"operation_type": "retry"},
        {"operation_version": "v2"},
    ],
)
def test_each_stable_input_partitions_the_key(changes):
    inputs = {
        "tenant_id": "tenant-001",
        "document_id": "doc-001",
        "export_target": "erp-main",
        "payload_fingerprint": "a" * 64,
        "operation_type": "export",
        "operation_version": "v1",
    }
    baseline = generate_export_idempotency_key(**inputs)
    inputs.update(changes)
    assert generate_export_idempotency_key(**inputs) != baseline


def test_unsafe_or_non_digest_inputs_are_rejected():
    with pytest.raises(ValueError):
        generate_export_idempotency_key(
            tenant_id=r"C:\private", document_id="doc-001", export_target="erp-main",
            payload_fingerprint="raw payload content", operation_type="export",
        )

