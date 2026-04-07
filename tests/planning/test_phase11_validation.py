from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE8_VERIFICATION = (
    REPO_ROOT / ".planning/phases/08-workspace-and-infrastructure/08-VERIFICATION.md"
)
REQUIREMENTS = REPO_ROOT / ".planning/REQUIREMENTS.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("expected markdown frontmatter")
    return match.group(1)


def extract_requirement_direct_proof(text: str, requirement_id: str) -> str:
    pattern = re.compile(
        rf"^\| {re.escape(requirement_id)} \| .*? \| SATISFIED \| (.*?) \|$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing requirements coverage row for {requirement_id}")
    return match.group(1)


class Phase11ValidationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.phase8_verification = read_text(PHASE8_VERIFICATION)
        self.requirements = read_text(REQUIREMENTS)

    def test_phase8_verification_is_authoritative_initial_artifact(self) -> None:
        frontmatter = extract_frontmatter(self.phase8_verification)

        self.assertIn("phase: 08-workspace-and-infrastructure", frontmatter)
        self.assertNotIn("re_verification:", frontmatter)
        self.assertIn(
            "# Phase 08: Workspace and Infrastructure Verification Report",
            self.phase8_verification,
        )

        required_sections = [
            "## Goal Achievement",
            "### Observable Truths",
            "## Required Artifacts",
            "## Key Link Verification",
            "## Behavioral Spot-Checks",
            "## Requirements Coverage",
            "## Anti-Patterns Found",
            "## Human Verification Required",
            "## Gaps Summary",
        ]
        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, self.phase8_verification)

    def test_phase8_verification_covers_all_phase11_requirements_with_direct_proof(
        self,
    ) -> None:
        expected_direct_proof_fragments = {
            "INFRA-01": [
                "ClassicLib-rs/Cargo.toml",
                "classic-path-core/Cargo.toml",
                "cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml",
            ],
            "INFRA-02": [
                "ClassicLib-rs/Cargo.toml",
                "classic-constants-core/Cargo.toml",
                "cargo check -p classic-constants-core --manifest-path ClassicLib-rs/Cargo.toml",
            ],
            "INFRA-03": [
                "classic-path-core/src/docs_path.rs",
                "focused Proton test command passes",
            ],
            "INFRA-04": [
                "classic-shared-core/Cargo.toml",
                "docs/api/classic-shared-core.md",
                "cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml",
            ],
            "INFRA-05": [
                "ClassicLib-rs/node-bindings/classic-node/index.d.ts",
                "tools/node_api_parity/check_dts_freshness.py",
                ".github/workflows/ci-typescript.yml",
                "bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check",
            ],
            "TEST-03": [
                "classic-path-core/tests/linux_proton_docs_path.rs",
                "focused and full crate test commands",
            ],
        }

        for requirement_id, fragments in expected_direct_proof_fragments.items():
            direct_proof = extract_requirement_direct_proof(
                self.phase8_verification, requirement_id
            )
            with self.subTest(requirement_id=requirement_id):
                for fragment in fragments:
                    self.assertIn(fragment, direct_proof)

    def test_infra03_and_test03_stay_separate_requirement_rows(self) -> None:
        infra_03_proof = extract_requirement_direct_proof(
            self.phase8_verification, "INFRA-03"
        )
        test_03_proof = extract_requirement_direct_proof(
            self.phase8_verification, "TEST-03"
        )

        self.assertNotEqual(infra_03_proof, test_03_proof)

        for proof in (infra_03_proof, test_03_proof):
            self.assertNotIn("see summary", proof.lower())
            self.assertNotIn("same as above", proof.lower())

        self.assertIn("classic-path-core/src/docs_path.rs", infra_03_proof)
        self.assertIn(
            "classic-path-core/tests/linux_proton_docs_path.rs", test_03_proof
        )

    def test_infra05_keeps_full_node_governance_evidence_bundle(self) -> None:
        required_bundle_fragments = [
            "ClassicLib-rs/node-bindings/classic-node/index.d.ts",
            "ClassicLib-rs/node-bindings/classic-node/.gitignore",
            "ClassicLib-rs/node-bindings/classic-node/package.json",
            "tools/node_api_parity/check_dts_freshness.py",
            ".github/workflows/ci-typescript.yml",
            "bun run parity:gate:local",
            "bun run test:bun",
            "bun run test:node",
            "bun run dts:freshness:check",
        ]

        for fragment in required_bundle_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.phase8_verification)

    def test_requirements_keep_phase11_workspace_closure_checked_and_complete(
        self,
    ) -> None:
        for requirement_id in [
            "INFRA-01",
            "INFRA-02",
            "INFRA-03",
            "INFRA-04",
            "INFRA-05",
            "TEST-03",
        ]:
            with self.subTest(requirement_id=requirement_id):
                self.assertRegex(
                    self.requirements,
                    rf"- \[x\] \*\*{re.escape(requirement_id)}\*\*:",
                )
                self.assertRegex(
                    self.requirements,
                    rf"\| {re.escape(requirement_id)} \| Phase 11 \| Complete \|",
                )


if __name__ == "__main__":
    unittest.main()
