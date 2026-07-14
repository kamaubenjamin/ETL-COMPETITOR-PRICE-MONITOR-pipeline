import json

from src.upload_runtime import (
    DocumentStateWriteReceipt,
    IngestionActivationReceipt,
    UploadActivationService,
    UploadArtifactReference,
    UploadCommand,
    validate_upload,
)


NOW = "2026-07-14T10:00:00Z"


class ExplodingState:
    def record_received(self, intent):
        raise RuntimeError(r"private token at C:\backend\artifact.pdf")


class Ingestion:
    def __init__(self):
        self.calls = 0

    def request_ingestion(self, intent):
        self.calls += 1
        return IngestionActivationReceipt(True, "accepted")


def test_integration_exception_is_safely_mapped_without_raw_details():
    ingestion = Ingestion()
    runtime = UploadActivationService(ingestion=ingestion, document_state=ExplodingState(), clock=lambda: NOW)
    command = UploadCommand("upload-001", "tenant-001", "actor-001", "invoice.pdf", 100, "pdf", "api")
    result = runtime.activate(command, validate_upload(command), UploadArtifactReference("artifact-001", "test_placeholder", "pdf", 100, NOW))
    serialized = json.dumps(result.to_dict()).lower()
    assert result.status == "failed"
    assert result.reason_code == "activation_failed"
    assert ingestion.calls == 0
    for forbidden in ("private token", "c:\\backend", "artifact.pdf", "stack", "traceback"):
        assert forbidden not in serialized


def test_opaque_reference_never_exposes_backend_location():
    reference = UploadArtifactReference("artifact-opaque", "test_placeholder", "pdf", 100, NOW)
    assert set(reference.to_dict()) == {"reference_id", "provider_code", "file_type", "size_bytes", "staged_at"}

