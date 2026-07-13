"""Explicit record-to-column mapping for SQLite persistence."""

from __future__ import annotations

from dataclasses import fields
import hashlib
import json
import sqlite3
from typing import Any, TypeVar

from ...errors import DocumentStateError
from ...records import PersistentRecord


RecordT = TypeVar("RecordT", bound=PersistentRecord)


def validate_record(record: object, expected: type[RecordT]) -> RecordT:
    if type(record) is not expected:
        raise DocumentStateError("invalid_record", field="record")
    try:
        return expected(**record.to_dict())
    except (TypeError, ValueError):
        raise DocumentStateError("invalid_record", field="record") from None


def record_columns(record_type: type[PersistentRecord]) -> tuple[str, ...]:
    return tuple(f"{item.name}_json" if item.name in {"metadata", "access_tags"} else item.name for item in fields(record_type))


def record_values(record: PersistentRecord) -> tuple[Any, ...]:
    values = record.to_dict()
    return tuple(
        json.dumps(values[item.name], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if item.name in {"metadata", "access_tags"} else values[item.name]
        for item in fields(record)
    )


def row_to_record(row: sqlite3.Row, expected: type[RecordT]) -> RecordT:
    try:
        values = {
            item.name: json.loads(row[f"{item.name}_json"])
            if item.name in {"metadata", "access_tags"} else row[item.name]
            for item in fields(expected)
        }
        return expected(**values)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, IndexError):
        raise DocumentStateError("internal_error") from None


def record_hash(record: PersistentRecord) -> str:
    canonical = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
