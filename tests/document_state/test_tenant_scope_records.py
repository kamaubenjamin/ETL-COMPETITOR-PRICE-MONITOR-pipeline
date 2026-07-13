import json

import pytest

from src.document_state import DocumentRecord, LEGACY_TENANT_ID


TS = "2026-07-13T12:00:00+00:00"


def test_document_record_accepts_safe_tenant_and_ownership_fields():
    record = DocumentRecord(
        "doc-tenant-001",
        "invoice.pdf",
        "invoice",
        "received",
        0.95,
        "ingest",
        TS,
        TS,
        TS,
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        created_by="principal-create",
        updated_by="principal-update",
        owner_principal_id="principal-owner",
        source_system="upload_runtime",
        access_tags=("finance", "accounts-payable", "finance"),
    )
    payload = record.to_dict()
    assert payload["tenant_id"] == "tenant-a"
    assert payload["workspace_id"] == "workspace-a"
    assert payload["created_by"] == "principal-create"
    assert payload["updated_by"] == "principal-update"
    assert payload["owner_principal_id"] == "principal-owner"
    assert payload["source_system"] == "upload_runtime"
    assert payload["access_tags"] == ["accounts-payable", "finance"]
    json.dumps(payload)


def test_document_record_without_tenant_fields_uses_legacy_local_tenant():
    record = DocumentRecord(
        "doc-legacy-001", "legacy.pdf", "invoice", "received", 0.9,
        "ingest", TS, TS, TS,
    )
    assert record.tenant_id == LEGACY_TENANT_ID
    assert record.workspace_id is None
    assert record.access_tags == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_id", ""),
        ("workspace_id", "bad\nworkspace"),
        ("created_by", "x" * 129),
        ("access_tags", ("",)),
    ],
)
def test_document_record_rejects_unsafe_scope_fields(field, value):
    values = {field: value}
    with pytest.raises(ValueError):
        DocumentRecord(
            "doc-invalid-001", "invalid.pdf", "invoice", "received", 0.9,
            "ingest", TS, TS, TS, **values,
        )
