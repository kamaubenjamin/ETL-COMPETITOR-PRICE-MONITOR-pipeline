import ast
from pathlib import Path


WRITER_ROOT = Path("src/document_state/writers")
FORBIDDEN_PREFIXES = (
    "src.api",
    "src.ui",
    "src.workflow_runtime",
    "src.review_runtime",
    "src.entity_runtime",
    "src.transforms",
    "src.matching_runtime",
    "src.document_engine",
    "src.storage",
    "src.telemetry",
)
FORBIDDEN_NAMES = {"sqlite3", "streamlit", "fastapi", "requests", "sqlalchemy", "openai"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


def test_writer_package_has_no_forbidden_imports():
    imported = {name for path in WRITER_ROOT.rglob("*.py") for name in _imports(path)}
    assert not {name for name in imported if name in FORBIDDEN_NAMES or name.startswith(FORBIDDEN_PREFIXES)}


def test_writer_contract_layer_contains_no_repository_calls_or_service_implementation():
    source = "\n".join(path.read_text(encoding="utf-8") for path in WRITER_ROOT.rglob("*.py"))
    assert "repositories_in_memory" not in source
    assert "persistence.sqlite" not in source

    tree = ast.parse((WRITER_ROOT / "ports.py").read_text(encoding="utf-8"))
    methods = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert methods
    assert all(len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and node.body[0].value.value is Ellipsis for node in methods)
