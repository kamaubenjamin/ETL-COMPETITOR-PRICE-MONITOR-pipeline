"""Repository-neutral lifecycle snapshot advancement service."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..errors import DocumentStateError
from ..records import DocumentRecord
from ..repositories import DocumentReadRepository, DocumentWriteRepository
from .contracts import LifecyclePolicyOutcome, LifecycleTransitionRequest
from .errors import LifecycleErrorCode
from .policy import evaluate_transition
from .results import LifecycleResultStatus, LifecycleTransitionResult


def _result(
    request: LifecycleTransitionRequest,
    status: LifecycleResultStatus,
    *,
    new_version: int | None = None,
    error_code: LifecycleErrorCode | None = None,
) -> LifecycleTransitionResult:
    return LifecycleTransitionResult(
        status=status,
        document_id=request.document_id,
        lifecycle_event_id=request.lifecycle_event_id,
        source_status=request.source_status,
        target_status=request.target_status,
        expected_version=request.expected_version,
        new_version=new_version,
        error_code=error_code,
    )


def _conflict(request: LifecycleTransitionRequest, event_persisted: bool) -> LifecycleTransitionResult:
    status = LifecycleResultStatus.PROJECTION_PENDING if event_persisted else LifecycleResultStatus.CONFLICT
    return _result(request, status, error_code=LifecycleErrorCode.VERSION_CONFLICT)


def _repository_failure(
    request: LifecycleTransitionRequest,
    error: DocumentStateError,
    *,
    event_persisted: bool,
) -> LifecycleTransitionResult:
    if error.code == "not_found":
        return _result(request, LifecycleResultStatus.REJECTED, error_code=LifecycleErrorCode.MISSING_DOCUMENT)
    if error.code == "conflict":
        return _conflict(request, event_persisted)
    if error.code == "source_unavailable":
        return _result(request, LifecycleResultStatus.FAILED, error_code=LifecycleErrorCode.REPOSITORY_UNAVAILABLE)
    return _result(request, LifecycleResultStatus.FAILED, error_code=LifecycleErrorCode.INTERNAL_ERROR)


class LifecycleAdvancementService:
    """Advance the mutable document projection through injected repository ports."""

    __slots__ = ("__reader", "__writer")

    def __init__(self, reader: DocumentReadRepository, writer: DocumentWriteRepository) -> None:
        if not isinstance(reader, DocumentReadRepository):
            raise ValueError("reader must implement DocumentReadRepository")
        if not isinstance(writer, DocumentWriteRepository):
            raise ValueError("writer must implement DocumentWriteRepository")
        self.__reader = reader
        self.__writer = writer

    def advance(
        self,
        request: LifecycleTransitionRequest,
        *,
        lifecycle_event_persisted: bool = False,
    ) -> LifecycleTransitionResult:
        if not isinstance(request, LifecycleTransitionRequest):
            raise ValueError("request must be a LifecycleTransitionRequest")
        if not isinstance(lifecycle_event_persisted, bool):
            raise ValueError("lifecycle_event_persisted must be a boolean")

        try:
            current = self.__reader.get_document(request.document_id)
        except DocumentStateError as error:
            return _repository_failure(request, error, event_persisted=lifecycle_event_persisted)
        except Exception:
            return _result(request, LifecycleResultStatus.FAILED, error_code=LifecycleErrorCode.INTERNAL_ERROR)

        if current.status == request.target_status:
            return _result(request, LifecycleResultStatus.NO_OP)
        if current.version != request.expected_version:
            return _conflict(request, lifecycle_event_persisted)
        if current.status != request.source_status:
            return _result(
                request,
                LifecycleResultStatus.REJECTED,
                error_code=LifecycleErrorCode.INVALID_TRANSITION,
            )

        decision = evaluate_transition(request)
        if decision.outcome == LifecyclePolicyOutcome.NO_OP.value:
            return _result(request, LifecycleResultStatus.NO_OP)
        if decision.outcome == LifecyclePolicyOutcome.REJECTED.value:
            return _result(
                request,
                LifecycleResultStatus.REJECTED,
                error_code=LifecycleErrorCode.INVALID_TRANSITION,
            )

        source_stage = request.source_stage
        if source_stage is None:
            metadata_stage: Any = request.metadata.get("source_stage")
            source_stage = metadata_stage if isinstance(metadata_stage, str) else request.target_status
        updated = replace(
            current,
            status=request.target_status,
            current_stage=source_stage,
            updated_at=request.occurred_at,
            version=request.expected_version + 1,
        )
        try:
            persisted = self.__writer.update_document(updated, expected_version=request.expected_version)
        except DocumentStateError as error:
            return _repository_failure(request, error, event_persisted=lifecycle_event_persisted)
        except Exception:
            return _result(request, LifecycleResultStatus.FAILED, error_code=LifecycleErrorCode.INTERNAL_ERROR)

        if not isinstance(persisted, DocumentRecord) or persisted.version != request.expected_version + 1:
            return _result(request, LifecycleResultStatus.FAILED, error_code=LifecycleErrorCode.INTERNAL_ERROR)
        return _result(request, LifecycleResultStatus.ADVANCED, new_version=persisted.version)
