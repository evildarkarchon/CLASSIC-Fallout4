from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MILESTONE_PHASES_ROOT = REPO_ROOT / ".planning/milestones/v9.1.0-phases"
RUST_DOCUMENTATION_INDEX = REPO_ROOT / "docs/RUST_DOCUMENTATION_INDEX.md"
RETIRED_CONSTANTS_CORE_DIR = (
    REPO_ROOT / "ClassicLib-rs/business-logic/classic-constants-core"
)
PHASE3_VERIFICATION = (
    MILESTONE_PHASES_ROOT / "03-constants-version-registry-merge/03-VERIFICATION.md"
)
NODE_PARITY_GATE_TEST = (
    REPO_ROOT / "tools/node_api_parity/tests/test_check_parity_gate.py"
)
NODE_PARITY_CONTRACT = (
    REPO_ROOT / "docs/implementation/node_api_parity/baseline/parity_contract.json"
)
NODE_PARITY_CONTRACT_MARKDOWN = (
    REPO_ROOT / "docs/implementation/node_api_parity/baseline/parity_contract.md"
)
NODE_PARITY_DIFF_REPORT = (
    REPO_ROOT / "docs/implementation/node_api_parity/baseline/parity_diff_report.md"
)
PHASE2_DEFERRED_ITEMS = (
    MILESTONE_PHASES_ROOT / "02-crashgen-config-merge/deferred-items.md"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class Phase05ValidationAuditTests(unittest.TestCase):
    def test_documentation_index_routes_only_to_surviving_owner_docs(self) -> None:
        text = read_text(RUST_DOCUMENTATION_INDEX)

        for retired_page in ["classic-yaml-core.md", "classic-constants-core.md"]:
            with self.subTest(retired_page=retired_page):
                self.assertNotIn(retired_page, text)

        for surviving_owner in [
            "classic-settings-core",
            "classic-version-registry-core",
            "classic-shared-core",
        ]:
            with self.subTest(surviving_owner=surviving_owner):
                self.assertIn(surviving_owner, text)

    def test_phase3_verification_reports_the_live_passed_state(self) -> None:
        text = read_text(PHASE3_VERIFICATION)

        self.assertFalse(RETIRED_CONSTANTS_CORE_DIR.exists())

        for fragment in [
            "status: passed",
            "score: 9/9 must-haves verified",
            "**Status:** passed",
            "**Re-verification:** Yes",
            "Contributor-doc closure refreshed to current owner docs",
            "Committed Python and Node parity surface artifacts were already refreshed",
            "Retired `classic-constants-py` directory remains absent from the live tree",
            "No blocking gaps found",
            "stale `gaps_found` bookkeeping was refreshed during Phase 05 cleanup",
        ]:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_node_floor_reconciliation_matches_the_live_one_tier_contract(self) -> None:
        gate_test = read_text(NODE_PARITY_GATE_TEST)
        deferred_items = read_text(PHASE2_DEFERRED_ITEMS)
        contract_markdown = read_text(NODE_PARITY_CONTRACT_MARKDOWN)
        diff_report = read_text(NODE_PARITY_DIFF_REPORT)
        contract = json.loads(read_text(NODE_PARITY_CONTRACT))
        description = contract.get("description", "")

        self.assertEqual(len(contract.get("tier1Mappings", [])), 705)
        self.assertNotIn("tier2", contract.get("tierDefinitions", {}))
        self.assertIn("one-tier", description)
        self.assertIn("705", description)
        self.assertNotIn("Hybrid-tiered", description)
        self.assertIn("Tier-1 contract rows: **705**", diff_report)
        self.assertIn("Tier-1 matched: **705**", diff_report)
        self.assertIn("assert len(tier1) >= 705", gate_test)
        self.assertIn('assert "one-tier" in description', gate_test)
        self.assertIn('assert "Hybrid-tiered" not in description', gate_test)
        self.assertNotIn("711", gate_test)
        self.assertIn("resolved during Phase 05 cleanup", deferred_items)
        self.assertIn("live one-tier contract floor is 705", deferred_items)
        self.assertIn("one-tier", contract_markdown)
        self.assertIn("705", contract_markdown)
        self.assertIn("parity_contract.json", contract_markdown)
        self.assertIn("parity_diff_report.md", contract_markdown)
        self.assertIn(
            "tools/node_api_parity/tests/test_check_parity_gate.py", contract_markdown
        )
        self.assertNotIn("hybrid-tiered", contract_markdown)
        self.assertNotIn("Tier 2 (defer-capable)", contract_markdown)


if __name__ == "__main__":
    unittest.main()
