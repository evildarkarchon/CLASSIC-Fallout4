---
phase: 02-cxx-bridge-surface-expansion
plan: 04
subsystem: cxx-bridge
tags: [cxx-bridge, xse-core, version-registry-core, classic::xse, classic::version_registry, cxxs-06, cxxs-09, d-01, d-02, d-04, d-07, d-08, d-09, d-10, d-11]
dependency_graph:
  requires:
    - 02-01-path-promotion-and-widening (build.rs + lib.rs patterns established)
    - 02-02-constants-bridge (4-place registration pattern confirmed)
    - 02-03-web-bridge (250-entry baseline established, GUI build workaround documented)
  provides:
    - classic::xse C++ namespace with full CXXS-09 surface
    - XseType as CXX shared enum (6 variants, D-04 #[repr(u8)])
    - XseInfoDto flat struct bridging XseInfo path/version/installed fields
    - classic::version_registry C++ namespace with full CXXS-06 surface
    - version_registry_get_all_for_game(game, is_vr) — new CXXS-06 fn
    - D-08 shims preserved in game.rs for all moved fns
    - xse.rs + version_registry.rs in build.rs + lib.rs + BOTH CMakeLists.txt
    - Refreshed parity baseline with 274 entries (was 250, +24 new entries)
  affects:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs (D-08 shims — UNCHANGED)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs (D-02 — UNCHANGED)
    - classic-gui/CMakeLists.txt (xse.rs + version_registry.rs added to FILES list)
    - classic-cli/CMakeLists.txt (xse.rs + version_registry.rs added to FILES list)
    - classic-gui/src/app/pathdialog.cpp (D-11 migration — xse_get_loader_name)
    - docs/implementation/cxx_api_parity/baseline/ (D-09 refresh, 274 entries)
tech_stack:
  added:
    - classic::xse CXX namespace (xse.rs fully bridged)
    - XseType shared enum (6 variants: F4SE=0, F4SEVR=1, SKSE=2, SKSE64=3, SKSEVR=4, SFSE=5)
    - XseInfoDto struct (xse_type: String, path: String, version: String, installed: bool)
    - classic::version_registry CXX namespace (version_registry.rs fully bridged)
    - version_registry_get_all_for_game(game, is_vr) — CXXS-06 new fn
    - 5 DTOs moved verbatim: VersionInfoDto, XseConfigDto, CrashgenConfigDto, MatchResultDto, GameVersionDto
  patterns:
    - D-04 shared enum pattern: #[repr(u8)] inside #[cxx::bridge(namespace = "classic::xse")]
    - Real &Path-taking signatures (Codex LOW correction)
    - Infallible from_game_id (GameId → XseType, no Option wrapping)
    - "f4se_" trailing underscore from dll_prefix() (Codex LOW correction verified)
    - D-08 backward-compat: game.rs shims call core directly, not xse.rs internals
key_files:
  created:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - classic-cli/CMakeLists.txt
    - classic-gui/CMakeLists.txt
    - classic-gui/src/app/pathdialog.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
decisions:
  - "xse.rs typed API uses real classic-xse-core &Path-taking signatures — Path::new(s) conversion at bridge boundary, not String-based dispatch (Codex LOW correction)"
  - "xse_get_type_from_game_id is string-to-GameId-to-XseType; only the string decode can fail, not from_game_id itself (INFALLIBLE — Codex LOW correction)"
  - "version_registry.rs uses get_all() iteration with manual filter for version_registry_get_all_for_game — equivalent to registry.get_all_for_game(game, Some(is_vr)) but avoids coupling to that helper"
  - "D-08 shims in game.rs call classic_xse_core and classic_version_registry_core directly — no cross-bridge-module calls; duplication is intentional"
  - "GUI D-10 clean build used system-fallback Qt from main repo (same CLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON + CMAKE_PREFIX_PATH workaround as 02-01/02-02)"
  - "GUI cmake build needed INCLUDE env var to include Windows SDK winrt/ dir for wrl/client.h (ba2/directxtex transitive dependency)"
  - "registry.rs is UNCHANGED — it is the classic-registry-core KV singleton, not version-registry; D-02 wording preserved"
metrics:
  duration: 27min
  completed_date: "2026-04-08"
  tasks_completed: 3
  files_changed: 11
---

# Phase 02 Plan 04: XSE and Version Registry Split Summary

Split XSE helpers and version-registry helpers from `game.rs` into two new bridge modules: `src/xse.rs` (CXXS-09, D-01) and `src/version_registry.rs` (CXXS-06, D-02). Both modules use real `classic-xse-core` and `classic-version-registry-core` signatures with ZERO `todo!()` placeholders. D-08 compatibility shims kept in `game.rs`. `pathdialog.cpp` exercises the new `classic::xse` namespace (D-11). Both CLI and GUI clean builds pass. Parity baseline refreshed from 250 to 274 entries.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Create src/xse.rs with XseType enum, XseInfoDto, typed + string-form API, 11 tests | ebe3097e | Done |
| 2 | Create src/version_registry.rs with all 5 DTOs, 8 fns + new get_all_for_game, 7 tests | 5ffe1c72 | Done |
| 3 | 4-place registration (build.rs, lib.rs, CMakeLists.txt x2), D-11 pathdialog.cpp, D-10 builds, D-09 baseline | 0232ad5c | Done |
| - | Fix comment false-positive todo! match in version_registry.rs | 38485d15 | Done |

## Codex Review Corrections Applied

### Codex LOW: Real XSE core signatures

- `is_xse_installed` takes `&Path` (not `&str`) — bridge converts via `Path::new(s)`
- `detect_xse_version` takes `&Path` and returns `XseResult<semver::Version>` (not `Option<String>`)
- `XseType::from_game_id(GameId) -> Self` is INFALLIBLE — the bridge's `xse_get_type_from_game_id` only fails at the string→GameId decode step
- `dll_prefix()` returns trailing underscore: `"f4se_"` not `"f4se"` — verified at `classic-xse-core/src/lib.rs:195`
- `xse_get_loader_name(F4SE)` returns `"f4se_loader.exe"` — verified at `classic-xse-core/src/lib.rs:169`

### Codex MEDIUM: ZERO todo!() placeholders in version_registry.rs

All 8 wrapper function bodies are concrete implementations moved verbatim from `game.rs`. No placeholder `todo!()` calls exist.

### Codex MEDIUM: D-11 pathdialog.cpp consumer migration

`classic-gui/src/app/pathdialog.cpp` now includes `classic_cxx_bridge/xse.h` and calls `classic::xse::xse_get_loader_name(classic::xse::XseType::F4SE)` to display the expected XSE loader filename in the game path dialog.

## Key Changes

### Task 1: xse.rs (ebe3097e)

**New file `src/xse.rs`:**
- `#[cxx::bridge(namespace = "classic::xse")]` block
- `XseType` shared enum: F4SE=0, F4SEVR=1, SKSE=2, SKSE64=3, SKSEVR=4, SFSE=5
- `XseInfoDto` flat struct: xse_type, path, version, installed
- Typed API (6 fns): xse_get_loader_name, xse_get_dll_prefix, xse_get_type_from_game_id, is_xse_installed, detect_xse_version, xse_get_info
- String-form D-08 compat (2 fns): detect_xse_version_string, is_xse_installed_check
- 11 Rust-side tests: exact string assertions ("f4se_loader.exe", "f4se_"), infallible from_game_id, fail-soft for nonexistent paths

**lib.rs:** Added `pub mod xse` and `pub mod version_registry` (both `#[cfg(windows)]`)

### Task 2: version_registry.rs (5ffe1c72)

**New file `src/version_registry.rs`:**
- `#[cxx::bridge(namespace = "classic::version_registry")]` block
- 5 DTOs: VersionInfoDto, XseConfigDto, CrashgenConfigDto, MatchResultDto, GameVersionDto
- 8 fns moved verbatim from game.rs: version_registry_get_by_id, get_all_ids, get_all_count, match_version, get_xse_config, get_crashgen_configs, get_crashgen_config, parse_game_version
- 1 new fn: version_registry_get_all_for_game(game, is_vr) — CXXS-06 new entry
- 7 Rust-side tests: count >= 4, get_all_ids nonempty, unknown ID returns not-found, Fallout4 non-VR/VR filtering, parse_game_version valid/invalid

### Task 3: Wiring + D-11 + D-10 + D-09 (0232ad5c + 38485d15)

**4-place registration:**
- `build.rs`: "src/xse.rs" and "src/version_registry.rs" inserted after "src/game.rs"
- `lib.rs`: Both `pub mod` declarations under `#[cfg(windows)]`
- `classic-cli/CMakeLists.txt`: xse.rs + version_registry.rs added to FILES list
- `classic-gui/CMakeLists.txt`: xse.rs + version_registry.rs added to FILES list

**D-11 consumer migration — pathdialog.cpp:**
- Added `#include "classic_cxx_bridge/xse.h"`
- Called `classic::xse::xse_get_loader_name(classic::xse::XseType::F4SE)` in game path dialog
- Result displayed as "The game folder should contain: f4se_loader.exe"

**D-10 clean-build outcomes:**

| Build | Command | Result |
|-------|---------|--------|
| CLI | build_cli.ps1 -Clean -Test | 24/24 tests PASSED |
| Rust tests | cargo test -p classic-cpp-bridge | 246/246 PASSED |
| GUI | cmake Release (system-fallback Qt) + INCLUDE/LIB env | 99/99 steps, 10/10 tests PASSED |
| Rust workspace | cargo build --workspace | Not separately run (GUI build invokes cargo) |

Generated headers confirmed:
- `classic_cxx_bridge/xse.h` — present in corrosion_generated
- `classic_cxx_bridge/version_registry.h` — present in corrosion_generated

**D-09 parity baseline:**
- Before: 250 entries (post 02-03)
- After: 274 entries (+24)
- New xse entries (10): 1 enum, 1 struct, 8 fns
- New version_registry entries (14): 5 structs, 9 fns (including new get_all_for_game)
- game entries unchanged: 19 (D-08 verified — zero removed rows)
- registry entries unchanged: 14 (D-02 verified)
- Drift: 0

## Deviations from Plan

### Auto-adapted Issues

**1. [Rule 1 - Bug] lib.rs needed both module declarations before either file could compile**
- **Found during:** Task 1 Rust test run
- **Issue:** `cargo test -p classic-cpp-bridge ... xse::tests` failed because `version_registry.rs` was declared in lib.rs but didn't exist yet (file not found for module)
- **Fix:** Created both `src/xse.rs` and `src/version_registry.rs` before running the first test suite; both module declarations were staged in the Task 1 commit since they were co-required
- **Impact:** No behavioral change; Tasks 1 and 2 tests verified together once both files existed
- **Commit:** ebe3097e

**2. [Rule 3 - Blocking] version_registry.rs comment contained "todo!" substring**
- **Found during:** Task 3 acceptance criteria verification
- **Issue:** The comment `// Codex MEDIUM: NO todo!()` contained the substring `todo!` which falsely matched the `git grep -n 'todo!'` acceptance criterion
- **Fix:** Rewrote comment to `// Codex MEDIUM correction applied — All wrapper bodies are concrete; no placeholder implementations.`
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs`
- **Commit:** 38485d15

**3. [Rule 3 - Blocking] GUI cmake build needed Windows SDK winrt/ in INCLUDE env**
- **Found during:** Task 3 D-10 GUI build
- **Issue:** The `ba2` crate's `directxtex` dependency includes `<wrl/client.h>` which lives in the Windows SDK `winrt/` directory — not covered by the INCLUDE paths used in Wave 1 plans
- **Fix:** Added `C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/winrt` to the INCLUDE env var (in addition to um/, shared/, ucrt/)
- **Impact:** Cargo/directxtex compiled successfully; xse.h and version_registry.h generated; D-10 requirement satisfied

**4. [Out of scope - Pre-existing] GUI -Clean flag triggered Qt rebuild from source**
- **Found during:** Task 3 D-10 GUI build
- **Issue:** Using `-Clean` with `build_gui.ps1` deleted the build dir; cmake tried to rebuild Qt 6.10.0 from source (vcpkg fetched a different version than installed), which failed
- **Disposition:** Same workaround as 02-01/02-02: configured with `-DCLASSIC_GUI_ALLOW_SYSTEM_QT_FALLBACK=ON -DCMAKE_PREFIX_PATH=J:/CLASSIC-Fallout4/classic-gui/build/vcpkg_installed/x64-windows -DVCPKG_MANIFEST_INSTALL=OFF` pointing to main repo's pre-built Qt
- **Impact:** D-10 requirement met — all 10/10 GUI tests passed; xse.h and version_registry.h both confirmed generated

## D-02 Verification: registry.rs UNCHANGED

`git diff HEAD~4 ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs` shows no changes. The `classic-registry-core` KV singleton bridge (`src/registry.rs`, namespace `classic::registry`) is untouched — it is a separate module from `src/version_registry.rs` (namespace `classic::version_registry`).

## Parity Baseline Details

- **Before:** 250 entries (from 02-03)
- **After:** 274 entries (+24)

**New xse module (10 entries):**
- Enum: XseType (6 variants)
- Struct: XseInfoDto
- Functions: detect_xse_version, detect_xse_version_string, is_xse_installed, is_xse_installed_check, xse_get_dll_prefix, xse_get_info, xse_get_loader_name, xse_get_type_from_game_id

**New version_registry module (14 entries):**
- Structs: CrashgenConfigDto, GameVersionDto, MatchResultDto, VersionInfoDto, XseConfigDto
- Functions: parse_game_version, version_registry_get_all_count, version_registry_get_all_for_game (NEW), version_registry_get_all_ids, version_registry_get_by_id, version_registry_get_crashgen_config, version_registry_get_crashgen_configs, version_registry_get_xse_config, version_registry_match_version

## Known Stubs

None. All bridge wrappers are fully implemented with concrete bodies calling real core APIs.

## Self-Check: PASSED

- `src/xse.rs` exists: YES
- `src/version_registry.rs` exists: YES
- Commit ebe3097e exists: YES
- Commit 5ffe1c72 exists: YES
- Commit 0232ad5c exists: YES
- Commit 38485d15 exists: YES
- `classic::xse` in parity_contract.json: YES (10 entries)
- `classic::version_registry` in parity_contract.json: YES (14 entries)
- `registry` module entries unchanged: YES (14 entries)
- `game` module entries unchanged: YES (19 entries — D-08 verified)
- Parity gate drift: 0
