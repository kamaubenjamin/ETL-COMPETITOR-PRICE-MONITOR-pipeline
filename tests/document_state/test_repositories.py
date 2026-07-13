import ast
import inspect
from pathlib import Path

from src import document_state
from src.document_state.repositories import (
    DocumentReadRepository,
    DocumentStateReadRepositories,
    DocumentStateWriteRepositories,
    DocumentWriteRepository,
    LifecycleWriteRepository,
)


class DocumentReader:
    def get_document(self, document_id): ...
    def list_documents(self, query, page): ...


class DocumentWriter:
    def create_document(self, record): ...
    def update_document(self, record, *, expected_version): ...


class LifecycleWriter:
    def append_lifecycle_event(self, record, *, idempotency_key): ...


def _public_methods(protocol):
    return {
        name: value for name, value in inspect.getmembers(protocol, inspect.isfunction)
        if not name.startswith("_")
    }


def test_repository_protocols_are_structural_and_read_write_separated():
    assert isinstance(DocumentReader(), DocumentReadRepository)
    assert isinstance(DocumentWriter(), DocumentWriteRepository)
    assert isinstance(LifecycleWriter(), LifecycleWriteRepository)
    read_names = set(_public_methods(DocumentStateReadRepositories))
    write_names = set(_public_methods(DocumentStateWriteRepositories))
    assert read_names and write_names and read_names.isdisjoint(write_names)
    assert all(name.startswith(("get_", "list_")) for name in read_names)
    assert all(name.startswith(("create_", "update_", "append_")) for name in write_names)


def test_write_protocols_expose_optimistic_and_idempotent_semantics():
    methods = _public_methods(DocumentStateWriteRepositories)
    for name, method in methods.items():
        parameters = inspect.signature(method).parameters
        if name.startswith("update_"):
            assert "expected_version" in parameters
        if name.startswith("append_"):
            assert "idempotency_key" in parameters


def test_document_state_package_has_only_standard_or_local_imports():
    root = Path(document_state.__file__).parent
    standard = {
        "__future__", "collections", "dataclasses", "datetime", "enum", "math",
        "threading", "types", "typing",
    }
    forbidden_tokens = {
        "api", "competitor", "database", "document_engine", "entity_runtime", "external",
        "flowsync", "llm", "matching_runtime", "ocr", "review_runtime", "storage",
        "streamlit", "telemetry", "transform", "transforms", "ui", "workflow_runtime",
    }
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                assert module.split(".")[0] in standard
                assert not set(module.lower().split(".")) & forbidden_tokens


def test_no_database_migration_or_adapter_surface_exists():
    root = Path(document_state.__file__).parent
    assert not (root / "providers").exists()
    assert not (root / "adapters").exists()
    assert not (root / "migrations").exists()
    assert not (root / "repositories").exists()
