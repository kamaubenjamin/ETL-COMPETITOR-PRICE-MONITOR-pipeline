"""Safe Phase 2 upload validation and read-summary provider."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any

from src.upload_runtime import UploadCommand, UploadValidationResult, validate_upload


_REQUEST_FIELDS = frozenset(
    {
        "upload_id", "filename", "declared_content_type", "file_size_bytes", "file_type",
        "source", "workspace_id", "document_type_hint", "content_fingerprint",
        "operation_version", "requested_at", "correlation_id", "metadata",
    }
)
_SUMMARY_FIELDS = frozenset(
    {"upload_id", "tenant_id", "filename", "file_type", "file_size_bytes", "source", "status", "received_at"}
)


class ReadOnlyUploadProvider:
    """Validate metadata and expose bounded tenant-filtered placeholder summaries."""

    def __init__(self, uploads: Iterable[Mapping[str, Any]] = ()) -> None:
        safe: list[Mapping[str, str | int]] = []
        for upload in uploads:
            if not isinstance(upload, Mapping) or not set(upload).issubset(_SUMMARY_FIELDS):
                raise ValueError("upload summary is invalid")
            projected: dict[str, str | int] = {}
            for key, value in upload.items():
                if isinstance(value, bool) or not isinstance(value, (str, int)):
                    raise ValueError("upload summary is invalid")
                if isinstance(value, str) and (not value or len(value) > 256):
                    raise ValueError("upload summary is invalid")
                if isinstance(value, int) and value < 0:
                    raise ValueError("upload summary is invalid")
                projected[key] = value
            safe.append(MappingProxyType(projected))
        self._uploads = tuple(safe)

    def validate_request(
        self,
        payload: Mapping[str, Any],
        *,
        tenant_id: str | None,
        actor_id: str | None,
        request_id: str | None,
    ) -> tuple[UploadCommand, UploadValidationResult]:
        if not isinstance(payload, Mapping) or not set(payload).issubset(_REQUEST_FIELDS):
            raise ValueError("upload request fields are invalid")
        required = {"filename", "file_size_bytes", "file_type"}
        if not required.issubset(payload):
            raise ValueError("upload request fields are invalid")
        command = UploadCommand(
            upload_id=payload.get("upload_id"),
            tenant_id=tenant_id,
            actor_id=actor_id,
            original_filename=payload["filename"],
            declared_content_type=payload.get("declared_content_type"),
            file_size_bytes=payload["file_size_bytes"],
            file_type=payload["file_type"],
            source=payload.get("source", "api"),
            workspace_id=payload.get("workspace_id"),
            document_type_hint=payload.get("document_type_hint"),
            content_fingerprint=payload.get("content_fingerprint"),
            operation_version=payload.get("operation_version", "v1"),
            requested_at=payload.get("requested_at"),
            correlation_id=payload.get("correlation_id"),
            request_id=request_id,
            metadata=payload.get("metadata", {}),
        )
        return command, validate_upload(command)

    def list_uploads(self, *, tenant_id: str | None = None) -> list[dict[str, str | int]]:
        return [
            {key: value for key, value in item.items() if key != "tenant_id"}
            for item in self._uploads
            if tenant_id is None or item.get("tenant_id") == tenant_id
        ]

    def get_upload(self, upload_id: str, *, tenant_id: str | None = None) -> dict[str, str | int] | None:
        return next(
            (
                {key: value for key, value in item.items() if key != "tenant_id"}
                for item in self._uploads
                if item.get("upload_id") == upload_id and (tenant_id is None or item.get("tenant_id") == tenant_id)
            ),
            None,
        )


empty_upload_provider = ReadOnlyUploadProvider()

