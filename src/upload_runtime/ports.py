"""Structural no-I/O ports for future upload artifact staging."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .commands import UploadCommand
from .contracts import UploadArtifactReference
from .validation import UploadValidationResult


@runtime_checkable
class UploadArtifactStagingPort(Protocol):
    """Stage one validated upload and return an opaque safe reference."""

    def stage(self, command: UploadCommand, validation: UploadValidationResult) -> UploadArtifactReference: ...

