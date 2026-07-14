import json

import pytest

from src.export_runtime import ExportError, ExportErrorCode, ExportPermission


def test_export_error_uses_fixed_safe_message_and_discards_raw_detail():
    raw = r"Traceback token=abc at C:\private\adapter.py"
    error = ExportError("adapter_failed", field="adapter", message=raw)
    projected = error.to_dict()

    assert projected["code"] == "adapter_failed"
    assert projected["detail_was_sanitized"] is True
    assert raw not in str(error)
    assert raw not in json.dumps(projected)


def test_export_error_codes_are_stable_and_unknown_codes_reject():
    assert ExportErrorCode.INTERNAL_ERROR.value == "internal_error"
    with pytest.raises(ValueError, match="unsupported export error code"):
        ExportError("raw_database_error")
    with pytest.raises(ValueError):
        ExportError("internal_error", field=r"C:\private")


def test_permission_contract_records_outcome_without_deciding_it():
    outcome = ExportPermission("doc-001", "tenant-001", False, "permission_denied")
    assert outcome.to_dict() == {
        "document_id": "doc-001",
        "tenant_id": "tenant-001",
        "allowed": False,
        "reason_code": "permission_denied",
        "permission": "document:export",
        "service_account": False,
        "cross_tenant": False,
    }
    with pytest.raises(ValueError, match="document:export"):
        ExportPermission("doc-001", "tenant-001", True, "allowed", permission="document:admin")

