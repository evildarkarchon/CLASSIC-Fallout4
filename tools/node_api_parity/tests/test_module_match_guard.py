"""Guard: a Node export may never claim a Rust module as its counterpart.

The gate's Rust-side check is satisfied by a symbol of *any* kind, which is how
placeholder rows accumulated unnoticed -- at one point 82 unrelated exports all
named the Rust module ``path_core`` and the gate still reported 913/913 matched.
Matching a module verifies nothing about the export, so it is now rejected.

``@rust`` proxy rows stay exempt: they carry no ``nodeExport`` and exist
precisely to record that a Rust module has no binding counterpart.
"""

from __future__ import annotations

import json
from pathlib import Path

import check_parity_gate as gate

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "node_api_parity"
    / "baseline"
    / "parity_contract.json"
)

RUST_MANIFEST = {
    "symbols": [
        {"symbol": "path_core", "kind": "module"},
        {"symbol": "detect_resource_type", "kind": "function"},
        {"symbol": "ResourceInfo", "kind": "struct"},
        # A name that is both a module and a type stays acceptable.
        {"symbol": "config", "kind": "module"},
        {"symbol": "config", "kind": "struct"},
    ]
}
NODE_MANIFEST = {
    "exports": [
        {"export": "detectResourceType", "kind": "function"},
        {"export": "joinPaths", "kind": "function"},
        {"export": "getConfig", "kind": "function"},
    ]
}


def row(**overrides) -> dict:
    base = {
        "id": "row-1",
        "tier": "tier1",
        "ownerModule": "aux",
        "rustSymbol": "detect_resource_type",
        "nodeExport": "detectResourceType",
    }
    base.update(overrides)
    return base


def validate(*rows: dict) -> list[str]:
    return gate.validate_contract_surface(
        {"tier1Mappings": list(rows)}, RUST_MANIFEST, NODE_MANIFEST
    )


def test_module_match_is_rejected() -> None:
    diagnostics = validate(row(rustSymbol="path_core", nodeExport="joinPaths"))
    assert len(diagnostics) == 1
    assert "is a Rust module" in diagnostics[0]
    assert "joinPaths" in diagnostics[0]


def test_real_symbol_match_is_accepted() -> None:
    assert validate(row()) == []


def test_symbol_that_is_both_module_and_type_is_accepted() -> None:
    """Only symbols whose *sole* kind is `module` are rejected."""
    assert validate(row(rustSymbol="config", nodeExport="getConfig")) == []


def test_rust_only_proxy_row_may_name_a_module() -> None:
    """Proxy rows exist to record Rust-only surface; a module is valid there."""
    assert validate(row(rustSymbol="path_core@rust", nodeExport=None)) == []


def test_unmapped_row_is_accepted_with_a_reason() -> None:
    diagnostics = validate(
        row(rustSymbol=None, nodeExport="joinPaths", unmappedReason="no counterpart")
    )
    assert diagnostics == []


def test_null_rust_symbol_without_a_reason_is_rejected() -> None:
    """`rustSymbol: null` must be a deliberate declaration, not an omission."""
    diagnostics = validate(row(rustSymbol=None, nodeExport="joinPaths"))
    assert len(diagnostics) == 1
    assert "missing rustSymbol" in diagnostics[0]
    assert "unmappedReason" in diagnostics[0]


def test_unmapped_row_must_still_name_its_binding_surface() -> None:
    diagnostics = validate(
        row(rustSymbol=None, nodeExport=None, unmappedReason="no counterpart")
    )
    assert len(diagnostics) == 1
    assert "no nodeExport" in diagnostics[0]


class TestCommittedContract:
    """The live contract must stay free of the shape this guard rejects."""

    def test_no_node_export_maps_to_a_module(self) -> None:
        import generate_baseline as gb

        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        rust_manifest = gb.parse_rust_surface(REPO_ROOT, set())
        kinds: dict[str, set[str]] = {}
        for item in rust_manifest["symbols"]:
            kinds.setdefault(item["symbol"], set()).add(item["kind"])
        module_only = {s for s, k in kinds.items() if k == {"module"}}

        offenders = [
            r["id"]
            for r in contract["tier1Mappings"]
            if r.get("nodeExport") is not None
            and isinstance(r.get("rustSymbol"), str)
            and not r["rustSymbol"].endswith("@rust")
            and r["rustSymbol"] in module_only
        ]
        assert not offenders, (
            f"{len(offenders)} contract rows map a Node export to a Rust module: "
            f"{offenders[:10]}"
        )

    def test_no_row_references_the_phantom_fn_symbol(self) -> None:
        """`fn` only ever existed as an artifact of the old const-fn regex bug."""
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        offenders = [
            r["id"]
            for r in contract["tier1Mappings"]
            if isinstance(r.get("rustSymbol"), str)
            and r["rustSymbol"].removesuffix("@rust") == "fn"
        ]
        assert not offenders, f"rows still reference the phantom 'fn' symbol: {offenders}"

    def test_every_unmapped_row_states_a_reason(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        offenders = [
            r["id"]
            for r in contract["tier1Mappings"]
            if r.get("rustSymbol") is None and not r.get("unmappedReason")
        ]
        assert not offenders, f"unmapped rows without a reason: {offenders}"
