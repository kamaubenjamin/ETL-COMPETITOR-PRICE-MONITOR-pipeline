"""Safe caller-supplied upload activation command."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .contracts import (
    MAX_FILENAME_INPUT_LENGTH,
    UploadContract,
    UploadFileType,
    UploadSource,
    bounded_text,
    non_negative_integer,
    optional_id,
    optional_text,
    optional_timestamp,
    safe_metadata,
    stable_id,
)


@dataclass(frozen=True, slots=True)
class UploadCommand(UploadContract):
    upload_id: str | None
    tenant_id: str | None
    actor_id: str | None
    original_filename: str
    file_size_bytes: int
    file_type: UploadFileType | str
    source: UploadSource | str
    declared_content_type: str | None = None
    workspace_id: str | None = None
    document_type_hint: str | None = None
    content_fingerprint: str | None = None
    operation_version: str = "v1"
    requested_at: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for name in ("upload_id", "tenant_id", "actor_id", "workspace_id", "correlation_id", "request_id"):
            object.__setattr__(self, name, optional_id(getattr(self, name), name))
        object.__setattr__(self, "original_filename", bounded_text(self.original_filename, "original_filename", maximum=MAX_FILENAME_INPUT_LENGTH))
        object.__setattr__(self, "file_size_bytes", non_negative_integer(self.file_size_bytes, "file_size_bytes"))
        raw_type = self.file_type.value if isinstance(self.file_type, UploadFileType) else bounded_text(self.file_type, "file_type", maximum=32).lower().lstrip(".")
        object.__setattr__(self, "file_type", raw_type)
        try:
            source = self.source if isinstance(self.source, UploadSource) else UploadSource(self.source)
        except (TypeError, ValueError):
            raise ValueError("source is invalid") from None
        object.__setattr__(self, "source", source.value)
        object.__setattr__(self, "declared_content_type", optional_text(self.declared_content_type, "declared_content_type", maximum=128))
        object.__setattr__(self, "document_type_hint", optional_text(self.document_type_hint, "document_type_hint", maximum=64))
        if self.content_fingerprint is not None:
            from .contracts import sha256_digest
            object.__setattr__(self, "content_fingerprint", sha256_digest(self.content_fingerprint))
        object.__setattr__(self, "operation_version", stable_id(self.operation_version, "operation_version"))
        object.__setattr__(self, "requested_at", optional_timestamp(self.requested_at, "requested_at"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))
