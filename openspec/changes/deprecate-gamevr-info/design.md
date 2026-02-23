## Context

The CLASSIC codebase currently stores version-specific game metadata in two parallel systems:

1. **YAML database sections** (`Game_Info` / `GameVR_Info` in `CLASSIC Fallout4.yaml`) — static metadata like game versions, XSE details, crash generator info, and script hashes.
2. **Version Registry** (`classic-version-registry-core`) — a Rust singleton with hardcoded defaults in `defaults.rs`, exposing `VersionInfo` structs that already contain most of this same data.

The YAML sections also serve double duty as a **runtime path cache namespace** — `game_path.py` and friends write discovered filesystem paths (exe location, data folders, docs folders) under the same `Game{VR}_Info` prefix in `YAML.Game_Local`.

All consumers branch on VR mode using `f"Game{vr_suffix}_Info.{key}"` at ~50+ call sites. The `GameVR_Info` section in the local YAML is left entirely blank when VR is not detected.

## Goals / Non-Goals

**Goals:**
- Make the Version Registry the single source of truth for all version-specific game metadata.
- Eliminate the `GameVR_Info` YAML section entirely (both in database and local YAML).
- Consolidate runtime path cache to a single `Game_Info` namespace regardless of active version.
- Remove VR-branching (`vr_suffix`) from YAML key construction across all consumers.
- Add missing fields to the Version Registry models (`docs_name`, `steam_id`, `full_name`, `file_count`, `acronym`, `dll_file`).
- Populate full script hashes (all 29) in `defaults.rs` for OG, NG, and VR entries.

**Non-Goals:**
- Migrating the `Crashgen_Registry` YAML section (per-crashgen settings validation config) — this is game-wide, not version-specific, and remains in YAML.
- Migrating non-version data from the YAML (backup file lists, game hints, default INI content, warning templates, crash patterns).
- Removing `get_vr()` entirely — it may still be useful for non-YAML purposes (exe name construction, etc.). Only its role in YAML key construction is removed.
- Adding Skyrim support to the Version Registry (separate change).
- Populating FO4_AE script hashes or exe hashes (data not yet available).

## Decisions

### D1: Extend `VersionInfo` with game-identity fields rather than creating a separate `GameConfig` struct

The fields `docs_name` and `steam_id` are properties of a game variant, but since the Version Registry treats every variant as a version entry, they belong on `VersionInfo`. OG, NG, and AE will all carry `steam_id: 377160` and `docs_name: "Fallout4"` — duplicated across entries but keeping each entry self-contained.

**Alternative considered:** A separate `GameConfig` struct keyed by game name. Rejected because it reintroduces the game-vs-version distinction this change aims to eliminate, and the duplication is trivial (two small fields across 4 entries).

### D2: New fields on `XseConfig` and `CrashgenConfig` rather than flattened on `VersionInfo`

`full_name` and `file_count` are XSE properties, so they belong on `XseConfig`. `acronym` and `dll_file` are crash generator properties, so they belong on `CrashgenConfig`. This keeps the model cohesive.

**Alternative considered:** Flattening all fields onto `VersionInfo`. Rejected because it would bloat the struct and break the logical grouping (XSE info on XseConfig, crashgen info on CrashgenConfig).

### D3: Populate all 29 script hashes per version in `defaults.rs`

Currently only 5 representative hashes exist for OG/NG and 0 for VR. The YAML has all 29. Since the registry is becoming the sole source, all hashes must be there. This makes `defaults.rs` larger but eliminates the YAML dependency for hash validation.

**Alternative considered:** Keeping a subset of representative hashes. Rejected because XSE script validation needs all hashes to detect tampered or mismatched script extender installations.

### D4: Runtime path cache uses `Game_Info` unconditionally

All runtime paths (Root_Folder_Game, Game_File_EXE, etc.) are written to and read from `Game_Info.{key}` in `YAML.Game_Local` regardless of whether the active version is VR, OG, NG, or AE. The active version from the registry determines what data populates these paths, not the YAML key namespace.

**Alternative considered:** Using the version ID as namespace (e.g., `FO4_VR.Root_Folder_Game`). Rejected because it would require migrating all runtime path consumers and offers no practical benefit — there's only ever one active version at a time.

### D5: Phased migration — Rust models first, then consumers, then YAML cleanup

1. **Phase 1 (Rust core):** Add new fields to models, populate `defaults.rs`, update PyO3/NAPI/CXX bindings, update Python model wrappers.
2. **Phase 2 (Consumer migration):** Migrate Python call sites from YAML reads to registry lookups for static data, and from `f"Game{vr_suffix}_Info.{key}"` to `"Game_Info.{key}"` for runtime paths.
3. **Phase 3 (YAML cleanup):** Remove deprecated fields from `Game_Info`, delete `GameVR_Info` section, remove `XSE_HashedScriptsNew` section.
4. **Phase 4 (Dead code removal):** Remove `config_section()` from `Fallout4Version`, clean up `YamlDataCore` VR-specific fields that are now sourced from registry, update Rust TUI.

This ordering ensures no consumer breaks — the registry has all data before YAML is stripped.

### D6: `YamlDataCore` fields that duplicate registry data get removed

`YamlDataCore` currently has `crashgen_name`, `crashgen_name_vr`, `game_root_name`, `game_root_name_vr`, `game_version`, `game_version_new`, `game_version_vr`, `crashgen_latest_og`, `crashgen_latest_vr`, `xse_acronym`. These are all read from `Game_Info`/`GameVR_Info` YAML sections. After this change, consumers read these from the Version Registry instead, and the `YamlDataCore` fields are removed (or the VR-specific variants are removed and the remaining fields are sourced from the registry).

## Risks / Trade-offs

**[Large blast radius]** → ~50+ Python call sites, multiple Rust crates, test fixtures, bindings layers. Mitigated by phased approach — each phase is independently testable and deployable.

**[`defaults.rs` grows significantly]** → Adding all 29 hashes × 3 versions (OG, NG, VR) plus new fields. Each version entry will have ~29 hash tuples. Mitigated by: this is static data that compiles away efficiently, and it's the single source of truth by design.

**[FO4_VR exe hashes remain placeholder]** → VR exe hash data is unavailable (no VR copy owned). Registry entry will have `exe_hash: None`. Risk is low — the existing YAML has `00000` placeholders, so behavior is unchanged.

**[FO4_AE has no script hashes]** → AE script hash data is not yet available. Registry entry keeps empty `script_hashes`. This is the current state and doesn't regress.

**[Test fixture updates]** → Many tests mock `Game_Info`/`GameVR_Info` YAML paths. These must be updated to either mock registry lookups or use `"Game_Info.{key}"` without VR branching. Mitigated by: test updates happen in Phase 2 alongside consumer migration.

## Open Questions

- Should `CLASSIC Skyrim.yaml` be addressed in this change, or in a separate follow-up? (Current scope focuses on Fallout 4.)
- Should the `YamlDataCore` VR-specific getter methods (`get_crashgen_name(is_vr)`, `get_game_root_name(is_vr)`) be removed entirely, or replaced with single non-VR methods that assume the registry handles version dispatch?
