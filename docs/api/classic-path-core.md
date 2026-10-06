# `classic-path-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-path-core/`](../../business-logic/classic-path-core).

Crate metadata:

- Crate: `classic-path-core`
- Description: `Core path management for CLASSIC (game paths, documents, validation, backups)`

This crate is the shared Rust path/setup helper layer for CLASSIC. It covers game-install detection, documents-folder detection, Game/Documents settings-path validation, lightweight INI parsing, read-only documents checks, the per-user YAML and app-notification cache directories, and versioned file backups.

The generic path primitives it builds on - existence, file/directory, permission, drive, and read-only checks, the OS cache root, and the `PathError` they report - are owned by [`classic-shared-core::path_core`](classic-shared-core.md#generic-path-primitives-path_core) (#245). This crate does not re-export them; see [Moved primitives](#moved-primitives) for the old-to-new import map.

The custom-scan folder policy - `is_restricted_path()`, `validate_custom_scan_path()`, and the combined `validate_settings_paths()` check - is owned by [`classic-scanlog-core::custom_scan`](classic-scanlog-core.md#custom-scan-folder-policy) (#254 follow-up). Scanlog depends on this crate, so path core neither depends on nor re-exports it; see [Moved custom-scan policy](#moved-custom-scan-policy).

It is a synchronous business-logic crate. It does not own a Tokio runtime, UI surface, or binding layer.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- resolve or validate a game installation path
- resolve or validate a game documents folder
- check common CLASSIC path inputs such as the Game/Documents settings paths and required files
- parse Bethesda-style INI files with case-insensitive section/key lookup
- run read-only checks over the documents folder before setup or scanning
- create version-labeled backups using version data extracted from an XSE log

Do not use this crate for:

- generic existence, file/directory, permission, drive, or read-only checks - use `classic_shared_core::path_core`
- custom-scan folder policy (restricted-path rejection, custom-scan validation, the combined settings-path check) - use `classic_scanlog_core::custom_scan`
- loading YAML settings or version-registry metadata
- async file I/O or runtime ownership
- higher-level game scan orchestration
- binding-specific wrapper APIs

Those concerns live in related crates such as [`classic-config-core`](../../business-logic/classic-config-core), [`classic-scangame-core`](../../business-logic/classic-scangame-core), and the C++/Node/Python binding crates.

---

## Module And API Map

All contributor-facing APIs are re-exported from `src/lib.rs`; the internal modules themselves are private.

### Path and detection APIs

- `GamePathFinder` - multi-strategy game install detection and validation
- `parse_xse_log()` - standalone XSE log parser that extracts the game root from `plugin directory = ...`
- `DocsPathFinder` - multi-strategy documents-folder detection and INI presence validation
- `get_system_documents_path()` - platform-specific system documents helper re-exported from `platform`
- `parse_steam_library()` - Steam library lookup helper re-exported from `platform`

### Validation APIs

- `validate_settings_path()` - one settings path, optionally with required files
- `validate_game_and_documents_paths()` - Game Path (with executable) then Documents Path settings validation
- `validate_required_files()` - directory plus required-entry presence check

### Cache directory APIs

- `notification_cache_dir()`, `ensure_notification_cache_dir()` (plus `_with_env` forms) - per-user `CLASSIC/app-notification/<owner>/<repo>` directory

It resolves its root through `classic_shared_core::path_core::user_cache_root_with_env()` and words its own failure, so its `PathError::InvalidPath` message (`... cannot resolve notification cache directory`) is unchanged.

The per-user YAML Data cache (`CLASSIC/yaml-cache`) is YAML file policy and moved to [`classic-config-core`](classic-config-core.md#yaml-cache-location) in issue #246 (`classic_config_core::yaml_cache_dir` and friends). This crate no longer resolves or re-exports it; the old `classic_path_core::yaml_cache_dir` paths ended without a forwarding re-export, because path must not point up into config.

### Documents and INI APIs

- `IniFile` - parsed INI wrapper with case-insensitive section/key lookup
- `DocumentsChecker` - read-only documents-folder checker
- `DocumentsCheckResult` / `DocumentsCheckState` - Rust-only rendered documents messages with structured state
- `IniCheckResult` - structured result for one INI check, also exposed by the Python binding

### Backup APIs

- `BackupManager` - version-aware backup creation/listing
- `XseVersion` - extracted XSE/runtime version wrapper used in backup paths

### Error APIs

- `ValidationError`, `GamePathError`, `DocsPathError`, `BackupError`
- `ValidationResult<T>`, `GamePathResult<T>`, `DocsPathResult<T>`, `BackupResult<T>`

Each domain error wraps the shared-core `PathError` through a `PathError(#[from] classic_shared_core::path_core::PathError)` variant.

### Windows-only root re-exports

- `query_game_registry()` - direct Windows registry lookup for game installs

### Moved primitives

These root exports ended in #245; import them from `classic_shared_core::path_core` instead. Values, error variants, and messages are unchanged.

| Old `classic_path_core::` path | New `classic_shared_core::path_core::` path |
| --- | --- |
| `is_valid_path`, `validate_path_exists`, `validate_is_directory`, `validate_is_file` | same names |
| `check_drive_exists`, `check_read_permissions`, `check_write_permissions`, `validate_path_with_permissions` | same names |
| `drive_exists`, `has_read_permission`, `has_write_permission` | same names |
| `remove_readonly_attribute`, `remove_readonly` (Windows only) | same names |
| `is_valid_executable_path` | `is_executable_file_path` (renamed so it cannot be confused with the different `classic_shared_core::version::pe_version::is_valid_executable_path`) |
| `PathError`, `PathResult` | same names |

The CXX, Node, and Python path adapters keep their existing export names (`is_valid_path`, `isValidExecutablePath`, `PathValidator.is_valid_executable_path`, `removeReadonly`, ...) and delegate to the shared-core owner.

### Moved custom-scan policy

These root exports ended in the #254 follow-up; import them from `classic_scanlog_core` (root re-exports of `classic_scanlog_core::custom_scan`) instead. They still return `classic_path_core::ValidationResult<()>`, so the `ValidationError` variants (including `RestrictedPath`) and messages are unchanged.

| Old `classic_path_core::` path | New path |
| --- | --- |
| `is_restricted_path`, `validate_custom_scan_path` | `classic_scanlog_core::` same names |
| `validate_settings_paths(game, docs, custom_scan, game_exe)` | `classic_scanlog_core::validate_settings_paths` (same signature); its Game/Documents half is `classic_path_core::validate_game_and_documents_paths(game, docs, game_exe)` |

The CXX (`is_restricted_path`, `check_restricted_path`, `path_validate_custom_scan`), Node (`isRestrictedPath`, `validateCustomScanPath`, `validateSettingsPaths`), and Python (`PathValidator.is_restricted_path`, `PathValidator.validate_custom_scan_path`, `PathValidator.validate_settings_paths`) exports keep their names and namespaces and delegate to the scanlog owner.

Contributor note:

- there are no public traits in the crate today
- `platform` is not a public module even though a few helpers are re-exported from it

---

## Public API Surface

## `GamePathFinder`

`GamePathFinder` is the main install-path entry point.

Construction:

- `GamePathFinder::new(game_exe, xse_loader, game_name, is_vr)`

Important methods:

- `find_game_path(cached_path, xse_log_path) -> GamePathResult<PathBuf>`
- `find_via_xse_log(log_path) -> GamePathResult<PathBuf>`
- `validate_game_path(path) -> GamePathResult<()>`
- accessors: `game_exe()`, `xse_loader()`, `is_vr()`

Behavior visible in source:

- `find_game_path()` tries cached path first, then Windows registry on Windows builds, then XSE log parsing
- there is no built-in user prompt or fallback callback; if all strategies fail, the API returns `GamePathError::NotFound`
- validation checks only that the directory contains the configured executable and optional XSE loader
- Windows registry lookup adds a `" VR"` suffix for VR installs and only enables the GOG fallback for `Fallout4`

## `parse_xse_log()`

`parse_xse_log(log_path)` is the standalone parser used by `GamePathFinder`.

- looks for `plugin directory = ...` or `plugin directory=...`
- trims optional surrounding quotes
- assumes the discovered directory ends at `Data/F4SE/Plugins`-style depth and pops three path components to reach the game root
- returns `GamePathError::XseLogParseError` if that shape is missing or the marker line is absent

That fixed `pop()` behavior is an important contributor assumption: if future XSE log formats change, this parser and its docs need to change together.

## `DocsPathFinder`

`DocsPathFinder` is the documents-folder discovery helper.

Construction:

- `DocsPathFinder::new(relative_path)` where `relative_path` is typically a game-specific path such as `My Games\\Fallout4`

Important methods:

- `find_docs_path(cached_path) -> DocsPathResult<PathBuf>`
- `with_steam_app_id(app_id: u32) -> Self (consuming builder)`
- `validate_docs_path(path) -> DocsPathResult<()>`
- `validate_ini_files(docs_path, required_inis) -> DocsPathResult<()>`
- `relative_path() -> &str`

Behavior visible in source:

- `find_docs_path()` tries the cached string path first
- on Windows it queries the registry-backed documents folder and appends `relative_path`
- on non-Windows builds it uses `home/.local/share/<relative_path>` by default; if the caller opted in via `DocsPathFinder::with_steam_app_id(app_id)`, the finder first tries a Steam/Proton documents path built from the Steam library metadata for that app ID and falls back to the legacy `.local/share` location if the Proton lookup fails or the Proton path is invalid. Callers that do not opt in get NO Proton lookup at all, so a generic non-Fallout-4 consumer no longer implicitly probes Fallout 4's `compatdata/377160` prefix.
- `validate_ini_files()` checks existence and then parses each required INI via `IniFile::load()`

## Validation helpers

The free functions in `validator.rs` are the crate's Game/Documents settings-path guardrails. They build on the shared-core generic primitives (`validate_is_directory()` and friends). The custom-scan restriction guardrails live in [`classic-scanlog-core`](classic-scanlog-core.md#custom-scan-folder-policy).

Most-used functions:

- `validate_required_files(directory, required_files)` - directory plus required-entry presence check
- `validate_settings_path(path, setting_name, required_files)` - existence check, plus directory and required-file checks when `required_files` is given
- `validate_game_and_documents_paths(game_path, docs_path, game_exe)` - validates `"Game Path"` (must contain `game_exe`) and then `"Documents Path"`, returning the first `ValidationError`

Behavior worth knowing:

- a missing settings path surfaces as `ValidationError::ValidationFailed { setting, reason: "Path does not exist: ..." }`
- a missing directory surfaces as `ValidationError::PathError(PathError::NotFound(..))`, and a file where a directory was expected as `ValidationError::PathError(PathError::NotADirectory(..))`

Contributor note:

- these helpers are synchronous and directly touch the filesystem; callers should not assume they are pure string validators

## `IniFile`

`IniFile` is the contributor-facing parsed INI wrapper built on `configparser`.

Important methods:

- `IniFile::load(path) -> DocsPathResult<IniFile>`
- `path()`
- `has_section()`, `has_key()`, `get()`
- `get_int()`, `get_bool()`
- `sections()`, `keys(section)`
- `validate_sections(required_sections)`
- `validate_keys(section, required_keys)`

Behavior worth knowing:

- `configparser` normalizes section and key names to lowercase
- section lookup is explicitly lowercased in this wrapper, so section access is case-insensitive
- `get_bool()` accepts `1/0`, `true/false`, `yes/no`, and `on/off`
- `sections()` and `keys()` return lowercase names because that is what the underlying parser stores
- invalid path encoding for `path.to_str()` becomes `DocsPathError::IniParseError`

## `DocumentsChecker` and `IniCheckResult`

`DocumentsChecker` is the read-only documents validation layer used by setup workflows.

Construction:

- `DocumentsChecker::new(game_name)`

Important Rust methods:

- `check_onedrive_in_path(docs_path) -> Option<String>`
- `check_onedrive_in_path_result(docs_path) -> Option<DocumentsCheckResult>`
- `validate_ini_file(docs_path, ini_name) -> DocsPathResult<IniCheckResult>`
- `run_all_check_results(docs_path) -> DocsPathResult<Vec<DocumentsCheckResult>>`
- `run_all_checks(docs_path) -> DocsPathResult<Vec<String>>`
- `game_name()`

Python `classic_path.DocumentsChecker` exposes the string-oriented surface only:

- `check_onedrive_in_path(docs_path) -> str | None`
- `validate_ini_file(docs_path, ini_name) -> IniCheckResult`
- `run_all_checks(docs_path) -> list[str]`
- `game_name`

`DocumentsCheckResult` fields:

- `state: DocumentsCheckState`
- `message`

`IniCheckResult` fields:

- `ini_name`, `exists`, `is_valid`, `message`, `issue`
- helpers: `has_issue()`, `state()`

Behavior worth knowing:

- missing or corrupted INIs are reported as successful `Ok(IniCheckResult)` values with `issue` populated; they are not treated as hard errors
- `run_all_check_results()` and its string-only `run_all_checks()` wrapper currently check only three files: `{Game}.ini`, `{Game}Custom.ini`, and `{Game}Prefs.ini`
- for `{Game}Custom.ini`, the checker requires an `[Archive]` section to consider archive invalidation enabled
- OneDrive detection is a simple case-insensitive substring search over the path string

## `XseVersion` and `BackupManager`

These types provide the crate's backup workflow.

`XseVersion`:

- `XseVersion::new(version)`
- `full_version()`
- `sanitized()` - replaces `.` with `_` for directory names

`BackupManager`:

- `BackupManager::new(backup_root)`
- `extract_version_from_xse_log(xse_log_path) -> BackupResult<XseVersion>`
- `create_backup(source_file, version) -> BackupResult<PathBuf>`
- `backup_root()`
- `list_versions() -> BackupResult<Vec<String>>`
- `get_version_path(version) -> PathBuf`

Behavior worth knowing:

- version extraction uses a regex matching either `version = ...` or `runtime version = ...`
- extraction returns the first matching version line in the file
- `create_backup()` stores files under `backup_root/<version_with_underscores>/<filename>`
- `create_backup()` copies one file at a time; it does not back up directory trees or store extra metadata beyond the version-based path layout
- `list_versions()` returns sorted directory names and silently returns an empty list if the backup root does not exist yet

---

## Path Resolution, Validation, And Backup Flow

The main source-visible flows are:

## Game-path flow

1. Construct `GamePathFinder` with the expected executable, optional XSE loader, game name, and VR flag.
2. Call `find_game_path(cached_path, xse_log_path)`.
3. The crate tries, in order:
   - provided cached path
   - Windows registry lookup on Windows builds
   - XSE log parsing if a log path was provided
4. Each candidate is validated by checking for the required executable and optional loader.
5. On success the validated `PathBuf` is returned; otherwise the API returns `GamePathError::NotFound`.

## Documents-path flow

1. Construct `DocsPathFinder` with a game-relative documents suffix such as `My Games\\Fallout4`.
2. Optionally call `.with_steam_app_id(app_id)` to opt in to a Steam/Proton documents path lookup on Linux (for Fallout 4, pass `377160` or use `Fallout4Version::Original.steam_app_id()` from `classic-version-registry-core`).
3. Call `find_docs_path(cached_path)`.
4. The crate tries the cached path first.
5. It then falls back to:
   - Windows registry documents path plus the relative suffix on Windows
   - on non-Windows builds: if a Steam app ID was set via `with_steam_app_id`, the finder first tries the Steam/Proton compatdata path for that app ID; if no app ID is set or the Proton lookup fails, it falls back to `home/.local/share/<relative_path>`
6. Optional follow-up validation can call `validate_ini_files()` for required INIs.

## Setup validation flow

1. Validate base filesystem facts with the shared-core `validate_path_exists()` / `validate_is_directory()`, or with `validate_required_files()` here.
2. For user-provided scan targets, call scanlog core's `validate_custom_scan_path()` to reject system or root-like locations.
3. For Game/Documents setup checks, call `validate_game_and_documents_paths()` here; scanlog core's `validate_settings_paths()` adds the optional custom-scan folder after it. Use the shared-core `validate_path_with_permissions()` when the caller needs permission checks rather than required-file checks.
4. For documents-specific checks, build `DocumentsChecker` and call `run_all_checks()`.

## Backup flow

1. Construct `BackupManager` with a backup root.
2. Call `extract_version_from_xse_log()` to build an `XseVersion` from an XSE log.
3. Call `create_backup(source_file, &version)`.
4. The file is copied to `backup_root/<sanitized_version>/<filename>`.
5. Call `list_versions()` or `get_version_path()` later to inspect the stored backup layout.

---

## Error Handling Model

This crate uses several domain-specific error enums rather than one shared top-level error type.

## `PathError`

Owned by `classic_shared_core::path_core` (see [its guide](classic-shared-core.md#generic-path-primitives-path_core)). This crate reports it from the cache-directory resolvers and wraps it in every domain error below.

## `ValidationError`

Used by higher-level validation helpers, including the custom-scan policy in `classic-scanlog-core`.

Variants:

- `RestrictedPath(PathBuf)` - reported only by scanlog core's custom-scan policy; kept here so its type and message are unchanged for every caller
- `RequiredFileNotFound { path, file }`
- `ValidationFailed { setting, reason }`
- `PathError(PathError)` via `#[from]`

## `GamePathError`

Used by game-install detection.

Important variants include:

- `NotFound`
- `RegistryNotFound`, `RegistryError(String)`
- `XseLogNotFound(PathBuf)`, `XseLogReadError { .. }`, `XseLogParseError(String)`
- `ExecutableNotFound { .. }`, `XseFileNotFound { .. }`
- `ValidationFailed(String)`
- `UserCancelled`, `InvalidPath(String)`
- `PathError(PathError)` and `IoError(std::io::Error)`

Source-observed note:

- `GamePathFinder::validate_game_path()` currently converts directory/file validation failures into `GamePathError::ValidationFailed(String)` instead of preserving the more specific `ExecutableNotFound` or `XseFileNotFound` variants

## `DocsPathError`

Used by documents-path, INI, and checker APIs.

Important variants include:

- `NotFound`
- `RegistryError(String)`
- `SteamLibraryNotFound(PathBuf)`, `SteamLibraryParseError(String)`, `GameNotInSteamLibrary(u32)`
- `IniValidationFailed { ini, reason }`
- `IniParseError { path, reason }`
- `UserCancelled`
- `PathError(PathError)` and `IoError(std::io::Error)`

## `BackupError`

Used by backup APIs.

Variants:

- `XseLogNotFound(PathBuf)`
- `VersionNotFound`
- `InvalidVersionFormat(String)`
- `CreateDirectoryFailed { path, source }`
- `CopyFileFailed { src, dst, source }`
- `SourceNotFound(PathBuf)`
- `PathError(PathError)` and `IoError(std::io::Error)`

Contributor note:

- `DocumentsChecker` intentionally mixes hard and soft failures: missing/corrupted INIs become `IniCheckResult` issues, while actual I/O/parsing operations still use `DocsPathError`

---

## Platform-Specific Notes

- Windows builds expose an extra root-level API: `query_game_registry()`
- `GamePathFinder` registry lookup exists only on Windows; non-Windows builds skip that strategy entirely
- `DocsPathFinder` uses the registry-backed `Personal` folder on Windows
- `get_system_documents_path()` returns the Windows documents folder on Windows, but only the home directory on Linux
- `parse_steam_library()` is useful only on Linux; the Windows stub returns `DocsPathError::NotFound`
- the crate has Windows and Linux implementations in source, but no macOS-specific implementation today

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `classic-shared-core` - generic path primitives, `PathError`, and the OS cache root
- `winreg` - Windows registry queries for game and documents paths
- `dirs` - home-directory discovery on non-Windows builds
- `configparser` - INI parsing with lowercase-normalized section/key maps
- `regex` - XSE/runtime version extraction from logs
- `thiserror` and `anyhow` - error ergonomics

Related CLASSIC crates and consumers:

- [`classic-scangame-core`](../../business-logic/classic-scangame-core) - uses `DocumentsChecker` in setup-time combined checks
- [`classic-config-core`](../../business-logic/classic-config-core) - neighboring config loader that supplies path settings but does not replace this crate's validation logic
- [`classic-xse-core`](../../business-logic/classic-xse-core) - uses `DocsPathFinder` for XSE folder derivation
- [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) - owns the custom-scan folder policy and composes `validate_game_and_documents_paths()` into its combined `validate_settings_paths()`
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - uses `GamePathFinder`, the documents checker, and backups for C++ interop
- [`classic-update-core`](../../business-logic/classic-update-core) - consumes the app-notification cache directory (the YAML Data cache directory is config-owned since issue #246)
- [`classic-node`](../../node-bindings/classic-node) and [`classic-path-py`](../../python-bindings/classic-path-py) - binding surfaces over this crate's APIs
- [`classic-tui`](../../ui-applications/classic-tui) - uses `DocsPathFinder` for local path discovery

In practice, `classic-path-core` sits between config-driven path settings and higher-level scan/setup orchestration.

---

## Usage Example

This example follows the current public API and shows the common contributor flow: resolve a game path, resolve documents, then run documents checks.

```rust
use classic_path_core::{DocsPathFinder, DocumentsChecker, GamePathFinder};
use std::path::PathBuf;

let game_finder = GamePathFinder::new(
    "Fallout4.exe",
    Some("f4se_loader.exe"),
    "Fallout4",
    false,
);

let game_path = game_finder.find_game_path(
    Some(PathBuf::from("C:/Games/Fallout4")).as_deref(),
    None,
)?;

let docs_finder = DocsPathFinder::new(r"My Games\Fallout4");
let docs_path = docs_finder.find_docs_path(None)?;

let checker = DocumentsChecker::new("Fallout4");
let messages = checker.run_all_checks(&docs_path)?;

println!("Game: {}", game_path.display());
for message in messages {
    println!("{message}");
}
# Ok::<(), classic_path_core::DocsPathError>(())
```

If the caller only needs the raw XSE-derived path, use `parse_xse_log()` directly and then run `GamePathFinder::validate_game_path()` separately.

---

## Contributor Notes And Known Limits

- `src/lib.rs` re-exports the public surface; internal modules are private
- `DocsPathFinder`'s Linux Proton lookup is opt-in via `with_steam_app_id(app_id)`; the default is `home/.local/share/...` only. Game-specific callers like the CXX bridge's `detect_fallout4_docs_path` and the TUI's `resolve_xse_folder_for_scan` opt in with `Fallout4Version::Original.steam_app_id()` (377160).
- `parse_xse_log()` assumes a fixed `.../Data/XSE/Plugins`-style suffix and pops exactly three path components
- `DocumentsChecker::run_all_check_results()` ignores per-file `Err` results internally and only appends messages from successful `validate_ini_file()` calls; `run_all_checks()` preserves the historical string-only wrapper
- `GamePathError` includes `ExecutableNotFound` and `XseFileNotFound`, but the current `GamePathFinder` implementation does not construct those variants during its normal validation path
- some public error variants such as `UserCancelled` are part of the API surface even though the current Rust crate does not include an interactive prompt path that returns them
- user-facing warning strings in `DocumentsChecker` currently include emoji; contributors changing message text should treat that as public behavior for bindings and setup reports, while structured callers should use `DocumentsCheckState` instead of parsing those strings

If you extend this crate, update this document when you change:

- root re-exports in `src/lib.rs`
- game-path or documents-path strategy order
- the opt-in rules for the Linux Proton documents lookup
- Game/Documents settings-path validation order or setting names
- INI parsing assumptions or case-normalization behavior
- documents-check message/report rules
- backup directory layout or XSE version extraction behavior
