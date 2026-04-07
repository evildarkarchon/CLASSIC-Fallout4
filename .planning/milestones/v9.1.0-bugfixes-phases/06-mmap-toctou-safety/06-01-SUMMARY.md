---
phase: 06-mmap-toctou-safety
plan: 01
subsystem: api
tags: [rust, memmap2, mmap, file-io, safety]
requires: []
provides:
  - read_file_mmap now uses MmapOptions::map_copy_read_only() for 1 MB+ files
  - read_file_mmap regression coverage preserves large-file UTF-8 and non-UTF-8 decode behavior
  - API and milestone docs now describe the locked Phase 6 mmap contract consistently
affects: [06-02, SAFE-05, classic-file-io-core]
tech-stack:
  added: []
  patterns: [conservative snapshot-style mmap wording, Rust-core-only file I/O safety changes]
key-files:
  created: [.planning/phases/06-mmap-toctou-safety/06-01-SUMMARY.md]
  modified:
    - ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs
    - docs/api/classic-file-io-core.md
    - .planning/PROJECT.md
    - .planning/REQUIREMENTS.md
key-decisions:
  - "Use MmapOptions::map_copy_read_only() on all platforms for the 1 MB+ read_file_mmap branch while preserving the existing decode path."
  - "Document the mmap change as a safer snapshot-style mitigation for this repo instead of claiming memmap2 removed all unsafe caveats."
patterns-established:
  - "Phase 6 mmap work keeps safety semantics in classic-file-io-core so bindings inherit the change unchanged."
  - "Active milestone docs must match the locked implementation contract in the same plan that lands the source change."
requirements-completed: [SAFE-05]
duration: 1 min
completed: 2026-04-06
---

# Phase 6 Plan 1: mmap contract alignment Summary

**Large-file reads now use `map_copy_read_only()` with unchanged text decoding and aligned Phase 6 safety documentation.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-06T10:08:08Z
- **Completed:** 2026-04-06T10:09:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Swapped the production 1 MB+ mmap branch to `MmapOptions::map_copy_read_only()` in Rust core.
- Extended `read_file_mmap` coverage to keep large UTF-8 and non-UTF-8 decode behavior stable.
- Updated API and milestone docs so SAFE-05 consistently points at `map_copy_read_only()`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Swap `read_file_mmap()` to `map_copy_read_only()` without changing the decode contract** - `ec972f4b` (feat)
2. **Task 2: Align API and milestone docs to the locked Phase 6 mmap contract** - `b197b33f` (docs)

**Plan metadata:** pending

## Files Created/Modified
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` - switched the large-file mapping constructor and expanded regression coverage.
- `docs/api/classic-file-io-core.md` - documented the 1 MB threshold and conservative `map_copy_read_only()` contract.
- `.planning/PROJECT.md` - aligned active milestone wording with the locked Phase 6 mmap decision.
- `.planning/REQUIREMENTS.md` - aligned SAFE-05 wording with `map_copy_read_only()`.

## Decisions Made
- Use `MmapOptions::map_copy_read_only()` for the production 1 MB+ branch on all platforms instead of keeping `Mmap::map()` or the older `map_copy()` wording.
- Keep documentation conservative: describe the change as this repo's safer snapshot-style mitigation, not as a blanket upstream safety guarantee.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed stale `Mmap` import after constructor swap**
- **Found during:** Task 1 (Swap `read_file_mmap()` to `map_copy_read_only()` without changing the decode contract)
- **Issue:** The initial constructor swap left `memmap2::Mmap` unused, causing the scoped Rust test build to fail under denied warnings.
- **Fix:** Removed the stale `Mmap` import and kept only `MmapOptions`.
- **Files modified:** `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs`
- **Verification:** `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture`
- **Committed in:** `ec972f4b` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix was required to get the Rust crate compiling cleanly after the planned mmap swap. No scope creep.

## Issues Encountered
- None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 plan 02 can now benchmark `map()`, `map_copy()`, and `map_copy_read_only()` against the committed production contract.
- SAFE-05 implementation and living docs are aligned for verifier review.

## Self-Check: PASSED

- Found summary file on disk.
- Verified task commits `ec972f4b` and `b197b33f` in git history.
