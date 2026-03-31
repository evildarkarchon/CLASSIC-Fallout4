# Game Setup Workflow

Contributor-facing workflow notes for setup and install validation across:

- [`classic-path-core`](../../ClassicLib-rs/business-logic/classic-path-core)
- [`classic-xse-core`](../../ClassicLib-rs/business-logic/classic-xse-core)
- [`classic-scangame-core`](../../ClassicLib-rs/business-logic/classic-scangame-core)
- [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core)

This page documents the current source-backed split of responsibilities for setup-time validation work in CLASSIC.

It does **not** describe a future unified setup pipeline. Today, contributors still need to understand how several crates fit together.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to understand how CLASSIC currently handles:

- game-path and documents-path detection
- basic install-path validation
- script-extender loader and version probing
- Address Library validation
- setup-time executable and documents checks
- where registry-backed version metadata enters the flow

This page is about contributor workflow and crate boundaries, not every individual API.

For crate-by-crate API details, see:

- [`classic-path-core.md`](classic-path-core.md)
- [`classic-xse-core.md`](classic-xse-core.md)
- [`classic-scangame-core.md`](classic-scangame-core.md)
- [`classic-version-registry-core.md`](classic-version-registry-core.md)

---

## Current Ownership By Crate

## `classic-path-core`

Owns filesystem-first path discovery and validation:

- `GamePathFinder` for cached-path, Windows-registry, and XSE-log-based game-root detection
- `DocsPathFinder` for cached-path and platform-specific documents-folder detection
- `validate_settings_paths()` and related validators for path existence, required files, and restricted custom-scan paths
- `DocumentsChecker` for read-only documents-folder checks such as OneDrive detection and INI validation

This crate is the entry point when the caller does not yet know where the install or documents folder lives.

## `classic-xse-core`

Owns narrow script-extender probing once the game root is already known:

- `XseType` naming and loader/DLL conventions
- `is_xse_installed()` loader existence checks
- `detect_xse_version()` DLL-filename-based version detection
- `get_xse_info()` for the combined installed/version payload

This crate does **not** discover the game path and does **not** compare against registry-backed compatibility metadata on its own.

## `classic-scangame-core`

Owns higher-level setup/install validation once the caller already has paths and version context:

- `run_combined_checks()` for executable integrity plus documents-folder checks
- `GameIntegrityChecker` for executable hash and install-location checks
- `XseChecker` for Address Library validation in `Data/<XSE>/Plugins`
- `needs_path_detection()` and game-version setting helpers in `setup.rs`

Important current boundary:

- `classic-scangame-core` depends on `classic-path-core` and `classic-version-registry-core`
- it does **not** currently depend on `classic-xse-core`
- `run_combined_checks()` currently runs integrity and documents checks only

## `classic-version-registry-core`

Owns known version metadata and fallback defaults:

- version matching and fallback selection
- Address Library metadata
- XSE metadata such as acronym, loader name, and compatible version strings
- executable hashes and other per-version metadata

This crate usually feeds the setup workflow indirectly: frontends or bridge layers resolve version metadata first, then pass the relevant fields into the path/XSE/scangame calls.

---

## Current Cross-Crate Flow

The current setup/install validation flow is best understood as a staged pipeline.

## 1. Decide Whether Path Detection Is Needed

If the caller already has saved settings, `classic-scangame-core::needs_path_detection()` is the cheap first gate:

- missing or empty `game_path` means game-root detection is still needed
- missing or empty `docs_path` means documents-folder detection is still needed

This helper does not resolve paths itself. It only answers whether detection work is still required.

## 2. Detect Or Validate The Game Root

Use `classic-path-core::GamePathFinder` when the game root may be missing or stale.

Current strategy order in `find_game_path()`:

1. cached path, if provided and valid
2. Windows registry lookup on Windows builds
3. XSE log parsing, if a log path is provided
4. `GamePathError::NotFound` if all strategies fail

`validate_game_path()` checks only for the configured executable and optional loader inside the candidate directory.

Practical implication:

- if you construct the finder with `Some("f4se_loader.exe")`, path validation also requires the loader to exist
- if you construct it without a loader, path validation only proves the game executable is present

## 3. Detect Or Validate The Documents Folder

Use `classic-path-core::DocsPathFinder` for the game's documents folder.

Current strategy order in `find_docs_path()`:

1. cached path, if provided and valid
2. Windows documents registry lookup plus the game-relative suffix on Windows
3. `home/.local/share/<relative_path>` on non-Windows builds
4. `DocsPathError::NotFound` if all strategies fail

After the folder is found, follow-up checks may use:

- `validate_ini_files()` for strict required-INI checks
- `DocumentsChecker::run_all_checks()` for read-only setup diagnostics

## 4. Validate Base Path Inputs

Before higher-level setup checks, callers can use `classic-path-core::validate_settings_paths()` to confirm:

- the game path exists and contains the expected game executable
- the documents path exists
- the optional custom scan path is not a restricted system/root-like path

This is still purely path validation. It does not hash the executable, inspect Address Library, or compare versions.

## 5. Probe Script Extender State From The Game Root

Once the game root is known, `classic-xse-core` becomes useful.

Typical flow:

1. choose an `XseType` explicitly or via `XseType::from_game_id()`
2. call `is_xse_installed()` or `get_xse_info()` with the game root
3. if installed, let `detect_xse_version()` scan sibling DLL filenames for a parseable version

Current behavior to remember:

- installation means only that the expected loader file exists
- version detection uses DLL filenames such as `f4se_1_10_163.dll`
- `get_xse_info()` is fail-soft: it can return `installed = true` and `version = None`

## 6. Resolve Version Registry Metadata

Registry data enters the setup workflow when the caller needs expected metadata, not just observed files.

Current uses include:

- matching a detected executable version to a known registry entry
- selecting Address Library file names and download URLs
- retrieving XSE metadata such as acronym, loader name, and compatible version text
- supplying executable hashes for integrity checks

Today that resolution happens outside the three setup crates more often than inside them.

Examples from current source:

- `classic-scangame-core::xse::AddressLibInfo` consults `get_version_registry()` for Address Library metadata
- C++ bridge code exposes registry lookups and matching separately from path/XSE/setup calls

## 7. Run Setup-Time Install Validation In `classic-scangame-core`

After the caller has assembled the needed inputs, `classic-scangame-core` runs the higher-level checks.

Current split:

- `run_combined_checks()` runs `GameIntegrityChecker` and, when `docs_path` is set, `classic_path_core::DocumentsChecker`
- `XseChecker` separately validates Address Library installation in the plugins directory using VR/non-VR mode and `classic_scangame_core::GameVersion`
- `GameScanOrchestrator::run_game_checks()` also runs `XseChecker` as one sub-check when `plugins_path` is provided

Important current limitation:

- `SetupCheckConfig.xse_hashes` exists in the public struct, but `run_combined_checks()` does not consume it today

That means the current "setup" API is not a single complete XSE/install validator by itself.

---

## Where Inputs Enter The Workflow

## Path Inputs

Path-like inputs enter first and usually come from cached settings, the frontend, or path detection:

- cached `game_path`
- cached `docs_path`
- optional XSE log path for `GamePathFinder`
- optional custom scan path for path validation
- known plugins path for Address Library validation

The core ownership is:

- discovery and basic validation -> [`classic-path-core`](classic-path-core.md)
- loader/version probing from a known game root -> [`classic-xse-core`](classic-xse-core.md)
- install/report checks using already-known paths -> [`classic-scangame-core`](classic-scangame-core.md)

## Version Registry Inputs

Registry-backed data enters once the workflow needs expected metadata rather than raw filesystem facts.

In current source, that includes:

- Address Library filenames and Nexus URLs used by `classic-scangame-core::xse`
- version display strings used in `classic_scangame_core::GameVersion::description()`
- XSE metadata and executable hashes exposed to frontends through separate registry lookups

Contributor rule of thumb:

- if you only need to know what is present on disk, stay in `classic-path-core` or `classic-xse-core`
- if you need to know what *should* be present for a supported version, you are in Version Registry territory

---

## Flow Sketch

This is the current contributor-facing shape of setup/install validation:

```text
saved settings / frontend inputs
        |
        +--> classic-scangame-core::needs_path_detection()
        |
        +--> classic-path-core::GamePathFinder
        |         - cached path
        |         - Windows registry
        |         - XSE log
        |
        +--> classic-path-core::DocsPathFinder
        |         - cached path
        |         - platform-specific fallback
        |
        +--> classic-path-core::validate_settings_paths()
        |
        +--> classic-xse-core::get_xse_info()
        |         - loader present?
        |         - DLL filename version?
        |
        +--> classic-version-registry-core::get_version_registry()
        |         - expected Address Library metadata
        |         - XSE metadata
        |         - exe hashes / version match
        |
        +--> classic-scangame-core
                  - run_combined_checks() for integrity + docs
                  - XseChecker for Address Library validation
```

---

## Grounded Fallout 4 Example

This sketch stays close to the current public Rust surface and shows the split contributors usually need to keep in mind.

```rust,no_run
use classic_constants_core::GameId;
use classic_path_core::{DocsPathFinder, GamePathFinder, validate_settings_paths};
use classic_scangame_core::{GameVersion as ScanGameVersion, XseChecker};
use classic_xse_core::{XseType, get_xse_info};
use std::path::Path;

let game_root = GamePathFinder::new(
    "Fallout4.exe",
    Some("f4se_loader.exe"),
    "Fallout4",
    false,
)
.find_game_path(None, Some(Path::new(r"C:\Users\Name\Documents\My Games\Fallout4\F4SE\f4se.log")))?;

let docs_root = DocsPathFinder::new(r"My Games\Fallout4").find_docs_path(None)?;

validate_settings_paths(&game_root, &docs_root, None, "Fallout4.exe")?;

let xse_type = XseType::from_game_id(GameId::Fallout4);
let xse_info = get_xse_info(&game_root, xse_type);

println!("Installed: {}", xse_info.installed);
println!("Detected XSE version: {:?}", xse_info.version);

let plugins_path = game_root.join("Data").join("F4SE").join("Plugins");
let address_lib_result = XseChecker::new(&plugins_path, false, ScanGameVersion::Original)?
    .check();

println!("Address Library result: {:?}", address_lib_result);
# Ok::<(), Box<dyn std::error::Error>>(())
```

What this example intentionally shows:

- path detection and path validation happen before XSE probing
- loader/version probing uses `classic-xse-core`
- Address Library validation uses `classic-scangame-core::XseChecker`, not `classic-xse-core`
- the caller still has to decide which `classic_scangame_core::GameVersion` to use

That last point is one of the main contributor friction points today.

---

## Common Contributor Confusion Points

## "Why doesn't `run_combined_checks()` cover all XSE validation?"

Because current source does not do that.

- `run_combined_checks()` runs integrity checks and documents checks
- `SetupCheckConfig.xse_hashes` is currently unused
- Address Library validation still lives in `XseChecker`
- loader/version probing still lives in `classic-xse-core`

## "Why are there two different XSE-related crates?"

They validate different things.

- [`classic-xse-core`](classic-xse-core.md) checks script-extender loader presence and tries to detect the XSE version from DLL filenames
- [`classic-scangame-core`](classic-scangame-core.md) `XseChecker` checks for the correct Address Library file in the plugins directory

They are related, but they are not the same validation step.

## "Where do expected loader names and Address Library file names come from?"

From different places today:

- loader/DLL naming conventions in `classic-xse-core::XseType`
- Address Library metadata in `classic-version-registry-core`
- caller-supplied `plugins_path` and game-version mode in `classic-scangame-core::XseChecker`

## "Why do I have both registry `GameVersion` and scangame `GameVersion`?"

Because the crates currently expose different version types for different jobs.

- `classic-version-registry-core::GameVersion` is the four-part parsed version used for matching registry entries
- `classic-scangame-core::GameVersion` is the coarse mode enum used by Address Library validation (`Original`, `NextGen`, `AnniversaryEdition`, `Vr`, `Null`)

There is no single shared cross-crate version type for this workflow today.

## "Why did game-path detection fail even though the install exists?"

Check how the finder was constructed.

- if `GamePathFinder` was created with an XSE loader, validation requires that loader file too
- `find_via_xse_log()` assumes the logged plugin directory is nested like `Data/.../Plugins` and then pops three path components
- if all strategies fail, the error is simply `GamePathError::NotFound`

## "Why does XSE show installed but no version?"

That is a valid current outcome.

- `get_xse_info()` sets `installed` from the loader file check
- version detection then scans sibling DLL filenames
- if no parseable DLL filename is found, `version` stays `None`

---

## Source-Backed Limits And Caveats

- `classic-scangame-core` does not currently call into `classic-xse-core`
- `run_combined_checks()` currently ignores `SetupCheckConfig.xse_hashes`
- `classic-path-core::GamePathFinder` has no built-in manual-prompt fallback; it returns `NotFound` when its automatic strategies fail
- `classic-path-core::parse_xse_log()` assumes a fixed directory depth under `Data/.../Plugins`
- `classic-path-core::DocsPathFinder` does not currently auto-build a Proton-specific documents path from Steam metadata
- `classic-xse-core::detect_xse_version()` uses filename parsing only and returns the first parseable matching DLL it sees
- `classic-xse-core::get_xse_info()` is fail-soft for version detection
- `classic-scangame-core::XseChecker` treats OG, NG, and AE Address Library files as acceptable in non-VR mode, while VR mode expects the VR file only
- `classic-scangame-core::XseChecker::new()` requires an existing plugins directory up front
- `classic-scangame-core::GameIntegrityChecker` only knows the hashes the caller provides; it does not fetch them from Version Registry by itself

These are current behavior notes, not design recommendations.

---

## Contributor Debugging Checklist

When setup/install validation behaves unexpectedly, debug in this order:

1. confirm which crate owns the failing step: path discovery, XSE probing, registry lookup, or scangame validation
2. verify the caller supplied the right path form: game root vs loader path vs plugins path vs documents path
3. check whether the workflow is using observed disk state or expected registry-backed metadata
4. confirm whether the code is using registry `GameVersion` or scangame `GameVersion`
5. inspect bridge/frontend wiring if the Rust APIs look correct but the assembled inputs are incomplete

For active bridge entry points, current contributors usually end up in:

- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs)
- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs)
- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs)

Those files make the current split especially visible because they expose path detection, registry lookups, XSE probing, and setup checks as separate bridge surfaces.
