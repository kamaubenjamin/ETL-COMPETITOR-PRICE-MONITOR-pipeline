"""Dependency-light validation helpers for Review Runtime contracts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from src.review_runtime.errors import (
    INVALID_TYPE,
    INVALID_VALUE,
    MISSING_FIELD,
    UNKNOWN_FIELD,
    UNSUPPORTED_VERSION,
    ReviewRuntimeError,
)
from src.review_runtime.contracts.enums import ReviewStatus

CONTRACT_VERSION = 1
MAX_IDENTIFIER_LENGTH = 128
MAX_CODE_LENGTH = 64
MAX_STAGE_LENGTH = 128
MAX_COMMENT_LENGTH = 512

CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
STAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
FIELD_PATH_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:(?:\.[A-Za-z_][A-Za-z0-9_]*)|(?:\[\d+\]))*$"
)

E = TypeVar("E", bound=Enum)


def mapping(value: Any, path: tuple[str | int, ...] = ()) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReviewRuntimeError(INVALID_TYPE, "Expected an object.", path)
    return value


def check_keys(
    payload: Mapping[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    path: tuple[str | int, ...] = (),
) -> None:
    for key in sorted(required):
        if key not in payload:
            raise ReviewRuntimeError(MISSING_FIELD, f"Missing required field '{key}'.", (*path, key))
    for key in payload:
        if key not in allowed:
            raise ReviewRuntimeError(UNKNOWN_FIELD, f"Unknown field '{key}'.", (*path, key))


def nonempty_string(
    value: Any,
    path: tuple[str | int, ...],
    *,
    max_length: int = MAX_IDENTIFIER_LENGTH,
) -> str:
    if not isinstance(value, str):
        raise ReviewRuntimeError(INVALID_TYPE, "Expected a string.", path)
    if not value.strip():
        raise ReviewRuntimeError(INVALID_VALUE, "Value must not be empty.", path)
    if len(value) > max_length:
        raise ReviewRuntimeError(INVALID_VALUE, f"Value must not exceed {max_length} characters.", path)
    return value


def identifier(value: Any, path: tuple[str | int, ...]) -> str:
    result = nonempty_string(value, path)
    if not IDENTIFIER_PATTERN.fullmatch(result):
        raise ReviewRuntimeError(INVALID_VALUE, "Identifier has an invalid format.", path)
    return result


def code(value: Any, path: tuple[str | int, ...]) -> str:
    result = nonempty_string(value, path, max_length=MAX_CODE_LENGTH)
    if not CODE_PATTERN.fullmatch(result):
        raise ReviewRuntimeError(INVALID_VALUE, "Code has an invalid format.", path)
    return result


def stage_name(value: Any, path: tuple[str | int, ...]) -> str:
    result = nonempty_string(value, path, max_length=MAX_STAGE_LENGTH)
    if not STAGE_PATTERN.fullmatch(result):
        raise ReviewRuntimeError(INVALID_VALUE, "Stage name has an invalid format.", path)
    return result


def field_path(value: Any, path: tuple[str | int, ...]) -> str:
    result = nonempty_string(value, path, max_length=256)
    if not FIELD_PATH_PATTERN.fullmatch(result):
        raise ReviewRuntimeError(INVALID_VALUE, "Field path has an invalid format.", path)
    return result


def timestamp(value: Any, path: tuple[str | int, ...]) -> str:
    result = nonempty_string(value, path, max_length=64)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewRuntimeError(INVALID_VALUE, "Timestamp must be ISO-8601.", path) from exc
    if parsed.tzinfo is None:
        raise ReviewRuntimeError(INVALID_VALUE, "Timestamp must include a timezone.", path)
    return result


def positive_version(value: Any, path: tuple[str | int, ...]) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ReviewRuntimeError(INVALID_VALUE, "Version must be a positive integer.", path)
    return value


def contract_version(value: Any, path: tuple[str | int, ...]) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReviewRuntimeError(INVALID_TYPE, "contract_version must be an integer.", path)
    if value != CONTRACT_VERSION:
        raise ReviewRuntimeError(UNSUPPORTED_VERSION, "Unsupported contract version.", path)
    return value


def enum_value(value: Any, enum_type: type[E], path: tuple[str | int, ...]) -> E:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ReviewRuntimeError(INVALID_VALUE, f"Unsupported {path[-1]} code.", path) from exc


def review_status(value: Any, path: tuple[str | int, ...]) -> ReviewStatus:
    """Normalize the sole legacy status alias at contract boundaries."""

    normalized = ReviewStatus.REVIEW_REQUIRED.value if value == "pending" else value
    return enum_value(normalized, ReviewStatus, path)


def optional_identifier(value: Any, path: tuple[str | int, ...]) -> str | None:
    return None if value is None else identifier(value, path)


def optional_code(value: Any, path: tuple[str | int, ...]) -> str | None:
    return None if value is None else code(value, path)


def string_tuple(
    value: Any,
    path: tuple[str | int, ...],
    *,
    max_items: int = 50,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ReviewRuntimeError(INVALID_TYPE, "Expected an array of identifiers.", path)
    if len(value) > max_items:
        raise ReviewRuntimeError(INVALID_VALUE, f"Array must not exceed {max_items} items.", path)
    items = tuple(identifier(item, (*path, index)) for index, item in enumerate(value))
    if len(set(items)) != len(items):
        raise ReviewRuntimeError(INVALID_VALUE, "Array values must be unique.", path)
    return items


def controlled_scalar(value: Any, path: tuple[str | int, ...]) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and len(value) > 4096:
            raise ReviewRuntimeError(INVALID_VALUE, "Controlled string value is too long.", path)
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ReviewRuntimeError(
        INVALID_TYPE,
        "Controlled values must be null, string, boolean, integer, or finite number.",
        path,
    )
