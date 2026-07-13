import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.document_state import (
    DocumentQuery,
    DocumentRecord,
    DocumentStateComposition,
    PageRequest,
    compose_document_state,
)
from src.document_state.persistence import PersistenceConfig, PersistenceError
from src.document_state.repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories


TS = "2026-07-13T09:00:00+00:00"


def _document():
    return DocumentRecord(
        "doc-001", "invoice.pdf", "invoice", "validated", 0.95,
        "validate_data", TS, TS, TS,
    )


def test_in_memory_composition_is_explicit_and_opens_no_database(tmp_path):
    composed = compose_document_state(PersistenceConfig("in_memory"))
    assert isinstance(composed, DocumentStateComposition)
    assert composed.backend == "in_memory"
    assert composed.is_durable is False
    assert isinstance(composed.reader, DocumentStateReadRepositories)
    assert isinstance(composed.writer, DocumentStateWriteRepositories)
    assert list(tmp_path.iterdir()) == []


def test_sqlite_composition_requires_explicit_path_and_exposes_durable_backend(tmp_path):
    path = tmp_path / "document-state.sqlite3"
    composed = compose_document_state(
        PersistenceConfig("sqlite", sqlite_path=str(path))
    )
    assert composed.backend == "sqlite"
    assert composed.is_durable is True
    assert isinstance(composed.reader, DocumentStateReadRepositories)
    assert isinstance(composed.writer, DocumentStateWriteRepositories)
    assert path.is_file()


def test_sqlite_composition_persists_across_reconstruction(tmp_path):
    config = PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "durable.sqlite3"))
    first = compose_document_state(config)
    first.writer.create_document(_document())

    second = compose_document_state(config)
    assert second.reader.get_document("doc-001") == _document()
    assert second.reader.list_documents(DocumentQuery(), PageRequest()).total == 1


@pytest.mark.parametrize(
    ("backend", "sqlite_path", "field"),
    [
        ("sqlite", None, "sqlite_path"),
        ("sqlite", ":memory:", "sqlite_path"),
        ("unknown", None, "backend"),
    ],
)
def test_invalid_backend_configuration_fails_safely(backend, sqlite_path, field):
    with pytest.raises(PersistenceError) as raised:
        config = PersistenceConfig(backend, sqlite_path=sqlite_path)
        compose_document_state(config)
    assert raised.value.code == "invalid_backend"
    assert raised.value.field == field
    assert backend not in str(raised.value)


def test_future_postgres_cannot_be_activated():
    config = PersistenceConfig("future_postgres")
    assert config.is_deferred and not config.is_active
    with pytest.raises(PersistenceError) as raised:
        compose_document_state(config)
    assert raised.value.code == "invalid_backend"
    assert raised.value.field == "backend"


def test_sqlite_failure_does_not_fall_back_to_in_memory(tmp_path):
    config = PersistenceConfig(
        "sqlite", sqlite_path=str(tmp_path / "missing-parent" / "state.sqlite3")
    )
    with pytest.raises(PersistenceError) as raised:
        compose_document_state(config)
    assert raised.value.code == "connection_unavailable"
    assert not (tmp_path / "missing-parent").exists()


def test_composition_result_is_immutable():
    composed = compose_document_state(PersistenceConfig("in_memory"))
    with pytest.raises(FrozenInstanceError):
        composed.backend = "sqlite"


def test_composition_imports_only_package_local_modules():
    path = Path(__file__).parents[2] / "src" / "document_state" / "composition.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    absolute_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            absolute_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            absolute_imports.append(node.module)
    assert set(absolute_imports) <= {"__future__", "dataclasses"}
    source = path.read_text(encoding="utf-8-sig").lower()
    for forbidden in (
        "fastapi", "streamlit", "workflow_runtime", "review_runtime", "storage",
        "telemetry", "flowsync", "competitor", "requests", "httpx", "postgres",
        "openai", "ocr",
    ):
        assert forbidden not in source
