import ast
import inspect
from pathlib import Path

from src import document_state
from src.document_state import InMemoryDocumentStateRepositories
from src.document_state.adapters import DocumentStateQueryFacadeAdapter


ROOT = Path(document_state.__file__).parent
REPO_ROOT = ROOT.parents[1]
STANDARD_ROOTS = {
    "__future__", "collections", "dataclasses", "datetime", "enum", "math",
    "threading", "types", "typing",
}


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(f"{'.' * node.level}{node.module}")
    return tuple(modules)


def test_core_document_state_recursively_imports_only_standard_or_package_local_modules():
    for path in ROOT.rglob("*.py"):
        if "adapters" in path.relative_to(ROOT).parts:
            continue
        for module in _imports(path):
            if module.startswith("."):
                continue
            assert module.split(".")[0] in STANDARD_ROOTS


def test_adapter_imports_only_approved_public_boundaries():
    adapter = ROOT / "adapters" / "query_facade_adapter.py"
    allowed = STANDARD_ROOTS | {"src.document_state", "src.workflow_runtime.query_facade"}
    for module in _imports(adapter):
        assert any(module == root or module.startswith(f"{root}.") for root in allowed)


def test_api_and_ui_do_not_import_document_state_directly():
    consumers = (
        REPO_ROOT / "src" / "api" / "document_intelligence",
        REPO_ROOT / "src" / "ui" / "streamlit",
    )
    for consumer in consumers:
        for path in consumer.rglob("*.py"):
            assert not any(
                module == "src.document_state" or module.startswith("src.document_state.")
                for module in _imports(path)
            ), path


def test_document_state_has_no_database_file_or_network_dependencies():
    forbidden_roots = {
        "aiohttp", "boto3", "database", "httpx", "pymongo", "redis", "requests",
        "socket", "sqlalchemy", "sqlite3", "urllib",
    }
    forbidden_calls = {"open", "urlopen"}
    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        assert not {module.split(".")[0] for module in _imports(path)} & forbidden_roots
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not calls & forbidden_calls


def test_read_surfaces_and_adapter_expose_no_mutation_methods():
    reader = InMemoryDocumentStateRepositories().reader
    adapter = DocumentStateQueryFacadeAdapter(reader, snapshot_at="2026-07-13T11:00:00+00:00")
    for surface in (reader, adapter):
        public = {
            name for name, value in inspect.getmembers(surface, callable)
            if not name.startswith("_")
        }
        assert public
        assert all(name.startswith(("get_", "list_")) for name in public)
        assert not any(name.startswith(("append_", "create_", "delete_", "update_")) for name in public)
