"""Unit tests for the Phase 4 Plan 1 bidirectional validate_contract_surface guard.

The guard MUST:
1. Walk every tier1Mappings row in the contract.
2. Reject 7 malformed row shapes with explicit diagnostics (H1 fail-closed
   hardening + Round 2 Fix 1.1 exotic-value extensions):
   a. Empty row (neither rustSymbol nor nodeExport)
   b. Missing rustSymbol (any nodeExport state)
   c. Missing nodeExport on a normal-shape row (rustSymbol not ``@rust``)
   d. Non-string rustSymbol (e.g., list, dict)
   e. Empty-string rustSymbol
   f. Non-string nodeExport (on a normal-shape row)
   g. Empty-string nodeExport (on a normal-shape row)
3. Check rustSymbol membership in the Rust surface (skipping the ``@rust``
   suffix for proxy rows); emit a rustCrate-aware remediation hint when the
   lookup misses. Legacy rows without rustCrate use ``<unknown>`` fallback.
4. Check nodeExport membership in the Node surface (only for non-proxy
   rows); emit a remediation hint referencing ``bun run build`` / index.d.ts
   refresh.
5. Only skip the Node-side check when rustSymbol ends in ``@rust``.

Tests reference the live ``rust_api_surface.json`` / ``node_api_surface.json``
shape verified 2026-04-09: top-level ``symbols`` / ``exports`` arrays, each
entry with ``symbol`` / ``export`` string keys.
"""
from __future__ import annotations

import pytest

import check_parity_gate as gate


@pytest.fixture
def rust_manifest() -> dict:
    """Matches live schema of rust_api_surface.json (top-level ``symbols``)."""
    return {
        "symbols": [
            {"symbol": "parse_version"},
            {"symbol": "extract_pe_version"},
            {"symbol": "FormIDAnalyzer"},
            {"symbol": "AnalysisConfig"},
        ]
    }


@pytest.fixture
def node_manifest() -> dict:
    """Matches live schema of node_api_surface.json (top-level ``exports``)."""
    return {
        "exports": [
            {"export": "parseVersion"},
            {"export": "extractPeVersion"},
            {"export": "JsAnalysisConfig"},
            {"export": "createAnalysisConfig"},
        ]
    }


# ============================================================================
# Baseline happy-path / empty-contract tests
# ============================================================================


def test_empty_contract_empty_diagnostics(rust_manifest, node_manifest) -> None:
    """Empty tier1Mappings array → empty diagnostics list."""
    diagnostics = gate.validate_contract_surface(
        {"tier1Mappings": []}, rust_manifest, node_manifest
    )
    assert diagnostics == []


def test_valid_row_empty_diagnostics(rust_manifest, node_manifest) -> None:
    """Well-formed row that exists on both sides → empty diagnostics."""
    contract = {
        "tier1Mappings": [
            {
                "id": "row-1",
                "rustSymbol": "parse_version",
                "nodeExport": "parseVersion",
            }
        ]
    }
    assert (
        gate.validate_contract_surface(contract, rust_manifest, node_manifest) == []
    )


def test_multiple_valid_rows_empty_diagnostics(rust_manifest, node_manifest) -> None:
    """Multiple well-formed rows → empty diagnostics."""
    contract = {
        "tier1Mappings": [
            {"id": "row-1", "rustSymbol": "parse_version", "nodeExport": "parseVersion"},
            {
                "id": "row-2",
                "rustSymbol": "AnalysisConfig",
                "nodeExport": "JsAnalysisConfig",
            },
        ]
    }
    assert (
        gate.validate_contract_surface(contract, rust_manifest, node_manifest) == []
    )


# ============================================================================
# H1 FAIL-CLOSED TESTS (malformed row rejection — 3 original shapes)
# ============================================================================


def test_h1_empty_row_is_rejected(rust_manifest, node_manifest) -> None:
    """H1: row with NEITHER rustSymbol NOR nodeExport MUST fire a diagnostic."""
    contract = {"tier1Mappings": [{"id": "empty-row"}]}
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "empty-row" in d and ("empty" in d.lower() or "missing" in d.lower())
        for d in diagnostics
    )


def test_h1_missing_rust_symbol_is_rejected(rust_manifest, node_manifest) -> None:
    """H1: row with nodeExport but NO rustSymbol MUST fire 'missing rustSymbol'."""
    contract = {
        "tier1Mappings": [{"id": "no-rust-row", "nodeExport": "parseVersion"}]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any("no-rust-row" in d and "rustSymbol" in d for d in diagnostics)


def test_h1_normal_row_missing_node_export_is_rejected(
    rust_manifest, node_manifest
) -> None:
    """H1: row with non-``@rust`` rustSymbol and NO nodeExport MUST fire
    'normal-shape but missing nodeExport'.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "no-node-row",
                "rustSymbol": "parse_version",
                "rustCrate": "classic-version-core",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any("no-node-row" in d and "nodeExport" in d for d in diagnostics)


# ============================================================================
# H1 @rust proxy row handling
# ============================================================================


def test_h1_at_rust_proxy_without_node_export_is_accepted(
    rust_manifest, node_manifest
) -> None:
    """H1: ONLY ``@rust``-suffixed rows may omit nodeExport. Proxy row with
    a stripped-symbol match in the rust surface is valid.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "proxy-row",
                "rustSymbol": "FormIDAnalyzer@rust",
                "rustCrate": "classic-scanlog-core",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert diagnostics == []


def test_at_rust_suffix_rust_missing_diagnostic(rust_manifest, node_manifest) -> None:
    """@rust proxy row whose stripped symbol is NOT in the rust surface
    → Rust-side diagnostic naming the missing symbol and the rustCrate.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "proxy-missing",
                "rustSymbol": "missing_type@rust",
                "rustCrate": "classic-scanlog-core",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "missing_type" in d and "classic-scanlog-core" in d for d in diagnostics
    )


# ============================================================================
# Round 2 Fix 1.1: exotic-value extensions (empty strings + wrong types)
# ============================================================================


def test_h1_empty_string_rust_symbol_is_rejected(
    rust_manifest, node_manifest
) -> None:
    """Round 2 Fix 1.1: empty-string rustSymbol MUST fire a diagnostic
    (None-check alone was insufficient since `""` is falsy-but-not-None).
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "empty-string-rust",
                "rustSymbol": "",
                "nodeExport": "parseVersion",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "empty-string-rust" in d and ("empty" in d.lower() or "rustSymbol" in d)
        for d in diagnostics
    )


def test_h1_empty_string_node_export_is_rejected(
    rust_manifest, node_manifest
) -> None:
    """Round 2 Fix 1.1: empty-string nodeExport on a normal-shape row MUST
    fire a diagnostic.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "empty-string-node",
                "rustSymbol": "parse_version",
                "nodeExport": "",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "empty-string-node" in d and ("empty" in d.lower() or "nodeExport" in d)
        for d in diagnostics
    )


def test_h1_wrong_type_rust_symbol_is_rejected(
    rust_manifest, node_manifest
) -> None:
    """Round 2 Fix 1.1: non-string rustSymbol (e.g., list) MUST fire a
    diagnostic WITHOUT raising an uncaught exception from the guard.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "wrong-type-rust",
                "rustSymbol": ["PeVersionResult"],
                "nodeExport": "parseVersion",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "wrong-type-rust" in d
        and ("type" in d.lower() or "string" in d.lower() or "rustSymbol" in d)
        for d in diagnostics
    )


def test_h1_wrong_type_node_export_is_rejected(
    rust_manifest, node_manifest
) -> None:
    """Round 2 Fix 1.1: non-string nodeExport (e.g., dict) MUST fire a
    diagnostic without raising.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "wrong-type-node",
                "rustSymbol": "parse_version",
                "nodeExport": {"name": "parseVersion"},
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "wrong-type-node" in d
        and ("type" in d.lower() or "string" in d.lower() or "nodeExport" in d)
        for d in diagnostics
    )


# ============================================================================
# Positive surface-miss diagnostics (row shape is valid, but symbol missing)
# ============================================================================


def test_missing_rust_symbol_diagnostic(rust_manifest, node_manifest) -> None:
    """Row with a well-formed shape but rustSymbol not in the rust surface →
    remediation hint that names the missing symbol and the declared rustCrate.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "row-bad",
                "rustSymbol": "missing_fn",
                "nodeExport": "parseVersion",
                "rustCrate": "classic-version-core",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "missing_fn" in d and "classic-version-core" in d and "pub use" in d
        for d in diagnostics
    )


def test_missing_node_export_diagnostic(rust_manifest, node_manifest) -> None:
    """Row where nodeExport is not in the node surface (e.g., still snake_case)
    → remediation hint referencing ``bun run build`` / ``index.d.ts`` refresh.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "row-bad",
                "rustSymbol": "parse_version",
                "nodeExport": "parse_version",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any(
        "parse_version" in d
        and ("bun run build" in d or "index.d.ts" in d)
        for d in diagnostics
    )


def test_missing_rust_crate_fallback_diagnostic(
    rust_manifest, node_manifest
) -> None:
    """Legacy row without a ``rustCrate`` field → diagnostic uses
    ``<unknown>`` fallback instead of KeyError.
    """
    contract = {
        "tier1Mappings": [
            {
                "id": "legacy-row",
                "rustSymbol": "missing_fn",
                "nodeExport": "parseVersion",
            }
        ]
    }
    diagnostics = gate.validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    assert len(diagnostics) >= 1
    assert any("<unknown>" in d for d in diagnostics)
