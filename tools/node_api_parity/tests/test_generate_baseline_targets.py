"""Per-crate parse_rust_surface() non-empty assertion.

Guards against the Phase 3 Pitfall 5 path-typo class of error: if a new
crate is added to ``RUST_TARGET_CRATES`` but the ``lib.rs`` path is wrong
(or points at an empty module), ``parse_rust_surface()`` silently returns
zero symbols for that crate and downstream gate reports show phantom
deferred rows.

The floor assertion is ``>= 17`` (NOT ``== 17``) so later crate additions
can legitimately expand the tracked set without blocking Plan 1.
"""

from __future__ import annotations

from pathlib import Path

import generate_baseline as gb

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rust_target_crates_floor_is_sixteen() -> None:
    """Phase 4 Plan 1 expands the tracked set from 10 to 16+ crates.

    Floor is load-bearing; tight equality is hostile to future discovery.
    (v9.1.0 Phase 2 reduced the tracked set by one when the former crashgen
    rules crate was absorbed into classic-config-core, and v9.1.0 Phase 3
    reduced it again when classic-constants-core was retired; actual
    post-Phase-3 count is 16.)
    """
    assert len(gb.RUST_TARGET_CRATES) >= 16, (
        f"expected >= 16 entries in RUST_TARGET_CRATES, got "
        f"{len(gb.RUST_TARGET_CRATES)}: {sorted(gb.RUST_TARGET_CRATES)}"
    )


def test_inventory_filter_is_deleted() -> None:
    """RUST_FULL_INVENTORY_CRATES set and include_rust_symbol() filter must
    both be gone after Plan 1 Task 1 — every tracked crate now produces full
    public-symbol output unconditionally.
    """
    assert not hasattr(gb, "RUST_FULL_INVENTORY_CRATES"), (
        "RUST_FULL_INVENTORY_CRATES must be deleted — Plan 1 removes the "
        "tier-2 filter so every tracked crate yields full public symbols."
    )
    assert not hasattr(gb, "include_rust_symbol"), (
        "include_rust_symbol() must be deleted — the filter is no longer "
        "applied after Plan 1 Task 1."
    )


def test_owner_by_crate_has_entry_for_every_target_crate() -> None:
    """Owner fallback tightening: every RUST_TARGET_CRATES key MUST have an
    explicit owner label. No silent default-to-aux fallback.
    """
    missing = sorted(set(gb.RUST_TARGET_CRATES) - set(gb.RUST_OWNER_BY_CRATE))
    assert missing == [], (
        f"Every tracked crate needs an explicit owner label — missing for: "
        f"{missing}. No default-to-aux fallback permitted."
    )


def test_owner_labels_are_distinct_phase3_style() -> None:
    """A5: Phase 3 keeps ``shared``, ``perf``, ``registry`` as distinct owner
    labels rather than collapsing them to ``aux``. Phase 4 mirrors that shape
    so the A10 sizing report produces per-owner counts that Plans 2-5 can
    act on individually.
    """
    # At least these distinct owner labels should appear after the expansion.
    required_owners = {"scanlog", "config", "version_registry"}
    observed = set(gb.RUST_OWNER_BY_CRATE.values())
    assert required_owners.issubset(observed), (
        f"expected at least {required_owners} owner labels, got {sorted(observed)}"
    )


def test_squad_by_owner_covers_every_owner() -> None:
    """Every owner label produced by RUST_OWNER_BY_CRATE MUST exist as a key
    in SQUAD_BY_OWNER so downstream handoff rendering does not KeyError.
    """
    owners = set(gb.RUST_OWNER_BY_CRATE.values())
    missing_squads = sorted(owners - set(gb.SQUAD_BY_OWNER))
    assert missing_squads == [], (
        f"SQUAD_BY_OWNER missing entries for owners: {missing_squads}"
    )


def test_every_target_crate_lib_rs_path_exists() -> None:
    """Catches Pitfall 5 path typos at the lib.rs level — a bad path would
    surface as a missing file before the surface parser ever ran.
    """
    missing_paths: list[str] = []
    for crate, rel in gb.RUST_TARGET_CRATES.items():
        path = REPO_ROOT / rel
        if not path.is_file():
            missing_paths.append(f"{crate} -> {rel}")
    assert missing_paths == [], (
        f"RUST_TARGET_CRATES points at non-existent lib.rs files: {missing_paths}"
    )


def test_node_target_paths_use_repo_root_layout_only() -> None:
    for rel in gb.RUST_TARGET_CRATES.values():
        assert not rel.startswith("ClassicLib-rs/"), rel

    source = (REPO_ROOT / "node-bindings" / "classic-node" / "package.json").read_text(
        encoding="utf-8"
    )
    for expected in (
        '"dts:refresh": "bun x napi build --platform --manifest-path ./Cargo.toml --dts index.d.ts --no-js"',
        "../../tools/node_api_parity/check_parity_gate.py --repo-root ../..",
        '"dts:freshness:check": "python ../../tools/node_api_parity/check_dts_freshness.py --repo-root ../.."',
        '"dts:freshness:ci": "python ../../tools/node_api_parity/check_dts_freshness.py --repo-root ../.."',
        "../../tools/enter_vs_dev_shell.ps1",
    ):
        assert expected in source
    assert "../../../tools/" not in source


def test_every_target_crate_parses_non_empty_symbols() -> None:
    """Per-crate parse_rust_surface() non-empty assertion.

    Isolates each crate by monkey-patching ``RUST_TARGET_CRATES`` to contain
    just that one entry, then asserts the parser returns at least one public
    symbol. Catches path typos and empty ``lib.rs`` files the second a new
    crate is added.
    """
    original = gb.RUST_TARGET_CRATES
    try:
        zero_symbol_crates: list[str] = []
        for crate, rel in original.items():
            gb.RUST_TARGET_CRATES = {crate: rel}
            # Use an empty tier1 set so we exercise the full-inventory path.
            surface = gb.parse_rust_surface(REPO_ROOT, tier1_rust_symbols=set())
            symbols = surface.get("symbols", [])
            if len(symbols) == 0:
                zero_symbol_crates.append(crate)
        assert zero_symbol_crates == [], (
            f"parse_rust_surface returned 0 symbols for: {zero_symbol_crates}"
            f" — likely a path typo or empty lib.rs"
        )
    finally:
        gb.RUST_TARGET_CRATES = original


def test_settings_yaml_ops_nested_modules_are_scanned() -> None:
    """The settings YAML facade stores inherent methods two module levels deep."""
    original = gb.RUST_TARGET_CRATES
    try:
        gb.RUST_TARGET_CRATES = {
            "classic-settings-core": "business-logic/classic-settings-core/src/lib.rs"
        }
        surface = gb.parse_rust_surface(REPO_ROOT, tier1_rust_symbols=set())
    finally:
        gb.RUST_TARGET_CRATES = original

    symbols = {
        entry["symbol"]: entry
        for entry in surface.get("symbols", [])
        if entry["crate"] == "classic-settings-core"
    }
    assert symbols["parse_yaml"]["source_file"] == (
        "business-logic/classic-settings-core/src/yaml_ops/operations.rs"
    )
    assert symbols["get_setting"]["source_file"] == (
        "business-logic/classic-settings-core/src/yaml_ops/accessors.rs"
    )


def test_pub_crate_modules_do_not_emit_public_symbols(tmp_path: Path) -> None:
    crate_dir = tmp_path / "fixture" / "src"
    crate_dir.mkdir(parents=True)
    (crate_dir / "lib.rs").write_text(
        "pub(crate) mod hidden;\npub mod visible;\n",
        encoding="utf-8",
    )
    (crate_dir / "hidden.rs").write_text(
        "pub fn hidden_api() {}\npub struct HiddenType;\n",
        encoding="utf-8",
    )
    (crate_dir / "visible.rs").write_text(
        "pub fn visible_api() {}\npub struct VisibleType;\n",
        encoding="utf-8",
    )

    original_targets = gb.RUST_TARGET_CRATES
    original_owners = gb.RUST_OWNER_BY_CRATE
    try:
        gb.RUST_TARGET_CRATES = {"fixture-crate": "fixture/src/lib.rs"}
        gb.RUST_OWNER_BY_CRATE = {"fixture-crate": "aux"}
        surface = gb.parse_rust_surface(tmp_path, tier1_rust_symbols=set())
    finally:
        gb.RUST_TARGET_CRATES = original_targets
        gb.RUST_OWNER_BY_CRATE = original_owners

    symbols = {entry["symbol"] for entry in surface.get("symbols", [])}
    assert "hidden_api" not in symbols
    assert "HiddenType" not in symbols
    assert "visible_api" in symbols
    assert "VisibleType" in symbols
