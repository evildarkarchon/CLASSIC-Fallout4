# `classic-cpp-bridge` Game Entry Points

Contributor-facing documentation for the active C++ bridge entry points in:

- [`cpp-bindings/classic-cpp-bridge/src/path.rs`](../../cpp-bindings/classic-cpp-bridge/src/path.rs)
- [`cpp-bindings/classic-cpp-bridge/src/game.rs`](../../cpp-bindings/classic-cpp-bridge/src/game.rs)
- [`cpp-bindings/classic-cpp-bridge/src/scangame.rs`](../../cpp-bindings/classic-cpp-bridge/src/scangame.rs)

This page documents the current CXX FFI surface that active C++ callers use for path detection, version-registry lookups, PE version probing, XSE probing, and setup-time checks.

It is intentionally about the bridge surface that exists in source today. It does **not** describe a future unified bridge or imply that the bridge exposes every capability of the underlying Rust crates.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to understand:

- which bridge file owns which `classic::*` C++ namespace
- which Rust business-logic crate each exported function actually calls
- where the bridge returns structured DTOs versus simple fail-soft primitives
- where the C++ bridge narrows, hardcodes, or drops part of the lower-level Rust API
- how to debug contributor issues that appear in the C++ frontend but originate in Rust path, registry, XSE, or setup code

This page is for contributors working on the active Rust/C++ path.

For crate-level behavior, see:

- [`classic-path-core.md`](classic-path-core.md)
- [`classic-xse-core.md`](classic-xse-core.md)
- [`classic-scangame-core.md`](classic-scangame-core.md)
- [`classic-version-registry-core.md`](classic-version-registry-core.md)
- [`classic-version-core.md`](classic-version-core.md)
- [`game-setup-workflow.md`](game-setup-workflow.md)

---

## Current Bridge Ownership

## `src/path.rs` -> `classic::path`

This file exposes Fallout 4-specific convenience detection only:

- `detect_fallout4_game_path(cached_path, selected_game_version) -> String`
- `resolve_fallout4_exe_name(selected_game_version) -> String`
- `detect_fallout4_docs_path(cached_path, selected_game_version) -> String`

It wraps `classic-path-core` directly and resolves Fallout 4 names from version-registry metadata.

## `src/game.rs` -> `classic::game`

This file is the broader mixed bridge surface. It exposes:

- Version Registry lookups and match helpers
- game-version string parsing
- PE version extraction from an `.exe` or `.dll`
- XSE type parsing plus XSE installation/version probing
- generic game-path lookup plus low-level path/restricted-path checks

This is currently the main bridge file where multiple crates meet.

## `src/scangame.rs` -> `classic::scangame`

This file exposes Game Setup Intake plus the broader scanner/checker bridge functions in this namespace.

- `run_game_setup_intake(...) -> GameSetupIntakeDto`
- `run_game_setup_intake_from_user_settings(classic_root, xse_log_path) -> GameSetupIntakeDto`
- `game_setup_intake_checks(...) -> Result<Vec<GameSetupCheckDto>>`
- `game_setup_needs_path_detection(game_path, docs_path) -> GameSetupPathDetectionNeeds`

Game Setup Intake is setup-only. ENB, crashgen, BA2, Wrye, INI, and mod-file checks remain separate bridge entry points.

---

## FFI Surface By File

## `classic::path` entry points

### `detect_fallout4_game_path(cached_path, selected_game_version) -> String`

Forwards to:

- `classic_path_core::GamePathFinder::new(...)`
- `classic_path_core::GamePathFinder::find_game_path(...)`

Current bridge choices:

- resolves the executable name from version-registry metadata (`docs_name + ".exe"`)
- passes `None` for `xse_loader`, so detection validates only the game executable, not `f4se_loader.exe` or `f4sevr_loader.exe`
- passes `None` for the XSE log path, so the bridge uses only cached-path and platform path-discovery strategies
- returns the detected path as a lossy UTF-8 `String`
- returns `""` on any failure instead of surfacing `GamePathError`

Practical contributor implication:

- this helper is narrower than `GamePathFinder`; callers cannot request loader-aware validation or XSE-log fallback through this bridge entry point

### `resolve_fallout4_exe_name(selected_game_version) -> String`

Returns the expected Fallout 4 executable filename for the selected version by resolving version-registry metadata.

### `detect_fallout4_docs_path(cached_path, selected_game_version) -> String`

Forwards to:

- `classic_path_core::DocsPathFinder::new(...)`
- `classic_path_core::DocsPathFinder::find_docs_path(...)`

Current bridge choices:

- resolves the documents subfolder from version-registry metadata (`docs_name`)
- accepts a cached string path and otherwise uses the crate's platform-specific discovery flow
- chains `DocsPathFinder::with_steam_app_id(Fallout4Version::Original.steam_app_id())` so Linux Proton documents-path detection for Fallout 4 still works. This is the canonical call site for the 377160 literal — the bridge now imports `classic_version_registry_core::Fallout4Version` rather than hard-coding the Steam ID.
- does not expose `validate_ini_files()` or `DocumentsChecker`
- returns `""` on failure instead of surfacing `DocsPathError`

---

## `classic::game` entry points

## Version Registry DTO functions

### `version_registry_get_by_id(id) -> VersionInfoDto`

Forwards to:

- `classic_version_registry_core::get_version_registry()`
- `VersionRegistry::get_by_id()`

Bridge DTO shape:

- `id`
- `version_string`
- `short_name`
- `game`
- `docs_name`
- `steam_id`
- `is_vr`
- `found`

Bridge narrowing:

- the DTO exposes only a small slice of `VersionInfo`
- fields like `display_name`, `description`, `priority`, `address_library`, `exe_hash`, and full crashgen metadata are omitted here
- a miss returns a sentinel DTO with `found = false` and mostly empty/default fields instead of `Option`

### `version_registry_get_all_ids() -> Vec<String>`

Forwards to `VersionRegistry::get_all()` and returns only the sorted ID list.

### `version_registry_get_all_count() -> usize`

Forwards to `VersionRegistry::get_all().len()`.

### `version_registry_match_version(version_str, game, is_vr) -> MatchResultDto`

Forwards to:

- `classic_version_registry_core::GameVersion::parse()`
- `VersionRegistry::match_version()`

Bridge DTO shape:

- `matched_id`
- `confidence`
- `message`
- `is_match`

Fail-soft behavior:

- parse failure does not cross FFI as an error
- instead the bridge returns `is_match = false`, `matched_id = ""`, and a message like `Failed to parse version: ...`
- `confidence` becomes the bridge-local string `"None"`, not a Rust enum variant

Bridge narrowing:

- the bridge drops `MatchResult.detected`
- it also drops the full matched `VersionInfo`
- `confidence` is stringified with `format!("{:?}", ...)`, so the C++ side sees display text, not a typed enum

### `version_registry_get_xse_config(id) -> XseConfigDto`

Forwards to `VersionRegistry::get_by_id(id)` plus `info.xse.as_ref()`.

Bridge DTO shape:

- `acronym`
- `full_name`
- `compatible_version`
- `loader`
- `file_count`
- `found`

Bridge narrowing:

- the DTO does not expose `script_hashes`, even though the Rust `XseConfig` model has them
- a miss returns a sentinel DTO with `found = false`

### `version_registry_get_crashgen_configs(id) -> Vec<CrashgenConfigDto>`

Forwards to `VersionRegistry::get_crashgen_versions(id)`.

### `version_registry_get_crashgen_config(id, crashgen_version) -> CrashgenConfigDto`

Forwards to `VersionRegistry::get_crashgen_for_version(id, crashgen_version)`.

Bridge DTO shape for both crashgen calls:

- `version`
- `name`
- `acronym`
- `dll_file`
- `description`
- `download_url`

Bridge narrowing:

- `compatible_range` is not exposed even though the Rust model carries it
- the single-config lookup returns an all-empty DTO on miss rather than `Option`

## Version parsing and PE probing

### `parse_game_version(version_str) -> GameVersionDto`

Forwards to `classic_version_registry_core::GameVersion::parse()`.

Bridge DTO shape:

- `major`
- `minor`
- `patch`
- `build`
- `valid`

Fail-soft behavior:

- invalid input becomes `{0, 0, 0, 0, valid = false}`
- parse errors are not preserved across the bridge

### `extract_pe_version_string(exe_path) -> String`

Forwards to `classic_version_core::pe_version::extract_pe_version()`.

Bridge narrowing:

- formats the Rust `(u16, u16, u16, u16)` tuple as `major.minor.patch.build`
- returns `""` on any `PeVersionError`
- the C++ side cannot distinguish invalid path, invalid PE image, missing version resource, or plain I/O failure from this entry point alone

## XSE helpers

### `detect_xse_version_string(exe_path, xse_type_str) -> String`

Forwards to:

- bridge-local `xse_type_from_str()`
- `classic_xse_core::detect_xse_version()`

Current behavior:

- accepted type strings are `F4SE`, `F4SEVR`, `SKSE`, `SKSE64`, `SKSEVR`, and `SFSE`
- parsing is case-insensitive because the bridge uppercases before matching
- the path argument is a loader path, not a game root
- the returned value is the semver string from `classic-xse-core`
- any invalid type or `XseError` becomes `""`

Bridge narrowing:

- the bridge duplicates `XseType` parsing instead of using `str::parse::<XseType>()`
- the C++ side gets no reason for failure

### `is_xse_installed_check(game_root, xse_type_str) -> bool`

Forwards to `classic_xse_core::is_xse_installed()`.

Current behavior:

- the path argument is the game root
- invalid type strings become `false`
- the check means only that the expected loader file exists
- this entry point does not inspect DLLs, version strings, registry compatibility, or Address Library state

### `resolve_xse_folder_for_scan(yaml_dir_data, game, selected_game_version, configured_docs_root) -> String`

Forwards to `classic_xse_core::resolve_xse_folder_for_scan()`.

Current behavior:

- reads `<yaml_dir_data>/CLASSIC <game> Local.yaml` through the Rust XSE module
- uses `Game_Info.Docs_Folder_XSE` first when present and non-blank
- otherwise derives from `Game_Info.Root_Folder_Docs`, `configured_docs_root`, or Version Registry-backed documents discovery
- appends the Rust XSE resolver's documents folder name for derived paths; Fallout 4 VR uses the shared `F4SE` subfolder even though its XSE acronym is `F4SEVR`
- returns `""` when the Rust module returns `None`

Bridge narrowing:

- `configured_docs_root = ""` is treated as `None`
- the C++ side gets no reason for missing or unreadable Local.yaml, unknown game/version, or documents discovery failure

## Path helpers

### `find_game_path(game_exe, xse_loader, game_name, is_vr, cached_path, xse_log_path) -> String`

Forwards to `classic_path_core::GamePathFinder::new(...)` plus `find_game_path(...)`.

This is the generic bridge counterpart to the narrower Fallout 4 helper in `src/path.rs`.

Current bridge behavior:

- empty `xse_loader` becomes `None`
- empty `cached_path` becomes `None`
- empty `xse_log_path` becomes `None`
- successful results are stringified with `to_string_lossy()`
- any `GamePathError` becomes `""`

Bridge simplification versus `classic-path-core`:

- error details are dropped
- the C++ side cannot tell whether failure came from cached-path validation, registry lookup, XSE-log parsing, or full `NotFound`

### `validate_path(path) -> bool`

Forwards to `classic_path_core::is_valid_path()`.

Important boundary:

- this is only an existence check
- it does not require a directory, game executable, loader, permissions, or any specific file shape

### `check_restricted_path(path) -> bool`

Forwards to `classic_path_core::is_restricted_path()`.

Important boundary:

- this is the custom-scan restriction heuristic from `classic-path-core`
- it is substring- and depth-based, not a canonicalized Windows policy check

---

## `classic::scangame` entry points

### `run_game_setup_intake(game_id, game_version, game_root, docs_path, xse_log_path, game_exe_path) -> GameSetupIntakeDto`

Forwards to:

- `classic_scangame_core::GameSetupIntake::new(...)`
- `GameSetupIntake::with_game_root(...)`
- `GameSetupIntake::with_game_exe_path(...)`
- `GameSetupIntake::with_docs_root(...)`
- `GameSetupIntake::with_xse_log_path(...)`
- `GameSetupIntake::run()`

Bridge DTO shape:

- `rendered_report`
- `status`
- `has_errors`
- `total_checks`
- `failed_checks`
- `action_count`
- `path_update_count`
- `path_updates: Vec<GameSetupPathUpdateDto>` with ordered `kind` and `path` proposals; UTF-8-representable paths are exact, while other native paths follow the CXX bridge's established lossy string conversion
- `game_root`
- `game_executable`
- `docs_root`

Current bridge behavior that matters:

- `game_id` must parse as a `classic_shared_core::GameId`
- empty path strings are treated as absent optional paths
- non-empty `game_exe_path` is forwarded to intake for root fallback, auto-version detection, executable checks, and install-location checks
- invalid `game_id` returns a fatal DTO rather than throwing across CXX
- setup diagnostics come from Rust core and include registry-backed executable, documents, and XSE checks where metadata exists

### `run_game_setup_intake_from_user_settings(classic_root, xse_log_path) -> GameSetupIntakeDto`

This is the cohesive GUI adapter. Rust opens `UserSettings` read-only, builds `GameSetupIntake` with `from_user_settings(...)`, optionally adds the XSE-log detection hint, and returns the same DTO shape as the positional compatibility entry point. Opening and running intake never creates, migrates, or updates User Settings; returned path proposals still require caller consent and one later explicit update commit.

### `game_setup_intake_checks(game_id, game_version, game_root, docs_path, xse_log_path, game_exe_path) -> Result<Vec<GameSetupCheckDto>>`

Returns the typed check list from the same intake run. Invalid intake inputs, such as an unknown `game_id`, are returned as CXX `Result` errors rather than being collapsed to an empty check list.

Bridge DTO shape:

- `kind`
- `state`
- `message`
- `details`

Use this when a C++ caller needs structured UI/status handling instead of only `rendered_report`.

### `game_setup_needs_path_detection(game_path, docs_path) -> GameSetupPathDetectionNeeds`

Forwards to `classic_scangame_core::game_setup_needs_path_detection()`.

Bridge DTO shape:

- `needs_game_path`
- `needs_docs_path`

Current behavior:

- empty strings are treated as missing paths
- non-empty strings are treated as present without validation
- this helper answers only whether detection work is needed, not whether the provided paths are valid

---

## Current DTO And Error Pattern

The active bridge mostly uses three patterns.

## 1. Sentinel string / bool returns

Several entry points erase Rust errors and return a default primitive instead:

- empty string on failure: path detection, PE version extraction, XSE version detection
- `false` on failure: XSE installed check for invalid type strings, path validation miss, restricted-path false branch

This is the dominant fail-soft style in the bridge.

## 2. Small DTOs with explicit `found` or `valid`

Registry and parsing calls often return structs that keep a success bit alongside partial payload fields:

- `VersionInfoDto.found`
- `XseConfigDto.found`
- `GameVersionDto.valid`

Those DTOs still flatten the underlying Rust models heavily.

## 3. Rendered text plus typed setup DTOs

`classic::scangame::run_game_setup_intake()` and `run_game_setup_intake_from_user_settings()` return Rust-rendered report text, summary counts, the resolved executable, and ordered typed path proposals for caller review. UTF-8-representable paths cross exactly; other native paths use the CXX bridge's established lossy string transport. Returning a proposal does not preview or persist User Settings.

`classic::scangame::game_setup_intake_checks()` exposes typed check records for callers that need structured state and propagates intake setup errors.

---

## Where The Bridge Narrows The Rust APIs

These are the main current narrowing points contributors should keep in mind.

## `src/path.rs`

- hardcodes Fallout 4 / Fallout 4 VR only
- does not let callers require XSE loader presence during game-root detection
- does not let callers supply an XSE log path
- does not expose document INI validation or document diagnostics

## `src/game.rs`

- returns only slices of `VersionInfo`, `XseConfig`, `CrashgenConfig`, and `MatchResult`
- collapses typed errors into empty strings, `false`, or message text
- exposes generic game-path lookup, but not the richer validators like `validate_settings_paths()`
- exposes XSE loader presence and DLL-filename version detection, but not `get_xse_info()` and not Address Library validation

## `src/scangame.rs`

- exposes Game Setup Intake as the setup-time bridge surface
- keeps ENB, crashgen, BA2, Wrye, INI, and integrity helper entry points separate from intake
- does not expose `GameScanOrchestrator` or full mod-scan orchestration through CXX

---

## Contributor Debugging Notes

## Path flow

When C++ path detection looks wrong, check these in order:

1. confirm whether the frontend is calling `classic::path::*` or `classic::game::find_game_path()`
2. check whether the bridge passed an empty cached path, empty XSE log path, or empty loader name
3. remember that `classic::path::detect_fallout4_game_path()` never validates `f4se_loader.exe`
4. if using `classic::game::find_game_path()`, inspect whether `GamePathFinder` was constructed with an `xse_loader`; that changes validation requirements
5. if XSE-log fallback should have worked, inspect the log for a `plugin directory = ...` line and the expected `Data/.../Plugins` depth

## Game / registry flow

When registry-backed data looks incomplete:

1. check whether the bridge entry point intentionally omits the field you expected
2. verify the version ID exists through `version_registry_get_by_id()` first
3. remember that `version_registry_get_xse_config()` does not expose `script_hashes`
4. remember that `version_registry_match_version()` returns stringified confidence and message text, not the full `MatchResult`

## XSE flow

When XSE output looks inconsistent:

1. confirm whether the input path is a loader path or a game root; the bridge uses both shapes in different functions
2. check whether the frontend passed a valid XSE type string
3. remember that `is_xse_installed_check()` only checks loader existence
4. remember that `detect_xse_version_string()` depends on sibling DLL filenames, not PE metadata or registry expectations
5. if install is true but version is empty, that is source-backed behavior in lower layers; loader detection and version detection are separate

## Game Setup Intake flow

When `run_game_setup_intake()` output looks wrong:

1. check the `status`, `action_count`, and typed checks before reading the rendered report text
2. confirm the frontend passed the expected `GameId` string and selected version
3. confirm empty strings were intended to mean missing optional paths
4. inspect whether the relevant typed check is `Failed`, `ActionRequired`, `Skipped`, or `Unsupported`
5. debug `classic-scangame-core::game_setup_intake` before adding bridge-side setup logic

---

## Source-Backed Limits And Caveats

- `src/path.rs` and `src/game.rs` both expose game-path detection, but only `src/game.rs` is generic and XSE-log-aware
- `src/path.rs::detect_fallout4_game_path()` constructs `GamePathFinder` without an XSE loader, so it can accept a Fallout 4 root that lacks `f4se_loader.exe`
- `src/path.rs` exposes no document validation beyond discovery
- `src/game.rs::validate_path()` is only `Path::exists()` through `classic_path_core::is_valid_path()`
- `src/game.rs::check_restricted_path()` reflects the current heuristic `classic-path-core` restriction rules, including shallow-path rejection
- `src/game.rs::detect_xse_version_string()` expects a loader path even though the parameter name is `exe_path`
- `src/game.rs` stringifies many failures as `""`; C++ callers cannot recover typed causes without adding new bridge surface
- `src/game.rs::version_registry_get_xse_config()` drops `script_hashes`, so callers cannot build script-hash validation from this DTO alone
- `src/scangame.rs::run_game_setup_intake()` collapses invalid `game_id` into a fatal DTO instead of exposing a typed Rust parse error
- `src/scangame.rs::game_setup_intake_checks()` recomputes intake separately from `run_game_setup_intake()` and returns a CXX `Result` on setup errors; keep callers aware if they call both
- Game Setup Intake is setup-only; ENB, crashgen, Wrye, BA2, loose-file, and mod INI checks remain separate bridge calls

These are current behavior notes, not recommendations for future design.

---

## Contributor Rule Of Thumb

- If you need Fallout 4-only auto-detection convenience, start in `src/path.rs`.
- If you need registry metadata, generic path lookup, PE version reads, or XSE loader/version probing, start in `src/game.rs`.
- If you need setup-time intake diagnostics or a cheap missing-path gate, start in `src/scangame.rs`.
- If you need richer Rust behavior than the bridge exposes, change the bridge intentionally and document the new boundary in this file and the crate-level docs in the same change.
