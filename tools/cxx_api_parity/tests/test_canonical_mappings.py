"""Behavior tests for canonical Rust metadata on generated CXX parity rows."""

from __future__ import annotations

import copy
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_baseline import (  # noqa: E402
    CanonicalMappingError,
    enrich_surface_with_canonical_mappings,
    validate_canonical_mapping_targets,
    validate_committed_canonical_metadata,
)


def _surface() -> dict[str, object]:
    """Return a minimal parsed CXX surface with stable production-shaped rows."""

    return {
        "generated_at_utc": "2026-08-15T00:00:00Z",
        "entries": [
            {
                "id": "canonical-id",
                "rustSymbol": "bridge_execute",
                "kind": "function",
                "bridgeModule": "scanner",
                "sourceFile": "cpp-bindings/classic-cpp-bridge/src/scanner.rs",
                "blockOrigin": "Rust",
                "signature": {"args": [], "returnType": "bool"},
            },
            {
                "id": "binding-only-id",
                "rustSymbol": "on_progress",
                "kind": "function",
                "bridgeModule": "scanner",
                "sourceFile": "cpp-bindings/classic-cpp-bridge/src/scanner.rs",
                "blockOrigin": "C++",
                "signature": {"args": [], "returnType": None},
            },
        ],
    }


def _mappings() -> dict[str, object]:
    """Return one canonical mapping and one explicit binding-only mapping."""

    return {
        "schema_version": 1,
        "entries": [
            {
                "id": "canonical-id",
                "rustSymbol": "bridge_execute",
                "kind": "function",
                "bridgeModule": "scanner",
                "ownerModule": "scanlog",
                "rustCrate": "classic-scanlog-core",
                "coreRustSymbol": "execute",
            },
            {
                "id": "binding-only-id",
                "rustSymbol": "on_progress",
                "kind": "function",
                "bridgeModule": "scanner",
                "unmappedReason": "C++ callback declaration has no Rust core symbol.",
            },
        ],
    }


def _mappings_with_crate_catalog() -> dict[str, object]:
    """Add the live Rust crate location used to validate canonical targets."""

    mappings = _mappings()
    mappings["rustCrates"] = [
        {
            "ownerModule": "scanlog",
            "rustCrate": "classic-scanlog-core",
            "libRs": "business-logic/classic-scanlog-core/src/lib.rs",
        }
    ]
    return mappings


def test_generated_rows_receive_canonical_or_binding_only_metadata() -> None:
    """Enrichment preserves row identity while recording exactly one mapping kind."""

    surface = _surface()
    enriched = enrich_surface_with_canonical_mappings(surface, _mappings())

    assert surface == _surface(), "enrichment must not mutate the parsed source model"
    canonical, binding_only = enriched["entries"]
    assert canonical["id"] == "canonical-id"
    assert canonical["ownerModule"] == "scanlog"
    assert canonical["rustCrate"] == "classic-scanlog-core"
    assert canonical["coreRustSymbol"] == "execute"
    assert "unmappedReason" not in canonical
    assert binding_only["id"] == "binding-only-id"
    assert binding_only["unmappedReason"].startswith("C++ callback")
    assert "ownerModule" not in binding_only
    assert "rustCrate" not in binding_only
    assert "coreRustSymbol" not in binding_only


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda mappings: mappings["entries"].pop(), "missing canonical mappings"),
        (
            lambda mappings: mappings["entries"].append(
                {
                    "id": "stale-id",
                    "rustSymbol": "removed",
                    "kind": "function",
                    "bridgeModule": "scanner",
                    "unmappedReason": "Removed binding-only row.",
                }
            ),
            "stale canonical mappings",
        ),
        (
            lambda mappings: mappings["entries"][0].update(
                {"rustSymbol": "wrong_bridge_symbol"}
            ),
            "identity metadata",
        ),
        (
            lambda mappings: mappings["entries"].append(
                copy.deepcopy(mappings["entries"][0])
            ),
            "duplicate canonical mapping id",
        ),
    ],
)
def test_missing_stale_or_mismatched_mapping_rows_fail_closed(
    mutate: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    """The generated model rejects mappings that no longer match bridge source rows."""

    mappings = copy.deepcopy(_mappings())
    mutate(mappings)

    with pytest.raises(CanonicalMappingError, match=message):
        enrich_surface_with_canonical_mappings(_surface(), mappings)


def test_partial_or_mixed_mapping_metadata_fails_closed() -> None:
    """A row cannot masquerade as canonical with incomplete or conflicting metadata."""

    mappings = _mappings()
    mappings["entries"][0].pop("coreRustSymbol")
    mappings["entries"][0]["unmappedReason"] = "Ambiguous on purpose."

    with pytest.raises(
        CanonicalMappingError, match="exactly one mapping classification"
    ):
        enrich_surface_with_canonical_mappings(_surface(), mappings)


def test_committed_contract_metadata_must_match_independent_enrichment() -> None:
    """Contract tampering cannot hide behind the source-only ABI comparator."""

    current = enrich_surface_with_canonical_mappings(_surface(), _mappings())
    committed = copy.deepcopy(current)
    canonical = committed["entries"][0]
    canonical.pop("ownerModule")
    canonical.pop("rustCrate")
    canonical.pop("coreRustSymbol")
    canonical["unmappedReason"] = "Fabricated binding-only classification."

    with pytest.raises(CanonicalMappingError, match="stale canonical metadata"):
        validate_committed_canonical_metadata(committed, current)


def test_canonical_target_must_exist_on_the_live_public_rust_surface(
    tmp_path: Path,
) -> None:
    """A mapping cannot survive after its core symbol is renamed or removed."""

    lib_rs = tmp_path / "business-logic" / "classic-scanlog-core" / "src" / "lib.rs"
    lib_rs.parent.mkdir(parents=True)
    lib_rs.write_text("pub fn execute() -> bool { true }\n", encoding="utf-8")
    mappings = _mappings_with_crate_catalog()

    validate_canonical_mapping_targets(tmp_path, mappings)
    lib_rs.write_text("pub fn renamed() -> bool { true }\n", encoding="utf-8")

    with pytest.raises(CanonicalMappingError, match="missing live Rust targets"):
        validate_canonical_mapping_targets(tmp_path, mappings)


def test_canonical_target_rejects_wrong_owner_or_module_only_matches(
    tmp_path: Path,
) -> None:
    """Owner/crate metadata must resolve to a non-module public Rust declaration."""

    lib_rs = tmp_path / "business-logic" / "classic-scanlog-core" / "src" / "lib.rs"
    lib_rs.parent.mkdir(parents=True)
    lib_rs.write_text("pub mod execute;\n", encoding="utf-8")
    (lib_rs.parent / "execute.rs").write_text("pub struct Detail;\n", encoding="utf-8")
    mappings = _mappings_with_crate_catalog()

    with pytest.raises(CanonicalMappingError, match="missing live Rust targets"):
        validate_canonical_mapping_targets(tmp_path, mappings)

    lib_rs.write_text("pub fn execute() {}\n", encoding="utf-8")
    mappings["entries"][0]["ownerModule"] = "wrong-owner"
    with pytest.raises(CanonicalMappingError, match="missing live Rust targets"):
        validate_canonical_mapping_targets(tmp_path, mappings)
