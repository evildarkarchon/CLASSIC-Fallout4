---
phase: 08-workspace-and-infrastructure
plan: 01
subsystem: infra
tags: [cargo, workspace-dependencies, slint, gui-bridge, rust]
requires: []
provides:
  - Workspace-owned `winreg` and `phf` dependency pins for shared Rust crates
  - Removal of the `classic-shared-core` crate-local `zerovec` workaround
  - Updated `classic-shared-core` API docs for the post-workaround `gui-bridge` contract
affects: [INFRA-03, INFRA-05, rust-workspace, docs]
tech-stack:
  added: []
  patterns: [Cargo workspace dependency inheritance, proof-based gui-bridge validation]
key-files:
  created: []
  modified:
    - ClassicLib-rs/Cargo.toml
    - ClassicLib-rs/business-logic/classic-path-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-constants-core/Cargo.toml
    - ClassicLib-rs/foundation/classic-shared-core/Cargo.toml
    - docs/api/classic-shared-core.md
key-decisions:
  - "Promoted `winreg` and `phf` into `ClassicLib-rs/Cargo.toml` without changing pinned versions so member crates only inherit ownership."
  - "Removed the `classic-shared-core` `zerovec` workaround outright and documented `gui-bridge` as building directly from workspace Slint dependencies after build proof passed."
patterns-established:
  - "Shared Rust dependency versions live in `[workspace.dependencies]`, including target-gated member dependencies."
  - "Phase-scoped workaround cleanup should be validated by direct crate proof before preserving any historical compatibility note."
requirements-completed: [INFRA-01, INFRA-02, INFRA-04]
duration: 13min
completed: 2026-04-06
---

# Phase 8 Plan 01: Workspace dependency ownership and gui-bridge cleanup Summary

**Workspace-owned `winreg`/`phf` pins plus removal of the `classic-shared-core` `zerovec` workaround with validated `gui-bridge` docs.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-06T23:47:41Z
- **Completed:** 2026-04-07T00:00:40Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Centralized `winreg` and `phf` version ownership in the Rust workspace root.
- Switched `classic-path-core` and `classic-constants-core` to inherit those shared dependencies via `workspace = true`.
- Removed the crate-local `zerovec` workaround from `classic-shared-core` and updated the API guide to match the validated `gui-bridge` state.

## Task Commits

Each task was committed atomically:

1. **Task 1: Promote `winreg` and `phf` to workspace-owned dependency declarations** - `59f9c041` (chore)
2. **Task 2: Remove the `zerovec` workaround and any directly blocking stale gui-bridge code** - `ae96fc81` (fix)

**Plan metadata:** pending

## Files Created/Modified
- `ClassicLib-rs/Cargo.toml` - Added workspace-owned `phf` and `winreg` declarations.
- `ClassicLib-rs/business-logic/classic-path-core/Cargo.toml` - Inherited `winreg` from the workspace in the Windows-only dependency block.
- `ClassicLib-rs/business-logic/classic-constants-core/Cargo.toml` - Inherited `phf` from the workspace.
- `ClassicLib-rs/foundation/classic-shared-core/Cargo.toml` - Removed the crate-local `zerovec` workaround from dev-dependencies.
- `docs/api/classic-shared-core.md` - Documented the post-workaround `gui-bridge` dependency state.

## Decisions Made
- Promoted `winreg` and `phf` by ownership only, keeping existing versions unchanged to preserve the plan's scoped manifest cleanup.
- Kept the `gui-bridge` cleanup local to `classic-shared-core` and its contributor docs because direct feature and workspace proof showed the workaround was no longer required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Loaded the Visual Studio developer environment for release workspace verification**
- **Found during:** Task 2 (Remove the `zerovec` workaround and any directly blocking stale gui-bridge code)
- **Issue:** The repo-wide `cargo test --workspace --release --all-features` proof failed from the plain shell because MSVC environment variables were not initialized for native dependencies.
- **Fix:** Re-ran the release workspace verification through `VsDevCmd.bat` so the required MSVC toolchain environment was available.
- **Files modified:** None
- **Verification:** `cargo test --workspace --release --all-features --manifest-path ClassicLib-rs/Cargo.toml` passed from the VS developer environment.
- **Committed in:** n/a (verification-only environment fix)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation was limited to verification environment setup and did not expand code scope.

## Issues Encountered
- Plain-shell release verification hit native-toolchain environment gaps; using the Visual Studio developer environment resolved the proof requirement without code changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The workspace dependency source of truth is aligned for Phase 8 follow-up work.
- `classic-shared-core` no longer carries the targeted workaround, so later infrastructure work can build on the cleaned dependency surface.

## Self-Check: PASSED

---
*Phase: 08-workspace-and-infrastructure*
*Completed: 2026-04-06*
