---
phase: 04-bounded-cache-replacement
plan: 04
subsystem: api
tags: [node, cache, napi, parity, typescript]
requires:
  - phase: 04-01
    provides: YAML cache stats and bounded core contract
  - phase: 04-02
    provides: settings cache stats and canonical field set
  - phase: 04-03
    provides: hash cache stats/reset helpers in Rust core
provides:
  - canonical Node cache stats for YAML, settings, and hash helpers
  - committed Node type definitions and runtime coverage metadata for cache helpers
  - parity and regression coverage for snake_case cache stats contracts
affects: [04-05, 04-06, node-bindings, parity]
tech-stack:
  added: []
  patterns: [snake_case NAPI cache DTOs, runtime-verified hash cache helper coverage, committed generated index.d.ts snapshots]
key-files:
  created: []
  modified:
    - ClassicLib-rs/node-bindings/classic-node/src/yaml.rs
    - ClassicLib-rs/node-bindings/classic-node/src/settings.rs
    - ClassicLib-rs/node-bindings/classic-node/src/fileio.rs
    - ClassicLib-rs/node-bindings/classic-node/index.d.ts
    - ClassicLib-rs/node-bindings/classic-node/__test__/yaml.spec.ts
    - ClassicLib-rs/node-bindings/classic-node/__test__/settings.spec.ts
    - ClassicLib-rs/node-bindings/classic-node/__test__/fileio.spec.ts
    - ClassicLib-rs/node-bindings/classic-node/__test__/parity_tier1.spec.ts
    - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json
    - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/tier1_regression.fixtures.ts
    - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json
    - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md
key-decisions:
  - "Preserve exact snake_case cache stat names in Node by using explicit NAPI naming overrides and typed return annotations instead of default camelCase generation."
  - "Classify the new hash cache helpers as runtime-verified Tier-2 aux coverage in the Node registry rather than leaving them newly uncovered."
  - "Validate bounded hash cache behavior through capacity and stats counters, not specific eviction-victim order."
patterns-established:
  - "Node cache adapters should mirror Rust core CacheStats through the exact fields hits, misses, hit_rate, size, and capacity."
  - "When index.d.ts cache signatures change, refresh both runtime coverage metadata and drift-regression fixtures in the same change unit."
requirements-completed: [CONS-03]
duration: 8 min
completed: 2026-04-05
---

# Phase 04 Plan 04: Node Cache Contract Alignment Summary

**Node now ships one canonical cache stats contract for YAML, settings, and hash helpers with committed snake_case TypeScript declarations and refreshed parity coverage metadata.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-06T04:50:24Z
- **Completed:** 2026-04-06T04:58:37Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Replaced Node YAML and settings cache stats drift with the canonical `hits`/`misses`/`hit_rate`/`size`/`capacity` contract.
- Added Node hash cache stats, reset, and clear helpers as thin adapters over `classic-file-io-core::hash::FileHasher`.
- Refreshed `index.d.ts`, runtime coverage registry entries, parity summaries, and drift regression fixtures so the Node contract matches the runtime surface.

## Task Commits

Each task was committed atomically:

1. **Task 1: Align Node YAML and settings stats to the canonical cache contract** - `e0c6d20c` (feat)
2. **Task 2: Add Node hash cache stats helpers and refresh the committed TypeScript and parity artifacts** - `185d216f` (feat)
3. **Follow-up fix: Refresh Node drift fixtures after full-suite verification** - `92552693` (fix)

## Files Created/Modified
- `ClassicLib-rs/node-bindings/classic-node/src/yaml.rs` - Switched YAML cache stats to the canonical five-field Node contract.
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` - Removed `keys` from `SettingsCacheStats` and preserved `hit_rate` as snake_case.
- `ClassicLib-rs/node-bindings/classic-node/src/fileio.rs` - Added hash cache stats/reset/clear exports backed directly by `FileHasher`.
- `ClassicLib-rs/node-bindings/classic-node/__test__/yaml.spec.ts` - Rewrote YAML cache assertions around the exact canonical field set.
- `ClassicLib-rs/node-bindings/classic-node/__test__/settings.spec.ts` - Rewrote settings cache assertions around `hit_rate` and `capacity`.
- `ClassicLib-rs/node-bindings/classic-node/__test__/fileio.spec.ts` - Added hash cache lifecycle, reset, and bounded-capacity coverage.
- `ClassicLib-rs/node-bindings/classic-node/__test__/parity_tier1.spec.ts` - Added parity smoke coverage for the canonical cache stats surfaces.
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` - Marked the new hash cache helpers as runtime-verified Tier-2 aux coverage.
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/tier1_regression.fixtures.ts` - Updated drift snapshots for the refreshed cache signatures.
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` - Committed the generated snake_case cache stats contract.
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` - Updated tracked/runtime totals after the new cache helper coverage.
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md` - Updated the human-readable runtime coverage totals.

## Decisions Made
- Used explicit NAPI naming controls to stop `hit_rate` from drifting back to `hitRate` in the runtime and generated TypeScript surface.
- Kept cache-specific extras outside the canonical stats objects; settings keys remain on `settingsCacheKeys()` and YAML stats no longer expose competing ad-hoc fields.
- Treated the new hash cache APIs as runtime-verified aux bindings so parity reports stay green without inventing new Rust-side business logic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Refreshed drift regression fixtures for the updated cache signatures**
- **Found during:** Final verification after Task 2
- **Issue:** `bun run test:bun` still expected the old `yamlGetCacheStats(): any` drift snapshot after the canonical cache contract landed.
- **Fix:** Updated `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/tier1_regression.fixtures.ts` and re-ran the full Bun/Node/parity verification set.
- **Files modified:** `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/tier1_regression.fixtures.ts`, `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json`, `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md`
- **Verification:** `bun run parity:gate:local`, `bun run test:bun`, and `bun run test:node` all passed afterward.
- **Committed in:** `92552693`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix only aligned the regression snapshot with the committed cache contract and parity outputs. No scope creep.

## Issues Encountered
- `bun run parity:gate:local` initially failed because the freshly generated `index.d.ts` and new hash cache exports had not yet been classified in runtime coverage metadata; adding the registry entry resolved the newly uncovered surfaces cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Python and C++ parity plans can now target the canonical cache stats surface as the Node contract source of truth.
- Node parity metadata is current, with 389 tracked surfaces and 280 runtime-verified surfaces after the cache helper refresh.

---
*Phase: 04-bounded-cache-replacement*
*Completed: 2026-04-05*

## Self-Check: PASSED

- FOUND: .planning/phases/04-bounded-cache-replacement/04-04-SUMMARY.md
- FOUND: e0c6d20c
- FOUND: 185d216f
- FOUND: 92552693
