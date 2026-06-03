"""
Shared fixtures and helpers for runtime boundary verification tests.

Provides:
- Runtime path discovery
- Shared test fixtures for exemption files
- Helper functions for verifying boundary reports
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
VERIFY_SCRIPT = SCRIPTS_DIR / "verify_boundaries.py"
DEFAULT_EXEMPTIONS = PROJECT_ROOT / "tests" / "boundaries" / "exemptions.json"

# Runtime package paths (relative to project root)
RUNTIME_PATHS: Dict[str, str] = {
    "document_runtime": "src/document_engine",
    "extract": "src/extract",
    "workflow_runtime": "src/workflow_runtime",
    "entity_runtime": "src/entity_runtime",
    "matching_runtime": "src/matching_runtime",
    "review_runtime": "src/review_runtime",
    "api_runtime": "src/api",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def verify_script_path() -> Path:
    """Return the path to verify_boundaries.py."""
    return VERIFY_SCRIPT


@pytest.fixture
def exemptions_file() -> Path:
    """Return the path to the exemptions registry."""
    return DEFAULT_EXEMPTIONS


@pytest.fixture
def temp_exemptions_file() -> Path:
    """Create a temporary exemptions file for testing.

    Yields the path and cleans up after the test.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({"schema_version": "1.0", "exemptions": []}, f)
        temp_path = Path(f.name)

    yield temp_path

    if temp_path.exists():
        os.unlink(temp_path)


@pytest.fixture
def temp_test_package(tmp_path: Path) -> Path:
    """Create a temporary Python package for isolation tests.

    Creates a minimal package structure under tmp_path with an __init__.py.
    """
    pkg_dir = tmp_path / "test_pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("")
    return pkg_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run_verification(
    exemptions_path: Optional[Path] = None,
    src_dir: Optional[str] = None,
    quiet: bool = True,
) -> subprocess.CompletedProcess:
    """Run verify_boundaries.py and return the CompletedProcess result.

    Args:
        exemptions_path: Path to exemptions.json (None = default)
        src_dir: Source directory to scan (None = 'src')
        quiet: If True, suppresses output

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    cmd = [sys.executable, str(VERIFY_SCRIPT)]
    if exemptions_path:
        cmd.extend(["--exemptions", str(exemptions_path)])
    if src_dir:
        cmd.extend(["--src-dir", src_dir])
    if quiet:
        cmd.append("--quiet")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    return result


def create_exemptions_file(path: Path, exemptions: List[Dict]) -> Path:
    """Write an exemptions.json file with the given exemption entries.

    Args:
        path: Path to write the file
        exemptions: List of exemption dicts

    Returns:
        The path that was written to
    """
    data = {
        "schema_version": "1.0",
        "exemptions": exemptions,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def assert_violation_in_report(
    report: str,
    rule_id: str,
    source_file: Optional[str] = None,
    forbidden_import: Optional[str] = None,
) -> None:
    """Assert that a specific violation is present in the report."""
    assert f"[{rule_id}]" in report, (
        f"Expected violation [{rule_id}] not found in report"
    )
    if source_file:
        assert source_file in report, (
            f"Expected source_file '{source_file}' not found in report"
        )
    if forbidden_import:
        assert forbidden_import in report, (
            f"Expected forbidden_import '{forbidden_import}' not found in report"
        )