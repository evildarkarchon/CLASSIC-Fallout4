from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE = REPO_ROOT / "CLAUDE.md"
PROJECT = REPO_ROOT / ".planning/PROJECT.md"
STACK = REPO_ROOT / ".planning/codebase/STACK.md"
REQUIREMENTS = REPO_ROOT / ".planning/REQUIREMENTS.md"
PHASE4_VERIFICATION = (
    REPO_ROOT / ".planning/phases/04-gate-validation-documentation/04-VERIFICATION.md"
)
API_README = REPO_ROOT / "docs/api/README.md"
BINDING_REFRESH_NOTE = REPO_ROOT / "docs/api/binding-contract-refresh-note.md"
QUICK_START = REPO_ROOT / "docs/api/QUICK_START.md"
PARITY_OVERVIEW = REPO_ROOT / "docs/api/binding-parity-overview.md"
CLASSIC_CONFIG_CORE = REPO_ROOT / "docs/api/classic-config-core.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_requirement_direct_proof(text: str, requirement_id: str) -> str:
    pattern = re.compile(
        rf"^\| `{re.escape(requirement_id)}` \| .*? \| ✓ SATISFIED \| (.*?) \|$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing requirements coverage row for {requirement_id}")
    return match.group(1)


class Phase04ValidationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.claude = read_text(CLAUDE)
        self.project = read_text(PROJECT)
        self.stack = read_text(STACK)
        self.requirements = read_text(REQUIREMENTS)
        self.phase4_verification = read_text(PHASE4_VERIFICATION)
        self.api_readme = read_text(API_README)
        self.binding_refresh_note = read_text(BINDING_REFRESH_NOTE)
        self.quick_start = read_text(QUICK_START)
        self.parity_overview = read_text(PARITY_OVERVIEW)
        self.classic_config_core = read_text(CLASSIC_CONFIG_CORE)

    def test_gate05_api_docs_keep_verify_first_and_historical_only_wording(
        self,
    ) -> None:
        for text in [self.binding_refresh_note, self.quick_start]:
            self.assertIn("bun run parity:gate", text)
            self.assertIn("bun run parity:gate:update-baseline", text)
            self.assertNotIn("parity:gate:local", text)

        self.assertIn("surviving 16 Rust business-logic crates", self.api_readme)
        self.assertIn(
            "Historical absorbed-crate names appear only as short migration notes",
            self.api_readme,
        )
        self.assertIn("former `classic-yaml-core`", self.parity_overview)
        self.assertIn("former `classic-crashgen-settings-core`", self.parity_overview)
        self.assertIn("historical note", self.classic_config_core)

    def test_gate06_contributor_docs_keep_16_crate_closure_state(self) -> None:
        expected_fragments = {
            "CLAUDE.md": "16 pure Rust crates",
            ".planning/PROJECT.md": "16 business-logic `-core` crates",
            ".planning/codebase/STACK.md": "16 pure Rust business-logic crates",
        }

        for document_name, fragment in expected_fragments.items():
            text = {
                "CLAUDE.md": self.claude,
                ".planning/PROJECT.md": self.project,
                ".planning/codebase/STACK.md": self.stack,
            }[document_name]
            with self.subTest(document=document_name):
                self.assertIn(fragment, text)

        self.assertIn("bun run parity:gate", self.claude)
        self.assertIn("bun run parity:gate:update-baseline", self.claude)
        self.assertNotIn("parity:gate:local", self.claude)
        self.assertIn("Phase 4 complete", self.project)
        self.assertIn("04-VERIFICATION.md", self.project)

    def test_phase4_verification_retains_required_sections_and_closure_evidence(
        self,
    ) -> None:
        required_sections = [
            "## Goal Achievement",
            "### Observable Truths",
            "### Required Artifacts",
            "### Key Link Verification",
            "### Behavioral Spot-Checks",
            "### Requirements Coverage",
            "### Anti-Patterns Found",
            "### Human Verification Required",
            "### Gaps Summary",
        ]

        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, self.phase4_verification)

        for fragment in [
            "doc audit evidence",
            "CXX parity gate exits 0",
            "Python parity gate exits 0",
            "Node parity gate exits 0",
            "cargo test --workspace",
            "build_cli.ps1 -Test",
            "build_gui.ps1 -Test",
            "one-tier zero-drift semantics",
        ]:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.phase4_verification)

    def test_phase4_requirements_stay_checked_and_trace_to_verification_proof(
        self,
    ) -> None:
        for requirement_id in [
            "GATE-01",
            "GATE-02",
            "GATE-03",
            "GATE-04",
            "GATE-05",
            "GATE-06",
        ]:
            with self.subTest(requirement_id=requirement_id):
                self.assertRegex(
                    self.requirements,
                    rf"- \[x\] \*\*{re.escape(requirement_id)}\*\*:",
                )
                self.assertRegex(
                    self.requirements,
                    rf"\| {re.escape(requirement_id)} \| Phase 4 \| Complete \|",
                )

                direct_proof = extract_requirement_direct_proof(
                    self.phase4_verification, requirement_id
                )
                self.assertNotIn("see summary", direct_proof.lower())
                self.assertNotIn("same as above", direct_proof.lower())
                self.assertGreater(len(direct_proof.strip()), 20)


if __name__ == "__main__":
    unittest.main()
