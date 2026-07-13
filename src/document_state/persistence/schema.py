"""Deterministic logical schema metadata for durable Document State."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from .errors import PersistenceError


class PrivacyClassification(str, Enum):
    OPERATIONAL_SUMMARY = "operational_summary"
    LINEAGE_SUMMARY = "lineage_summary"
    AUDIT_SUMMARY = "audit_summary"
    SYSTEM_METADATA = "system_metadata"


class TableSemantics(str, Enum):
    MUTABLE_SNAPSHOT = "mutable_snapshot"
    APPEND_ONLY = "append_only"


def _identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise PersistenceError("invalid_schema", field=field)
    if value.lower() != value or not value.replace("_", "").isalnum() or value[0].isdigit():
        raise PersistenceError("invalid_schema", field=field)
    return value


def _identifiers(values: object, field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise PersistenceError("invalid_schema", field=field)
    result = tuple(_identifier(value, field) for value in values)
    if len(set(result)) != len(result):
        raise PersistenceError("invalid_schema", field=field)
    return result


@dataclass(frozen=True, slots=True)
class TableMetadata:
    table_name: str
    primary_key_fields: tuple[str, ...]
    ordering_fields: tuple[str, ...]
    indexed_fields: tuple[str, ...]
    privacy_classification: PrivacyClassification | str
    semantics: TableSemantics | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "table_name", _identifier(self.table_name, "table_name"))
        object.__setattr__(self, "primary_key_fields", _identifiers(self.primary_key_fields, "primary_key_fields"))
        object.__setattr__(self, "ordering_fields", _identifiers(self.ordering_fields, "ordering_fields"))
        object.__setattr__(self, "indexed_fields", _identifiers(self.indexed_fields, "indexed_fields"))
        try:
            privacy = PrivacyClassification(self.privacy_classification).value
            semantics = TableSemantics(self.semantics).value
        except (TypeError, ValueError):
            raise PersistenceError("invalid_schema", field="classification") from None
        object.__setattr__(self, "privacy_classification", privacy)
        object.__setattr__(self, "semantics", semantics)
        if not set(self.primary_key_fields).issubset(self.indexed_fields):
            raise PersistenceError("invalid_schema", field="indexed_fields")
        if not set(self.ordering_fields).issubset(self.indexed_fields):
            raise PersistenceError("invalid_schema", field="indexed_fields")

    @property
    def append_only(self) -> bool:
        return self.semantics == TableSemantics.APPEND_ONLY.value

    @property
    def mutable_snapshot(self) -> bool:
        return self.semantics == TableSemantics.MUTABLE_SNAPSHOT.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "primary_key_fields": list(self.primary_key_fields),
            "ordering_fields": list(self.ordering_fields),
            "indexed_fields": list(self.indexed_fields),
            "privacy_classification": self.privacy_classification,
            "semantics": self.semantics,
            "append_only": self.append_only,
            "mutable_snapshot": self.mutable_snapshot,
        }


SCHEMA_TABLES = (
    TableMetadata("documents", ("document_id",), ("received_at", "document_id"), ("document_id", "tenant_id", "status", "document_type", "received_at"), "operational_summary", "mutable_snapshot"),
    TableMetadata("document_lifecycle_events", ("event_id",), ("occurred_at", "event_id"), ("event_id", "document_id", "status", "occurred_at"), "lineage_summary", "append_only"),
    TableMetadata("processing_snapshots", ("snapshot_id",), ("updated_at", "stage", "snapshot_id"), ("snapshot_id", "document_id", "workflow_run_id", "status", "updated_at", "stage"), "operational_summary", "mutable_snapshot"),
    TableMetadata("validation_issues", ("issue_id",), ("severity", "field", "rule_id", "issue_id"), ("issue_id", "document_id", "severity", "field", "rule_id"), "operational_summary", "append_only"),
    TableMetadata("matching_summaries", ("match_id",), ("confidence", "candidate_id", "match_id"), ("match_id", "document_id", "status", "entity_type", "confidence", "candidate_id"), "operational_summary", "append_only"),
    TableMetadata("review_summaries", ("review_case_id",), ("priority", "created_at", "review_case_id"), ("review_case_id", "document_id", "status", "priority", "created_at"), "operational_summary", "mutable_snapshot"),
    TableMetadata("correction_summaries", ("correction_id",), ("occurred_at", "correction_id"), ("correction_id", "review_case_id", "document_id", "occurred_at"), "lineage_summary", "append_only"),
    TableMetadata("reprocess_plans", ("plan_id",), ("created_at", "plan_id"), ("plan_id", "review_case_id", "document_id", "created_at"), "lineage_summary", "append_only"),
    TableMetadata("workflow_runs", ("run_id",), ("started_at", "run_id"), ("run_id", "workflow_name", "status", "started_at"), "operational_summary", "mutable_snapshot"),
    TableMetadata("audit_events", ("event_id",), ("occurred_at", "event_id"), ("event_id", "event_type", "document_id", "review_case_id", "occurred_at"), "audit_summary", "append_only"),
    TableMetadata("schema_migrations", ("migration_id",), ("sequence", "migration_id"), ("migration_id", "engine", "sequence"), "system_metadata", "append_only"),
)

TABLES_BY_NAME = MappingProxyType({table.table_name: table for table in SCHEMA_TABLES})
