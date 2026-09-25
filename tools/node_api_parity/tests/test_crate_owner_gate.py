"""Node source parity resolves each claimed Rust symbol in its declared crate."""

from __future__ import annotations

from pathlib import Path

import check_parity_gate as gate
import generate_baseline as baseline
import resolve_node_rust_symbols as resolver


RUST_MANIFEST = {
    "symbols": [
        {"crate": "classic-right-core", "symbol": "SharedName", "kind": "module"},
        {"crate": "classic-other-core", "symbol": "SharedName", "kind": "struct"},
        {"crate": "classic-other-core", "symbol": "OtherName", "kind": "struct"},
    ]
}
NODE_MANIFEST = {"exports": [{"export": "sharedName", "kind": "class"}]}
REPO_ROOT = Path(__file__).resolve().parents[3]


def row(**changes: object) -> dict[str, object]:
    """Build a contract row whose claimed crate has only a module match."""
    mapping: dict[str, object] = {
        "id": "stable-row-id",
        "tier": "tier1",
        "ownerModule": "aux",
        "rustCrate": "classic-right-core",
        "rustSymbol": "SharedName",
        "nodeExport": "sharedName",
    }
    mapping.update(changes)
    return mapping


def test_same_named_symbol_in_another_crate_cannot_satisfy_mapping() -> None:
    """A mapping must resolve the symbol in the crate named by rustCrate."""
    contract = {"tier1Mappings": [row(rustSymbol="OtherName")]}

    diagnostics = gate.validate_contract_surface(
        contract, RUST_MANIFEST, NODE_MANIFEST
    )
    report = baseline.generate_diff_report(contract, RUST_MANIFEST, NODE_MANIFEST)

    assert any(
        "stable-row-id" in message and "classic-right-core" in message
        for message in diagnostics
    )
    assert report["contract_results"][0]["status"] == "missing_rust"
    assert report["contract_results"][0]["rust_crate"] == "classic-right-core"


def test_symbol_in_declared_crate_satisfies_mapping() -> None:
    """The same name is accepted when its actual crate matches the row."""
    contract = {
        "tier1Mappings": [
            row(rustCrate="classic-other-core", rustSymbol="OtherName")
        ]
    }

    assert gate.validate_contract_surface(contract, RUST_MANIFEST, NODE_MANIFEST) == []
    report = baseline.generate_diff_report(contract, RUST_MANIFEST, NODE_MANIFEST)
    assert report["contract_results"][0]["status"] == "matched"
    assert report["contract_results"][0]["rust_crate"] == "classic-other-core"


def test_module_only_match_is_judged_within_the_declared_crate() -> None:
    """A struct with the same name in another crate cannot rescue a module match."""
    diagnostics = gate.validate_contract_surface(
        {"tier1Mappings": [row()]}, RUST_MANIFEST, NODE_MANIFEST
    )

    assert len(diagnostics) == 1
    assert "is a Rust module" in diagnostics[0]


def test_rust_only_proxy_must_resolve_in_declared_crate() -> None:
    """A Rust-only row does not borrow a matching symbol from another crate."""
    diagnostics = gate.validate_contract_surface(
        {"tier1Mappings": [row(rustSymbol="OtherName@rust", nodeExport=None)]},
        RUST_MANIFEST,
        NODE_MANIFEST,
    )

    assert any("classic-right-core" in message for message in diagnostics)


def test_mapped_row_must_name_its_rust_crate() -> None:
    """A claimed counterpart without a crate has no verifiable owner."""
    diagnostics = gate.validate_contract_surface(
        {"tier1Mappings": [row(rustCrate=None, rustSymbol="OtherName")]},
        RUST_MANIFEST,
        NODE_MANIFEST,
    )

    assert any("rustCrate" in message for message in diagnostics)


def test_wrapper_source_rejects_another_crate_with_the_same_symbol() -> None:
    """A second public VersionInfo does not replace the type used by the DTO."""
    rust_manifest = {
        "symbols": [
            {"crate": "classic-version-core", "symbol": "VersionInfo", "kind": "struct"},
            {
                "crate": "classic-version-registry-core",
                "symbol": "VersionInfo",
                "kind": "struct",
            },
        ]
    }
    node_manifest = {"exports": [{"export": "JsVersionInfo", "kind": "interface"}]}
    contract = {
        "tier1Mappings": [
            row(
                rustCrate="classic-version-core",
                rustSymbol="VersionInfo",
                nodeExport="JsVersionInfo",
            )
        ]
    }
    wrapper_resolutions = resolver.resolve_all(REPO_ROOT, rust_manifest)

    assert wrapper_resolutions["JsVersionInfo"].rust_crate == "classic-version-registry-core"
    assert wrapper_resolutions["JsVersionInfo"].crate_from_source
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )
    report = baseline.generate_diff_report(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )

    assert any("classic-version-registry-core" in message for message in diagnostics)
    assert report["contract_results"][0]["status"] == "owner_mismatch"


def test_imported_core_type_disambiguates_the_node_enum() -> None:
    """A same-named enum in another crate cannot replace the imported type."""
    rust_manifest = {
        "symbols": [
            {"crate": "classic-scangame-core", "symbol": "GameVersion", "kind": "enum"},
            {
                "crate": "classic-version-registry-core",
                "symbol": "GameVersion",
                "kind": "enum",
            },
        ]
    }
    node_manifest = {"exports": [{"export": "JsGameVersion", "kind": "const_enum"}]}
    contract = {
        "tier1Mappings": [
            row(
                rustCrate="classic-version-registry-core",
                rustSymbol="GameVersion",
                nodeExport="JsGameVersion",
            )
        ]
    }
    wrapper_resolutions = resolver.resolve_all(REPO_ROOT, rust_manifest)

    assert resolver.source_backed_crate(wrapper_resolutions["JsGameVersion"]) == (
        "classic-scangame-core"
    )
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )
    report = baseline.generate_diff_report(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )

    assert any("classic-scangame-core" in message for message in diagnostics)
    assert report["contract_results"][0]["status"] == "owner_mismatch"


def test_direct_converter_rejects_a_wrong_symbol_in_the_right_crate() -> None:
    """A DTO cannot claim another public symbol from its actual crate."""
    rust_manifest = {
        "symbols": [
            {
                "crate": "classic-version-registry-core",
                "symbol": "VersionInfo",
                "kind": "struct",
            },
            {
                "crate": "classic-version-registry-core",
                "symbol": "GameVersion",
                "kind": "enum",
            },
        ]
    }
    node_manifest = {"exports": [{"export": "JsVersionInfo", "kind": "interface"}]}
    contract = {
        "tier1Mappings": [
            row(
                rustCrate="classic-version-registry-core",
                rustSymbol="GameVersion",
                nodeExport="JsVersionInfo",
            )
        ]
    }
    wrapper_resolutions = resolver.resolve_all(REPO_ROOT, rust_manifest)

    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )
    report = baseline.generate_diff_report(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )

    assert any("VersionInfo" in message for message in diagnostics)
    assert report["contract_results"][0]["status"] == "owner_mismatch"
