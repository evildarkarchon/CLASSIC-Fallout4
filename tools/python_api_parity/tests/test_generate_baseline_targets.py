"""PYT-01 unit guard: every RUST_TARGET_CRATES / PYTHON_TARGET_MODULES entry parses cleanly."""

from __future__ import annotations

from pathlib import Path

# sys.path bootstrap handled by conftest.py
from generate_baseline import (  # noqa: E402
    PYTHON_OWNER_BY_MODULE,
    PYTHON_TARGET_MODULES,
    RUST_OWNER_BY_CRATE,
    RUST_TARGET_CRATES,
    SQUAD_BY_OWNER,
    parse_rust_surface,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rust_target_crates_count_matches_repo_root_inventory() -> None:
    assert len(RUST_TARGET_CRATES) == 18, (
        f"Expected 18 RUST_TARGET_CRATES in the repo-root inventory, "
        f"got {len(RUST_TARGET_CRATES)}"
    )


def test_classic_shared_py_is_in_rust_target_crates() -> None:
    assert "classic-shared-py" in RUST_TARGET_CRATES
    assert RUST_TARGET_CRATES["classic-shared-py"] == (
        "foundation/classic-shared-py/src/lib.rs"
    )


def test_classic_crashgen_settings_core_is_excluded() -> None:
    # Per Phase 3 RESEARCH.md Assumption Correction A5: this crate has no -py adapter
    assert "classic-crashgen-settings-core" not in RUST_TARGET_CRATES


def test_every_rust_target_parses_to_nonempty_symbols() -> None:
    manifest = parse_rust_surface(REPO_ROOT, set())
    symbols_by_crate: dict[str, int] = {}
    for entry in manifest["symbols"]:
        symbols_by_crate[entry["crate"]] = symbols_by_crate.get(entry["crate"], 0) + 1
    for crate_name in RUST_TARGET_CRATES:
        assert symbols_by_crate.get(crate_name, 0) > 0, (
            f"Crate '{crate_name}' parsed to zero symbols -- check the lib.rs path"
        )


def test_settings_yaml_ops_nested_modules_are_scanned() -> None:
    """The settings YAML facade stores inherent methods two module levels deep."""
    manifest = parse_rust_surface(REPO_ROOT, set())
    symbols = {
        entry["symbol"]: entry
        for entry in manifest["symbols"]
        if entry["crate"] == "classic-settings-core"
    }
    assert symbols["parse_yaml"]["source_file"] == (
        "business-logic/classic-settings-core/src/yaml_ops/operations.rs"
    )
    assert symbols["get_setting"]["source_file"] == (
        "business-logic/classic-settings-core/src/yaml_ops/accessors.rs"
    )


def test_python_target_modules_count_matches_repo_root_inventory() -> None:
    assert len(PYTHON_TARGET_MODULES) == 17


def test_classic_shared_pyi_path_is_correct() -> None:
    assert "classic_shared" in PYTHON_TARGET_MODULES
    assert PYTHON_TARGET_MODULES["classic_shared"] == (
        "foundation/classic-shared-py/classic_shared.pyi"
    )


def test_python_target_paths_use_repo_root_layout_only() -> None:
    for rel_path in (*RUST_TARGET_CRATES.values(), *PYTHON_TARGET_MODULES.values()):
        assert not rel_path.startswith("ClassicLib-rs/"), rel_path


def test_every_pyi_file_exists_on_disk() -> None:
    for module_name, rel_path in PYTHON_TARGET_MODULES.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.exists(), (
            f"PYTHON_TARGET_MODULES['{module_name}'] -> {rel_path} does not exist"
        )


def test_owner_dict_keys_match_target_dict_keys() -> None:
    assert set(RUST_OWNER_BY_CRATE.keys()) == set(RUST_TARGET_CRATES.keys())
    assert set(PYTHON_OWNER_BY_MODULE.keys()) == set(PYTHON_TARGET_MODULES.keys())


def test_every_owner_label_is_in_squad_by_owner() -> None:
    for owner in RUST_OWNER_BY_CRATE.values():
        assert owner in SQUAD_BY_OWNER, f"Owner '{owner}' missing from SQUAD_BY_OWNER"
    for owner in PYTHON_OWNER_BY_MODULE.values():
        assert owner in SQUAD_BY_OWNER, f"Owner '{owner}' missing from SQUAD_BY_OWNER"
    # The aux owner is needed for the file-io aux entry (Plan 8)
    assert "aux" in SQUAD_BY_OWNER, (
        "SQUAD_BY_OWNER must include 'aux' for the classic_file_io.FileHasher.cache_size entry"
    )
