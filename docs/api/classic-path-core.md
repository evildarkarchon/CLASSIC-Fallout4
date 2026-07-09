# `classic-path-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-path-core/`](../../business-logic/classic-path-core).

Crate metadata:

- Crate: `classic-path-core`
- Description: `Core path management for CLASSIC (game paths, documents, validation, backups)`

This crate is the shared Rust path/setup helper layer for CLASSIC. It covers game-install detection, documents-folder detection, general path validation, lightweight INI parsing, read-only documents checks, and versioned file backups.

It is a synchronous business-logic crate. It does not own a Tokio runtime, UI surface, or binding layer.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- resolve or validate a game installation path
- resolve or validate a game documents folder
- check common CLASSIC path inputs such as custom-scan folders and required files
- parse Bethesda-style INI files with case-insensitive section/key lookup
- run read-only checks over the documents folder before setup or scanning
- create version-labeled backups using version data extracted from an XSE log

Do not use this crate for:

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

- `is_valid_path()`, `validate_path_exists()`, `validate_is_directory()`, `validate_is_file()`
- `validate_required_files()`, `validate_custom_scan_path()`, `validate_settings_path()`, `validate_settings_paths()`
- `is_valid_executable_path()`
- `check_drive_exists()`, `check_read_permissions()`, `check_write_permissions()`, `validate_path_with_permissions()`
- `drive_exists()`, `has_read_permission()`, `has_write_permission()` - boolean wrappers over the stricter checks
- `remove_readonly_attribute()` - cross-platform read-only clearing helper

### Documents and INI APIs

- `IniFile` - parsed INI wrapper with case-insensitive section/key lookup
- `DocumentsChecker` - read-only documents-folder checker
- `DocumentsCheckResult` / `DocumentsCheckState` - Rust-only rendered documents messages with structured state
- `IniCheckResult` - structured result for one INI check, also exposed by the Python binding

### Backup APIs

- `BackupManager` - version-aware backup creation/listing
- `XseVersion` - extracted XSE/runtime version wrapper used in backup paths

### Error APIs

- `PathError`, `ValidationError`, `GamePathError`, `DocsPathError`, `BackupError`
- `PathResult<T>`, `ValidationResult<T>`, `GamePathResult<T>`, `DocsPathResult<T>`, `BackupResult<T>`

### Windows-only root re-exports

- `query_game_registry()` - direct Windows registry lookup for game installs
- `remove_readonly()` - Windows-specific best-effort read-only clearing helper

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

The free functions in `validator.rs` are the crate's low-level path guardrails.

Most-used functions:

- `validate_required_files(directory, required_files)` - directory plus required-entry presence check
- `validate_custom_scan_path(path)` - directory check plus restricted-path guard
- `validate_settings_paths(game_path, docs_path, custom_scan_path, game_exe)` - combined setup validation helper
- `validate_path_with_permissions(path, check_read, check_write)` - existence plus optional permission checks

Behavior worth knowing:

- `is_restricted_path()` uses substring checks against names like `windows`, `program files`, `system32`, and `appdata`
- `is_restricted_path()` also treats very shallow paths and roots as restricted when `parent().is_none()` or component count is `<= 2`
- `check_write_permissions()` probes writability by creating and deleting `.classic_test_write`
- `check_drive_exists()` is meaningful only on Windows; other platforms always return `Ok(())`
- `remove_readonly_attribute()` is a no-op on non-Windows builds

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

1. Validate base filesystem facts with `validate_path_exists()`, `validate_is_directory()`, or `validate_required_files()`.
2. For user-provided scan targets, call `validate_custom_scan_path()` to reject system or root-like locations.
3. For combined setup checks, call `validate_settings_paths()` or `validate_path_with_permissions()` depending on whether the caller needs required-file checks or permission checks.
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

Used by the low-level path validators and permission helpers.

Variants:

- `NotFound(PathBuf)`
- `NotADirectory(PathBuf)`
- `NotAFile(PathBuf)`
- `IoError { path, source }`
- `PermissionDenied(String)`
- `InvalidPath(String)`

## `ValidationError`

Used by higher-level validation helpers.

Variants:

- `RestrictedPath(PathBuf)`
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

- Windows builds expose extra root-level APIs: `query_game_registry()` and `remove_readonly()`
- `GamePathFinder` registry lookup exists only on Windows; non-Windows builds skip that strategy entirely
- `DocsPathFinder` uses the registry-backed `Personal` folder on Windows
- `get_system_documents_path()` returns the Windows documents folder on Windows, but only the home directory on Linux
- `parse_steam_library()` is useful only on Linux; the Windows stub returns `DocsPathError::NotFound`
- `remove_readonly_attribute()` is a no-op on non-Windows platforms
- the crate has Windows and Linux implementations in source, but no macOS-specific implementation today

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `winreg` - Windows registry queries for game and documents paths
- `dirs` - home-directory discovery on non-Windows builds
- `configparser` - INI parsing with lowercase-normalized section/key maps
- `regex` - XSE/runtime version extraction from logs
- `thiserror` and `anyhow` - error ergonomics

Related CLASSIC crates and consumers:

- [`classic-scangame-core`](../../business-logic/classic-scangame-core) - uses `DocumentsChecker` in setup-time combined checks
- [`classic-config-core`](../../business-logic/classic-config-core) - neighboring config loader that supplies path settings but does not replace this crate's validation logic
- [`classic-xse-core`](../../business-logic/classic-xse-core) - converts or reuses `PathError` in its own error model
- [`classic-resource-core`](../../business-logic/classic-resource-core) - re-exports `PathError` and `PathResult`
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - uses `GamePathFinder`, `is_valid_path()`, and `is_restricted_path()` for C++ interop
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
- `is_restricted_path()` is heuristic string matching, not a canonicalized allow/deny policy
- `check_write_permissions()` writes a temporary `.classic_test_write` file into the target directory
- `DocumentsChecker::run_all_check_results()` ignores per-file `Err` results internally and only appends messages from successful `validate_ini_file()` calls; `run_all_checks()` preserves the historical string-only wrapper
- `GamePathError` includes `ExecutableNotFound` and `XseFileNotFound`, but the current `GamePathFinder` implementation does not construct those variants during its normal validation path
- some public error variants such as `UserCancelled` are part of the API surface even though the current Rust crate does not include an interactive prompt path that returns them
- user-facing warning strings in `DocumentsChecker` currently include emoji; contributors changing message text should treat that as public behavior for bindings and setup reports, while structured callers should use `DocumentsCheckState` instead of parsing those strings

If you extend this crate, update this document when you change:

- root re-exports in `src/lib.rs`
- game-path or documents-path strategy order
- the opt-in rules for the Linux Proton documents lookup
- restricted-path heuristics or permission-probe behavior
- INI parsing assumptions or case-normalization behavior
- documents-check message/report rules
- backup directory layout or XSE version extraction behavior
