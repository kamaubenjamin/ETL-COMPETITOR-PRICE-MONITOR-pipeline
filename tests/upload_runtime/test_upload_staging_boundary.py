import pytest

from src.upload_runtime import UploadArtifactReference, UploadCommand, validate_upload
from src.upload_runtime.staging import ValidatedStagedUpload


NOW = "2026-07-14T10:00:00Z"


def command():
    return UploadCommand("upload-001", "tenant-001", "actor-001", "invoice.pdf", 100, "pdf", "api")


def test_validated_staged_upload_binds_matching_opaque_reference_without_io():
    source = command()
    staged = ValidatedStagedUpload(
        source,
        validate_upload(source),
        UploadArtifactReference("artifact-001", "test_placeholder", "pdf", 100, NOW),
    )
    assert staged.artifact_reference.reference_id == "artifact-001"
    assert "path" not in staged.to_dict()["artifact_reference"]


@pytest.mark.parametrize(
    "reference",
    [
        UploadArtifactReference("artifact-001", "test_placeholder", "csv", 100, NOW),
        UploadArtifactReference("artifact-001", "test_placeholder", "pdf", 101, NOW),
    ],
)
def test_mismatched_artifact_reference_is_rejected(reference):
    source = command()
    with pytest.raises(ValueError, match="does not match"):
        ValidatedStagedUpload(source, validate_upload(source), reference)


def test_invalid_upload_cannot_bind_staged_reference():
    source = UploadCommand("upload-001", None, "actor-001", "invoice.pdf", 100, "pdf", "api")
    with pytest.raises(ValueError, match="successful validation"):
        ValidatedStagedUpload(source, validate_upload(source), UploadArtifactReference("artifact-001", "test_placeholder", "pdf", 100, NOW))

