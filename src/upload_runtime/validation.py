"""Pure deterministic upload command validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from .commands import UploadCommand
from .contracts import UploadContract, UploadFileType, safe_code


class UploadValidationIssueCode(str):
    pass


_ISSUE_ORDER = (
    "tenant_scope_missing", "actor_missing", "path_traversal_detected", "filename_too_long",
    "unsafe_filename", "unsafe_extension", "unsupported_file_type", "upload_empty",
    "upload_too_large", "mime_type_mismatch", "metadata_invalid", "internal_error",
)
_UNSAFE_EXTENSIONS = frozenset({"exe", "dll", "com", "bat", "cmd", "ps1", "sh", "js", "vbs", "scr", "msi", "jar", "py", "php", "html", "htm", "zip", "rar", "7z"})
_MIME_TYPES = {
    "pdf": frozenset({"application/pdf"}),
    "csv": frozenset({"text/csv", "application/csv", "text/plain"}),
    "xlsx": frozenset({"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
    "txt": frozenset({"text/plain"}),
    "eml": frozenset({"message/rfc822", "text/plain"}),
}


@dataclass(frozen=True, slots=True)
class UploadValidationPolicy(UploadContract):
    max_file_size_bytes: int = 25 * 1024 * 1024
    max_filename_length: int = 255
    allowed_file_types: tuple[str, ...] = tuple(item.value for item in UploadFileType)

    def __post_init__(self) -> None:
        if isinstance(self.max_file_size_bytes, bool) or not isinstance(self.max_file_size_bytes, int) or self.max_file_size_bytes < 1:
            raise ValueError("max_file_size_bytes must be positive")
        if isinstance(self.max_filename_length, bool) or not isinstance(self.max_filename_length, int) or not 1 <= self.max_filename_length <= 255:
            raise ValueError("max_filename_length is invalid")
        allowed = tuple(sorted(set(self.allowed_file_types)))
        if not allowed or any(item not in {kind.value for kind in UploadFileType} for item in allowed):
            raise ValueError("allowed_file_types is invalid")
        object.__setattr__(self, "allowed_file_types", allowed)


@dataclass(frozen=True, slots=True)
class UploadValidationIssue(UploadContract):
    code: str
    field: str
    message: str

    def __post_init__(self) -> None:
        if self.code not in _ISSUE_ORDER:
            raise ValueError("validation issue code is invalid")
        object.__setattr__(self, "field", safe_code(self.field, "field"))
        if not isinstance(self.message, str) or not self.message or len(self.message) > 160:
            raise ValueError("message is invalid")


@dataclass(frozen=True, slots=True)
class UploadValidationResult(UploadContract):
    issues: tuple[UploadValidationIssue, ...] = ()

    def __post_init__(self) -> None:
        items = tuple(self.issues)
        if any(not isinstance(item, UploadValidationIssue) for item in items):
            raise ValueError("issues must contain UploadValidationIssue values")
        order = {code: index for index, code in enumerate(_ISSUE_ORDER)}
        object.__setattr__(self, "issues", tuple(sorted(items, key=lambda item: (order[item.code], item.field))))

    @property
    def valid(self) -> bool:
        return not self.issues


_MESSAGES = {
    "tenant_scope_missing": ("tenant_id", "Tenant scope is required."),
    "actor_missing": ("actor_id", "Actor identity is required."),
    "path_traversal_detected": ("original_filename", "Filename contains path traversal."),
    "filename_too_long": ("original_filename", "Filename exceeds the allowed length."),
    "unsafe_filename": ("original_filename", "Filename is unsafe."),
    "unsafe_extension": ("file_type", "File extension is unsafe."),
    "unsupported_file_type": ("file_type", "File type is not supported."),
    "upload_empty": ("file_size_bytes", "Upload is empty."),
    "upload_too_large": ("file_size_bytes", "Upload exceeds the allowed size."),
    "mime_type_mismatch": ("declared_content_type", "Declared content type does not match the file type."),
}


def _issue(code: str) -> UploadValidationIssue:
    field, message = _MESSAGES[code]
    return UploadValidationIssue(code, field, message)


def validate_upload(command: UploadCommand, policy: UploadValidationPolicy | None = None) -> UploadValidationResult:
    if not isinstance(command, UploadCommand):
        raise ValueError("command must be an UploadCommand")
    policy = policy or UploadValidationPolicy()
    if not isinstance(policy, UploadValidationPolicy):
        raise ValueError("policy must be an UploadValidationPolicy")
    codes: list[str] = []
    if command.tenant_id is None:
        codes.append("tenant_scope_missing")
    if command.actor_id is None:
        codes.append("actor_missing")
    filename = command.original_filename
    normalized = filename.replace("\\", "/")
    parts = normalized.split("/")
    if "/" in normalized or ".." in parts or normalized.startswith(("/", "~")):
        codes.append("path_traversal_detected")
    if len(filename) > policy.max_filename_length:
        codes.append("filename_too_long")
    if filename in {".", ".."} or filename.strip() != filename or filename.endswith((".", " ")) or any(character in filename for character in '<>:"|?*'):
        codes.append("unsafe_filename")
    suffix = PurePath(normalized).suffix.lower().lstrip(".")
    if suffix in _UNSAFE_EXTENSIONS or command.file_type in _UNSAFE_EXTENSIONS:
        codes.append("unsafe_extension")
    elif command.file_type not in policy.allowed_file_types or suffix != command.file_type:
        codes.append("unsupported_file_type")
    if command.file_size_bytes == 0:
        codes.append("upload_empty")
    elif command.file_size_bytes > policy.max_file_size_bytes:
        codes.append("upload_too_large")
    if command.declared_content_type is not None and command.file_type in _MIME_TYPES and command.declared_content_type.lower() not in _MIME_TYPES[command.file_type]:
        codes.append("mime_type_mismatch")
    return UploadValidationResult(tuple(_issue(code) for code in dict.fromkeys(codes)))

