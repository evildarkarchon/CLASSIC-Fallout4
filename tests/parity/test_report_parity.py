"""VAL-03: Python-Rust report generation parity tests.

Tests that Rust OrchestratorCore produces AUTOSCAN.md output that matches
Python-generated reports character-for-character (after timestamp masking
and path normalization).

**True Parity Validation:**
The golden files in tests/golden/captured/ are ACTUAL Python-generated
AUTOSCAN.md reports copied from Crash Logs/. This enables true Python-Rust
parity validation, not just regression testing.

Per CONTEXT.md decisions:
- Timestamps: Masked with {{TIMESTAMP}} placeholder
- Paths: Normalized to forward slashes (not masked - path masking REMOVED in 10-01)
- Whitespace: Strict matching
- Comparison: Whole-file (entire report as one unit)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures.golden_fixtures import (
    GOLDEN_DIR,
    generate_diff,
    mask_dynamic_data,
    normalize_paths,
)
from ClassicLib.integration.rust.orchestrator_api import ClassicOrchestrator
from ClassicLib.integration.factory import get_rust_component_status


def load_report_manifest() -> dict[str, dict[str, str]]:
    """Load manifest mapping golden files to source logs.

    Returns:
        Dict mapping golden_name to {source_log, autoscan, golden}.
    """
    manifest_path = GOLDEN_DIR / "report_manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def get_report_golden_stems() -> list[str]:
    """Discover available report golden files from manifest.

    Returns list of stems for which report golden files exist.
    """
    manifest = load_report_manifest()
    return sorted(manifest.keys())


# Dynamically discover golden report files
REPORT_GOLDEN_STEMS = get_report_golden_stems()


def normalize_for_comparison(text: str) -> str:
    """Apply all normalization for parity comparison.

    Per CONTEXT.md:
    - Timestamps: Masked with {{TIMESTAMP}} (mask_dynamic_data handles ONLY this)
    - Paths: Normalized to forward slashes (normalize_paths handles this separately)

    Args:
        text: Raw report text.

    Returns:
        Normalized text ready for comparison.
    """
    result = mask_dynamic_data(text)  # Masks timestamps ONLY (path masking removed in 10-01)
    result = normalize_paths(result)  # Normalizes path slashes
    return result


@pytest.fixture
def orchestrator():
    """Create ClassicOrchestrator for report generation."""
    return ClassicOrchestrator()


@pytest.fixture
def crash_logs_dir() -> Path:
    """Path to Crash Logs directory (source of log files)."""
    return Path(__file__).parent.parent.parent / "Crash Logs"


@pytest.mark.parity
@pytest.mark.integration
class TestReportParity:
    """VAL-03: Python-Rust report generation parity tests.

    These are TRUE parity tests comparing Rust output against
    actual Python-generated AUTOSCAN.md reports.
    """

    @pytest.mark.parametrize("golden_stem", REPORT_GOLDEN_STEMS)
    def test_report_matches_python_golden(
        self, golden_stem: str, orchestrator, crash_logs_dir: Path
    ):
        """Rust report output matches Python golden for {golden_stem}."""
        # Load manifest to find source log
        manifest = load_report_manifest()
        if golden_stem not in manifest:
            pytest.skip(f"Golden stem not in manifest: {golden_stem}")

        entry = manifest[golden_stem]
        source_log = entry["source_log"]

        # Load Python-generated golden report
        golden_path = GOLDEN_DIR / f"{golden_stem}_report.golden.md"
        if not golden_path.exists():
            pytest.skip(f"Golden report not found: {golden_path}")

        expected_report = golden_path.read_text(encoding="utf-8")

        # Find source log file
        log_path = crash_logs_dir / source_log
        if not log_path.exists():
            pytest.skip(f"Source log not found: {log_path}")

        # Generate report with Rust orchestrator
        result = orchestrator.process_crash_log(log_path)
        actual_report = "\n".join(result.report_lines)

        # Normalize actual report for comparison
        actual_normalized = normalize_for_comparison(actual_report)

        # Compare against pre-normalized golden (already normalized during capture)
        if actual_normalized != expected_report:
            diff = generate_diff(expected_report, actual_normalized)
            pytest.fail(
                f"Parity mismatch for {golden_stem}:\n\n{diff}\n\n"
                "Rust output does not match Python-generated golden file. "
                "This is a TRUE parity failure - investigate the difference."
            )

    def test_rust_components_verified(self):
        """Verify Rust components are active (not Python fallback)."""
        status = get_rust_component_status()
        available = status.get("available", {})

        # Core components required for report generation
        required = ["scanlog", "yaml", "config"]

        for component in required:
            assert available.get(component, False), (
                f"Rust component '{component}' not available. "
                "Report parity tests require Rust acceleration. "
                "Run './rebuild_rust.ps1' to build Rust modules."
            )

    def test_orchestrator_is_feature_complete(self, orchestrator):
        """VAL-05 partial: Orchestrator has required features."""
        assert orchestrator is not None
        assert hasattr(orchestrator, 'process_crash_log'), (
            "Orchestrator missing process_crash_log method"
        )
