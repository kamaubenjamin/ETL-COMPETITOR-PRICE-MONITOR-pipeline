from src.upload_runtime import (
    DocumentStateWriteReceipt,
    IngestionActivationReceipt,
    UploadActivationService,
    UploadArtifactReference,
    UploadCommand,
    validate_upload,
)


NOW = "2026-07-14T10:00:00Z"


def command(**overrides):
    values = dict(
        upload_id="upload-001", tenant_id="tenant-001", actor_id="actor-001",
        original_filename="invoice.pdf", file_size_bytes=100, file_type="pdf", source="api",
        declared_content_type="application/pdf", requested_at=NOW, document_type_hint="invoice",
        content_fingerprint="a" * 64,
    )
    values.update(overrides)
    return UploadCommand(**values)


def artifact(**overrides):
    values = dict(reference_id="artifact-001", provider_code="test_placeholder", file_type="pdf", size_bytes=100, staged_at=NOW)
    values.update(overrides)
    return UploadArtifactReference(**values)


class FakeState:
    def __init__(self, recorded=True):
        self.recorded = recorded
        self.calls = []

    def record_received(self, intent):
        self.calls.append(intent)
        return DocumentStateWriteReceipt(self.recorded, intent.document_id, "recorded" if self.recorded else "rejected")


class FakeIngestion:
    def __init__(self, accepted=True):
        self.accepted = accepted
        self.calls = []

    def request_ingestion(self, intent):
        self.calls.append(intent)
        return IngestionActivationReceipt(self.accepted, "accepted" if self.accepted else "rejected")


def service(ingestion=None, state=None):
    ingestion = ingestion or FakeIngestion()
    state = state or FakeState()
    return UploadActivationService(ingestion=ingestion, document_state=state, clock=lambda: NOW), ingestion, state


def test_activation_blocked_without_successful_validation_and_calls_no_ports():
    runtime, ingestion, state = service()
    invalid_command = command(tenant_id=None)
    result = runtime.activate(invalid_command, validate_upload(invalid_command), artifact())

    assert result.status == "failed"
    assert result.reason_code == "validation_required"
    assert ingestion.calls == state.calls == []


def test_activation_deferred_without_staged_artifact_and_calls_no_ports():
    runtime, ingestion, state = service()
    source = command()
    result = runtime.activate(source, validate_upload(source), None)

    assert result.status == "deferred_staging_required"
    assert result.reason_code == "staging_required"
    assert ingestion.calls == state.calls == []


def test_valid_staged_activation_records_received_then_requests_ingestion():
    runtime, ingestion, state = service()
    source = command()
    result = runtime.activate(source, validate_upload(source), artifact())

    assert result.status == "ingestion_requested"
    assert result.document_state_recorded is True
    assert result.lifecycle_stage == "received"
    assert len(state.calls) == len(ingestion.calls) == 1
    assert state.calls[0].tenant_id == ingestion.calls[0].tenant_id == "tenant-001"
    assert state.calls[0].actor_id == ingestion.calls[0].actor_id == "actor-001"
    assert state.calls[0].document_id == ingestion.calls[0].document_id == result.document_id


def test_document_state_rejection_prevents_ingestion_request():
    runtime, ingestion, state = service(state=FakeState(recorded=False))
    source = command()
    result = runtime.activate(source, validate_upload(source), artifact())
    assert result.status == "failed"
    assert result.reason_code == "document_state_rejected"
    assert len(state.calls) == 1
    assert ingestion.calls == []


def test_ingestion_rejection_preserves_recorded_received_state():
    runtime, ingestion, state = service(ingestion=FakeIngestion(accepted=False))
    source = command()
    result = runtime.activate(source, validate_upload(source), artifact())
    assert result.status == "failed"
    assert result.reason_code == "ingestion_rejected"
    assert result.document_state_recorded is True
    assert result.lifecycle_stage == "received"

