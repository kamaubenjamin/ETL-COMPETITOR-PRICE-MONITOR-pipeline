"""Domain-separated deterministic upload idempotency keys."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .commands import UploadCommand
from .contracts import UploadContract, sha256_digest
from .validation import validate_upload


@dataclass(frozen=True, slots=True)
class UploadIdempotencyKey(UploadContract):
    value: str
    operation_version: str = "v1"

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.startswith("upl_") or len(self.value) != 68:
            raise ValueError("idempotency key is invalid")
        sha256_digest(self.value[4:], "idempotency key digest")
        if not isinstance(self.operation_version, str) or not self.operation_version:
            raise ValueError("operation_version is invalid")


def upload_idempotency_key(command: UploadCommand) -> UploadIdempotencyKey:
    if not isinstance(command, UploadCommand):
        raise ValueError("command must be an UploadCommand")
    validation = validate_upload(command)
    if not validation.valid:
        raise ValueError("command must pass upload validation")
    canonical = json.dumps(
        {
            "domain": "idp.upload.idempotency.v1",
            "tenant": command.tenant_id,
            "actor": command.actor_id,
            "filename": command.original_filename,
            "size": command.file_size_bytes,
            "file_type": command.file_type,
            "content_fingerprint": command.content_fingerprint,
            "operation_version": command.operation_version,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return UploadIdempotencyKey(f"upl_{digest}", command.operation_version or "v1")

