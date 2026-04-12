---
phase: 03-constants-version-registry-merge
plan: 03
subsystem: bindings
tags: [node, cxx, napi-rs, cxx, constants-redistribution]
requires:
  - phase: 03-01
    provides: Rust semantic owners for GameId, YamlFile, and Fallout4Version
provides:
  - Node bindings expose GameId, YamlFile, and Fallout4Version from semantic modules with no constants module
  - CXX bridge exposes GameId from classic::shared, YamlFile from classic::settings, and Fallout4Version from classic::version_registry
  - Production GUI code consumes classic::shared instead of classic::constants
affects: [03-04, node parity, cxx parity, gui]
tech-stack:
  added: []
  patterns: [semantic binding-module ownership, classic::shared CXX namespace, root-export regression testing]
key-files:
  created:
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/shared.rs
  modified:
    - ClassicLib-rs/node-bindings/classic-node/src/version_registry.rs
    - ClassicLib-rs/node-bindings/classic-node/src/settings.rs
    - ClassicLib-rs/node-bindings/classic-node/src/shared.rs
    - ClassicLib-rs/node-bindings/classic-node/index.d.ts
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/settings.rs
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs
    - classic-cli/CMakeLists.txt
    - classic-gui/CMakeLists.txt
    - classic-gui/src/app/mainwindow.cpp
key-decisions:
  - Keep __test__/constants.spec.ts as the single root-export regression suite because the public Node surface remains flat.
  - Introduce classic::shared as the permanent CXX home for bridged GameId values instead of preserving a compatibility constants namespace.
patterns-established:
  - Node semantic exports live in shared.rs, settings.rs, and version_registry.rs while index.js remains the flat public surface.
  - CXX bridge module registration for new semantic namespaces requires synchronized lib.rs, build.rs, and both native CMakeLists files.
requirements-completed: [CNST-01, CNST-02]
duration: 30 min
completed: 2026-04-12
---

# Phase 03 Plan 03: Node and CXX constants redistribution Summary

**Node root exports now come from semantic modules while the CXX bridge retires `classic::constants` in favor of `classic::shared`, `classic::settings`, and `classic::version_registry`.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-04-12T00:30:00Z
- **Completed:** 2026-04-12T01:00:09Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments
- Folded the Node `constants.rs` content into `shared.rs`, `settings.rs`, and `version_registry.rs`, then regenerated `index.d.ts`.
- Deleted the CXX `constants.rs` bridge, added `classic::shared`, and redistributed GameId, YamlFile, and Fallout4Version bindings into semantic namespaces.
- Migrated `classic-gui/src/app/mainwindow.cpp` off `classic_cxx_bridge/constants.h` and `classic::constants::*` to prove a real production consumer uses the new surface.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fold Node constants into semantic modules and keep constants.spec.ts as the regression suite** - `ae98292c36bfb671ef8767b9175cbe7de5e8d09c` (feat)
2. **Task 2: Create classic::shared, retire classic::constants, and prove the old CXX surface is gone** - `a5b92a5457442c62dd8cc83efdca40be0f0333b4` (feat)

**Plan metadata:** pending summary commit

## Files Created/Modified
- `ClassicLib-rs/node-bindings/classic-node/src/shared.rs` - now owns `JsGameId`, `getGameName`, and `getAllGameIds`.
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` - now owns `JsYamlFile`, `getYamlFileDescription`, and `getAllYamlFiles`.
- `ClassicLib-rs/node-bindings/classic-node/src/version_registry.rs` - now owns `JsFallout4Version` and Fallout 4 version info helpers.
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` - regenerated typings after semantic relocation.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/shared.rs` - new `classic::shared` bridge module for `GameId`.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/settings.rs` - now owns `YamlFile`, `must_not_be_none_key`, and `settings_ignore_none_contains` bridge items.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` - now owns `Fallout4Version` bridge helpers and `is_null_version`.
- `classic-cli/CMakeLists.txt` / `classic-gui/CMakeLists.txt` - replaced `constants.rs` bridge generation with `shared.rs`.
- `classic-gui/src/app/mainwindow.cpp` - switched the live GUI consumer to `classic::shared` and `shared.h`.

## Decisions Made
- Kept `ClassicLib-rs/node-bindings/classic-node/__test__/constants.spec.ts` intact as the explicit regression suite for flat root exports.
- Treated `include/classic_cxx_bridge/` as generated output only, matching the plan and avoiding source-controlled header edits.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing classic-node dev dependencies before verification**
- **Found during:** Task 1 (Node binding verification)
- **Issue:** `bun run build` failed because the worktree had no installed Node package dependencies, so `napi` and `@types/node` were unavailable.
- **Fix:** Ran `bun install` in `ClassicLib-rs/node-bindings/classic-node` before re-running the required build/test commands.
- **Files modified:** none committed
- **Verification:** `bun run build`, `bun run test:bun`, and `bun run test:node` all passed afterward.
- **Committed in:** ae98292c36bfb671ef8767b9175cbe7de5e8d09c (task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Environment-only fix required to complete the planned verification; implementation scope stayed aligned with the plan.

## Issues Encountered
- Initial Node verification in this worktree failed until package dependencies were installed locally. After `bun install`, the required Node build and both runtime test suites passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Node and CXX binding surfaces are redistributed and validated, so Phase 03-04 can focus on docs/parity closure.
- No tracked code changes remain outside this plan summary.

## Self-Check: PASSED

- Verified `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/shared.rs` and `.planning/phases/03-constants-version-registry-merge/03-03-SUMMARY.md` exist.
- Verified task commits `ae98292c36bfb671ef8767b9175cbe7de5e8d09c` and `a5b92a5457442c62dd8cc83efdca40be0f0333b4` resolve in git.
