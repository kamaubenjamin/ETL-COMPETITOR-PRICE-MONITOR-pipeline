import pytest

from src.export_runtime import (
    ExportIdempotencyPolicy,
    ExportPayloadBuildCommand,
    ExportPayloadLine,
    ExportTarget,
    build_export_payload,
    fingerprint_export_payload,
    payload_readiness_issues,
)


def built_payload():
    result = build_export_payload(
        ExportPayloadBuildCommand(
            document_id="doc-001",
            tenant_id="tenant-001",
            export_target=ExportTarget("erp-main", "erp", "Main ERP"),
            currency="KES",
            lines=(ExportPayloadLine("line-001", "SKU-001", 1, 10, 10),),
        )
    )
    assert result.payload is not None
    return result.payload


def test_policy_builds_deterministic_opaque_key_from_payload():
    payload = built_payload()
    policy = ExportIdempotencyPolicy()

    first = policy.key_for_payload(payload)
    second = policy.key_for_payload(payload)

    assert first == second
    assert "tenant-001" not in first.value
    assert "doc-001" not in first.value
    assert "erp-main" not in first.value


def test_key_changes_for_fingerprint_target_and_operation_version():
    payload = built_payload()
    digest = fingerprint_export_payload(payload)
    baseline = ExportIdempotencyPolicy().key_for_inputs(
        tenant_id="tenant-001",
        document_id="doc-001",
        export_target="erp-main",
        payload_fingerprint=digest,
    )

    assert baseline != ExportIdempotencyPolicy().key_for_inputs(
        tenant_id="tenant-001", document_id="doc-001", export_target="erp-main", payload_fingerprint="b" * 64
    )
    assert baseline != ExportIdempotencyPolicy().key_for_inputs(
        tenant_id="tenant-001", document_id="doc-001", export_target="erp-secondary", payload_fingerprint=digest
    )
    assert baseline != ExportIdempotencyPolicy(operation_version="v2").key_for_inputs(
        tenant_id="tenant-001", document_id="doc-001", export_target="erp-main", payload_fingerprint=digest
    )


def test_policy_rejects_unsafe_raw_input():
    with pytest.raises(ValueError):
        ExportIdempotencyPolicy().key_for_inputs(
            tenant_id=r"C:\private\tenant.json",
            document_id="doc-001",
            export_target="erp-main",
            payload_fingerprint="a" * 64,
        )


def test_payload_validity_links_to_blocking_readiness_issue():
    target = ExportTarget("erp-main", "erp", "Main ERP")
    success = build_export_payload(
        ExportPayloadBuildCommand("doc-001", "tenant-001", target, "KES", (ExportPayloadLine("line-1", "SKU-1", 1, 1, 1),))
    )
    failure = build_export_payload(ExportPayloadBuildCommand(None, "tenant-001", target, "KES", ()))

    assert payload_readiness_issues(success) == ()
    assert [issue.code for issue in payload_readiness_issues(failure)] == ["payload_invalid"]

