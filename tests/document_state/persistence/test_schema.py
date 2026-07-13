from dataclasses import FrozenInstanceError
import json

import pytest

from src.document_state.persistence import (
    SCHEMA_TABLES,
    TABLES_BY_NAME,
    PersistenceError,
    TableMetadata,
)


EXPECTED_TABLES = (
    "documents",
    "document_lifecycle_events",
    "processing_snapshots",
    "validation_issues",
    "matching_summaries",
    "review_summaries",
    "correction_summaries",
    "reprocess_plans",
    "workflow_runs",
    "audit_events",
    "schema_migrations",
)


def test_schema_metadata_contains_every_planned_table_in_deterministic_order():
    assert tuple(table.table_name for table in SCHEMA_TABLES) == EXPECTED_TABLES
    assert tuple(TABLES_BY_NAME) == EXPECTED_TABLES
    assert len(set(EXPECTED_TABLES)) == len(EXPECTED_TABLES)


def test_every_table_has_keys_ordering_indexes_privacy_and_semantics():
    for table in SCHEMA_TABLES:
        assert table.primary_key_fields
        assert table.ordering_fields
        assert set(table.primary_key_fields + table.ordering_fields) <= set(table.indexed_fields)
        assert table.privacy_classification
        assert table.semantics in {"mutable_snapshot", "append_only"}
        json.dumps(table.to_dict())


def test_schema_metadata_is_immutable():
    with pytest.raises(FrozenInstanceError):
        SCHEMA_TABLES[0].table_name = "private_table"
    with pytest.raises(TypeError):
        TABLES_BY_NAME["private_table"] = SCHEMA_TABLES[0]
    assert TABLES_BY_NAME["schema_migrations"].append_only


def test_invalid_schema_metadata_is_rejected_safely():
    with pytest.raises(PersistenceError) as raised:
        TableMetadata("Bad Table", ("id",), ("created_at",), ("id",), "operational_summary", "append_only")
    assert raised.value.code == "invalid_schema"
    assert "Bad Table" not in str(raised.value)
