---
phase: 03-constants-version-registry-merge
plan: 01
subsystem: api
tags: [rust, cargo, constants, version-registry, settings, shared-core]
requires:
  - phase: 02-crashgen-config-merge
    provides: crashgen/config merge precedent for crate deletion flow
provides:
  - Fallout4Version and NULL_VERSION from classic-version-registry-core
  - YamlFile settings helpers from classic-settings-core
  - GameId from classic-shared-core and a workspace free of classic-constants-core
affects: [03-02, 03-03, 03-04, bindings, docs]
tech-stack:
  added: []
  patterns: [semantic crate ownership, flat crate-root re-exports, pre-delete manifest sweep]
key-files:
  created:
    - ClassicLib-rs/business-logic/classic-version-registry-core/src/fallout4_version.rs
    - ClassicLib-rs/business-logic/classic-settings-core/src/yaml_file.rs
    - ClassicLib-rs/foundation/classic-shared-core/src/game_id.rs
  modified:
    - ClassicLib-rs/Cargo.toml
    - ClassicLib-rs/business-logic/classic-version-core/src/lib.rs
    - ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs
    - ClassicLib-rs/business-logic/classic-web-core/src/lib.rs
    - ClassicLib-rs/ui-applications/classic-tui/src/app.rs
key-decisions:
  - "Wave 1 kept binding source rewrites deferred but removed every live workspace Cargo edge to classic-constants-core first."
  - "classic-resource-core had no live constants usage, so its dependency was removed instead of replaced."
patterns-established:
  - "Redistribute multi-domain constants into semantic owner crates and re-export them at the crate root."
  - "Run targeted Rust checks plus structural sweeps before deleting a source crate needed by later binding waves."
requirements-completed: [CNST-01, CNST-02, CNST-03]
duration: 9 min
completed: 2026-04-12
---

# Phase 3 Plan 1: Constants Redistribution Summary

**Fallout4Version, YamlFile settings helpers, and GameId now live in their semantic Rust crates while the workspace no longer depends on `classic-constants-core`.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-12T00:33:45Z
- **Completed:** 2026-04-12T00:43:10Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments
- Added `fallout4_version.rs`, `yaml_file.rs`, and `game_id.rs` with migrated inline tests in their destination crates.
- Rewired Rust consumers and live workspace manifests to semantic owner crates.
- Removed `classic-constants-core` from workspace membership and deleted the crate.

## Task Commits

Each task was committed atomically:

1. **Task 1: Move constants slices and migrate inline coverage before deleting the source crate** - `9e52bf8d` (feat)
2. **Task 2: Sweep Rust consumers, rewrite workspace Cargo edges, and delete classic-constants-core** - `5d7f0997` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/fallout4_version.rs` - new home for `Fallout4Version` and `NULL_VERSION` plus migrated tests
- `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_file.rs` - new home for `YamlFile`, `SETTINGS_IGNORE_NONE`, and `must_not_be_none`
- `ClassicLib-rs/foundation/classic-shared-core/src/game_id.rs` - new home for `GameId`
- `ClassicLib-rs/Cargo.toml` - removed `classic-constants-core` workspace member
- `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` - re-exported version metadata directly from version-registry-core
- `ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs` - switched to `classic_shared_core::GameId`
- `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` - switched URL helpers and tests to `classic_shared_core::GameId`
- `ClassicLib-rs/ui-applications/classic-tui/src/app.rs` - switched TUI version imports to version-registry-core

## Decisions Made
- Kept Wave 1 validation focused on destination crates and affected Rust consumers because Python/Node/CXX source rewrites are intentionally deferred to 03-02 and 03-03.
- Removed the unused `classic-resource-core` dependency instead of inventing a replacement crate edge.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed stale literal references that tripped the structural sweep**
- **Found during:** Task 2 (consumer and manifest sweep)
- **Issue:** The plan's grep-backed verification still found `classic-constants-core` in a binding manifest description and `classic_constants_core` in a TUI source comment after the functional migration was complete.
- **Fix:** Updated the lingering description/comment text to the new semantic owners so the structural cleanup assertion matched the real workspace state.
- **Files modified:** `ClassicLib-rs/python-bindings/classic-constants-py/Cargo.toml`, `ClassicLib-rs/ui-applications/classic-tui/src/app.rs`
- **Verification:** Re-ran the plan's Python structural sweep successfully.
- **Committed in:** `5d7f0997`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Verification-only cleanup; no scope creep beyond making the workspace sweep truthful.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for `03-02-PLAN.md` to split Python binding sources while building on the new Cargo ownership.
- Wave 1 intentionally leaves Python/Node/CXX source imports for later plans, so targeted Rust checks are the expected boundary proof here.

## Self-Check: PASSED

---
*Phase: 03-constants-version-registry-merge*
*Completed: 2026-04-12*
