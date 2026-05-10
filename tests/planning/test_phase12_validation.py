from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE12_DIR = REPO_ROOT / ".planning" / "phases" / "12-integration-replay-and-verification-closure"
PHASE08_DIR = REPO_ROOT / ".planning" / "phases" / "08-wrapper-and-parity-rewire"
PHASE09_DIR = REPO_ROOT / ".planning" / "phases" / "09-clean-validation-and-ci-refresh"
ROOT_MILESTONE_AUDIT = REPO_ROOT / ".planning" / "milestones" / "v9.1.0-root-MILESTONE-AUDIT.md"
ROOT_MILESTONE_ROADMAP = REPO_ROOT / ".planning" / "milestones" / "v9.1.0-root-ROADMAP.md"
PROJECT = REPO_ROOT / ".planning" / "PROJECT.md"
STATE = REPO_ROOT / ".planning" / "STATE.md"
MILESTONES = REPO_ROOT / ".planning" / "MILESTONES.md"
PHASE12_AUDIT_COMMAND = (
    "uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q"
)


PHASE12_SUMMARY_REQUIREMENTS = {
    "12-01-SUMMARY.md": ["INTG-01", "INTG-04"],
    "12-02-SUMMARY.md": ["INTG-01", "INTG-02"],
    "12-03-SUMMARY.md": ["INTG-03", "INTG-04"],
}

PHASE08_SUMMARY_REQUIREMENTS = {
    "08-01-SUMMARY.md": ["INTG-01"],
    "08-02-SUMMARY.md": ["INTG-01"],
    "08-03-SUMMARY.md": ["INTG-02"],
    "08-04-SUMMARY.md": ["INTG-02"],
    "08-05-SUMMARY.md": ["INTG-02"],
    "08-06-SUMMARY.md": ["INTG-01", "INTG-02"],
}

PHASE09_SUMMARY_REQUIREMENTS = {
    "09-01-SUMMARY.md": ["INTG-04"],
    "09-02-SUMMARY.md": ["INTG-03"],
    "09-03-SUMMARY.md": ["INTG-03"],
    "09-04-SUMMARY.md": ["INTG-03", "INTG-04"],
}


def read_text(path: Path) -> str:
    """Read a UTF-8 planning artifact and fail with the path in the assertion context."""
    if not path.exists():
        raise AssertionError(f"expected artifact to exist: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def extract_frontmatter(text: str) -> str:
    """Return the markdown frontmatter block for simple string-based contract checks."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("expected markdown frontmatter")
    return match.group(1)


def extract_table_row(text: str, first_cell: str) -> str:
    """Return the first markdown table row whose first cell matches the requested value."""
    pattern = re.compile(rf"^\| {re.escape(first_cell)} \|.*?$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing markdown table row for {first_cell}")
    return match.group(0)


class Phase12ValidationAuditTests(unittest.TestCase):
    """Audit Phase 12 Nyquist closure against the current archived milestone state."""

    maxDiff = None

    def assert_summary_frontmatter(
        self, phase_dir: Path, summary_name: str, expected_requirements: list[str]
    ) -> None:
        """Assert a summary exposes machine-checkable phase, plan, and requirement metadata."""
        text = read_text(phase_dir / summary_name)
        frontmatter = extract_frontmatter(text)
        plan = summary_name.split("-")[1]

        self.assertIn(f"phase: {phase_dir.name}", frontmatter)
        self.assertRegex(frontmatter, rf"(?m)^plan:\s*['\"]?{plan}['\"]?$")
        self.assertIn("requirements-completed:", frontmatter)
        for requirement_id in expected_requirements:
            self.assertIn(requirement_id, frontmatter)

    def test_phase12_validation_contract_is_current_and_compliant(self) -> None:
        """The new validation contract must be the current automated guard for Phase 12."""
        validation = read_text(PHASE12_DIR / "12-VALIDATION.md")
        frontmatter = extract_frontmatter(validation)

        for fragment in (
            "phase: 12",
            "slug: integration-replay-and-verification-closure",
            "status: approved",
            "nyquist_compliant: true",
            "wave_0_complete: true",
        ):
            self.assertIn(fragment, frontmatter)

        for task_id in ("12-01-01", "12-02-01", "12-03-01", "12-99-01"):
            row = extract_table_row(validation, task_id)
            self.assertIn(PHASE12_AUDIT_COMMAND, row)
            self.assertIn("green", row)

        self.assertIn("All phase behaviors have automated verification.", validation)
        self.assertIn("Validation Audit 2026-05-10", validation)
        self.assertNotIn("test_phase08_validation.py -q", validation)
        self.assertNotIn("test_phase09_validation.py -q", validation)
        self.assertNotIn("phase09_clean_run.ps1", validation)

    def test_phase12_and_parent_summaries_expose_requirement_metadata(self) -> None:
        """Phase 12 must preserve the frontmatter traceability it backfilled upstream."""
        for summary_name, requirement_ids in PHASE12_SUMMARY_REQUIREMENTS.items():
            with self.subTest(summary=summary_name):
                self.assert_summary_frontmatter(PHASE12_DIR, summary_name, requirement_ids)

        for summary_name, requirement_ids in PHASE08_SUMMARY_REQUIREMENTS.items():
            with self.subTest(summary=summary_name):
                self.assert_summary_frontmatter(PHASE08_DIR, summary_name, requirement_ids)

        for summary_name, requirement_ids in PHASE09_SUMMARY_REQUIREMENTS.items():
            with self.subTest(summary=summary_name):
                self.assert_summary_frontmatter(PHASE09_DIR, summary_name, requirement_ids)

    def test_phase8_and_phase9_verification_reports_cover_integration_ids(self) -> None:
        """The canonical parent verification reports must still cover all integration IDs."""
        phase8 = read_text(PHASE08_DIR / "08-VERIFICATION.md")
        phase9 = read_text(PHASE09_DIR / "09-VERIFICATION.md")

        intg1_row = extract_table_row(phase8, "INTG-01")
        for fragment in (
            "rebuild_rust.ps1",
            "classic-cli/build_cli.ps1 -Test",
            "classic-gui/build_gui.ps1 -Test",
            "cargo run -p classic-tui -- --version",
        ):
            self.assertIn(fragment, intg1_row)

        intg2_row = extract_table_row(phase8, "INTG-02")
        for fragment in (
            "python tools/python_api_parity/check_parity_gate.py --repo-root .",
            "bun run parity:gate",
            "bun run dts:freshness:check",
            "python tools/cxx_api_parity/check_parity_gate.py --repo-root .",
        ):
            self.assertIn(fragment, intg2_row)

        intg3_row = extract_table_row(phase9, "INTG-03")
        for fragment in (
            ".github/workflows/ci-rust.yml",
            ".github/workflows/ci-python-bindings.yml",
            ".github/workflows/ci-typescript.yml",
            ".github/workflows/ci-cpp.yml",
            "classic-gui/build_gui.ps1 -Package",
        ):
            self.assertIn(fragment, intg3_row)

        intg4_row = extract_table_row(phase9, "INTG-04")
        for fragment in (
            "09-CLEAN-VALIDATION-AUDIT.md",
            ".venv",
            "wrapper replay",
            "no-new-residue",
        ):
            self.assertIn(fragment, intg4_row)

        phase9_audit = read_text(PHASE09_DIR / "09-CLEAN-VALIDATION-AUDIT.md")
        self.assertIn("python-bindings/.venv", phase9_audit)
        self.assertIn("rebuild_rust.ps1 -Target python -BuildOnly", phase9_audit)

    def test_archived_milestone_no_longer_lists_phase12_nyquist_debt(self) -> None:
        """Current milestone surfaces must not keep advertising the closed 12-VALIDATION gap."""
        audit = read_text(ROOT_MILESTONE_AUDIT)
        roadmap = read_text(ROOT_MILESTONE_ROADMAP)
        project = read_text(PROJECT)
        state = read_text(STATE)
        milestones = read_text(MILESTONES)

        self.assertIn("overall: \"compliant\"", audit)
        self.assertIn("missing_phases: []", audit)
        self.assertIn(
            "| 12 Integration Replay and Verification Closure | `12-VERIFICATION.md` passed | `12-VALIDATION.md` compliant",
            audit,
        )

        for text in (audit, roadmap, project, state, milestones):
            with self.subTest(surface=text[:40]):
                self.assertNotIn("12-VALIDATION.md` is still missing", text)
                self.assertNotIn("No 12-VALIDATION.md exists", text)
                self.assertNotIn("missing Phase 12 validation contract", text)

    def test_phase12_validation_replaces_retired_migration_test_references(self) -> None:
        """The current guard should use archived closure artifacts, not deleted migration tests."""
        validation = read_text(PHASE12_DIR / "12-VALIDATION.md")

        self.assertIn("244935ff", validation)
        self.assertIn("obsolete migration tests", validation)
        self.assertIn("v9.1.0-root-MILESTONE-AUDIT.md", validation)
        self.assertIn("v9.1.0-root-ROADMAP.md", validation)

        retired_paths = (
            REPO_ROOT / "tests" / "planning" / "test_phase08_validation.py",
            REPO_ROOT / "tests" / "planning" / "test_phase09_validation.py",
            REPO_ROOT / "tests" / "planning" / "phase09_clean_run.ps1",
        )
        for retired_path in retired_paths:
            with self.subTest(path=retired_path.name):
                self.assertFalse(retired_path.exists())


if __name__ == "__main__":
    unittest.main()
