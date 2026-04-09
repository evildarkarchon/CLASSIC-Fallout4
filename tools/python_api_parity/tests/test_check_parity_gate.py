"""PYT-03 snapshot guard: tier1_contract_total invariant for Plan 9 cleanup."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    """Plan 1 baseline: exactly 59 Tier-1 rows.

    Plan 01 only refreshes the baseline; it does NOT add rows. Subsequent
    plans bump this number per per-plan progression:
      - Plan 02: 59 -> 133 (+74 scanlog Wave 1)
      - Plan 03: 133 -> 190 (+57 scanlog Wave 2, per R9 GLOBAL_FCX_HANDLER exclusion)
      - Plan 04: 190 -> 240 (+50 scanlog Wave 3a)
      - Plan 05: 240 -> 286 (+46 scanlog Wave 3b report)
      - Plan 06: 286 -> 312 (+26 config)
      - Plan 07: 312 -> 347 (+35 version_registry)
      - Plan 08: 347 -> 358 (+11 classic_shared + file_io initial; Plan 08 also
        claims any residual classic_file_io rows found post-refresh)
      - Plan 09a: 358 -> 358 + residual A10 count
    The exact equality below is the Plan 01 snapshot; later plans supersede
    it with their own snapshot assertions.
    """
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert len(contract["tier1Mappings"]) == 59, (
        f"Plan 01 baseline expects exactly 59 Tier-1 rows, "
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
