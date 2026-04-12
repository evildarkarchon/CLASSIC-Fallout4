---
phase: 07-crate-relocation-and-path-rewire
plan: 02
subsystem: rust-workspace
tags: [cargo, workspace, rust, relocation, bindings, benchmarks]
requires:
  - phase: 07-crate-relocation-and-path-rewire
    provides: relocation audit artifact and validation scaffold
provides:
  - repo-root layer directories for all live Rust crates
  - root-relative workspace member list with preserved crate-local Cargo paths
  - relocated benchmark and audit surfaces that still resolve from the new layout
affects: [07-03, phase-08, cargo-workspace, benchmarks, bindings]
tech-stack:
  added: []
  patterns: [whole-layer strip-prefix relocation, minimal path rewrites, history-preserving git mv]
key-files:
  created: [.planning/phases/07-crate-relocation-and-path-rewire/07-02-SUMMARY.md]
  modified: [Cargo.toml, foundation/, business-logic/, cpp-bindings/, node-bindings/, python-bindings/, ui-applications/, validate_stubs.py, tests/planning/test_phase06_validation.py, benches/common/mod.rs, benches/common/config.rs]
key-decisions:
  - "Move the six Rust layer directories intact with git mv and strip only the ClassicLib-rs/ prefix from root workspace members."
  - "Keep representative Cargo manifest path edges unchanged when the preserved directory geometry still resolves after the move."
  - "Fix only repo-relative helper includes and transitional audit assumptions that actually broke because moved crates now sit one level closer to repo root."
patterns-established:
  - "When a whole subtree moves closer to repo root, benchmark and test include_str/#[path] edges need the same minimal break-fix sweep as manifests."
  - "Legacy-compatible helper normalization may continue to accept ./ClassicLib-rs input while resolving back to the live repo-root workspace."
requirements-completed: []
duration: current session
completed: 2026-04-12
---

# Phase 7 Plan 2: Crate relocation and path rewire summary

**All six Rust layer directories now live at repo root, the workspace member list is root-relative, and representative Cargo manifests still resolve without blanket path churn.**

## Performance

- **Duration:** current session
- **Completed:** 2026-04-12
- **Tasks:** 2

## Accomplishments

- Moved `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/` from `ClassicLib-rs/` to repo root with `git mv`.
- Rewrote the root `Cargo.toml` workspace members from `ClassicLib-rs/...` to root-relative paths for all 37 packages.
- Verified that representative binding/TUI manifests kept their existing `../../foundation/...` and `../../business-logic/...` path relationships unchanged after the move.
- Rebased broken repo-relative benchmark helper and doc include paths exposed by the move, and aligned Phase 6 audit/helper expectations with the new repo-root layout.

## Task Commits

No task commits were created. The user did not request commits during execution.

## Files Created/Modified

- `Cargo.toml` - root workspace member list rewritten to repo-root-relative crate paths.
- `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, `ui-applications/` - relocated intact from `ClassicLib-rs/`.
- `validate_stubs.py` - legacy input normalization now resolves to the live repo-root workspace after relocation.
- `tests/planning/test_phase06_validation.py` - Phase 6 audit updated to the relocated crate layout.
- `business-logic/*/benches/*.rs`, `python-bindings/*/benches/*.rs`, `benches/common/{mod,config}.rs`, and `business-logic/classic-scanlog-core/tests/once_lock_migration_audit.rs` - repo-relative include paths rebased to the new directory depth.

## Decisions Made

- Preserved Cargo manifest `path =` edges where relocation kept the same relative geometry.
- Limited rewrites to the root member list and the move-exposed include/helper paths that actually failed under all-target validation.
- Treated the benchmark and audit include-path rebases as relocation fallout, not as scope expansion into broader modernization.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rebased broken repo-relative include paths exposed by the move**
- **Found during:** post-move validation
- **Issue:** Several moved benchmark/test sources still referenced repo-root helpers with pre-move `../../../../...` paths, which became one directory too deep after relocation.
- **Fix:** Rebased those include paths to `../../../...` only where validation proved they were broken.
- **Verification:** `cargo check --workspace --all-targets`

## Issues Encountered

- The crate move itself preserved Cargo manifest relationships, but repo-relative helper includes in moved benchmark and test sources needed a narrow follow-up sweep.

## User Setup Required

None.

## Next Phase Readiness

- All live crates now exist under repo-root layer directories with a working root workspace member list.
- Ready for `07-03-PLAN.md` to finalize the relocation audit and close the `ClassicLib-rs` authority boundary.

## Self-Check: PASSED

- Found all six moved layer directories at repo root.
- Confirmed `cargo metadata --format-version 1 --no-deps` reports 37 workspace members from repo-root layer paths.

---
*Phase: 07-crate-relocation-and-path-rewire*
*Completed: 2026-04-12*
