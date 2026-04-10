"""Phase 4 Plan 1 baseline floor + Plan 6 xfail snapshot tests.

These tests exercise the committed ``parity_contract.json`` and act as a
tripwire for downstream plans:

- ``test_tier1_contract_total_baseline_floor`` — locks the current
  tier1Mappings count at the Plan 1 snapshot floor. Plans 2-5 raise the
  floor as they land promotions; each plan updates the assertion value
  to the new post-promotion count.

- ``test_tier2_definition_removed_after_plan_6`` — asserts that
  ``tierDefinitions.tier2`` is DELETED from the contract. Marked
  ``xfail(strict=True)`` because tier2 is still present at Plan 1 close.
  The marker is REMOVED in Plan 6's atomic cascade (when the Tier-2
  cleanup deletes the tierDefinitions.tier2 key) and the test flips to
  passing then.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PARITY_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "node_api_parity"
    / "baseline"
    / "parity_contract.json"
)


def _load_contract() -> dict:
    return json.loads(PARITY_CONTRACT.read_text(encoding="utf-8"))


def test_tier1_contract_total_baseline_floor() -> None:
    """Plan 1 snapshot: tier1Mappings must not regress below 261 rows.

    Plans 2-5 each raise this floor as they promote deferred rows. When a
    plan lands, its summary records the new floor and updates this
    assertion to the new value. The floor is a tripwire to catch
    accidental row deletions or contract-file corruption.
    """
    contract = _load_contract()
    tier1 = contract.get("tier1Mappings", [])
    # Phase 4 close floor: 711 = 261 (start) + 66 (Plan 2) + 34 (Plan 3)
    # + 7 (Plan 4) + 343 (Plan 5). Updated by Plan 6 M7 atomic cascade.
    assert len(tier1) >= 711, (
        f"tier1Mappings regressed below Phase 4 floor: "
        f"{len(tier1)} < 711. Something deleted contract rows."
    )


def test_tier2_definition_removed_after_plan_6() -> None:
    """Plan 6 tripwire: ``tierDefinitions.tier2`` must be absent post-cascade.

    The xfail marker was REMOVED in Plan 6's M7 atomic commit when the
    Tier-2 cleanup cascade deleted the key from ``parity_contract.json``.
    """
    contract = _load_contract()
    tier_defs = contract.get("tierDefinitions", {})
    assert "tier2" not in tier_defs, (
        "tierDefinitions.tier2 should be removed as of Plan 6"
    )


def test_parity_contract_file_exists() -> None:
    """Sanity check: the committed contract file path is discoverable from
    the test directory without any ``sys.path`` juggling.
    """
    assert PARITY_CONTRACT.is_file(), (
        f"parity_contract.json not found at {PARITY_CONTRACT}"
    )
