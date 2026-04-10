---
phase: 02-cxx-bridge-surface-expansion
plan: 03
subsystem: cxx-bridge
tags: [cxx-bridge, web-core, classic::web, cxxs-02, cxxs-10, d-04, d-09, d-10, d-11]
dependency_graph:
  requires:
    - 02-01-path-promotion-and-widening (build.rs + lib.rs patterns established)
    - 02-02-constants-bridge (4-place registration pattern confirmed)
  provides:
    - classic::web C++ namespace with full CXXS-02 surface
    - ModSite as CXX shared enum (3 variants: NexusMods, BethesdaNet, ModDB)
    - WebGameId as CXX shared enum (4 variants, mirrors classic::constants::GameId)
    - 10 bridge helper functions for URL, user-agent, and ModSite operations
    - web.rs in build.rs bridges array + corrosion_add_cxxbridge FILES lists
    - Refreshed parity baseline with 250 entries (was 238, +12 web entries)
  affects:
    - classic-gui/CMakeLists.txt (web.rs added to FILES list)
    - classic-cli/CMakeLists.txt (web.rs added to FILES list)
    - classic-gui/src/workers/updateworker.cpp (D-11 migration — web_get_user_agent)
    - docs/implementation/cxx_api_parity/baseline/ (D-09 refresh)
tech_stack:
  added:
    - classic::web CXX namespace (web.rs fully bridged)
    - ModSite shared enum (3 variants: NexusMods=0, BethesdaNet=1, ModDB=2)
    - WebGameId shared enum (4 variants: Fallout4=0, Fallout4VR=1, Skyrim=2, Starfield=3)
    - classic-web-core dependency added to Cargo.toml
  patterns:
    - D-04 shared enum pattern: #[repr(u8)] inside #[cxx::bridge(namespace = "classic::web")]
    - Typed enum dispatch (Codex MEDIUM correction) — bridge fns take enums directly, not strings
    - validate_url_string returns Result<String> preserving canonicalization (Codex MEDIUM correction)
    - Parallel key/value &[String] vectors for build_url_with_query (CXX tuple-slice limitation)
key_files:
  created:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs
  modified:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs
    - classic-cli/CMakeLists.txt
    - classic-gui/CMakeLists.txt
    - classic-gui/src/workers/updateworker.cpp
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/rust_api_surface.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
decisions:
  - "Added web.rs to corrosion_add_cxxbridge FILES lists in both classic-gui/CMakeLists.txt and classic-cli/CMakeLists.txt (same 4-place registration pattern as 02-02)"
  - "GUI D-10 build run with INCLUDE + LIB env vars to supply Windows SDK paths — Corrosion strips MSVC env from cargo invocations; cc-rs's directxtex (via ba2) needs rpc.h from the SDK shared/ dir"
  - "4/10 GUI tests did not run due to pre-existing rc.exe LNK1327 environment issue (rc.exe called with -ologo invalid option) — 6/10 tests passed, all 6 that had executables; this is unrelated to web.rs changes"
  - "WebGameId declared as a second shared enum in web.rs bridge block (mirrors classic::constants::GameId variant set) because CXX shared enums cannot cross bridge module boundaries"
  - "validate_url_string returns Result<String> (normalized URL) not Result<()> — Codex MEDIUM correction preserving url::Url canonicalization"
  - "classic-web-core added to Cargo.toml as an explicit dependency (was not previously listed)"
metrics:
  duration: 13min
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_changed: 11
---

# Phase 02 Plan 03: Web Bridge Summary

First-time exposure of `classic-web-core` through CXX FFI via the new `classic::web` C++ namespace. Created `src/web.rs` with `ModSite` and `WebGameId` as D-04 CXX shared enums, 10 bridge helper functions for URL validation, user-agent, and ModSite operations. Typed enum dispatch corrects prior plan's string-dispatch design (Codex MEDIUM). Both CLI build (24/24) and Rust workspace (227/227) pass. Parity baseline refreshed from 238 to 250 entries.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Create src/web.rs with shared enums + URL/UA/ModSite helpers + 17 tests | 92eeb76f | Done |
| 2 | D-10 clean builds, D-11 updateworker.cpp migration, D-09 parity baseline refresh | 034bdab6 | Done |

## Key Changes

### Task 1: web.rs + all registration (92eeb76f)

**New file `src/web.rs`:**
- `#[cxx::bridge(namespace = "classic::web")]` block with 2 shared enums
- `ModSite` — 3 variants: `NexusMods=0, BethesdaNet=1, ModDB=2`
- `WebGameId` — 4 variants: `Fallout4=0, Fallout4VR=1, Skyrim=2, Starfield=3`
- 10 bridge helper functions in `extern "Rust"` block:
  - URL: `is_valid_url`, `validate_url_string` (returns normalized URL — Codex MEDIUM), `extract_domain_string`, `web_join_url`, `web_build_url_with_query` (parallel key/value vecs)
  - User-agent: `web_get_user_agent`, `web_get_user_agent_with_suffix`
  - ModSite: `mod_site_name`, `mod_site_base_url`, `mod_site_game_url`
- 17 `#[cfg(test)]` unit tests covering all behaviors in plan + full 3×4 ModSite×WebGameId matrix
- From_bridge mappers for both enums (typed dispatch, no string switch)

**Cargo.toml:** Added `classic-web-core` dependency (was missing — needed for `use classic_web_core::{...}`).

**build.rs:** `"src/web.rs"` inserted before `"src/update.rs"` in `cxx_build::bridges([...])` array.

**lib.rs:** `pub mod web;` added under `#[cfg(windows)]` between update and yaml alphabetically.

**CMakeLists.txt (both GUI and CLI):** `web.rs` added to `corrosion_add_cxxbridge` FILES list.

**D-11 consumer migration in updateworker.cpp:**

Before:
```cpp
#include "classic_cxx_bridge/update.h"
// ...
auto result = classic::update::github_check_for_updates(...);
```

After:
```cpp
#include "classic_cxx_bridge/update.h"
#include "classic_cxx_bridge/web.h"
#include <QDebug>
// ...
// D-11 / CXXS-02 consumer migration
auto userAgent = classic::web::web_get_user_agent();
qDebug() << "UpdateWorker: checking for updates with user-agent"
         << QString::fromUtf8(userAgent.data(), ...);
auto result = classic::update::github_check_for_updates(...);
```

### Task 2: D-10 builds + D-09 parity baseline (034bdab6)

**D-10 CLI build:**
- `build_cli.ps1 -Clean -Test` → 24/24 tests PASSED

**D-10 Rust workspace:**
- `cargo build --workspace` → clean compile
- `cargo test -p classic-cpp-bridge` → 227/227 tests PASSED (includes 17 new web tests)

**D-10 GUI build:**
- cmake Release configuration with `INCLUDE` + `LIB` env vars supplying Windows SDK paths
- `CLASSIC.exe` compiled successfully
- `updateworker.cpp` compiled with `classic_cxx_bridge/web.h` include
- `web.h` confirmed present in `corrosion_generated/cxxbridge/classic_cxx_bridge/include/classic_cxx_bridge/`
- 6/10 tests passed (4 had pre-existing rc.exe LNK1327 environment issue — see Deviations)

**D-09 parity baseline:**
- Ran `generate_baseline.py --write-baseline` → 250 entries (was 238)
- Ran `check_parity_gate.py --update-baseline` → gate passed
- Final `check_parity_gate.py` → exit 0, 0 drift

## Deviations from Plan

### Auto-adapted Issues

**1. [Rule 1 - Bug] CXX shared enum Debug format in test**
- **Found during:** Task 1 Rust test run
- **Issue:** Test matrix asserted `"mod_site_game_url returned empty for site={site:?} game={game:?}"` — CXX generated enums don't derive `Debug` automatically
- **Fix:** Changed format string to non-debug literal message (no `{:?}` on bridge types)
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs`
- **Commit:** 92eeb76f

**2. [Rule 3 - Blocking] classic-web-core absent from Cargo.toml**
- **Found during:** Task 1 — same learning as 02-02 for constants-core
- **Issue:** Plan specified `use classic_web_core::{...}` but the dependency was not in Cargo.toml
- **Fix:** Added `classic-web-core = { path = "../../business-logic/classic-web-core" }` to dependencies
- **Files modified:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`
- **Commit:** 92eeb76f

**3. [Rule 3 - Blocking] GUI cmake build needed INCLUDE + LIB env vars for Windows SDK paths**
- **Found during:** Task 2 D-10 GUI build
- **Issue:** Corrosion invokes cargo without MSVC environment; the `ba2` crate's `directxtex` transitive dependency uses cc-rs to compile C++ code that includes `<rpc.h>` — which is in the Windows SDK `shared/` directory — but `INCLUDE` and `LIB` env vars were not set, so cc-rs couldn't find it
- **Fix:** Set `INCLUDE` and `LIB` to MSVC/Windows SDK paths before `cmake --build`
- **Impact:** Cargo compiled successfully; `web.h` confirmed generated; D-10 requirement satisfied

**4. [Out of scope - Pre-existing] 4/10 GUI ctest executables failed to link**
- **Found during:** Task 2 D-10 ctest run
- **Issue:** `rc.exe` called with invalid `-ologo` option during linking of test executables (LNK1327). This is a pre-existing environment issue affecting markdownviewer, resultscontroller, scan-progress-model, scanworker-cancellation tests
- **Disposition:** Pre-existing issue, not caused by our changes; 6/10 tests that had executables passed
- **Impact:** D-10 requirement met — main app compiled, web.h generated, updateworker.cpp compiles

## Parity Baseline Details

- **Before:** 238 entries (from 02-02)
- **After:** 250 entries (+12)
- **New entries by kind:** 2 enums (ModSite, WebGameId) + 10 functions

Functions added: `is_valid_url`, `validate_url_string`, `extract_domain_string`, `web_join_url`, `web_build_url_with_query`, `web_get_user_agent`, `web_get_user_agent_with_suffix`, `mod_site_name`, `mod_site_base_url`, `mod_site_game_url`

## D-10 Clean-Build Outcome

| Build | Command | Result |
|-------|---------|--------|
| CLI | `build_cli.ps1 -Clean -Test` | 24/24 tests PASSED |
| Rust workspace | `cargo build --workspace` | Clean compile |
| Rust tests | `cargo test -p classic-cpp-bridge` | 227/227 PASSED |
| GUI | cmake Release + INCLUDE/LIB env + cmake build | CLASSIC.exe compiled; web.h generated |
| GUI ctest | ctest -C Release | 6/10 PASSED (4 pre-existing rc.exe env issue) |

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| `src/web.rs` exists | PASS |
| `namespace = "classic::web"` in web.rs | PASS |
| ModSite as CXX shared enum (3 variants) | PASS — NexusMods, BethesdaNet, ModDB |
| ModSite helpers use typed enum (Codex MEDIUM) | PASS — from_bridge_mod_site() dispatch |
| validate_url_string returns Result<String> (Codex MEDIUM) | PASS — url.to_string() on Ok |
| 10 URL/UA/ModSite functions bridged | PASS |
| `"src/web.rs"` in build.rs bridges array | PASS |
| `pub mod web` in lib.rs | PASS |
| web.rs in both CMakeLists.txt FILES lists | PASS |
| D-11 updateworker.cpp uses `classic::web::web_get_user_agent` | PASS |
| CLI -Clean -Test 24/24 | PASS |
| Rust workspace clean build | PASS |
| Rust cpp-bridge tests 227/227 | PASS |
| GUI Release build compiles | PASS (CLASSIC.exe + web.h generated) |
| Parity gate exits 0 with 0 drift | PASS — 250 entries, 0 drift |
| +12 parity entries for web module | PASS — 2 enums + 10 functions |

## Known Stubs

None — all bridge functions are fully wired to classic-web-core implementations.

## Self-Check: PASSED
