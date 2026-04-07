---
phase: 07-consistency-sweep
plan: 02
subsystem: api
tags: [rust, LazyLock, DashMap, quick_cache, cargo]
requires:
  - phase: 07-01
    provides: scanlog-core LazyLock and OnceLock migration removing the last owned code-level once_cell usage
provides:
  - registry and perf globals migrated to std::sync::LazyLock
  - owned direct once_cell manifest declarations removed from the Phase 7 target set
  - registry, perf, and settings API docs aligned to LazyLock and quick_cache wording
affects: [docs/api, Cargo.toml, registry, perf, consistency-sweep]
tech-stack:
  added: [serial_test]
  patterns: [std::sync::LazyLock globals with DashMap::new, same-change manifest and docs cleanup]
key-files:
  created: [.planning/phases/07-consistency-sweep/07-02-SUMMARY.md]
  modified:
    - ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs
    - ClassicLib-rs/business-logic/classic-perf-core/src/metrics.rs
    - ClassicLib-rs/Cargo.toml
    - ClassicLib-rs/business-logic/classic-registry-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-perf-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-yaml-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml
    - ClassicLib-rs/business-logic/classic-scangame-core/Cargo.toml
    - docs/api/classic-registry-core.md
    - docs/api/classic-perf-core.md
    - docs/api/classic-settings-core.md
key-decisions:
  - "Use std::sync::LazyLock with DashMap::new for registry and perf globals to match the Phase 4/5 repo pattern without API churn."
  - "Treat Phase 7 success as removal of owned direct once_cell usage and manifest declarations, while allowing transitive lockfile once_cell entries to remain."
patterns-established:
  - "Lazy global migration: replace direct once_cell statics with std::sync::LazyLock while preserving existing global-state tests."
  - "Consistency sweep: update source, manifests, and contributor docs in the same change so dependency cleanup and docs stay aligned."
requirements-completed: [CONS-01]
duration: 5 min
completed: 2026-04-06
---

# Phase 07 Plan 02: Consistency Sweep Summary

**Registry and perf global stores now use std::sync::LazyLock, and the remaining owned direct once_cell manifest/docs references were removed from the Phase 7 target set.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T11:54:43Z
- **Completed:** 2026-04-06T11:59:44Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Added RED-phase tests that proved the registry and perf globals had not yet moved to `LazyLock`.
- Migrated `REGISTRY` and `METRICS` to `std::sync::LazyLock` while keeping their `DashMap::new` lazy initialization behavior and crate tests green.
- Removed direct `once_cell` declarations from the workspace target manifests and updated the touched API docs to describe `LazyLock` and `quick_cache` internals instead.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: add failing LazyLock migration checks** - `36be4cdf` (test)
2. **Task 1 GREEN: migrate registry and perf globals** - `9c477af3` (feat)
3. **Task 2: remove direct once_cell manifests and align docs** - `67d18ea3` (chore)

**Plan metadata:** pending final docs/state commit

_Note: Task 1 used TDD and produced separate RED and GREEN commits._

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs` - migrated the process-global registry map to `LazyLock` and added migration audit coverage.
- `ClassicLib-rs/business-logic/classic-perf-core/src/metrics.rs` - migrated the process-global metrics map to `LazyLock` and added migration audit coverage.
- `ClassicLib-rs/Cargo.toml` - removed the workspace `once_cell` declaration and retained a root `serial_test` entry needed by the Phase 7 manifest contract.
- `ClassicLib-rs/business-logic/classic-registry-core/Cargo.toml` - removed the crate-level direct `once_cell` dependency.
- `ClassicLib-rs/business-logic/classic-perf-core/Cargo.toml` - removed the crate-level direct `once_cell` dependency.
- `ClassicLib-rs/business-logic/classic-yaml-core/Cargo.toml` - removed the stale workspace `once_cell` dependency reference.
- `ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml` - removed the stale workspace `once_cell` dependency reference.
- `ClassicLib-rs/business-logic/classic-scangame-core/Cargo.toml` - removed the stale workspace `once_cell` dependency reference.
- `docs/api/classic-registry-core.md` - updated contributor guidance from `once_cell::sync::Lazy` to `std::sync::LazyLock`.
- `docs/api/classic-perf-core.md` - updated contributor guidance from `once_cell::sync::Lazy` to `std::sync::LazyLock`.
- `docs/api/classic-settings-core.md` - updated dependency notes to describe the bounded `quick_cache` + `LazyLock` cache implementation.

## Decisions Made
- Used `std::sync::LazyLock` with the existing `DashMap::new` constructor shape for both globals so the migration stayed one-for-one and repo-consistent.
- Scoped the dependency cleanup to owned direct manifest declarations and contributor docs; transitive `Cargo.lock` references were not treated as plan failures.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The first attempt at the combined PowerShell audit/build verification command had an extra closing brace; rerunning the corrected command completed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 7 now has both plan summaries on disk and is ready for roadmap/state completion.
- No additional Phase 7 code work remains after the workspace verification pass.

## Self-Check: PASSED

- FOUND: `.planning/phases/07-consistency-sweep/07-02-SUMMARY.md`
- FOUND: `36be4cdf`
- FOUND: `9c477af3`
- FOUND: `67d18ea3`
