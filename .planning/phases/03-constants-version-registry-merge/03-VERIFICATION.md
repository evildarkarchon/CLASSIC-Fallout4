---
phase: 03-constants-version-registry-merge
verified: 2026-04-12T01:41:41.8853046Z
status: gaps_found
score: 6/9 must-haves verified
gaps:
  - truth: "Contributor-facing docs no longer point to retired constants artifacts"
    status: failed
    reason: "An active API doc still links to the retired classic-constants-py crate."
    artifacts:
      - path: "docs/api/classic-version-registry-core.md"
        issue: "Line 349 still references classic-constants-py as a maintained integration layer."
    missing:
      - "Remove the retired classic-constants-py reference and point contributors only at surviving bindings."
  - truth: "Refreshed parity artifacts no longer reference retired constants-era owners/crates/modules"
    status: failed
    reason: "Committed generated parity surface artifacts are stale and still describe deleted constants/yaml/crashgen owners."
    artifacts:
      - path: "docs/implementation/python_api_parity/baseline/python_api_surface.json"
        issue: "Generated 2026-04-10 and still lists classic_constants and classic-yaml-py source files."
      - path: "docs/implementation/node_api_parity/baseline/rust_api_surface.json"
        issue: "Generated 2026-04-10 and still lists classic-constants-core, classic-yaml-core, and classic-crashgen-settings-core."
    missing:
      - "Regenerate and commit the stale parity surface artifacts after the redistribution."
      - "Verify no active baseline artifact references classic-constants-core, classic_constants, classic-yaml-core, classic_yaml, or classic-crashgen-settings-core."
  - truth: "The retired classic-constants-py crate directory is fully removed"
    status: partial
    reason: "The module is no longer importable, but the crate directory still exists with leftover backup/dist artifacts."
    artifacts:
      - path: "ClassicLib-rs/python-bindings/classic-constants-py/"
        issue: "Directory still contains .maturin-temp/, dist/, and Cargo.toml.backup.*."
    missing:
      - "Delete the leftover classic-constants-py directory artifacts so the retired crate is truly gone from the repo tree."
---

# Phase 3: constants-version-registry-merge Verification Report

**Phase Goal:** classic-constants-core no longer exists as a separate crate; its contents are redistributed by semantic domain: Fallout4Version and NULL_VERSION live in classic-version-registry-core, YamlFile and settings constants live in classic-settings-core, and GameId lives in classic-shared-core (foundation). Zero consumer-visible behavior change.
**Verified:** 2026-04-12T01:41:41.8853046Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Fallout4Version and NULL_VERSION are available from `classic-version-registry-core` with preserved coverage. | ✓ VERIFIED | `classic-version-registry-core/src/lib.rs` re-exports `fallout4_version::*`; `src/fallout4_version.rs` defines both symbols and inline tests. |
| 2 | YamlFile, SETTINGS_IGNORE_NONE, and must_not_be_none are available from `classic-settings-core` with preserved coverage. | ✓ VERIFIED | `classic-settings-core/src/lib.rs` re-exports `yaml_file::*`; `src/yaml_file.rs` defines all three and inline tests. |
| 3 | GameId is available from `classic-shared-core` with preserved coverage. | ✓ VERIFIED | `classic-shared-core/src/lib.rs` re-exports `game_id::*`; `src/game_id.rs` defines GameId and inline tests. |
| 4 | Live Rust/Python/Node/CXX consumers use semantic owners instead of retired constants surfaces. | ✓ VERIFIED | No `classic_constants_core`, `classic::constants`, `classic_cxx_bridge/constants.h`, `mod constants;`, or active Python `import classic_constants` hits in live source; consumer files read cleanly. |
| 5 | `classic-constants-core` is removed from workspace membership and disk. | ✓ VERIFIED | `ClassicLib-rs/Cargo.toml` has no workspace member entry; no `ClassicLib-rs/business-logic/classic-constants-core/**` files exist. |
| 6 | Workspace Rust behavior still holds after redistribution. | ✓ VERIFIED | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` and `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` both succeeded during verification. |
| 7 | Contributor-facing docs no longer point to retired constants artifacts. | ✗ FAILED | `docs/api/classic-version-registry-core.md:349` still links to `classic-constants-py`. |
| 8 | Refreshed parity artifacts no longer reference retired constants-era owners/crates/modules. | ✗ FAILED | `python_api_surface.json` and `node rust_api_surface.json` are still stamped `2026-04-10` and still name deleted constants/yaml/crashgen owners. |
| 9 | The retired `classic-constants-py` crate directory is fully removed. | ✗ FAILED | `ClassicLib-rs/python-bindings/classic-constants-py/` still exists with leftover artifact-only contents. |

**Score:** 6/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `ClassicLib-rs/business-logic/classic-version-registry-core/src/fallout4_version.rs` | Fallout4Version + NULL_VERSION home | ✓ VERIFIED | Exists, substantive, tested, crate-root re-exported. |
| `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_file.rs` | YamlFile/settings constants home | ✓ VERIFIED | Exists, substantive, tested, crate-root re-exported. |
| `ClassicLib-rs/foundation/classic-shared-core/src/game_id.rs` | GameId home | ✓ VERIFIED | Exists, substantive, tested, crate-root re-exported. |
| `ClassicLib-rs/python-bindings/classic-version-registry-py/src/fallout4_version.rs` | Python Fallout4Version/NULL_VERSION exposure | ✓ VERIFIED | Registered in `classic_version_registry` and stubbed as `NULL_VERSION: str`. |
| `ClassicLib-rs/python-bindings/classic-settings-py/src/yaml_file.rs` | Python YamlFile/settings constants exposure | ✓ VERIFIED | Registered in `classic_settings` and exports list-valued `SETTINGS_IGNORE_NONE`. |
| `ClassicLib-rs/foundation/classic-shared-py/src/game_id.rs` | Python GameId exposure | ✓ VERIFIED | Registered in `classic_shared`. |
| `ClassicLib-rs/node-bindings/classic-node/src/shared.rs` | Node GameId destination | ✓ VERIFIED | Owns `JsGameId`, `get_game_name`, `get_all_game_ids`. |
| `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` | Node YamlFile destination | ✓ VERIFIED | Owns `JsYamlFile`, `get_yaml_file_description`, `get_all_yaml_files`. |
| `ClassicLib-rs/node-bindings/classic-node/src/version_registry.rs` | Node Fallout4Version destination | ✓ VERIFIED | Owns `JsFallout4Version`, `get_fallout4_version_info`, `get_all_fallout4_versions`. |
| `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/shared.rs` | CXX `classic::shared` GameId bridge | ✓ VERIFIED | Exists and registered in build/CMake wiring. |
| `docs/api/classic-version-registry-core.md` | Updated contributor docs | ⚠️ PARTIAL | Documents redistributed symbols, but still contains one stale `classic-constants-py` link. |
| `docs/implementation/python_api_parity/baseline/python_api_surface.json` | Refreshed Python parity surface | ✗ FAILED | Still references `classic_constants` and `classic_yaml`; timestamp predates Phase 3. |
| `docs/implementation/node_api_parity/baseline/rust_api_surface.json` | Refreshed Node parity surface | ✗ FAILED | Still references `classic-constants-core`, `classic-yaml-core`, and `classic-crashgen-settings-core`; timestamp predates Phase 3. |
| `ClassicLib-rs/python-bindings/classic-constants-py/` | Removed retired crate directory | ⚠️ PARTIAL | Not an active workspace member, but artifact directory still exists. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `classic-version-registry-core/src/lib.rs` | `src/fallout4_version.rs` | `mod fallout4_version; pub use fallout4_version::*;` | ✓ WIRED | Re-export present at lines 49 and 57. |
| `classic-settings-core/src/lib.rs` | `src/yaml_file.rs` | `mod yaml_file; pub use yaml_file::*;` | ✓ WIRED | Re-export present at lines 89 and 106. |
| `classic-shared-core/src/lib.rs` | `src/game_id.rs` | `mod game_id; pub use game_id::*;` | ✓ WIRED | Re-export present at lines 21 and 28. |
| `classic-version-registry-py/src/lib.rs` | `src/fallout4_version.rs` | `fallout4_version::register(m)?;` | ✓ WIRED | Registration call at line 67. |
| `classic-settings-py/src/lib.rs` | `src/yaml_file.rs` | `yaml_file::register(m)?;` | ✓ WIRED | Registration call at line 753. |
| `classic-shared-py/src/lib.rs` | `src/game_id.rs` | `game_id::register(m)?;` | ✓ WIRED | Registration call at line 327. |
| `classic-cpp-bridge/build.rs` | native CMake bridge lists | `shared.rs` registration | ✓ WIRED | `build.rs`, `classic-cli/CMakeLists.txt`, and `classic-gui/CMakeLists.txt` all include `shared.rs`. |
| `classic-gui/src/app/mainwindow.cpp` | `classic-cpp-bridge/src/shared.rs` | `classic::shared::game_id_as_str(...)` | ✓ WIRED | `mainwindow.cpp` includes `shared.h` and calls `classic::shared`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `classic-version-registry-py/src/fallout4_version.rs` | `NULL_VERSION` / enum methods | Direct Rust-core delegation to `classic_version_registry_core` | Yes | ✓ FLOWING |
| `classic-settings-py/src/yaml_file.rs` | `SETTINGS_IGNORE_NONE` / `must_not_be_none` | Direct Rust-core delegation + module literal list matching core contract | Yes | ✓ FLOWING |
| `classic-shared-py/src/game_id.rs` | `PyGameId.inner` | Direct Rust-core delegation to `classic_shared_core::GameId` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Rust workspace builds after redistribution | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | Finished `dev` profile successfully | ✓ PASS |
| Rust workspace tests after redistribution | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | Workspace tests reported only `test result: ok` lines, no failures | ✓ PASS |
| Redistributed Python modules import and expose expected values | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import classic_version_registry, classic_settings, classic_shared; ..."` | Printed `0.0.0`, `SCAN Custom Path`, `Fallout4` | ✓ PASS |
| Legacy `classic_constants` module is absent | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import importlib.util; ..."` | Exit code 0; module not found | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| CNST-01 | 03-01, 03-02, 03-03, 03-04 | `classic-constants-core` content redistributed to version-registry/settings/shared with same public names | ✓ SATISFIED | New Rust core modules exist and re-export correctly; Python/Node/CXX bindings point at semantic owners. |
| CNST-02 | 03-01, 03-02, 03-03, 03-04 | Consumers now import semantic owner crates/modules instead of constants-core | ✓ SATISFIED | No live `classic_constants_core`, `classic::constants`, `classic_cxx_bridge/constants.h`, or active Python `classic_constants` imports in source. |
| CNST-03 | 03-01, 03-02, 03-04 | `classic-constants-core` removed from workspace members and directory deleted | ✓ SATISFIED | Root workspace has no member entry and `ClassicLib-rs/business-logic/classic-constants-core/` is absent. |

**Orphaned requirements:** None. `REQUIREMENTS.md` maps only CNST-01, CNST-02, and CNST-03 to Phase 3, and all appear in plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `docs/api/classic-version-registry-core.md` | 349 | stale retired-crate reference | ⚠️ Warning | Contributor docs still point at deleted binding surface. |
| `docs/implementation/python_api_parity/baseline/python_api_surface.json` | 2 / 17 / 38 | stale generated artifact references old owners | 🛑 Blocker | Phase-closure parity artifacts do not reflect actual Phase 3 ownership. |
| `docs/implementation/node_api_parity/baseline/rust_api_surface.json` | 2 / 23 / 44 | stale generated artifact references old owners | 🛑 Blocker | Same; committed baseline surface still describes deleted crates. |
| `ClassicLib-rs/python-bindings/classic-constants-py/` | n/a | leftover retired crate directory | ⚠️ Warning | Old artifact directory remains in tree despite retirement. |

### Gaps Summary

The live implementation goal is largely achieved: the Rust symbols were redistributed correctly, consumers were rewired, `classic-constants-core` is gone, and the workspace still builds/tests cleanly. However, phase closure is incomplete. One contributor-facing API doc still points to the retired Python constants crate, two committed parity surface artifacts are clearly stale and still describe pre-merge owners, and the retired `classic-constants-py` directory still exists as leftover artifact-only debris. Because the prompt asked to verify the whole phase against its plans and must-haves, these closure gaps keep the phase from being fully verified as complete.

---

_Verified: 2026-04-12T01:41:41.8853046Z_
_Verifier: the agent (gsd-verifier)_
