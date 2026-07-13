import json
from dataclasses import FrozenInstanceError

import pytest

from src.document_state.writers.commands import (
    AppendLifecycleEventCommand,
    ArtifactReference,
    CreateDocumentCommand,
    MatchingSummaryInput,
    ValidationIssueInput,
    WriteAuditEventCommand,
    WriteCorrectionSummaryCommand,
    WriteMatchingSummariesCommand,
    WriteProcessingSnapshotCommand,
    WriteReprocessPlanCommand,
    WriteReviewSummaryCommand,
    WriteValidationIssuesCommand,
    WriteWorkflowRunCommand,
)


NOW = "2026-07-13T09:00:00+00:00"


def test_commands_are_immutable_and_json_compatible():
    artifact = ArtifactReference("artifact-001", "normalized_document", "document_engine", "a" * 64)
    commands = (
        CreateDocumentCommand("doc-001", "source-001", "invoice.pdf", "invoice", 0.9, NOW, NOW, "document_engine", artifact),
        AppendLifecycleEventCommand("event-001", "source-001", "doc-001", "received", NOW, "document_engine", "ingestion"),
        WriteProcessingSnapshotCommand("snapshot-001", "source-002", "doc-001", "run-001", "classification", "succeeded", NOW, NOW, completed_at=NOW, duration_ms=5, artifact_reference=artifact),
        WriteValidationIssuesCommand("source-003", "doc-001", "validation-001", (ValidationIssueInput("issue-001", "warning", "invoice_number", "required", "missing", "Required field is missing.", NOW),)),
        WriteMatchingSummariesCommand("source-004", "doc-001", "matching-001", (MatchingSummaryInput("match-001", "supplier", "candidate-001", 0.8, "ambiguous", NOW),)),
        WriteReviewSummaryCommand("source-005", "review-001", "doc-001", "invalid_data", "high", "review_required", NOW, NOW),
        WriteCorrectionSummaryCommand("source-006", "correction-001", "review-001", "doc-001", "invoice.total", "replace", "invalid_data", "reviewer-001", NOW, "review"),
        WriteReprocessPlanCommand("source-007", "plan-001", "review-001", "doc-001", "validate_data", "matching", 1, 2, "corrected_data", "reviewer-001", NOW),
        WriteWorkflowRunCommand("source-008", "run-001", "invoice_processing", "succeeded", NOW, NOW, NOW, completed_at=NOW, stage_count=2, succeeded_stage_count=2),
        WriteAuditEventCommand("source-009", "audit-001", "workflow_run_completed", "system", NOW, document_id="doc-001", workflow_run_id="run-001", metadata={"stage_count": 2}),
    )

    for command in commands:
        json.dumps(command.to_dict())
        with pytest.raises(FrozenInstanceError):
            command.source_event_id = "changed"


def test_issue_and_matching_collections_are_copied_and_deterministically_ordered():
    issues = [
        ValidationIssueInput("issue-002", "error", "total", "max", "too_large", "Value exceeds limit.", NOW),
        ValidationIssueInput("issue-001", "warning", "date", "required", "missing", "Required field is missing.", NOW),
    ]
    matches = [
        MatchingSummaryInput("match-002", "supplier", "candidate-b", 0.8, "ambiguous", NOW),
        MatchingSummaryInput("match-001", "supplier", "candidate-a", 0.9, "matched", NOW),
    ]
    issue_command = WriteValidationIssuesCommand("source-001", "doc-001", "validation-001", tuple(issues))
    match_command = WriteMatchingSummariesCommand("source-002", "doc-001", "matching-001", tuple(matches))

    issues.clear()
    matches.clear()
    assert [item.issue_id for item in issue_command.issues] == ["issue-001", "issue-002"]
    assert [item.match_id for item in match_command.summaries] == ["match-001", "match-002"]


@pytest.mark.parametrize("metadata", [
    {"raw_rows": "private"},
    {"document_content": "private"},
    {"new_value": "private"},
    {"artifact_payload": "private"},
    {"stack_trace": "private"},
    {"storage_path": "C:/private"},
    {"credentials": "private"},
])
def test_unsafe_metadata_is_rejected(metadata):
    with pytest.raises(ValueError):
        WriteAuditEventCommand("source-001", "audit-001", "safe_event", "system", NOW, metadata=metadata)


@pytest.mark.parametrize("artifact_id", ["C:/private/document.pdf", "https://example.test/file", "user:secret@example.test"])
def test_artifact_references_reject_paths_urls_and_credentials(artifact_id):
    with pytest.raises(ValueError):
        ArtifactReference(artifact_id, "document", "producer")


def test_artifact_reference_contains_only_opaque_safe_fields():
    reference = ArtifactReference("artifact-001", "normalized_document", "document_engine", "sha256:" + "b" * 64)
    assert reference.to_dict() == {
        "artifact_id": "artifact-001",
        "artifact_kind": "normalized_document",
        "producer": "document_engine",
        "checksum": "sha256:" + "b" * 64,
    }


def test_correction_command_has_no_raw_value_fields():
    command = WriteCorrectionSummaryCommand("source-001", "correction-001", "review-001", "doc-001", "invoice.total", "replace", "invalid_data", "reviewer-001", NOW, "review")
    assert "old_value" not in command.to_dict()
    assert "new_value" not in command.to_dict()
    with pytest.raises(TypeError):
        WriteCorrectionSummaryCommand(
            "source-001", "correction-001", "review-001", "doc-001", "invoice.total", "replace", "invalid_data", "reviewer-001", NOW, "review", new_value="private"
        )


def test_expected_versions_are_explicit_and_validated():
    update = WriteProcessingSnapshotCommand("snapshot-001", "source-001", "doc-001", "run-001", "validation", "running", NOW, NOW, expected_version=2)
    assert update.expected_version == 2
    with pytest.raises(ValueError):
        WriteProcessingSnapshotCommand("snapshot-001", "source-001", "doc-001", "run-001", "validation", "running", NOW, NOW, expected_version=0)
