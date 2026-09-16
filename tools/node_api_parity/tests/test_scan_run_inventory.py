"""Ensure the maintained contract inventories the complete public Scan Run surface."""

import json
from pathlib import Path

from tools.node_api_parity.generate_baseline import parse_node_surface


def test_every_scan_run_export_has_a_truthful_contract_row():
    """Top-level classes, DTOs, and operation functions must not escape the denominator."""
    root = Path(__file__).resolve().parents[3]
    surface = parse_node_surface(
        root, set(), {}, "node-bindings/classic-node/index.d.ts"
    )
    exports = {
        row["export"]: row["kind"]
        for row in surface["exports"]
        if row["export"].startswith(("ScanRun", "JsScanRun", "scanRun"))
    }
    contract = json.loads(
        (
                root / "docs/implementation/node_api_parity/baseline/parity_contract.json"
        ).read_text()
    )
    rows = {row.get("nodeExport"): row for row in contract["tier1Mappings"]}
    assert not exports.keys() - rows.keys()
    for name, kind in exports.items():
        assert rows[name]["nodeKind"] == kind
