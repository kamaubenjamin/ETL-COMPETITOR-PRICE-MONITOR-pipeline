from src.upload_runtime import UploadActivationResult, UploadResult, project_activation_result, project_progress_summary, project_upload_result


NOW = "2026-07-14T10:00:00Z"


def test_activation_projection_uses_only_recorded_stage():
    result = UploadActivationResult("upload-1", "document-1", "ingestion_requested", "ingestion_accepted", "received", True)
    summary = project_activation_result(result, occurred_at=NOW)
    assert summary.current_stage == "ingestion_requested"
    assert summary.status == "ingestion_requested"
    assert summary.current_stage != "processing_started"


def test_upload_failure_projection_uses_fixed_safe_summary():
    result = UploadResult("failed", upload_id="upload-1", error_code="internal_error")
    summary = project_upload_result(result, occurred_at=NOW)
    assert summary.failure.summary == "Processing could not be completed."


def test_progress_is_omitted_when_source_facts_are_insufficient():
    summary = project_progress_summary(
        upload_id="upload-1", status="received", started_at=NOW, progress_is_derivable=False,
    )
    assert summary.progress_percent is None
    assert summary.progress_approximate is False


def test_progress_percentage_is_deterministic_and_marked_approximate():
    first = project_progress_summary(upload_id="upload-1", status="staged", started_at=NOW)
    second = project_progress_summary(upload_id="upload-1", status="staged", started_at=NOW)
    assert first.progress_percent == second.progress_percent
    assert first.progress_approximate is True

