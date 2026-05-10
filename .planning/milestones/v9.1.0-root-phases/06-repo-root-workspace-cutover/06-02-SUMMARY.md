---
phase: 06-repo-root-workspace-cutover
plan: 02
subsystem: infra
tags: [cargo, benchmarks, criterion, rust, planning-audit]
requires:
  - phase: 06-01
    provides: repo-root workspace shell and Phase 6 benchmark-audit scaffold
provides:
  - repo-root criterion and benchmark threshold configuration
  - repo-root shared benchmark helper modules under benches/common
  - repaired crate-level benchmark helper includes plus audit coverage
affects: [06-03, benchmarks-ci, rust-benchmarks, phase-06-validation]
tech-stack:
  added: []
  patterns: [repo-root benchmark support ownership, relative #[path] rewires for shared bench helpers, benchmark relocation audit coverage]
key-files:
  created: [.planning/phases/06-repo-root-workspace-cutover/06-02-SUMMARY.md]
  modified: [criterion.toml, benchmark-config.yaml, benches/common/mod.rs, benches/common/config.rs, benches/common/db_fixtures.rs, benches/common/fixtures.rs, ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs, ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs, ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs, ClassicLib-rs/business-logic/classic-database-core/benches/database_benchmarks.rs, ClassicLib-rs/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs, ClassicLib-rs/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs, tests/planning/test_phase06_validation.py]
key-decisions:
  - "Keep benchmark support files owned only at repo root so Criterion config and shared helper discovery have one canonical location during Phase 6."
  - "Standardize crate-level benchmark helper imports on ../../../../benches/common/* so every known benchmark keeps resolving after the repo-root move."
patterns-established:
  - "Benchmark support relocation: move criterion.toml, benchmark-config.yaml, and benches/common/* together and delete legacy copies in the same cutover."
  - "Benchmark audit tripwire: Phase 6 validation asserts both repo-root support-file ownership and the post-move #[path] include targets."
requirements-completed: [ROOT-01, ROOT-02]
duration: 1 min
completed: 2026-04-12
---

# Phase 06 Plan 02: Move benchmark-owned support files to repo root and remove old copies Summary

**Repo-root Criterion config, repo-root shared benchmark helpers, and rewired crate-level benchmark includes backed by a Phase 6 relocation audit**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-12T12:47:26Z
- **Completed:** 2026-04-12T12:48:10Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Verified the benchmark support set now lives only at repo root with `criterion.toml`, `benchmark-config.yaml`, and `benches/common/*` using the real checked-in contents.
- Verified every known crate-level benchmark helper import now targets the repo-root `benches/common/*` location.
- Confirmed the Phase 6 planning audit catches both legacy benchmark-support copies and stale pre-move helper paths.

## Task Commits

Each task was committed atomically:

1. **Task 1: Relocate the benchmark support set to repo root using the real file contents** - `518b86f9` (feat)
2. **Task 2: Sweep and repair benchmark helper include paths after the move** - `c9e04ff7` (fix)

**Additional auto-fix:** `1d0b8300` (fix)

**Plan metadata:** pending docs commit created after summary/state updates.

## Files Created/Modified
- `criterion.toml` - Repo-root Criterion workspace configuration with `./target/criterion` output.
- `benchmark-config.yaml` - Repo-root benchmark regression thresholds used by the workflow audit.
- `benches/common/mod.rs` - Shared repo-root benchmark helper entrypoint.
- `benches/common/config.rs` - Shared Criterion mode/config helper for workspace benchmarks.
- `benches/common/db_fixtures.rs` - Shared deterministic SQLite fixture generator for benchmark datasets.
- `benches/common/fixtures.rs` - Shared benchmark fixture loading and synthetic-data helpers.
- `ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs` - Rewired shared-helper include to repo-root benches/common.
- `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs` - Rewired shared-helper and DB fixture includes to repo root.
- `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` - Rewired shared-helper include to repo root.
- `ClassicLib-rs/business-logic/classic-database-core/benches/database_benchmarks.rs` - Rewired shared-helper and DB fixture includes to repo root.
- `ClassicLib-rs/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs` - Rewired shared-helper include to repo root.
- `ClassicLib-rs/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs` - Rewired shared-helper include to repo root.
- `tests/planning/test_phase06_validation.py` - Added benchmark support and include-path audits for the Phase 6 cutover.

## Decisions Made
- Treated repo root as the only valid home for benchmark support files so there is no lingering `ClassicLib-rs` ambiguity in workspace-owned benchmark discovery.
- Kept the benchmark sweep scoped to source-level viability and audit coverage instead of expanding Phase 6 into a benchmark-CI green-status gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reordered touched benchmark imports to satisfy rustfmt after include rewires**
- **Found during:** Task 2 (Sweep and repair benchmark helper include paths after the move)
- **Issue:** The helper-path rewrite left a few touched benchmark files with import ordering that failed repo formatting expectations.
- **Fix:** Reordered Criterion imports in the touched benchmark files without changing behavior.
- **Files modified:** `ClassicLib-rs/business-logic/classic-settings-core/benches/yaml_benchmarks.rs`, `ClassicLib-rs/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs`, `ClassicLib-rs/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs`
- **Verification:** `python -m pytest tests/planning/test_phase06_validation.py -q -k "benchmark_support_set"`
- **Committed in:** `1d0b8300` (part of task completion)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The auto-fix kept the benchmark rewire commits aligned with repo formatting expectations without changing scope.

## Issues Encountered
- The task commits for this plan were already present on the working branch; I verified the benchmark-support audit and finalized execution metadata instead of duplicating code commits.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 benchmark support ownership is now anchored at repo root with validation coverage for stale legacy paths.
- Ready for `06-03-PLAN.md` to finish workflow/doc rewires and the clean repo-root Cargo proof.

## Self-Check: PASSED
- FOUND: `.planning/phases/06-repo-root-workspace-cutover/06-02-SUMMARY.md`
- FOUND: `518b86f9`
- FOUND: `c9e04ff7`
- FOUND: `1d0b8300`

---
*Phase: 06-repo-root-workspace-cutover*
*Completed: 2026-04-12*
