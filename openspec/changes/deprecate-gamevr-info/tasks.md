## 1. Rust Model Expansion

- [ ] 1.1 Add `docs_name: String` and `steam_id: u32` fields to `VersionInfo` in `classic-version-registry-core/src/models.rs`
- [ ] 1.2 Add `full_name: String` and `file_count: u32` fields to `XseConfig` in `classic-version-registry-core/src/models.rs`
- [ ] 1.3 Add `acronym: String` and `dll_file: String` fields to `CrashgenConfig` in `classic-version-registry-core/src/models.rs`
- [ ] 1.4 Update all constructors (`new`, `with_script_hashes`, `with_range`, `from_version_string`) to accept and populate new fields
- [ ] 1.5 Update unit tests in `models.rs` for new fields

## 2. Populate Defaults

- [ ] 2.1 Populate all 29 OG script hashes in `create_fo4_og()` (replace current 5 representative hashes)
- [ ] 2.2 Populate all 29 NG script hashes in `create_fo4_ng()` (replace current 5 representative hashes)
- [ ] 2.3 Populate all 29 VR script hashes in `create_fo4_vr()` (currently empty)
- [ ] 2.4 Add `docs_name`, `steam_id` to all four version entries (OG, NG, AE, VR) in `defaults.rs`
- [ ] 2.5 Add `full_name`, `file_count` to all `XseConfig` entries in `defaults.rs`
- [ ] 2.6 Add `acronym`, `dll_file` to all `CrashgenConfig` entries in `defaults.rs`
- [ ] 2.7 Update `defaults.rs` unit tests for new fields and full hash counts

## 3. Rust Bindings

- [ ] 3.1 Expose new `VersionInfo` fields (`docs_name`, `steam_id`) in PyO3 bindings (`classic-version-registry-py`)
- [ ] 3.2 Expose new `XseConfig` fields (`full_name`, `file_count`) in PyO3 bindings
- [ ] 3.3 Expose new `CrashgenConfig` fields (`acronym`, `dll_file`) in PyO3 bindings
- [ ] 3.4 Update Python `.pyi` stub file for `classic_version_registry`
- [ ] 3.5 Expose new fields in NAPI-RS bindings (`classic-node/src/version_registry.rs`)
- [ ] 3.6 Expose new fields in CXX bridge (`classic-cpp-bridge`)
- [ ] 3.7 Build and verify all bindings compile: `.\rebuild_rust.ps1`

## 4. Python Model Wrappers

- [ ] 4.1 Add `docs_name` and `steam_id` properties to `VersionInfo` in `ClassicLib/support/versions/models.py`
- [ ] 4.2 Add `full_name` and `file_count` properties to `XseConfig` in `ClassicLib/support/versions/models.py`
- [ ] 4.3 Add `acronym` and `dll_file` properties to `CrashgenConfig` in `ClassicLib/support/versions/models.py`
- [ ] 4.4 Update Python tests for version registry models (`tests/version_registry/`)

## 5. Consumer Migration — Static Metadata Reads

- [ ] 5.1 Migrate `ClassicLib/support/docs_path.py` — replace `yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")` and `Main_Docs_Name`/`Main_SteamID` reads with registry lookups
- [ ] 5.2 Migrate `ClassicLib/support/game_path.py` — replace `XSE_Acronym`, `Main_Root_Name` YAML reads with registry lookups
- [ ] 5.3 Migrate `ClassicLib/support/integrity.py` — replace `Main_Root_Name` YAML read with registry lookup
- [ ] 5.4 Migrate `ClassicLib/support/xse.py` — replace XSE-related YAML reads with registry lookups
- [ ] 5.5 Migrate `ClassicLib/support/documents.py` — replace `Main_Docs_Name` YAML read with registry lookup
- [ ] 5.6 Migrate `ClassicLib/support/setup.py` — replace `Main_Root_Name` YAML read with registry lookup
- [ ] 5.7 Migrate `ClassicLib/scanning/game/check_crashgen.py` — replace `CRASHGEN_LogName` YAML read with registry lookup
- [ ] 5.8 Migrate `ClassicLib/scanning/game/checks/validators.py` — replace `XSE_Acronym` YAML read with registry lookup
- [ ] 5.9 Migrate `ClassicLib/scanning/logs/util_legacy.py` — replace `Docs_Folder_XSE` related reads

## 6. Consumer Migration — Runtime Path Cache Consolidation

- [ ] 6.1 Update `ClassicLib/support/game_path.py` — change all `f"Game{vr_suffix}_Info.{key}"` to `"Game_Info.{key}"` for runtime path reads/writes
- [ ] 6.2 Update `ClassicLib/support/docs_path.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.3 Update `ClassicLib/support/integrity.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.4 Update `ClassicLib/support/xse.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.5 Update `ClassicLib/support/setup.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.6 Update `ClassicLib/support/backup.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.7 Update `ClassicLib/support/resources.py` — consolidate `_local_yaml_key` to remove VR branching
- [ ] 6.8 Update `ClassicLib/support/gui_components.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.9 Update `ClassicLib/support/path_validator.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.10 Update `ClassicLib/support/papyrus.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.11 Update `ClassicLib/scanning/game/orchestrator.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.12 Update `ClassicLib/scanning/game/scan_mod_inis.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.13 Update `ClassicLib/scanning/game/wrye_check.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.14 Update `ClassicLib/scanning/game/check_xse_plugins.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.15 Update `ClassicLib/scanning/game/config.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.16 Update `ClassicLib/Interface/settings/path_manager.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.17 Update `ClassicLib/Interface/settings/dialog.py` — consolidate to `"Game_Info.{key}"`
- [ ] 6.18 Update `ClassicLib/Interface/controllers/path_dialog.py` if needed

## 7. Rust Consumer Migration

- [ ] 7.1 Update `classic-config-core/src/yamldata.rs` — remove VR-specific fields (`crashgen_name_vr`, `game_root_name_vr`, `crashgen_latest_vr`, `game_version_vr`, etc.) and their `GameVR_Info` YAML reads
- [ ] 7.2 Update `classic-config-core/src/yamldata.rs` — remove VR dispatch methods (`get_crashgen_name(is_vr)`, `get_game_root_name(is_vr)`) or simplify to single non-VR variant
- [ ] 7.3 Update `classic-constants-core/src/lib.rs` — deprecate or remove `Fallout4Version::config_section()` method
- [ ] 7.4 Update `classic-tui/src/app.rs` — remove `GameVR_Info` branching
- [ ] 7.5 Update `classic-config-core` integration tests that embed `GameVR_Info` in test YAML
- [ ] 7.6 Update `classic-scangame-core/src/setup.rs` — remove VR config section branching

## 8. YAML Database Cleanup

- [ ] 8.1 Remove `GameVR_Info` section from `CLASSIC Fallout4.yaml`
- [ ] 8.2 Remove version-specific static fields from `Game_Info` in `CLASSIC Fallout4.yaml` (GameVersion, GameVersionNEW, EXE_Hashed*, CRASHGEN_*, XSE_*, Main_Root_Name, Main_Docs_Name, Main_SteamID)
- [ ] 8.3 Remove `XSE_HashedScriptsNew` section from `CLASSIC Fallout4.yaml`
- [ ] 8.4 Verify remaining YAML sections (Crashgen_Registry, Backup *, Game_Hints, Default_*, Warnings_*) are intact

## 9. Test Updates

- [ ] 9.1 Update test fixtures that mock `GameVR_Info` YAML paths (`tests/fixtures/`)
- [ ] 9.2 Update `tests/backup/test_backup_configuration_unit.py` — remove `GameVR_Info` assertions
- [ ] 9.3 Update `tests/core/test_documents_checker_unit.py` — remove `GameVR_Info` assertions
- [ ] 9.4 Update `tests/gui/test_gui_components_unit.py` — remove `GameVR_Info` assertions
- [ ] 9.5 Update `tests/game/test_xse_check_unit.py` — remove `GameVR_Info` assertions
- [ ] 9.6 Update `tests/game/integrity/test_integrity_configuration_unit.py` — remove `GameVR_Info` assertions
- [ ] 9.7 Update `tests/interface/settings/test_path_manager_unit.py` — remove `GameVR_Info` assertions
- [ ] 9.8 Update `tests/setup/test_setup_coordinator_unit.py` — remove `GameVR_Info` assertions
- [ ] 9.9 Update `tests/rust_integration/parity/test_config_parity.py` — adjust for removed YamlData VR fields
- [ ] 9.10 Update `tests/fixtures/registry_fixtures.py` — remove `Game_Info.CRASHGEN_LogName` / `Game_Info.XSE_Acronym` mock entries where registry now provides these
- [ ] 9.11 Run full test suite: `uv run pytest` and `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`

## 10. Verification

- [ ] 10.1 Verify Rust builds clean: `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- [ ] 10.2 Verify Rust lints clean: `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`
- [ ] 10.3 Verify Python lints clean: `uv run ruff check .`
- [ ] 10.4 Rebuild all PyO3 bindings: `.\rebuild_rust.ps1`
- [ ] 10.5 Run full Python test suite: `uv run pytest --skip-slow --skip-network --skip-performance --skip-stress`
- [ ] 10.6 Run full Rust test suite: `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
