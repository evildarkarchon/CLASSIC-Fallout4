"""Committed Node parity contract tripwires for the live one-tier baseline.

These tests exercise the checked-in ``parity_contract.json`` directly:

- ``test_tier1_contract_total_baseline_floor`` locks the current live
  one-tier contract floor at 706 rows so accidental row deletions or
  contract-file corruption fail fast.

- ``test_tier2_definition_removed_after_plan_6`` keeps a positive
  assertion that ``tierDefinitions.tier2`` is absent from the committed
  one-tier contract.
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
    """tier1Mappings must not regress below the live 706-row contract floor."""
    contract = _load_contract()
    tier1 = contract.get("tier1Mappings", [])
    # The committed contract and checked-in diff report currently show a
    # one-tier 706/706 matched baseline with no tier2 definition.
    assert len(tier1) >= 706, (
        f"tier1Mappings regressed below the live one-tier floor: "
        f"{len(tier1)} < 706. Something deleted contract rows."
    )


def test_tier2_definition_removed_after_plan_6() -> None:
    """``tierDefinitions.tier2`` must remain absent from the live contract."""
    contract = _load_contract()
    tier_defs = contract.get("tierDefinitions", {})
    assert "tier2" not in tier_defs, (
        "tierDefinitions.tier2 should remain absent from the one-tier contract"
    )


def test_contract_description_matches_live_one_tier_baseline() -> None:
    """The committed contract narrative must stay aligned to the live baseline."""
    contract = _load_contract()
    description = contract.get("description", "")

    assert "one-tier" in description, (
        "parity_contract.json description must describe the live one-tier baseline"
    )
    assert "706" in description, (
        "parity_contract.json description must preserve the live 706-row floor"
    )
    assert "Hybrid-tiered" not in description, (
        "parity_contract.json description must not drift back to hybrid-tier wording"
    )


def test_parity_contract_file_exists() -> None:
    """Sanity check: the committed contract file path is discoverable from
    the test directory without any ``sys.path`` juggling.
    """
    assert PARITY_CONTRACT.is_file(), (
        f"parity_contract.json not found at {PARITY_CONTRACT}"
    )


def test_node_gate_defaults_use_repo_root_paths() -> None:
    source = (
        REPO_ROOT / "tools" / "node_api_parity" / "check_parity_gate.py"
    ).read_text(encoding="utf-8")
    assert 'default="node-bindings/classic-node/index.d.ts"' in source
    assert 'default="node-bindings/classic-node/parity-artifacts"' in source
    assert (
        'default="node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"'
        in source
    )
    assert "ClassicLib-rs/node-bindings/classic-node" not in source
    assert '"rust_api_surface.json",' in source
    assert '"node_api_surface.json",' in source


def test_dts_freshness_defaults_use_repo_root_paths() -> None:
    source = (
        REPO_ROOT / "tools" / "node_api_parity" / "check_dts_freshness.py"
    ).read_text(encoding="utf-8")
    assert 'default="node-bindings/classic-node"' in source
    assert 'default="node-bindings/classic-node/parity-artifacts"' in source
    assert "ClassicLib-rs/node-bindings/classic-node" not in source
