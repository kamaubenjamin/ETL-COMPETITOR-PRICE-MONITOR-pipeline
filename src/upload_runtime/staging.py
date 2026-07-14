"""No-I/O validation of command-to-opaque-artifact binding."""

from __future__ import annotations

from dataclasses import dataclass

from .commands import UploadCommand
from .contracts import UploadArtifactReference, UploadContract
from .validation import UploadValidationResult


@dataclass(frozen=True, slots=True)
class ValidatedStagedUpload(UploadContract):
    command: UploadCommand
    validation: UploadValidationResult
    artifact_reference: UploadArtifactReference

    def __post_init__(self) -> None:
        if not isinstance(self.command, UploadCommand):
            raise ValueError("command is invalid")
        if not isinstance(self.validation, UploadValidationResult) or not self.validation.valid:
            raise ValueError("successful validation is required")
        if not isinstance(self.artifact_reference, UploadArtifactReference):
            raise ValueError("artifact_reference is invalid")
        if self.artifact_reference.file_type != self.command.file_type:
            raise ValueError("artifact file type does not match command")
        if self.artifact_reference.size_bytes != self.command.file_size_bytes:
            raise ValueError("artifact size does not match command")

