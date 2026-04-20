from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNING_ROOT = REPO_ROOT / ".planning"
MILESTONES_DIR = PLANNING_ROOT / "milestones"
PHASE7_DIR = REPO_ROOT / ".planning/phases/07-crate-relocation-and-path-rewire"
RELOCATION_AUDIT = PHASE7_DIR / "07-RELOCATION-AUDIT.md"
VERIFICATION_REPORT = PHASE7_DIR / "07-VERIFICATION.md"
REQUIREMENTS = MILESTONES_DIR / "v9.1.0-root-REQUIREMENTS.md"
if not REQUIREMENTS.exists():
    REQUIREMENTS = PLANNING_ROOT / "REQUIREMENTS.md"

MILESTONE_AUDIT = MILESTONES_DIR / "v9.1.0-root-MILESTONE-AUDIT.md"
if not MILESTONE_AUDIT.exists():
    MILESTONE_AUDIT = PLANNING_ROOT / "v9.1.0-MILESTONE-AUDIT.md"

LEGACY_ROOT = REPO_ROOT / "ClassicLib-rs"

REQUIRED_VERIFICATION_SECTIONS = [
    "## Goal Achievement",
    "### Observable Truths",
    "### Required Artifacts",
    "### Key Link Verification",
    "### Behavioral Spot-Checks",
    "### Requirements Coverage",
    "### Gaps Summary",
]

SUMMARY_ONLY_FRAGMENTS = [
    "07-03-SUMMARY.md",
    "see summary",
    "same as above",
    "summary-only",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("expected markdown frontmatter")
    return match.group(1)


def extract_table_row(text: str, first_cell: str) -> str:
    pattern = re.compile(rf"^\| {re.escape(first_cell)} \| .*?$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing markdown table row for {first_cell}")
    return match.group(0)


def extract_requirement_evidence(text: str, requirement_id: str) -> str:
    pattern = re.compile(
        rf"^\| {re.escape(requirement_id)} \| .*? \| .*? \| (.*?) \|$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing requirements coverage row for {requirement_id}")
    return match.group(1)


def audit_residue_rows(text: str) -> list[str]:
    in_section = False
    rows: list[str] = []
    for line in text.splitlines():
        if line == "## Legacy ClassicLib-rs Residue":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("| `"):
            rows.append(line.strip())
    return rows


def legacy_residue_inventory() -> list[str]:
    if not LEGACY_ROOT.is_dir():
        return []

    return sorted(
        f"{entry.name}/" if entry.is_dir() else entry.name
        for entry in LEGACY_ROOT.iterdir()
    )


class Phase11ValidationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.relocation_audit = read_text(RELOCATION_AUDIT)
        cls.requirements = read_text(REQUIREMENTS)
        cls.milestone_audit = read_text(MILESTONE_AUDIT)
        cls.live_residue = legacy_residue_inventory()

    def test_phase7_audit_uses_live_residue_inventory_without_stale_cargo_entry(
        self,
    ) -> None:
        self.assertIn("## Legacy ClassicLib-rs Residue", self.relocation_audit)
        self.assertNotIn("| `.cargo/` |", self.relocation_audit)

        expected_rows = [f"| `{entry}` |" for entry in self.live_residue]
        actual_rows = audit_residue_rows(self.relocation_audit)

        if LEGACY_ROOT.is_dir():
            self.assertEqual(sorted(expected_rows), sorted(actual_rows))
        else:
            self.assertEqual([], actual_rows)

    def test_phase7_verification_report_has_frontmatter_and_current_section_shape(
        self,
    ) -> None:
        verification_text = read_text(VERIFICATION_REPORT)
        frontmatter = extract_frontmatter(verification_text)

        self.assertIn("phase: 07-crate-relocation-and-path-rewire", frontmatter)
        self.assertIn("status:", frontmatter)
        self.assertIn(
            "# Phase 7: Crate Relocation and Path Rewire Verification Report",
            verification_text,
        )

        for section in REQUIRED_VERIFICATION_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, verification_text)

    def test_move_requirements_use_direct_phase7_evidence_in_verification(self) -> None:
        verification_text = read_text(VERIFICATION_REPORT)

        expected_fragments = {
            "MOVE-01": [
                "07-RELOCATION-AUDIT.md",
                "Old to New Crate Mapping",
                "foundation/classic-shared-core",
            ],
            "MOVE-02": [
                "07-RELOCATION-AUDIT.md",
                "cargo metadata --format-version 1 --no-deps",
                "workspace_root=J:\\CLASSIC-Fallout4",
            ],
        }

        for requirement_id, fragments in expected_fragments.items():
            evidence = extract_requirement_evidence(verification_text, requirement_id)
            with self.subTest(requirement_id=requirement_id):
                for fragment in fragments:
                    self.assertIn(fragment, evidence)
                for forbidden in SUMMARY_ONLY_FRAGMENTS:
                    self.assertNotIn(forbidden.lower(), evidence.lower())

    def test_requirements_mark_move_requirements_complete_in_phase11(self) -> None:
        for requirement_id in ["MOVE-01", "MOVE-02"]:
            with self.subTest(requirement_id=requirement_id):
                self.assertRegex(
                    self.requirements,
                    rf"- \[x\] \*\*{re.escape(requirement_id)}\*\*:",
                )
                self.assertRegex(
                    self.requirements,
                    rf"\| {re.escape(requirement_id)} \| Phase 11 \| Complete \|",
                )

    def test_milestone_audit_no_longer_reports_the_stale_phase7_gap(self) -> None:
        stale_gap_fragments = [
            "07-VERIFICATION.md is missing",
            "test_phase07_validation.py:50-60",
            "ClassicLib-rs/.cargo residue",
            "The checked-in relocation proof is stale and no longer rerunnable cleanly.",
        ]

        for fragment in stale_gap_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, self.milestone_audit)

        for requirement_id in ["MOVE-01", "MOVE-02"]:
            row = extract_table_row(self.milestone_audit, requirement_id)
            with self.subTest(requirement_id=requirement_id):
                self.assertNotIn("Unsatisfied (orphaned)", row)
                self.assertNotIn("missing", row)


if __name__ == "__main__":
    unittest.main()
