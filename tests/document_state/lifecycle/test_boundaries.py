import ast
from pathlib import Path


LIFECYCLE_ROOT = Path("src/document_state/lifecycle")
FORBIDDEN_PREFIXES = (
    "src.api",
    "src.ui",
    "src.workflow_runtime",
    "src.review_runtime",
    "src.entity_runtime",
    "src.transforms",
    "src.matching_runtime",
    "src.document_engine",
    "src.document_state.writers",
    "src.document_state.persistence",
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


def test_lifecycle_package_has_no_forbidden_imports():
    imported = {name for path in LIFECYCLE_ROOT.rglob("*.py") for name in _imports(path)}
    assert not {name for name in imported if name in FORBIDDEN_NAMES or name.startswith(FORBIDDEN_PREFIXES)}


def test_phase_one_has_no_repository_or_service_calls():
    source = "\n".join(path.read_text(encoding="utf-8") for path in LIFECYCLE_ROOT.rglob("*.py"))
    forbidden = (
        "DocumentStateReadRepositories",
        "DocumentStateWriteRepositories",
        "update_document(",
        "append_lifecycle_event(",
        "LifecycleAdvancementService",
        "repositories_in_memory",
        "persistence.sqlite",
    )
    assert not any(item in source for item in forbidden)
