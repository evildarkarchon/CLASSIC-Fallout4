"""Guard: a Python export may never claim a Rust module as its counterpart.

Same defect the Node gate carried. The Pitfall-2 check is satisfied by a symbol
of *any* kind, so rows naming a Rust module counted as matched while verifying
nothing: ``FileIOCore`` was mapped to the modules ``core``, ``game_files`` and
``similarity`` in three separate rows.
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
    / "python_api_parity"
    / "baseline"
    / "parity_contract.json"
)

RUST_MANIFEST = {
    "symbols": [
        {"symbol": "core", "kind": "module"},
        {"symbol": "load_yaml_file", "kind": "function"},
        # A name that is both a module and a type stays acceptable.
        {"symbol": "config", "kind": "module"},
        {"symbol": "config", "kind": "struct"},
    ]
}


def row(**overrides) -> dict:
    base = {
        "id": "row-1",
        "tier": "tier1",
        "ownerModule": "file_io",
        "rustCrate": "classic-file-io-core",
        "rustSymbol": "load_yaml_file",
        "pythonModule": "classic_file_io",
        "pythonExport": "load_yaml_file",
    }
    base.update(overrides)
    return base


def validate(*rows: dict) -> list[str]:
    return gate.validate_contract_rust_symbols(
        {"tier1Mappings": list(rows)}, RUST_MANIFEST
    )


def test_module_match_is_rejected() -> None:
    diagnostics = validate(row(rustSymbol="core", pythonExport="FileIOCore"))
    assert len(diagnostics) == 1
    assert "is a Rust module" in diagnostics[0]


def test_real_symbol_match_is_accepted() -> None:
    assert validate(row()) == []


def test_symbol_that_is_both_module_and_type_is_accepted() -> None:
    assert validate(row(rustSymbol="config")) == []


def test_unmapped_row_is_accepted_with_a_reason() -> None:
    assert validate(row(rustSymbol=None, unmappedReason="no counterpart")) == []


def test_null_rust_symbol_without_a_reason_is_rejected() -> None:
    diagnostics = validate(row(rustSymbol=None))
    assert len(diagnostics) == 1
    assert "unmappedReason" in diagnostics[0]


def test_missing_symbol_is_still_rejected() -> None:
    diagnostics = validate(row(rustSymbol="does_not_exist"))
    assert len(diagnostics) == 1
    assert "not in the parsed Rust surface" in diagnostics[0]


class TestCommittedContract:
    """The live contract must stay free of the shape this guard rejects."""

    def test_no_python_export_maps_to_a_module(self) -> None:
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
            if isinstance(r.get("rustSymbol"), str) and r["rustSymbol"] in module_only
        ]
        assert not offenders, (
            f"{len(offenders)} contract rows map a Python export to a Rust "
            f"module: {offenders[:10]}"
        )

    def test_no_row_references_the_phantom_fn_symbol(self) -> None:
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
