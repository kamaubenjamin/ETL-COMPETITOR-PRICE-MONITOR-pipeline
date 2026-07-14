"""Structural producer and Document State integration ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .contracts import UploadContract, safe_code, stable_id
from .processing import UploadDocumentStateWriteIntent, UploadIngestionActivationIntent


@dataclass(frozen=True, slots=True)
class IngestionActivationReceipt(UploadContract):
    accepted: bool
    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a boolean")
        object.__setattr__(self, "code", safe_code(self.code, "code"))


@dataclass(frozen=True, slots=True)
class DocumentStateWriteReceipt(UploadContract):
    recorded: bool
    document_id: str
    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.recorded, bool):
            raise ValueError("recorded must be a boolean")
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))
        object.__setattr__(self, "code", safe_code(self.code, "code"))


@runtime_checkable
class UploadIngestionActivationPort(Protocol):
    def request_ingestion(self, intent: UploadIngestionActivationIntent) -> IngestionActivationReceipt: ...


@runtime_checkable
class UploadDocumentStateWriterPort(Protocol):
    def record_received(self, intent: UploadDocumentStateWriteIntent) -> DocumentStateWriteReceipt: ...

