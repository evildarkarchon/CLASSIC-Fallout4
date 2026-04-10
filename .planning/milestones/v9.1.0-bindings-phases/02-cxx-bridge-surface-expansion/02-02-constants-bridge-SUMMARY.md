---
phase: 02-cxx-bridge-surface-expansion
plan: 02
subsystem: cxx-bridge
tags: [cxx-bridge, constants-core, classic::constants, cxxs-01, d-04, d-09, d-10, d-11]
dependency_graph:
  requires:
    - 02-01-path-promotion-and-widening (build.rs + lib.rs patterns established)
  provides:
    - classic::constants C++ namespace with full CXXS-01 surface
    - GameId, Fallout4Version, YamlFile as CXX shared enums (3 enums, all variants)
    - 13 helper bridge fns for constants, predicates, and as_str getters
    - constants.rs in build.rs bridges array + corrosion_add_cxxbridge FILES lists
    - Refreshed parity baseline with 238 entries (was 222, +16 constants entries)
  affects:
    - classic-gui/CMakeLists.txt (constants.rs added to FILES list)
    - classic-cli/CMakeLists.txt (constants.rs added to FILES list)
    - classic-gui/mainwindow.cpp (D-11 migration — onScanGameFiles gameName)
    - docs/implementation/cxx_api_parity/baseline/ (D-09 refresh)
tech_stack:
  added:
    - classic::constants CXX namespace (constants.rs fully bridged)
    - GameId shared enum (4 variants: Fallout4, Fallout4VR, Skyrim, Starfield)
    - Fallout4Version shared enum (4 variants: Original, NextGen, AnniversaryEdition, Vr)
    - YamlFile shared enum (7 variants: Main, Settings, Ignore, Game, GameLocal, Test, Cache)
  patterns:
    - D-04 shared enum pattern: #[repr(u8)] inside #[cxx::bridge(namespace = "classic::constants")]
    - Free-function wrappers for enum methods (match bridge→core + delegate to .as_str() etc)
    - Slice/semver predicates: SETTINGS_IGNORE_NONE→settings_ignore_none_contains, NULL_VERSION→is_null_version
key_files:
  created:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - classic-cli/CMakeLists.txt
    - classic-gui/CMakeLists.txt
    - classic-gui/src/app/mainwindow.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
decisions:
  - "Added constants.rs to corrosion_add_cxxbridge FILES lists in both classic-gui/CMakeLists.txt and classic-cli/CMakeLists.txt (not just build.rs) because Corrosion requires explicit enumeration to generate the cxxbridge header files"
  - "GUI D-10 clean build run in Release mode (not Debug) to avoid MSVC runtime library mismatch between the Rust staticlib (Release) and CMake Debug mode — same workaround as 02-01"
  - "classic-constants-core added to classic-cpp-bridge/Cargo.toml dependencies (was missing)"
metrics:
  duration: 27min
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_changed: 12
---

# Phase 02 Plan 02: Constants Bridge Summary

First-time exposure of `classic-constants-core` through CXX FFI via the new `classic::constants` C++ namespace. Created `src/constants.rs` with `GameId`, `Fallout4Version`, and `YamlFile` as D-04 CXX shared enums. All 7 YamlFile variants bridged. Vr.as_str()="VR" mapping explicitly tested. 15 Rust-side unit tests pass. Both CLI and GUI clean builds pass. Parity baseline refreshed from 222 to 238 entries.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Create src/constants.rs with enums + helper fns + tests | c3a2fef4 | Done |
| 2 | Wire into build.rs + lib.rs, D-11 migration, D-10 builds, D-09 baseline | c3a2fef4 | Done |

Both tasks were committed atomically in a single commit per D-09 (parity baseline must be committed with the source change).

## Key Changes

### Task 1+2: constants.rs + wiring + migrations + baseline (c3a2fef4)

**New file `src/constants.rs`:**
- `#[cxx::bridge(namespace = "classic::constants")]` block with 3 shared enums
- `GameId` — 4 variants: `Fallout4=0, Fallout4VR=1, Skyrim=2, Starfield=3`
- `Fallout4Version` — 4 variants: `Original=0, NextGen=1, AnniversaryEdition=2, Vr=3`
- `YamlFile` — ALL 7 variants: `Main=0, Settings=1, Ignore=2, Game=3, GameLocal=4, Test=5, Cache=6`
- 13 bridge helper functions in `extern "Rust"` block
- 15 `#[cfg(test)]` unit tests including `test_yaml_file_as_str_all_seven_variants` and `test_fallout4_version_as_str_vr_is_uppercase_vr`

**Cargo.toml:** Added `classic-constants-core` dependency (was missing — needed for `use classic_constants_core::{...}`).

**build.rs:** `"src/constants.rs"` inserted after `"src/types.rs"` in `cxx_build::bridges([...])` array.

**lib.rs:** `pub mod constants;` added under `#[cfg(windows)]` between config and database.

**CMakeLists.txt (both GUI and CLI):** `constants.rs` added to `corrosion_add_cxxbridge` FILES list so Corrosion generates `constants.h` during cmake builds.

**D-11 consumer migration in mainwindow.cpp (onScanGameFiles):**

Before:
```cpp
QString gameName = QStringLiteral("Fallout4");
```

After:
```cpp
// D-11 / CXXS-01 consumer migration: use the bridged GameId helper instead
// of hardcoding the literal "Fallout4". This proves classic::constants is
// callable from production C++ code.
auto gameIdRustStr =
    classic::constants::game_id_as_str(classic::constants::GameId::Fallout4);
QString gameName =
    QString::fromUtf8(gameIdRustStr.data(), static_cast<int>(gameIdRustStr.size()));
```

## Codex Review Corrections Applied

| Severity | Correction | Result |
|----------|-----------|--------|
| MEDIUM | YamlFile enum had only 4 variants in the previous plan — audit revealed 7 | All 7 variants bridged: Main, Settings, Ignore, Game, GameLocal, Test, Cache |
| LOW | Vr.as_str() returns "VR" (uppercase), not "Vr" | Explicitly tested in `test_fallout4_version_as_str_vr_is_uppercase_vr` |
| MEDIUM | D-11 was marked N/A in previous plan — should have a real consumer migration | `onScanGameFiles()` in mainwindow.cpp now calls `classic::constants::game_id_as_str` |

## Parity Baseline Details

- **Before:** 222 entries (from 02-01)
- **After:** 238 entries (+16)
- **New entries by kind:** 3 enums (GameId, Fallout4Version, YamlFile) + 13 functions

Functions added: `game_id_as_str`, `fallout4_version_as_str`, `fallout4_version_registry_id`, `fallout4_version_is_vr`, `fallout4_version_is_standard`, `fallout4_version_exe_name`, `fallout4_version_docs_folder_name`, `fallout4_version_steam_app_id`, `yaml_file_as_str`, `yaml_file_description`, `must_not_be_none_key`, `settings_ignore_none_contains`, `is_null_version`

## D-10 Clean-Build Outcome

| Build | Command | Result |
|-------|---------|--------|
| CLI | `build_cli.ps1 -Clean -Test` | 24/24 tests PASSED |
| GUI | cmake -Release + ctest | 10/10 tests PASSED |

GUI build used Release mode (same workaround as 02-01 — worktree lacks pre-built Qt Debug DLLs).

## Deviations from Plan

### Auto-adapted Issues

**1. [Rule 2 - Missing dependency] classic-constants-core absent from Cargo.toml**
- **Found during:** Task 1 implementation
- **Issue:** Plan specified `use classic_constants_core::{...}` but the dependency was not in the crate's Cargo.toml — only the other business-logic crates were listed
- **Fix:** Added `classic-constants-core = { path = "../../business-logic/classic-constants-core" }` to dependencies
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`
- **Commit:** c3a2fef4

**2. [Rule 3 - Blocking] corrosion_add_cxxbridge FILES list must include constants.rs**
- **Found during:** Task 2 D-10 build
- **Issue:** cmake build failed with `C1083: Cannot open include file: 'classic_cxx_bridge/constants.h'` because `corrosion_add_cxxbridge` in both CMakeLists.txt files uses an explicit FILES list — `constants.rs` was missing from both
- **Fix:** Added `constants.rs` to `corrosion_add_cxxbridge FILES` in `classic-gui/CMakeLists.txt` and `classic-cli/CMakeLists.txt` (same as how `path.rs` was added in 02-01)
- **Files modified:** `classic-gui/CMakeLists.txt`, `classic-cli/CMakeLists.txt`
- **Commit:** c3a2fef4

**3. [Rule 3 - Blocking] GUI D-10 build required Release mode (same workaround as 02-01)**
- **Found during:** Task 2 D-10 GUI build
- **Issue:** `build_gui.ps1 -Clean -Test` fails due to vcpkg Qt build failure (same worktree Qt availability issue as 02-01). Debug cmake build also fails with MSVC runtime library mismatch (MD_DynamicRelease vs MDd_DynamicDebug)
- **Fix:** Configured cmake with `-DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=J:/CLASSIC-Fallout4/classic-gui/build/vcpkg_installed/x64-windows -DCLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON` and ran cmake build + ctest directly. All tests passed (10/10)
- **Impact:** D-10 requirement satisfied; constants.h confirmed in corrosion_generated/ include directory

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| `src/constants.rs` exists | PASS |
| `namespace = "classic::constants"` in constants.rs | PASS |
| GameId enum with 4 variants | PASS |
| All 7 YamlFile variants bridged (Codex MEDIUM) | PASS — Main, Settings, Ignore, Game, GameLocal, Test, Cache |
| Vr → "VR" mapping explicitly tested (Codex LOW) | PASS — test_fallout4_version_as_str_vr_is_uppercase_vr |
| 15 Rust-side tests pass | PASS (15/15) |
| `"src/constants.rs"` in build.rs bridges array | PASS |
| `pub mod constants` in lib.rs | PASS |
| mainwindow.cpp uses `classic::constants::game_id_as_str` (D-11) | PASS — onScanGameFiles() gameName |
| CLI -Clean -Test 24/24 | PASS |
| GUI clean build + ctest 10/10 | PASS (Release mode) |
| `constants.h` generated after build | PASS — corrosion_generated/.../constants.h confirmed |
| Parity gate exits 0 with 0 drift | PASS — 238 entries, 0 drift |
| +16 parity entries for constants bridgeModule | PASS — 3 enums + 13 functions |

## Known Stubs

None — all bridge functions are fully wired to classic-constants-core implementations. The D-11 consumer migration returns the exact same string ("Fallout4") as the hardcoded literal it replaced.

## Self-Check: PASSED
