## Why

The `Game_Info` and `GameVR_Info` sections in the game database YAML files duplicate version-specific metadata (game versions, XSE details, crash generator info, script hashes) that the Version Registry already owns as its single source of truth. Every consumer must branch on VR mode with `f"Game{vr_suffix}_Info.{key}"` across ~50+ call sites, and the VR section is left blank when VR is not detected. Consolidating to a single `Game_Info` runtime namespace — with the Version Registry providing all static metadata — eliminates this branching, removes data duplication, and completes the Version Registry's role as the authoritative source for version-specific information.

## What Changes

- **BREAKING**: Remove the `GameVR_Info` section from `CLASSIC Fallout4.yaml` (and `CLASSIC Skyrim.yaml` if applicable). All VR-specific static metadata moves to the Version Registry's `FO4_VR` entry.
- **BREAKING**: Remove version-specific static fields from `Game_Info` in the database YAML (game versions, XSE info, crash generator info, exe hashes, script hashes, `Main_Root_Name`, `Main_Docs_Name`, `Main_SteamID`). The Version Registry becomes the sole source for these.
- Expand the `VersionInfo` model with new fields: `docs_name`, `steam_id`.
- Expand the `XseConfig` model with new fields: `full_name`, `file_count`.
- Expand the `CrashgenConfig` model with new fields: `acronym`, `dll_file`.
- Populate full script hashes (all 29 per version) in `defaults.rs` for FO4_OG, FO4_NG, and FO4_VR (currently only 5 representative hashes for OG/NG, 0 for VR).
- Consolidate all runtime path cache writes to use `Game_Info.{key}` regardless of VR mode — the active version from the registry determines which data populates the paths.
- Migrate all `f"Game{vr_suffix}_Info.{key}"` call sites (~50+) to either `"Game_Info.{key}"` (for runtime paths) or direct Version Registry lookups (for static metadata).
- Remove or deprecate `get_vr()` / `get_config_suffix()` as YAML key construction helpers (they may remain for other non-YAML uses).

## Capabilities

### New Capabilities
- `version-registry-game-metadata`: Extends the Version Registry model to carry all game metadata fields previously stored in `Game_Info`/`GameVR_Info` YAML sections (docs name, Steam ID, XSE full name/file count, crashgen acronym/DLL file, full script hashes).

### Modified Capabilities
- `crashgen-schema-registry`: The crashgen registry currently coexists with `CRASHGEN_*` fields in `Game_Info`/`GameVR_Info`. After this change, all crashgen identity fields (name, acronym, DLL file, latest version) come from the Version Registry. The `Crashgen_Registry` YAML section for per-crashgen settings validation config is unaffected.

## Impact

- **Rust crates**: `classic-version-registry-core` (model expansion + defaults), `classic-config-core` (stop reading Game_Info/GameVR_Info for version fields from YAML, read from registry instead), `classic-constants-core` (`config_section()` method on `Fallout4Version` becomes unnecessary).
- **Rust bindings**: `classic-version-registry-py`, `classic-node`, `classic-cpp-bridge` all need to expose new fields.
- **Python models**: `ClassicLib/support/versions/models.py` gains new properties for new fields.
- **Python consumers** (~50+ call sites): `game_path.py`, `docs_path.py`, `integrity.py`, `xse.py`, `setup.py`, `resources.py`, `path_manager.py`, `gui_components.py`, `check_crashgen.py`, `check_xse_plugins.py`, `validators.py`, `documents.py`, `scan_mod_inis.py`, `wrye_check.py`, `papyrus.py`, `backup.py`, `orchestrator.py`, `config.py`.
- **Rust TUI**: `classic-tui/src/app.rs` uses `GameVR_Info` section name.
- **Test fixtures**: Many test files mock `Game_Info`/`GameVR_Info` YAML paths.
- **YAML database files**: `CLASSIC Fallout4.yaml` (and potentially `CLASSIC Skyrim.yaml`) lose their `Game_Info` version fields and `GameVR_Info` section entirely.
