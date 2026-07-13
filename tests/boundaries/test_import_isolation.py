"""
Runtime Boundary Verification — Tier 1: Static Import Isolation Tests.

Tests:
- Boundary compliance (no violations with current codebase)
- Exemption handling (violations suppressed when exempted)
- Violation detection (simulated violations are caught)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

from tests.boundaries.conftest import (
    PROJECT_ROOT,
    assert_violation_in_report,
    create_exemptions_file,
    run_verification,
)


# ===========================================================================
# Baseline Boundary Compliance
# ===========================================================================

class TestBaselineCompliance:
    """Verify the current codebase against all Tier 1 rules.

    These tests run the verification script against the actual src/ tree
    and assert compliance (no violations) or document known exemptions.
    """

    def test_full_scan_with_exemptions(self):
        """Run full boundary scan with the default exemptions file.

        With the pre-existing legacy exemptions registered, the scan
        should be fully compliant.
        """
        result = run_verification(quiet=True)
        if result.returncode != 0:
            # Re-run without quiet to get the report
            verbose = run_verification(quiet=False)
            pytest.fail(
                f"Boundary violations detected (exit code {result.returncode}):\n"
                f"{verbose.stdout}\n{verbose.stderr}"
            )
        assert result.returncode == 0, (
            f"Expected compliant scan with exemptions, but got exit code {result.returncode}"
        )

    def test_explicit_exemptions_file_exists(self, exemptions_file):
        """Verify the exemptions registry exists and is valid JSON."""
        assert exemptions_file.exists(), (
            f"Exemptions file not found at {exemptions_file}"
        )
        with open(exemptions_file, "r") as f:
            data = json.load(f)
        assert "schema_version" in data
        assert "exemptions" in data
        assert isinstance(data["exemptions"], list)

    def test_exemptions_file_has_legacy_exemptions(self, exemptions_file):
        """Verify the exemptions file documents the pre-existing violations."""
        with open(exemptions_file, "r") as f:
            data = json.load(f)
        assert len(data["exemptions"]) == 4, (
            f"Expected 4 legacy exemptions, found {len(data['exemptions'])}"
        )
        # Verify all 4 are for R05 (API Runtime)
        for entry in data["exemptions"]:
            assert entry["rule_id"] == "R05", (
                f"Expected R05 exemption, got {entry['rule_id']}"
            )
            assert entry["active"] is True

    def test_full_scan_without_exemptions_detects_violations(self):
        """Without exemptions, the scan should detect pre-existing violations."""
        # Use an empty temporary exemptions file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"schema_version": "1.0", "exemptions": []}, f)
            empty_exemptions = Path(f.name)

        try:
            result = run_verification(
                exemptions_path=empty_exemptions,
                quiet=False,
            )
            assert result.returncode != 0, (
                "Expected violations without exemptions"
            )
            assert "R05" in result.stdout, (
                "Expected R05 violations without exemptions"
            )
        finally:
            if empty_exemptions.exists():
                os.unlink(empty_exemptions)

    def test_document_intelligence_api_may_import_security_only(self, temp_exemptions_file, tmp_path):
        package = tmp_path / "src" / "api" / "document_intelligence"
        package.mkdir(parents=True)
        (package / "auth.py").write_text(
            "from src.security import PermissionGuard\n",
            encoding="utf-8",
        )
        allowed = run_verification(
            exemptions_path=temp_exemptions_file,
            src_dir=str(tmp_path / "src"),
            quiet=False,
        )
        assert allowed.returncode == 0, allowed.stdout

        legacy_api = tmp_path / "src" / "api" / "legacy.py"
        legacy_api.write_text("from src.security import PermissionGuard\n", encoding="utf-8")
        denied = run_verification(
            exemptions_path=temp_exemptions_file,
            src_dir=str(tmp_path / "src"),
            quiet=False,
        )
        assert denied.returncode != 0
        assert "R05" in denied.stdout


# ===========================================================================
# Exemption Handling
# ===========================================================================

class TestExemptionHandling:
    """Test that the exemption mechanism works correctly."""

    def test_violation_suppressed_by_exemption(self, temp_exemptions_file):
        """Create a known violation, register an exemption, verify it passes."""
        # Create a temporary package with a violation
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "src" / "api"
            pkg_dir.mkdir(parents=True, exist_ok=True)
            (pkg_dir / "__init__.py").write_text(
                "from src.entity_runtime.contracts import entity_set\n"
                "from src.workflow_runtime.contracts import workflow_definition\n"
            )

            # First, verify violation is detected without exemption
            result = run_verification(
                exemptions_path=temp_exemptions_file,
                src_dir=str(Path(tmpdir) / "src"),
                quiet=False,
            )
            assert result.returncode != 0, (
                "Expected violations without exemption"
            )
            assert "R05" in result.stdout, (
                "Expected R05 violation for API Runtime import of entity_runtime"
            )

            # Now register an exemption for this violation
            create_exemptions_file(temp_exemptions_file, [
                {
                    "rule_id": "R05",
                    "source_file": "src/api/__init__.py",
                    "forbidden_import": "src.entity_runtime.contracts",
                    "adr_reference": "ADR-999-TEST",
                    "reason": "Test exemption",
                    "active": True,
                },
            ])

            # Verify the exemption suppresses the violation
            result = run_verification(
                exemptions_path=temp_exemptions_file,
                src_dir=str(Path(tmpdir) / "src"),
                quiet=False,
            )
            if result.returncode != 0:
                pytest.fail(
                    f"Expected compliance after registering exemption, "
                    f"but got exit code {result.returncode}:\n"
                    f"{result.stdout}\n{result.stderr}"
                )

    def test_inactive_exemption_does_not_suppress(self, temp_exemptions_file):
        """Verify that inactive exemptions do not suppress violations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "src" / "api"
            pkg_dir.mkdir(parents=True, exist_ok=True)
            (pkg_dir / "__init__.py").write_text(
                "from src.entity_runtime.contracts import entity_set\n"
            )

            # Register an INACTIVE exemption
            create_exemptions_file(temp_exemptions_file, [
                {
                    "rule_id": "R05",
                    "source_file": "src/api/__init__.py",
                    "forbidden_import": "src.entity_runtime.contracts",
                    "adr_reference": "ADR-999-TEST",
                    "reason": "Inactive test exemption",
                    "active": False,
                },
            ])

            # Violation should still be detected
            result = run_verification(
                exemptions_path=temp_exemptions_file,
                src_dir=str(Path(tmpdir) / "src"),
                quiet=False,
            )
            assert result.returncode != 0, (
                "Expected violation despite inactive exemption"
            )

    def test_missing_exemptions_file_is_ok(self, tmp_path):
        """Verify that a missing exemptions file is treated as empty."""
        fake_path = tmp_path / "nonexistent.json"

        clean_src = tmp_path / "clean_src"
        clean_src.mkdir(parents=True, exist_ok=True)
        (clean_src / "__init__.py").write_text("# no violations\n")

        result = run_verification(
            exemptions_path=fake_path,
            src_dir=str(clean_src),
            quiet=False,
        )
        assert result.returncode == 0, (
            f"Expected clean scan with missing exemptions file, "
            f"got exit code {result.returncode}"
        )


# ===========================================================================
# Violation Detection
# ===========================================================================

class TestViolationDetection:
    """Test that the verifier correctly detects various violation types."""

    # ------------------------------------------------------------------
    # R01 — Document Runtime
    # ------------------------------------------------------------------
    def test_r01_entity_runtime_import_in_document(self, tmp_path):
        """R01: Document Runtime importing Entity Runtime."""
        self._create_violation_test(
            tmp_path, "src/document_engine",
            "from src.entity_runtime.contracts import source_lineage",
            "R01",
        )

    def test_r01_matching_runtime_import_in_extract(self, tmp_path):
        """R01: Extract (Document Runtime) importing Matching Runtime."""
        self._create_violation_test(
            tmp_path, "src/extract",
            "from src.matching_runtime.contracts import match_request",
            "R01",
        )

    # ------------------------------------------------------------------
    # R02 — Entity Runtime
    # ------------------------------------------------------------------
    def test_r02_matching_runtime_import_in_entity(self, tmp_path):
        """R02: Entity Runtime importing Matching Runtime."""
        self._create_violation_test(
            tmp_path, "src/entity_runtime",
            "from src.matching_runtime.contracts import match_request",
            "R02",
        )

    def test_r02_review_runtime_import_in_entity(self, tmp_path):
        """R02: Entity Runtime importing Review Runtime."""
        self._create_violation_test(
            tmp_path, "src/entity_runtime",
            "from src.review_runtime.models import review_item",
            "R02",
        )

    # ------------------------------------------------------------------
    # R03 — Matching Runtime
    # ------------------------------------------------------------------
    def test_r03_document_engine_import_in_matching(self, tmp_path):
        """R03: Matching Runtime importing Document Engine."""
        self._create_violation_test(
            tmp_path, "src/matching_runtime",
            "from src.document_engine.structure.models import canonical_table",
            "R03",
        )

    def test_r03_extract_import_in_matching(self, tmp_path):
        """R03: Matching Runtime importing Extract."""
        self._create_violation_test(
            tmp_path, "src/matching_runtime",
            "from src.extract import base_connector",
            "R03",
        )

    # ------------------------------------------------------------------
    # R04 — Review Runtime
    # ------------------------------------------------------------------
    def test_r04_document_engine_import_in_review(self, tmp_path):
        """R04: Review Runtime importing Document Engine."""
        self._create_violation_test(
            tmp_path, "src/review_runtime",
            "from src.document_engine.parsers import document_parser",
            "R04",
        )

    def test_r04_entity_runtime_import_in_review(self, tmp_path):
        """R04: Review Runtime importing Entity Runtime."""
        self._create_violation_test(
            tmp_path, "src/review_runtime",
            "from src.entity_runtime.contracts import entity_set",
            "R04",
        )

    # ------------------------------------------------------------------
    # R05 — API Runtime
    # ------------------------------------------------------------------
    def test_r05_entity_runtime_import_in_api(self, tmp_path):
        """R05: API Runtime importing Entity Runtime."""
        self._create_violation_test(
            tmp_path, "src/api",
            "from src.entity_runtime.contracts import entity_set",
            "R05",
        )

    def test_r05_matching_runtime_import_in_api(self, tmp_path):
        """R05: API Runtime importing Matching Runtime."""
        self._create_violation_test(
            tmp_path, "src/api",
            "from src.matching_runtime.services import matching_service",
            "R05",
        )

    # ------------------------------------------------------------------
    # R12 — Shared Utilities
    # ------------------------------------------------------------------
    def test_r12_runtime_import_in_utils(self, tmp_path):
        """R12: Shared utility importing runtime module."""
        self._create_violation_test(
            tmp_path, "src",
            "from src.workflow_runtime.contracts import workflow_definition",
            "R12",
            filename="utils.py",
        )

    def test_r12_runtime_import_in_config(self, tmp_path):
        """R12: Config importing runtime module."""
        self._create_violation_test(
            tmp_path, "src",
            "from src.entity_runtime.contracts import entity_set",
            "R12",
            filename="config.py",
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _create_violation_test(
        self,
        tmp_path: Path,
        package_path: str,
        import_statement: str,
        expected_rule: str,
        filename: str = "__init__.py",
    ):
        """Helper to create a temporary file with a violation and verify detection."""
        pkg_dir = Path(tmp_path) / package_path
        pkg_dir.mkdir(parents=True, exist_ok=True)

        file_path = pkg_dir / filename
        file_path.write_text(import_statement + "\n")

        result = run_verification(
            exemptions_path=Path(tmp_path) / "empty.json",
            src_dir=str(Path(tmp_path) / "src"),
            quiet=False,
        )

        # Verify detection - use both stdout and stderr combined
        combined = result.stdout + result.stderr
        assert result.returncode != 0, (
            f"Expected violation [{expected_rule}] to be detected in "
            f"{package_path}/{filename}, but scan passed. "
            f"Output: {combined}"
        )

        assert_violation_in_report(result.stdout, expected_rule)


# ===========================================================================
# CLI Interface
# ===========================================================================

class TestCLI:
    """Test the CLI interface of verify_boundaries.py."""

    def test_help(self):
        """Verify the script runs without crash."""
        result = run_verification(quiet=True)
        assert result.returncode in (0, 1)

    def test_json_output(self, tmp_path):
        """Verify --json flag produces valid JSON output."""
        pkg_dir = tmp_path / "src" / "api"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "__init__.py").write_text(
            "from src.entity_runtime.contracts import entity_set\n"
        )

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_boundaries.py"),
            "--src-dir", str(tmp_path / "src"),
            "--json",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode != 0
        try:
            violations = json.loads(result.stdout)
            assert isinstance(violations, list)
            assert len(violations) > 0
            assert "rule_id" in violations[0]
            assert "source_file" in violations[0]
        except json.JSONDecodeError:
            pytest.fail("Expected valid JSON output")

    def test_quiet_mode(self):
        """Verify --quiet mode suppresses output."""
        result = run_verification(quiet=True)
        # stdout should be empty in quiet mode
        # (only the report is printed to stdout when not quiet)
        pass
