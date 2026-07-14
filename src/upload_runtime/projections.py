"""Pure projections from safe upload facts to progress read models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import UploadStatus, optional_id, optional_text, optional_timestamp, safe_code, stable_id
from .processing import UploadActivationResult, UploadProcessingStatus
from .progress import UploadProgressStatus, approximate_progress
from .read_models import (
    UploadProcessingFailure,
    UploadProgressEvent,
    UploadProgressSummary,
    UploadProcessingTimeline,
)
from .results import UploadResult


_STATUS_STAGE = {
    "received": "received",
    "validation_failed": "received",
    "validated": "validated",
    "staged": "staged",
    "document_state_recorded": "document_state_recorded",
    "ingestion_requested": "ingestion_requested",
    "processing_started": "processing_started",
    "completed": "completed",
    "failed": "failed",
    "duplicate_prevented": "received",
    "deferred_staging_required": "validated",
    "unsupported_activation": "validated",
}


_SAFE_FAILURE_SUMMARIES = {
    "validation_failed": "Upload validation failed.",
    "activation_failed": "Upload activation failed.",
    "document_state_rejected": "Document state recording was not accepted.",
    "ingestion_rejected": "Ingestion request was not accepted.",
    "internal_error": "Processing could not be completed.",
}


def _failure(code: str | None) -> UploadProcessingFailure:
    safe = safe_code(code or "internal_error", "failure code")
    return UploadProcessingFailure(safe, _SAFE_FAILURE_SUMMARIES.get(safe, "Processing could not be completed."))


def project_progress_summary(
    *,
    upload_id: str,
    status: UploadProcessingStatus | UploadProgressStatus | UploadStatus | str,
    started_at: str,
    updated_at: str | None = None,
    document_id: str | None = None,
    completed_at: str | None = None,
    failure_code: str | None = None,
    source_label: str | None = None,
    actor_label: str | None = None,
    progress_is_derivable: bool = True,
) -> UploadProgressSummary:
    value = status.value if isinstance(status, (UploadProcessingStatus, UploadProgressStatus, UploadStatus)) else status
    try:
        normalized = UploadProgressStatus(value)
    except (TypeError, ValueError):
        raise ValueError("processing status is invalid") from None
    stage = _STATUS_STAGE[normalized.value]
    progress = approximate_progress(stage, sufficient=progress_is_derivable)
    failure = _failure(failure_code) if normalized in {UploadProgressStatus.FAILED, UploadProgressStatus.VALIDATION_FAILED} else None
    return UploadProgressSummary(
        upload_id=upload_id,
        document_id=document_id,
        status=normalized,
        current_stage=stage,
        started_at=started_at,
        updated_at=updated_at or started_at,
        completed_at=completed_at,
        progress_percent=progress,
        progress_approximate=progress is not None and stage != "completed",
        failure=failure,
        source_label=source_label,
        actor_label=actor_label,
    )


def project_upload_result(result: UploadResult, *, occurred_at: str) -> UploadProgressSummary:
    if not isinstance(result, UploadResult) or result.upload_id is None:
        raise ValueError("upload result cannot be projected")
    return project_progress_summary(
        upload_id=result.upload_id,
        document_id=result.processing_intent.document_id if result.processing_intent else None,
        status=result.status,
        started_at=occurred_at,
        failure_code=result.error_code,
    )


def project_activation_result(result: UploadActivationResult, *, occurred_at: str) -> UploadProgressSummary:
    if not isinstance(result, UploadActivationResult) or result.upload_id is None:
        raise ValueError("activation result cannot be projected")
    return project_progress_summary(
        upload_id=result.upload_id,
        document_id=result.document_id,
        status=result.status,
        started_at=occurred_at,
        failure_code=result.reason_code if result.status == "failed" else None,
    )


def project_safe_upload_summary(source: Mapping[str, Any]) -> UploadProgressSummary:
    """Project only the allowlisted safe facts used by the API placeholder provider."""
    if not isinstance(source, Mapping):
        raise ValueError("upload summary is invalid")
    allowed = {
        "upload_id", "document_id", "status", "received_at", "updated_at", "completed_at",
        "failure_code", "source", "actor_label", "progress_is_derivable",
    }
    facts = {key: source[key] for key in allowed if key in source}
    required = {"upload_id", "status", "received_at"}
    if not required.issubset(facts):
        raise ValueError("upload summary is invalid")
    progress_is_derivable = facts.get("progress_is_derivable", True)
    if not isinstance(progress_is_derivable, bool):
        raise ValueError("progress_is_derivable must be a boolean")
    return project_progress_summary(
        upload_id=stable_id(facts["upload_id"], "upload_id"),
        document_id=optional_id(facts.get("document_id"), "document_id"),
        status=facts["status"],
        started_at=optional_timestamp(facts["received_at"], "received_at") or "",
        updated_at=optional_timestamp(facts.get("updated_at"), "updated_at"),
        completed_at=optional_timestamp(facts.get("completed_at"), "completed_at"),
        failure_code=facts.get("failure_code"),
        source_label=optional_text(facts.get("source"), "source", maximum=64),
        actor_label=optional_text(facts.get("actor_label"), "actor_label", maximum=64),
        progress_is_derivable=progress_is_derivable,
    )


def project_timeline(upload_id: str, events: tuple[UploadProgressEvent, ...]) -> UploadProcessingTimeline:
    return UploadProcessingTimeline(upload_id=upload_id, events=events)
