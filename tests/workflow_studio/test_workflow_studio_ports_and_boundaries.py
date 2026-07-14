import ast
from pathlib import Path

from src.workflow_studio import InMemoryWorkflowOperationCatalog, WorkflowOperationCatalogPort
from src.workflow_studio.ports import (
    WorkflowDefinitionReadPort,
    WorkflowDefinitionWritePort,
    WorkflowVersionReadPort,
    WorkflowVersionWritePort,
)


PACKAGE = Path("src/workflow_studio")
FORBIDDEN = {
    "api", "apps", "document_state", "export_runtime", "platform_runtime", "security",
    "storage", "streamlit", "telemetry", "upload_runtime", "workflow_runtime",
}


def test_catalog_satisfies_runtime_checkable_port() -> None:
    assert isinstance(InMemoryWorkflowOperationCatalog(), WorkflowOperationCatalogPort)


def test_repository_ports_are_runtime_checkable_structural_protocols() -> None:
    class Empty:
        pass

    assert not isinstance(Empty(), WorkflowDefinitionReadPort)
    assert not isinstance(Empty(), WorkflowDefinitionWritePort)
    assert not isinstance(Empty(), WorkflowVersionReadPort)
    assert not isinstance(Empty(), WorkflowVersionWritePort)


def test_package_imports_only_standard_library_and_package_local_modules() -> None:
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                root = (node.module or "").split(".")[0]
                assert root not in FORBIDDEN, f"forbidden import {root} in {path}"
                assert root != "src", f"non-local src import in {path}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN


def test_package_has_no_execution_or_io_calls() -> None:
    forbidden_calls = {"eval", "exec", "open", "compile", "__import__"}
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        calls = {
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not calls.intersection(forbidden_calls), f"execution/I-O call in {path}"
