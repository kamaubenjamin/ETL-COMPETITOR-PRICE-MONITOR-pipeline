from dataclasses import FrozenInstanceError
import json

import pytest

from src.export_runtime import (
    ExportReadinessIssue,
    ExportReadinessResult,
    ExportStatus,
    ExportTarget,
)


def target() -> ExportTarget:
    return ExportTarget("erp-main", "erp", "Main ERP", metadata={"region": "local"})


def test_no_blocking_issues_is_ready_and_json_safe():
    result = ExportReadinessResult(document_id="doc-001", target=target())

    assert result.ready is True
    assert result.status == ExportStatus.READY.value
    assert result.safe_summary == "Export is ready."
    assert json.loads(json.dumps(result.to_dict()))["target"]["target_id"] == "erp-main"


def test_blocking_issue_makes_result_not_ready():
    issue = ExportReadinessIssue("validation_not_passed", field="validation")
    result = ExportReadinessResult("doc-001", target(), blocking_issues=(issue,))

    assert result.ready is False
    assert result.status == "not_ready"
    assert result.blocking_issues[0].message == "Document validation has blocking issues."


def test_warnings_alone_preserve_ready_state():
    warning = ExportReadinessIssue("matching_not_completed", field="matching")
    result = ExportReadinessResult("doc-001", target(), warning_issues=(warning,))

    assert result.ready is True
    assert result.safe_summary == "Export is ready with warnings."


def test_missing_target_requires_explicit_blocking_issue():
    with pytest.raises(ValueError, match="missing target"):
        ExportReadinessResult("doc-001", None)

    result = ExportReadinessResult(
        "doc-001",
        None,
        blocking_issues=(ExportReadinessIssue("export_target_missing"),),
    )
    assert result.ready is False


def test_readiness_contracts_are_immutable_and_messages_are_fixed():
    issue = ExportReadinessIssue("permission_denied")
    with pytest.raises(FrozenInstanceError):
        issue.code = "internal_error"
    assert "claim" not in issue.message.lower()

