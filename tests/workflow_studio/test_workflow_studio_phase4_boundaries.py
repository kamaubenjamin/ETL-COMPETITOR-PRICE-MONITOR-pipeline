import ast
from pathlib import Path
PACKAGE=Path("src/workflow_studio"); PHASE4={"preview.py","preview_contracts.py","preview_limits.py","preview_fixtures.py","preview_adapter.py","preview_results.py","preview_errors.py","preview_audit.py"}; FORBIDDEN={"api","apps","document_state","export_runtime","platform_runtime","security","storage","streamlit","telemetry","upload_runtime","workflow_runtime","sqlite3","requests","httpx","openai"}
def test_phase4_imports_are_standard_library_or_package_local():
    for filename in PHASE4:
        tree=ast.parse((PACKAGE/filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and not node.level: assert (node.module or "").split(".")[0] not in FORBIDDEN|{"src"}
            if isinstance(node,ast.Import): assert not {x.name.split(".")[0] for x in node.names}.intersection(FORBIDDEN)
def test_phase4_has_no_io_execution_or_mutation_imports():
    forbidden={"eval","exec","open","__import__","connect","urlopen"}
    for filename in PHASE4:
        tree=ast.parse((PACKAGE/filename).read_text(encoding="utf-8")); calls={n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}; assert not calls.intersection(forbidden)
def test_existing_packages_do_not_import_workflow_studio():
    actual = [str(p) for p in Path("src").glob("*/**/*.py") if PACKAGE not in p.parents and "workflow_studio" in p.read_text(encoding="utf-8-sig")]
    allowed = [str(p) for p in Path("src/api/document_intelligence").rglob("*.py") if "workflow_studio" in p.read_text(encoding="utf-8-sig")]
    assert actual == allowed
