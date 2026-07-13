#!/usr/bin/env python3
"""
Runtime Boundary Verification — Tier 1: Static Import Isolation Analysis.

Scans runtime packages under src/ for forbidden cross-runtime imports.
Reads exemptions from tests/boundaries/exemptions.json.
Generates a readable violation report.
Exits non-zero when violations exist, zero when compliant.

Rules verified (from RUNTIME_BOUNDARY_MAP.md):
  R01 — Document Runtime must not import Entity, Matching, or Review runtimes
  R02 — Entity Runtime must not import Matching or Review runtimes
  R03 — Matching Runtime must not import Document Runtime
  R04 — Review Runtime must not import Document or Entity runtimes
  R05 — API Runtime may import Workflow Runtime/shared utilities; Document Intelligence API may import Security
  R12 — Shared utilities must not import runtime-specific modules
"""

import ast
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Runtime package definitions (mapped from RUNTIME_BOUNDARY_MAP.md Appendix A)
# ---------------------------------------------------------------------------
RUNTIME_PACKAGES: Dict[str, List[str]] = {
    "document_runtime": ["src.document_engine", "src.extract"],
    "workflow_runtime": ["src.workflow_runtime"],
    "entity_runtime":   ["src.entity_runtime"],
    "matching_runtime": ["src.matching_runtime"],
    "review_runtime":   ["src.review_runtime"],
    "api_runtime":      ["src.api"],
}

SHARED_UTILITY_PACKAGES: List[str] = [
    "src.utils",
    "src.config",
    "src.schema_utils",
]

# Dynamic: will be populated from the runtime package map
ALL_RUNTIME_PREFIXES: Set[str] = set()
for prefixes in RUNTIME_PACKAGES.values():
    ALL_RUNTIME_PREFIXES.update(prefixes)


# ---------------------------------------------------------------------------
# Forbidden import rules
# ---------------------------------------------------------------------------
# Each rule: (consumer_runtime_key, [list_of_forbidden_producer_prefixes])
# The consumer is identified by its package prefixes in RUNTIME_PACKAGES.
FORBIDDEN_IMPORT_RULES: List[Tuple[str, List[str], str]] = [
    # R01: Document Runtime must not import Entity, Matching, or Review
    ("document_runtime",
     ["src.entity_runtime", "src.matching_runtime", "src.review_runtime"],
     "R01"),
    # R02: Entity Runtime must not import Matching or Review
    ("entity_runtime",
     ["src.matching_runtime", "src.review_runtime"],
     "R02"),
    # R03: Matching Runtime must not import Document Runtime
    ("matching_runtime",
     ["src.document_engine", "src.extract"],
     "R03"),
    # R04: Review Runtime must not import Document or Entity runtimes
    ("review_runtime",
     ["src.document_engine", "src.extract", "src.entity_runtime"],
     "R04"),
    # R05: API Runtime has a narrow approved Document Intelligence -> Security edge
    ("api_runtime",
     None,  # special: forbid all runtime imports except workflow_runtime
     "R05"),
]

# R12: Shared utilities must not import any runtime package
SHARED_FORBIDDEN_RULE = ("R12", ["src.document_engine", "src.extract",
                                 "src.workflow_runtime", "src.entity_runtime",
                                 "src.matching_runtime", "src.review_runtime",
                                 "src.api"])


# ---------------------------------------------------------------------------
# Violation data structure
# ---------------------------------------------------------------------------
class Violation:
    def __init__(self, rule_id: str, source_file: str, line_number: int,
                 import_statement: str, description: str):
        self.rule_id = rule_id
        self.source_file = source_file
        self.line_number = line_number
        self.import_statement = import_statement
        self.description = description

    def __repr__(self) -> str:
        return (f"[{self.rule_id}] {self.source_file}:{self.line_number}  "
                f"{self.import_statement}  ({self.description})")

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "source_file": self.source_file,
            "line_number": self.line_number,
            "import_statement": self.import_statement,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Exemption loading
# ---------------------------------------------------------------------------
def load_exemptions(path: Optional[str] = None) -> Set[str]:
    """Load exemption entries from exemptions.json.

    Returns a set of fingerprint strings for exempted violations.
    Each fingerprint is: rule_id:source_file:forbidden_import
    """
    if path is None:
        script_dir = Path(__file__).resolve().parent
        path = str(script_dir.parent / "tests" / "boundaries" / "exemptions.json")

    exemptions_file = Path(path)
    if not exemptions_file.exists():
        return set()

    with open(exemptions_file, "r") as f:
        data = json.load(f)

    exempted = set()
    registry = data.get("exemptions", [])
    for entry in registry:
        if not entry.get("active", True):
            continue
        fp = _make_fingerprint(
            entry.get("rule_id", ""),
            entry.get("source_file", ""),
            entry.get("forbidden_import", ""),
        )
        if fp:
            exempted.add(fp)
    return exempted


def _make_fingerprint(rule_id: str, source_file: str,
                       forbidden_import: str) -> str:
    """Create a normalized fingerprint for exemption matching.

    Normalizes backslashes to forward slashes to ensure cross-platform matching.
    """
    norm_file = source_file.replace("\\", "/")
    return f"{rule_id}:{norm_file}:{forbidden_import}"


# ---------------------------------------------------------------------------
# Import scanning
# ---------------------------------------------------------------------------
def scan_file_imports(filepath: str) -> List[dict]:
    """Return a list of import dicts from a single Python file.

    Each dict has keys: module, lineno, statement
    """
    imports = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        # Skip files with syntax errors (e.g., binary, corrupted)
        print(f"  [WARN] Skipping {filepath}: syntax error ({e})",
              file=sys.stderr)
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "lineno": node.lineno,
                    "statement": f"import {alias.name}",
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append({
                    "module": node.module,
                    "lineno": node.lineno,
                    "statement": f"from {node.module} import ...",
                })
    return imports


def matches_any_prefix(name: str, prefixes: List[str]) -> bool:
    """Check if name starts with any of the given prefixes.

    Handles both dotted Python module notation and slash-separated file paths.
    E.g., "src.entity_runtime" matches "src.entity_runtime.contracts.entity_set"
    and "src/workflow_runtime/runtime/workflow_runner" matches "src/workflow_runtime".
    """
    # Normalize both sides: replace backslashes, strip .py extension
    name_normalized = name.replace("\\", "/")
    if name_normalized.endswith(".py"):
        name_normalized = name_normalized[:-3]

    for prefix in prefixes:
        prefix_normalized = prefix.replace("\\", "/")

        # Check dotted matching (module-style)
        prefix_parts = prefix_normalized.split(".")
        name_parts = name_normalized.split(".")
        if len(name_parts) >= len(prefix_parts):
            if name_parts[:len(prefix_parts)] == prefix_parts:
                return True

        # Check path matching (filepath-style)
        prefix_path = prefix_normalized.replace(".", "/")
        if name_normalized == prefix_path or name_normalized.startswith(prefix_path + "/"):
            return True

    return False


# ---------------------------------------------------------------------------
# Rule checking
# ---------------------------------------------------------------------------
def check_rules(
    filepath: str,
    rel_path: str,
    imports: List[dict],
    exemptions: Set[str],
) -> List[Violation]:
    """Check all import rules for a single file. Returns list of violations."""
    violations: List[Violation] = []

    # Determine which runtime(s) this file belongs to
    consumer_runtimes: List[str] = []
    for runtime_key, prefixes in RUNTIME_PACKAGES.items():
        if matches_any_prefix(rel_path.replace("\\", "/").replace(".py", ""),
                              [p.replace(".", "/") for p in prefixes]):
            consumer_runtimes.append(runtime_key)

    # Check if this is a shared utility
    is_shared = False
    for sp in SHARED_UTILITY_PACKAGES:
        sp_path = sp.replace(".", "/")
        if rel_path.replace("\\", "/").startswith(sp_path):
            is_shared = True
            break

    for imp in imports:
        module = imp["module"]

        for runtime_key in consumer_runtimes:
            violations.extend(
                _check_consumer_rule(runtime_key, filepath, rel_path,
                                     module, imp, exemptions))

        if is_shared:
            violations.extend(
                _check_shared_rule(filepath, rel_path, module, imp,
                                   exemptions))

    return violations


def _check_consumer_rule(
    runtime_key: str,
    filepath: str,
    rel_path: str,
    module: str,
    imp: dict,
    exemptions: Set[str],
) -> List[Violation]:
    """Check rules for a specific consumer runtime."""
    violations: List[Violation] = []

    for rule_key, forbidden_prefixes, rule_id in FORBIDDEN_IMPORT_RULES:
        if runtime_key != rule_key:
            continue

        if rule_key == "api_runtime":
            # R05 special: API may import workflow_runtime. ADR-020 additionally
            # approves Document Intelligence API -> provider-neutral Security.
            if matches_any_prefix(module, ["src.workflow_runtime"]):
                continue
            normalized_path = rel_path.replace("\\", "/")
            if (
                normalized_path.startswith("src/api/document_intelligence/")
                and matches_any_prefix(module, ["src.security"])
            ):
                continue
            # Also allow standard library and third-party packages
            if not module.startswith("src."):
                continue
            # Also allow shared utilities (src.utils, src.config, src.schema_utils)
            if matches_any_prefix(module, SHARED_UTILITY_PACKAGES):
                continue
            # Anything else starting with src. is forbidden
            desc = "API Runtime import is outside approved Workflow/shared/Security boundaries"
            fp = _make_fingerprint(rule_id, rel_path, module)
            if fp not in exemptions:
                violations.append(Violation(
                    rule_id=rule_id, source_file=rel_path,
                    line_number=imp["lineno"],
                    import_statement=imp["statement"],
                    description=desc,
                ))
            continue

        # Standard forbidden-prefix check
        if matches_any_prefix(module, forbidden_prefixes):
            desc = (f"Runtime '{runtime_key}' must not import from "
                    f"{module}")
            fp = _make_fingerprint(rule_id, rel_path, module)
            if fp not in exemptions:
                violations.append(Violation(
                    rule_id=rule_id, source_file=rel_path,
                    line_number=imp["lineno"],
                    import_statement=imp["statement"],
                    description=desc,
                ))

    return violations


def _check_shared_rule(
    filepath: str,
    rel_path: str,
    module: str,
    imp: dict,
    exemptions: Set[str],
) -> List[Violation]:
    """Check R12 for shared utility files."""
    violations: List[Violation] = []

    if matches_any_prefix(module, SHARED_FORBIDDEN_RULE[1]):
        rule_id = SHARED_FORBIDDEN_RULE[0]
        desc = f"Shared utility must not import runtime module '{module}'"
        fp = _make_fingerprint(rule_id, rel_path, module)
        if fp not in exemptions:
            violations.append(Violation(
                rule_id=rule_id, source_file=rel_path,
                line_number=imp["lineno"],
                import_statement=imp["statement"],
                description=desc,
            ))

    return violations


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------
def scan_runtime_packages(src_dir: str,
                          exemptions: Set[str]) -> List[Violation]:
    """Scan all Python files in runtime packages for import violations."""
    all_violations: List[Violation] = []

    # Collect all files to scan — scan the entire src/ tree
    src_path = Path(src_dir)
    if not src_path.exists():
        print(f"Error: Source directory '{src_dir}' not found.", file=sys.stderr)
        sys.exit(1)

    python_files = sorted(src_path.rglob("*.py"))

    for filepath in python_files:
        rel_path = str(filepath.relative_to(src_path.parent))
        imports = scan_file_imports(str(filepath))
        if not imports:
            continue

        violations = check_rules(str(filepath), rel_path, imports, exemptions)
        all_violations.extend(violations)

    return all_violations


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(violations: List[Violation],
                    exemptions: Set[str]) -> str:
    """Generate a readable violation report."""
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append("RUNTIME BOUNDARY VERIFICATION — TIER 1 REPORT")
    lines.append("=" * 72)
    lines.append("")

    if not violations:
        lines.append("  RESULT: COMPLIANT")
        lines.append("  No boundary violations detected.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"  RESULT: {len(violations)} VIOLATION(S) FOUND")
    lines.append("")

    # Group by rule
    by_rule: Dict[str, List[Violation]] = {}
    for v in violations:
        by_rule.setdefault(v.rule_id, []).append(v)

    for rule_id in sorted(by_rule.keys()):
        rule_violations = by_rule[rule_id]
        lines.append(f"  [{rule_id}] — {len(rule_violations)} violation(s)")
        lines.append(f"  {'-' * 68}")
        for v in rule_violations:
            lines.append(f"    File:      {v.source_file}")
            lines.append(f"    Line:      {v.line_number}")
            lines.append(f"    Import:    {v.import_statement}")
            lines.append(f"    Reason:    {v.description}")
            lines.append("")
        lines.append("")

    # Exemption summary
    if exemptions:
        lines.append(f"  Exemptions active: {len(exemptions)}")
        for e in sorted(exemptions):
            lines.append(f"    - {e}")
    else:
        lines.append("  No exemptions active.")

    lines.append("=" * 72)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Runtime Boundary Verification — Tier 1 Static Import Analysis")
    parser.add_argument("--src-dir", default="src",
                        help="Source directory to scan (default: src)")
    parser.add_argument("--exemptions", default=None,
                        help="Path to exemptions.json (default: tests/boundaries/exemptions.json)")
    parser.add_argument("--json", action="store_true",
                        help="Output violations as JSON")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress non-violation output")

    args = parser.parse_args()

    exemptions = load_exemptions(args.exemptions)
    violations = scan_runtime_packages(args.src_dir, exemptions)

    report = generate_report(violations, exemptions)

    if args.json and violations:
        import json as json_mod
        print(json_mod.dumps([v.to_dict() for v in violations], indent=2))
    elif not args.quiet:
        print(report)

    if violations:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
