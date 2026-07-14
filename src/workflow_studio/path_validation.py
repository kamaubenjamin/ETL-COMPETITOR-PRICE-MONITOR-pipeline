"""Deterministic logical field-path validation without filesystem access."""

from __future__ import annotations

import re

from .contracts import bounded_text
from .validation_errors import ValidationIssueCode, validation_issue
from .validation_results import ValidationLayer, ValidationSeverity, WorkflowValidationIssue


MAX_PATH_LENGTH = 256
MAX_PATH_SEGMENTS = 32
PROTECTED_PATH_PREFIXES = ("_internal", "internal", "system", "security", "auth", "credentials")
_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\[\])?$")
_UNSAFE = re.compile(
    r"(?:^[A-Za-z]:[\\/]|[\\]|://|\.\.|\*|\$|;|`|\|&|[(){}]|\[(?!\])|(?<!\[)\]|"
    r"\b(?:select|insert|update|delete|drop|exec|eval|powershell|cmd)\b)",
    re.IGNORECASE,
)


def validate_logical_path(path: object, *, rule_id: str | None = None, action_id: str | None = None) -> tuple[WorkflowValidationIssue, ...]:
    if not isinstance(path, str) or not path or len(path) > MAX_PATH_LENGTH or _UNSAFE.search(path):
        return (_invalid(rule_id, action_id),)
    segments = path.split(".")
    if len(segments) > MAX_PATH_SEGMENTS or any(not segment or not _SEGMENT.fullmatch(segment) for segment in segments):
        return (_invalid(rule_id, action_id),)
    root = segments[0].removesuffix("[]").lower()
    if root in PROTECTED_PATH_PREFIXES:
        return (validation_issue(ValidationIssueCode.PROTECTED_PATH, ValidationSeverity.BLOCKING, ValidationLayer.SECURITY, rule_id=rule_id, action_id=action_id),)
    return ()


def safe_logical_path(path: object, field_name: str = "path") -> str:
    issues = validate_logical_path(path)
    if issues:
        raise ValueError(f"{field_name} must be a safe logical path")
    return bounded_text(path, field_name, maximum=MAX_PATH_LENGTH)


def _invalid(rule_id: str | None, action_id: str | None) -> WorkflowValidationIssue:
    return validation_issue(ValidationIssueCode.INVALID_PATH, ValidationSeverity.BLOCKING, ValidationLayer.PATH, rule_id=rule_id, action_id=action_id)
