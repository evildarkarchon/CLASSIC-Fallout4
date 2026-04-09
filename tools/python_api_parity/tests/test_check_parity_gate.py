"""PYT-03 snapshot guard: tier1_contract_total invariant for Plan 9 cleanup."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "python_api_parity"
    / "baseline"
    / "parity_contract.json"
)


def test_tier1_contract_total_baseline_floor() -> None:
    """Phase 3 close-out floor: at least 1098 Tier-1 rows (Plan 09a + 09b snapshot).

    Per-plan progression through Phase 3:
      - Plan 01 baseline:               59
      - Plan 02 (scanlog Wave 1):       59 -> 133 (+74)
      - Plan 03 (scanlog Wave 2):       133 -> 190 (+57, R9 GLOBAL_FCX_HANDLER exclusion)
      - Plan 04 (scanlog Wave 3a):      190 -> 240 (+50)
      - Plan 05 (scanlog Wave 3b):      240 -> 286 (+46)
      - Plan 06 (config):               286 -> 312 (+26)
      - Plan 07 (version_registry):     312 -> 347 (+35)
      - Plan 08 (classic_shared+file_io): 347 -> 505 (+158, two-owner enrollment)
      - Plan 09a (A10 residual promotion): 505 -> 1098 (+593, 14 owners + scanlog residuals)
      - Plan 09b (Tier-2 deletion):     1098 -> 1098 (no row changes; structural cleanup)

    Plan 09b closed Phase 3; this floor locks in the Phase 3 endgame count.
    Future milestones that grow the contract should raise this floor; future
    milestones that legitimately shrink the contract must update the assertion
    with a cross-AI-reviewed rationale.
    """
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert len(contract["tier1Mappings"]) >= 1098, (
        f"Phase 3 close-out floor expects at least 1098 Tier-1 rows, "
        f"got {len(contract['tier1Mappings'])}"
    )


def test_tier2_definition_removed_after_plan_9() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    tier_definitions = contract.get("tierDefinitions", {})
    assert "tier2" not in tier_definitions, (
        "Plan 9b must delete tierDefinitions.tier2 from parity_contract.json"
    )


def test_tier2_gap_total_removed_from_summary() -> None:
    """Plan 9b A9 cleanup: tier2_gap_total is no longer emitted by generate_baseline.

    This test passes AFTER Task 2 Step 11 refreshes the baseline in the SAME commit.
    M7 fix: combining Tasks 2+3 prevents a bisect-breaking intermediate where this
    test reads a stale parity_diff_report.json with tier2_gap_total still present.
    """
    diff = json.loads(
        (
            REPO_ROOT
            / "docs"
            / "implementation"
            / "python_api_parity"
            / "baseline"
            / "parity_diff_report.json"
        ).read_text(encoding="utf-8")
    )
    assert "tier2_gap_total" not in diff["summary"], (
        "Plan 9b must remove tier2_gap_total from parity_diff_report.json::summary"
    )
