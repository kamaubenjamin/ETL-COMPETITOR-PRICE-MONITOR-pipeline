import pytest

from src.upload_runtime import UploadCommand, UploadValidationPolicy, validate_upload


def command(**overrides):
    values = dict(
        upload_id="upload-001", tenant_id="tenant-001", actor_id="actor-001",
        original_filename="invoice.pdf", file_size_bytes=1024, file_type="pdf", source="api",
        declared_content_type="application/pdf",
    )
    values.update(overrides)
    return UploadCommand(**values)


def codes(source):
    return [issue.code for issue in validate_upload(source).issues]


def test_valid_upload_passes_default_policy():
    assert validate_upload(command()).valid


def test_missing_tenant_and_actor_fail_in_stable_order():
    assert codes(command(tenant_id=None, actor_id=None)) == ["tenant_scope_missing", "actor_missing"]


@pytest.mark.parametrize(
    ("filename", "file_type", "expected"),
    [
        ("invoice.docx", "docx", "unsupported_file_type"),
        ("invoice.exe", "exe", "unsafe_extension"),
        ("script.ps1", "ps1", "unsafe_extension"),
        ("../invoice.pdf", "pdf", "path_traversal_detected"),
        (r"C:\private\invoice.pdf", "pdf", "path_traversal_detected"),
        (" invoice.pdf", "pdf", "unsafe_filename"),
        ("invoice?.pdf", "pdf", "unsafe_filename"),
    ],
)
def test_filename_and_extension_safety(filename, file_type, expected):
    assert expected in codes(command(original_filename=filename, file_type=file_type))


def test_filename_too_long_is_reported():
    filename = f"{'a' * 252}.pdf"
    assert "filename_too_long" in codes(command(original_filename=filename))


def test_empty_and_oversized_uploads_fail():
    assert codes(command(file_size_bytes=0)) == ["upload_empty"]
    policy = UploadValidationPolicy(max_file_size_bytes=100)
    result = validate_upload(command(file_size_bytes=101), policy)
    assert [issue.code for issue in result.issues] == ["upload_too_large"]


def test_declared_mime_mismatch_fails():
    assert codes(command(declared_content_type="text/csv")) == ["mime_type_mismatch"]


@pytest.mark.parametrize(
    ("filename", "file_type", "content_type"),
    [
        ("data.csv", "csv", "text/csv"), ("sheet.xlsx", "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("notes.txt", "txt", "text/plain"), ("message.eml", "eml", "message/rfc822"),
    ],
)
def test_initial_supported_types_validate(filename, file_type, content_type):
    assert validate_upload(command(original_filename=filename, file_type=file_type, declared_content_type=content_type)).valid

