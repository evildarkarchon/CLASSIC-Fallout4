---
phase: 07-consistency-sweep
plan: 01
subsystem: api
tags: [rust, lazylock, oncelock, scanlog, docs]
requires:
  - phase: 04-bounded-cache-replacement
    provides: repo-standard LazyLock static patterns for Rust core crates
  - phase: 05-pattern-caching-and-performance
    provides: scanlog-local LazyLock examples and cache validation style
provides:
  - classic-scanlog-core lazy statics migrated to std::sync::LazyLock
  - RecordScanner per-instance matcher caches migrated to std::sync::OnceLock
  - classic-scanlog-core direct once_cell dependency removed with aligned API docs
affects: [07-02, classic-scanlog-core, docs/api]
tech-stack:
  added: []
  patterns: [std::sync::LazyLock for module statics, std::sync::OnceLock for per-instance deferred caches]
key-files:
  created:
    - ClassicLib-rs/business-logic/classic-scanlog-core/tests/lazylock_static_audit.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/tests/once_lock_migration_audit.rs
  modified:
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/report.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/formid_analyzer.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/formid.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/record_scanner.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml
    - docs/api/classic-scanlog-core.md
key-decisions:
  - "Used source-backed TDD audit tests to lock the std LazyLock/OnceLock migration contract before implementation."
  - "Kept RecordScanner on per-instance get_or_init semantics by swapping OnceCell to OnceLock instead of redesigning construction flow."
patterns-established:
  - "Use LazyLock::new(...) for classic-scanlog-core module statics instead of once_cell::sync::Lazy."
  - "Use OnceLock fields when lazy initialization depends on instance data and must stay behind get_or_init calls."
requirements-completed: [CONS-01]
duration: 7h 8m
completed: 2026-04-06
---

# Phase 7 Plan 1: classic-scanlog-core once_cell sweep Summary

**classic-scanlog-core now uses std::sync::LazyLock and OnceLock for its remaining lazy state, with matching crate-manifest cleanup and updated contributor docs.**

## Performance

- **Duration:** 7h 8m
- **Started:** 2026-04-06T11:41:27Z
- **Completed:** 2026-04-06T18:49:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Replaced the remaining scanlog module statics that directly used `once_cell::sync::Lazy` with `std::sync::LazyLock`.
- Migrated `RecordScanner` matcher caches to `std::sync::OnceLock` while preserving lazy per-instance `get_or_init` behavior.
- Removed the crate's direct `once_cell` dependency and aligned the scanlog API guide with the new std primitives.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace the remaining scanlog lazy statics with `std::sync::LazyLock`** - `2baba4ea` (test), `6cb70b98` (feat)
2. **Task 2: Replace `RecordScanner` field caches with `OnceLock` and remove the scanlog direct manifest dependency** - `ab6a470f` (test), `a297f616` (feat)

**Plan metadata:** recorded in the final docs commit for this plan.

_Note: This plan used TDD red/green commits for both tasks._

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-scanlog-core/tests/lazylock_static_audit.rs` - failing-then-passing audit for std `LazyLock` migration coverage.
- `ClassicLib-rs/business-logic/classic-scanlog-core/tests/once_lock_migration_audit.rs` - failing-then-passing audit for `RecordScanner`, docs, and manifest cleanup.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` - migrated `GLOBAL_FCX_HANDLER` to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` - migrated parser statics to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` - migrated version regex static to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs` - migrated plugin regex static to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/report.rs` - migrated `STRING_POOL` to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` - migrated local module regex static to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/formid_analyzer.rs` - migrated formid regex static to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/formid.rs` - migrated formid regex statics to `LazyLock`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/record_scanner.rs` - migrated matcher fields to `OnceLock` and added reuse coverage.
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` - removed direct `once_cell` dependency.
- `docs/api/classic-scanlog-core.md` - documented `RecordScanner`'s std `OnceLock` cache behavior.

## Decisions Made
- Used TDD audit tests to lock the exact migration surface before implementation because the plan's success criteria are source- and manifest-specific.
- Preserved `RecordScanner`'s existing `get_or_init` matcher flow so the migration stayed correctness-preserving and did not broaden into a structural refactor.
- Limited validation to the touched Rust crate and source/doc audit because Phase 7 Plan 1 does not change binding-visible contracts.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `cargo test` briefly waited on the shared Rust artifact directory lock, but the runs completed successfully without requiring code changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `classic-scanlog-core` no longer has direct `once_cell` usage in source, docs, or its manifest.
- Phase 07 Plan 02 can now finish the remaining registry/perf/workspace-side sweep and broader manifest cleanup.

## Self-Check: PASSED

---
*Phase: 07-consistency-sweep*
*Completed: 2026-04-06*
