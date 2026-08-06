"""Per-class smoke tests for Phase 3 Plan 06 — classic-config-py promotions.

Covers the surviving promoted contract rows:
  - deferred config backlog entries for YAML Data and non-User-Settings helpers
  - 2 Tier-2 runtime-verified migrations (get_application_dir, set_application_dir)

R1 HIGH: fixture-backed construction — every promoted #[pyclass] is either constructed
directly or deserialized via YamlData.from_yaml_content() with real field access.
No hasattr-only tests.

Per inventory in .planning/phases/03-python-tier-collapse/03-06-CONSTRUCTOR-INVENTORY.md:
- CrashgenEntryRaw, CoreModEntry, CoreModExclude, ModConflictEntry,
  ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackRule,
  SuspectStackCountRule, ConfigError all have NO PyO3 wrappers — they surface
  only through YamlData getters as dicts/lists. The Pitfall 2 guard test
  (test_rust_only_symbols_in_core_surface) asserts they exist in the parsed
  Rust surface to prove the @rust-suffixed contract rows are backed by real
  source symbols.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

import classic_config

from .fixtures.tier1_parity_fixtures import (
    PARITY_GAME_YAML,
    PARITY_IGNORE_YAML,
    PARITY_MAIN_YAML,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RUST_API_SURFACE = (
    REPO_ROOT
    / "docs"
    / "implementation"
    / "python_api_parity"
    / "baseline"
    / "rust_api_surface.json"
)


# =============================================================================
# #[pyclass] direct construction
# =============================================================================


def test_yaml_source_classattrs_and_dunders() -> None:
    """YamlSource — 6 non-User-Settings constants plus standard dunders."""
    main = classic_config.YamlSource.MAIN
    ignore = classic_config.YamlSource.IGNORE
    game = classic_config.YamlSource.GAME
    game_local = classic_config.YamlSource.GAME_LOCAL
    test = classic_config.YamlSource.TEST
    cache = classic_config.YamlSource.CACHE

    # All six constants must be distinct.
    all_sources = [main, ignore, game, game_local, test, cache]
    assert len({hash(s) for s in all_sources}) == 6

    # __eq__ dunder via ==
    assert main == classic_config.YamlSource.MAIN
    assert main != ignore

    # __str__ dunder
    assert str(main) == "MAIN"

    # __repr__ dunder
    assert repr(main) == "YamlSource.MAIN"

    # __hash__ dunder
    assert hash(main) == 0  # per PyYamlSource::__hash__
    assert hash(cache) == 6


def test_yaml_source_path_and_display_name_methods() -> None:
    """YamlSource — exercise path/display_name/display_name_with_game methods."""
    main = classic_config.YamlSource.MAIN
    # path() returns a PathBuf-string; should contain the game identifier
    fo4_path = main.path("Fallout4")
    assert isinstance(fo4_path, str)
    assert len(fo4_path) > 0
    # display_name is a static descriptor
    assert isinstance(main.display_name(), str)
    # display_name_with_game weaves in the game identifier
    dn = main.display_name_with_game("Fallout4")
    assert isinstance(dn, str)
    assert len(dn) > 0


# =============================================================================
# Fixture-backed YamlData deserialization
# =============================================================================


def test_yaml_data_from_yaml_content_fixture() -> None:
    """YamlData — real-fixture deserialization using the repo PARITY_*_YAML set."""
    data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        PARITY_GAME_YAML,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    # Exercise several promoted getters (which internally convert the rust types
    # CrashgenEntryRaw/ModConflictEntry/SuspectErrorRule/etc. to Python dicts/lists).
    assert data.classic_version == "9.0.0"
    assert data.xse_acronym == "F4SE"
    assert data.crashgen_name == "Buffout 4"
    assert data.warn_outdated == "Outdated"
    # These getters internally convert the rust dict-bearing types
    assert isinstance(data.game_mods_conf, list)  # ModConflictEntry list
    assert isinstance(data.game_mods_core, list)  # CoreModEntry list
    assert isinstance(data.game_mods_freq, list)  # ModSolutionEntry list (FREQ)
    assert isinstance(data.game_mods_solu, list)  # ModSolutionEntry list (SOLU)
    assert isinstance(data.suspect_error_rules, list)  # SuspectErrorRule list
    assert isinstance(data.suspect_stack_rules, list)  # SuspectStackRule list


def test_yaml_data_mod_conflict_fix_is_optional() -> None:
    """Missing Mods_CONF remediation remains absent in the Python projection."""
    game_yaml = PARITY_GAME_YAML.replace(
        "Mods_CONF: []",
        "\n".join(
            (
                "Mods_CONF:",
                "  - mod_a: Upscaling.dll",
                "    mod_b: FSR3_AA.dll",
                "    name_a: Upscaling",
                "    name_b: FSR 3 Antialiasing",
                "    description: The mods are redundant with each other.",
            )
        ),
    )

    data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        game_yaml,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )

    assert data.game_mods_conf[0]["fix"] is None
    # __repr__ dunder
    assert "YamlData(" in repr(data)


def test_yaml_data_has_no_positional_directory_constructor() -> None:
    """YamlData cannot be built from a directory list."""
    # The positional two/three-directory constructor was removed with the
    # Installed YAML Data cutover: selection policy is owned by Rust, so a
    # Python caller must go through load_installed_yaml_data (installed policy)
    # or load_explicit_yaml_data (deterministic caller-selected files). Direct
    # instantiation must fail rather than silently accept paths CLASSIC would
    # then read under a policy it does not own.
    with pytest.raises(TypeError):
        classic_config.YamlData(["/nonexistent/yaml/dir"], "Fallout4", "auto")


def test_yaml_data_structured_mod_solu_with_real_rules() -> None:
    """ModSolutionEntry + ModSolutionCriteria — exercised through structured Mods_SOLU."""
    structured_game_yaml = PARITY_GAME_YAML.replace(
        "Mods_SOLU: []",
        "\n".join(
            (
                "Mods_SOLU:",
                "  - id: solu-mod-01",
                "    criteria:",
                "      any:",
                '        - "SoluMod"',
                '    name: "Solution Mod"',
                '    description: "Solution mod description"',
            )
        ),
    )
    data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        structured_game_yaml,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    solu_entries = cast(list[dict[str, Any]], data.game_mods_solu)
    assert len(solu_entries) == 1
    # Exercises ModSolutionEntry field access via the getter-produced dict
    first = solu_entries[0]
    assert first["id"] == "solu-mod-01"
    assert first["name"] == "Solution Mod"
    # ModSolutionCriteria::Any variant: becomes {"any": [...]}
    criteria = cast(dict[str, Any], first["criteria"])
    assert "any" in criteria
    assert criteria["any"] == ["SoluMod"]
    classic_config.clear_yaml_cache()


# =============================================================================
# Free functions (3 promoted)
# =============================================================================


def test_create_yamldata_factory_is_removed() -> None:
    """create_yamldata is gone along with the positional constructor it wrapped.

    It was only a functional-style alias for ``YamlData(yaml_dirs, ...)``, so it
    carried the same bypass of Rust-owned Installed YAML Data selection.
    """
    assert not hasattr(classic_config, "create_yamldata")


def test_get_and_set_application_dir_roundtrip(tmp_path: Path) -> None:
    """get_application_dir / set_application_dir — Tier-2 migrations.

    Both are top-level #[pyfunction]s visible in the Python surface.
    """
    original = classic_config.get_application_dir()
    try:
        classic_config.set_application_dir(str(tmp_path))
        assert classic_config.get_application_dir() == str(tmp_path)
    finally:
        if original is not None:
            classic_config.set_application_dir(original)


def test_clear_yaml_cache_call() -> None:
    """clear_yaml_cache — idempotent no-arg free function."""
    classic_config.clear_yaml_cache()
    classic_config.clear_yaml_cache()  # Calling twice should still succeed


# =============================================================================
# Exception classes (already in tier1 via register_exceptions! but exercised)
# =============================================================================


def test_config_exception_classes_hierarchy() -> None:
    """RustConfigError hierarchy — verifies define_exceptions! / register_exceptions! wiring."""
    assert issubclass(classic_config.RustConfigError, Exception)
    assert issubclass(classic_config.RustConfigIOError, classic_config.RustConfigError)
    assert issubclass(classic_config.RustConfigParseError, classic_config.RustConfigError)
    # Exercise a raise path that hits the real config error conversion
    with pytest.raises(classic_config.RustConfigParseError):
        classic_config.YamlData.from_yaml_content(
            "{ invalid: yaml: content: }}}",
            PARITY_GAME_YAML,
            PARITY_IGNORE_YAML,
            "Fallout4",
            "auto",
        )


# =============================================================================
# Pitfall 2 guard: verify rust-only @rust-suffixed symbols exist in core surface
# =============================================================================


def test_rust_only_symbols_in_core_surface() -> None:
    """Pitfall 2 guard: every rust-only symbol promoted via @rust proxy rows
    must exist in the parsed classic-config-core Rust surface.

    If a symbol is missing, the parity gate would fail with tier1_missing_rust > 0.
    This test catches the same condition at pytest time, providing a second
    layer of protection against drift between baseline refreshes.
    """
    surface = json.loads(RUST_API_SURFACE.read_text(encoding="utf-8"))
    symbols = surface.get("symbols", [])
    config_core_symbols = {
        sym["symbol"]
        for sym in symbols
        if sym.get("crate") == "classic-config-core" and sym.get("symbol")
    }

    expected_rust_only = {
        # From yamldata.rs (no Python wrappers; surface via YamlData getters)
        "ConfigError",
        "CoreModEntry",
        "CoreModExclude",
        "CrashgenEntryRaw",
        "ModConflictEntry",
        "ModSolutionCriteria",
        "ModSolutionEntry",
        "SuspectErrorRule",
        "SuspectStackCountRule",
        "SuspectStackRule",
        # Sub-module markers
        "yaml_source",
        "yamldata",
        # Free functions
        "format_registry_game_version",
        "resolve_registry_version_info",
        # Re-export from shared-core
        "get_runtime",
    }
    missing = expected_rust_only - config_core_symbols
    assert not missing, (
        f"Pitfall 2: rust-only config symbols missing from classic-config-core "
        f"surface: {sorted(missing)}"
    )
