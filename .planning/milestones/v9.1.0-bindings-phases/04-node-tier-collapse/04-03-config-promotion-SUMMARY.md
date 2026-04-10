---
phase: 04-node-tier-collapse
plan: 03
subsystem: node-parity
tags: [node-parity, napi-rs, tier-collapse, config, proxy-rows, rust-suffix, real-shape-tests, runtime-coverage]

# Dependency graph
requires:
  - phase: 04-node-tier-collapse
    plan: 02
    provides: "66 scanlog tier1Mappings rows; proxy-row-aware diff pipeline (_effective_rust_symbol); registry bump pattern; deferred backlog regeneration pattern"
provides:
  - "34 new tier1Mappings rows (11 @rust proxy + 23 normal) covering all config deferred entries except ModConflictEntry (Issue 4 carve-out for Plan 5)"
  - "config.deferred dropped from 26 -> 1 in runtime_coverage_summary.json (1 = ModConflictEntry, reserved for Plan 5 per Issue 4)"
  - "4 new describe blocks in config.spec.ts with real-shape assertions (~100 lines)"
  - "1 cross-runtime D-TEST-02 test in runtime.node.test.mjs for config cache/detection APIs"
  - "_add_plan03_normal_rows.py helper script for repeatable normal-row authoring"
affects:
  - "04-04-version-registry-and-pe-version (proxy row pattern reusable for version sub-module Rust-only symbols)"
  - "04-05-aux-promotion (ModConflictEntry normal row is Plan 5's responsibility per Issue 4; _add_plan03_normal_rows.py pattern reusable)"
  - "04-06-tier2-cleanup-cascade (Plan 6 clears ModConflictEntry's last deferred entry + deletes gap_type branches)"

# Tech tracking
tech-stack:
  added: []  # No new dependencies
  patterns:
    - "H2 cross-crate routing via live rust_api_surface.json lookup: all 11 proxy rows resolved to classic-config-core despite plan expectation of a split with classic-crashgen-settings-core"
    - "rustSymbol for NAPI wrapper functions mapped to the core type/const they delegate to (e.g., getHashCacheStats -> FileHasher, getDefaultCacheCleanupInterval -> DEFAULT_CACHE_CLEANUP_INTERVAL_SECS)"
    - "Real-shape smoke tests with typed-field assertions: every interface test checks at least one runtime-observable field, not {} as Type stubs"
    - "Registry selector bump reuses existing node-tier1-config entry with contractCount and contractIdsHash updates"

key-files:
  created:
    - ".planning/phases/04-node-tier-collapse/_add_plan03_normal_rows.py (normal row authoring script for 23 config entries)"
  modified:
    - "docs/implementation/node_api_parity/baseline/parity_contract.json (327 -> 361 tier1Mappings: +11 proxy + +23 normal)"
    - "docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md} (refreshed: 11 fewer rust_unmapped config gaps, 23 fewer node_unmapped config gaps)"
    - "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md} (config runtime_verified 50 -> 87; deferred 26 -> 1)"
    - "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json (config entries 26 -> 1)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json (node-tier1-config: contractCount 50 -> 84, contractIdsHash recomputed via _stable_id_hash)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/config.spec.ts (+4 describe blocks with real-shape assertions ~100 lines)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs (+1 cross-runtime D-TEST-02 test ~40 lines)"

key-decisions:
  - "All 11 proxy rows route to classic-config-core (not classic-crashgen-settings-core): live rust_api_surface.json shows all symbols under classic-config-core because lib.rs re-exports the crashgen types from yamldata module"
  - "ModConflictEntry excluded from proxy rows per Issue 4 reconciliation: JsModConflictEntry exists as a NAPI binding (classic-node/src/config.rs line 44); Plan 5 promotes it as a normal row"
  - "config.deferred == 1 (not 0): the 1 remaining entry is ModConflictEntry (Issue 4 carve-out); Plan 5 absorbs it"
  - "rustSymbol for NAPI wrapper functions uses the core type/const they delegate to, not the NAPI function name (which doesn't exist in rust_api_surface.json)"
  - "Registry bump strategy: update existing node-tier1-config selector (contractCount 50 -> 84) rather than creating a Plan-3-specific entry"

patterns-established:
  - "H2 routing reconciliation: when plan expects cross-crate routing but live surface shows single-crate, the surface is authoritative"
  - "NAPI wrapper function rustSymbol mapping: use the core symbol the wrapper delegates to (FileHasher for hash cache functions, DEFAULT_CACHE_CLEANUP_INTERVAL_SECS for the getter function, etc.)"
  - "Per-task deferred backlog regeneration: each promotion task regenerates deferred_runtime_backlog.json from the fresh diff report"

requirements-completed: []  # NODE-02..NODE-05 addressed but not completed (they span all Plans 2-5)

# Metrics
duration: 18min
completed: 2026-04-10
---

# Phase 04 Plan 3: Config Promotion Summary

**Promoted 34 config deferred entries to enforced Tier-1 contract rows (11 @rust proxy + 23 normal) with real-shape bun:test and node:test smoke tests; config deferred dropped from 26 to 1 (ModConflictEntry reserved for Plan 5 per Issue 4)**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-10T00:06:12Z
- **Completed:** 2026-04-10T00:24:34Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 10 (1 created, 9 modified)

## Accomplishments

- 11 `@rust`-suffix proxy rows cover every Rust-only config public symbol (9 classes/enums: ConfigError, CoreModEntry, CoreModExclude, CrashgenEntryRaw, ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackCountRule, SuspectStackRule; 2 free functions: format_registry_game_version, resolve_registry_version_info) in `parity_contract.json`. Each row has `rustCrate: "classic-config-core"`, `rustSymbol: "<Symbol>@rust"`, and intentionally no `nodeExport` field. ModConflictEntry excluded per Issue 4 (Plan 5 promotes it).
- 23 normal `nodeExport` rows for the Node-exposed config exports: 3 consts (DEFAULT_CACHE_CLEANUP_INTERVAL, DEFAULT_CACHE_CLEANUP_THRESHOLD, DEFAULT_QUERY_CACHE_CAPACITY), 9 interfaces (HashCacheStats, JsAnalysisConfig, JsConfigIssue, JsFcxConfigIssue, JsGameScanConfig, JsIntegrityConfig, JsPathDetectionResult, JsTomlConfigIssue, JsXseConfig), 1 const_enum (JsEnbConfigResult), 1 class (JsConfigDuplicateDetector), 9 functions (clearHashCache, detectConfigDuplicates, getDefaultCacheCleanupInterval, getDefaultCacheCleanupThreshold, getDefaultQueryCacheCapacity, getFcxConfigIssues, getHashCacheStats, needsPathDetection, resetHashCacheStats).
- `config.deferred` dropped from 26 to 1 in `runtime_coverage_summary.json`. The sole remaining entry is `ModConflictEntry` (Issue 4 reconciliation -- Plan 5 Task 1 promotes it as a normal row with `rustCrate: classic-config-core`).
- `runtime_coverage_registry.json` `node-tier1-config` selector bumped from `contractCount: 50` to `84` with recomputed `contractIdsHash` via `_stable_id_hash` (full 64-char SHA-256 hex, no truncation per D-HASH-01).
- MEDIUM concern resolved: 4 new `describe` blocks in `config.spec.ts` (~100 lines) with **real-shape assertions** -- cache constants verified as positive numbers with getter parity, hash cache stats verified with 5 typed numeric fields, duplicate detector class instantiation and factory method tested, path detection result shape verified with boolean fields.
- 1 cross-runtime D-TEST-02 test in `runtime.node.test.mjs` exercising `getHashCacheStats`, `resetHashCacheStats`, `clearHashCache`, all 3 cache constants/getters, and `needsPathDetection` under `node:test`.
- No Rust source changes -- no `pub use` re-exports needed (all symbols already visible at their crate root per Plan 1's expansion).

## Task Commits

Each task was committed atomically with normal pre-commit hooks (no `--no-verify`):

1. **Task 1: Author 11 @rust-suffix proxy rows for Rust-only config symbols** -- `3b7d7a2f` (feat)
2. **Task 2: Author 23 normal config rows + smoke tests with real-shape assertions + registry bump** -- `28e8ff75` (feat)
3. **Task 3: Human-verify checkpoint** -- no commit (approval gate)

## Files Created/Modified

**Created (1):**
- `.planning/phases/04-node-tier-collapse/_add_plan03_normal_rows.py` -- normal row authoring script; builds 23 config rows with correct rustSymbol and rustCrate

**Modified (9):**
- `docs/implementation/node_api_parity/baseline/parity_contract.json` -- tier1Mappings: 327 -> 361 (+11 proxy + +23 normal)
- `docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md}` -- refreshed: 11 fewer `rust_unmapped` config gaps, 23 fewer `node_unmapped` config gaps
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md}` -- config `runtime_verified`: 50 -> 87; `deferred`: 26 -> 1; `deferred_total`: 379 -> 342
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` -- config entries: 26 -> 1 (ModConflictEntry only)
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` -- `node-tier1-config` selector: `contractCount` 50 -> 84, `contractIdsHash` recomputed
- `ClassicLib-rs/node-bindings/classic-node/__test__/config.spec.ts` -- +4 `describe` blocks with real-shape assertions (~100 lines)
- `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs` -- +1 cross-runtime D-TEST-02 test (~40 lines)

## Reconciliation

### H2 Cross-Crate Routing

| Metric | Plan expectation | Live data (authoritative) | Reconciliation |
|--------|-----------------|---------------------------|----------------|
| Proxy rows routing to classic-config-core | "some" | 11 (all) | All 11 symbols appear under classic-config-core in rust_api_surface.json because lib.rs re-exports crashgen types from yamldata module |
| Proxy rows routing to classic-crashgen-settings-core | "some" (SuspectErrorRule, CrashgenEntryRaw, etc.) | 0 | These types are defined in classic-config-core's yamldata.rs, not in classic-crashgen-settings-core; the plan explicitly says "use the live surface lookup as the source of truth" |

### Issue 4 (ModConflictEntry)

| Metric | Plan header | Actual | Delta |
|--------|-------------|--------|-------|
| Proxy rows | 11 | 11 | 0 |
| Normal rows | 23 | 23 | 0 |
| Total new rows | 34 | 34 | 0 |
| config.deferred | 0 (plan objective) | 1 (ModConflictEntry) | +1 (expected Issue 4 carve-out) |

### rustSymbol Guard Fixes

8 normal rows required rustSymbol adjustment because the NAPI wrapper function names (snake_case) do not appear in `rust_api_surface.json`. The fix mapped each to the core type/constant the wrapper delegates to:

| nodeExport | Original rustSymbol | Fixed rustSymbol | Reason |
|-----------|-------------------|-----------------|--------|
| getDefaultCacheCleanupInterval | get_default_cache_cleanup_interval | DEFAULT_CACHE_CLEANUP_INTERVAL_SECS | Returns this const |
| getDefaultCacheCleanupThreshold | get_default_cache_cleanup_threshold | DEFAULT_CACHE_CLEANUP_OP_THRESHOLD | Returns this const |
| getDefaultQueryCacheCapacity | get_default_query_cache_capacity | DEFAULT_QUERY_CACHE_CAPACITY | Returns this const |
| getFcxConfigIssues | get_fcx_config_issues | ConfigIssue | Produces ConfigIssue objects |
| getHashCacheStats | get_hash_cache_stats | FileHasher | Delegates to FileHasher::cache_stats() |
| resetHashCacheStats | reset_hash_cache_stats | FileHasher | Delegates to FileHasher::reset_cache_stats() |
| clearHashCache | clear_hash_cache | FileHasher | Delegates to FileHasher::clear_cache() |
| detectConfigDuplicates | detect_config_duplicates | ConfigDuplicateDetector | Delegates to the detector class |

## Decisions Made

1. **All 11 proxy rows route to classic-config-core (not a split)** -- The plan expected H2 cross-crate routing would split rows between classic-config-core and classic-crashgen-settings-core. The live `rust_api_surface.json` (the authoritative H2 source per the plan) shows all 11 symbols under `classic-config-core` because `classic-config-core/src/lib.rs` re-exports the crashgen types (SuspectErrorRule, CrashgenEntryRaw, etc.) from its yamldata module. The plan explicitly says "use the live surface lookup as the source of truth, not a hard-coded set."
2. **config.deferred == 1 (not 0)** -- The 1 remaining entry is ModConflictEntry, excluded from Plan 3 per Issue 4 reconciliation. Plan 5 Task 1 promotes it as a normal row. The plan objective's "config.deferred == 0" was written before Issue 4 moved ModConflictEntry to Plan 5.
3. **rustSymbol uses core delegation targets** -- NAPI wrapper function names (e.g., `get_hash_cache_stats`) don't exist in the Rust surface because they're binding-only. The bidirectional guard requires symbols that exist in `rust_api_surface.json`, so the rustSymbol was mapped to the core type/constant each wrapper delegates to (e.g., FileHasher for hash cache functions).
4. **Registry bump: existing selector, not new entry** -- The `node-tier1-config` selector naturally captures all config tier1 rows via `contractSelector: {ownerModule: "config", tier: "tier1"}`. No need for a Plan-3-specific entry.

## Deviations from Plan

None -- plan executed as written. The rustSymbol adjustments (8 rows) were part of normal execution flow: the plan's Step 4 says "If the bidirectional guard fires on any row, the underlying Rust symbol isn't visible at its declared rustCrate lib.rs -- add the missing pub use or adjust." Adjusting rustSymbol to match the guard was the expected remediation path.

## Issues Encountered

- **H2 routing surprise: all proxy rows -> classic-config-core** -- The plan expected a cross-crate split between classic-config-core and classic-crashgen-settings-core for the proxy rows. Investigation showed that `classic-config-core/src/lib.rs` already re-exports all the crashgen types (SuspectErrorRule, CrashgenEntryRaw, etc.) from its yamldata module. The `classic-crashgen-settings-core` crate defines the rule evaluator model (CrashgenSettingsRules, EvaluationContext, etc.) but NOT the YAML-parsed entry types that appear in the config owner's deferred set. This is consistent with the crate architecture: classic-config-core owns the YAML data model, classic-crashgen-settings-core owns the runtime evaluator.

## User Setup Required

None -- no external service configuration required. All tooling runs locally via `python`, `bun`, and `node`.

## Known Stubs

None -- all promoted contract rows point to real symbols in `rust_api_surface.json` and `node_api_surface.json`; no placeholder or TODO values.

## Next Phase Readiness

**Ready for Plan 4 (version-registry + PE-version):**
- Proxy-row-aware diff pipeline (`_effective_rust_symbol()` + proxy-row filtering) continues to work. Plan 4 can add proxy rows for version/version_registry owner modules without pipeline breakage.
- `parity_contract.json` now has 361 rows (327 pre-Plan-3 + 34 new config). Plan 4 appends to this file.
- `deferred_runtime_backlog.json` has 342 entries remaining (down from 379 post-Plan-2). Plan 4 targets version_registry (5 entries) + version (16 entries) + HARM-01/02 PE-version (3 new rows).
- The test scaffold pattern (real-shape describe blocks + cross-runtime D-TEST-02) is established and reusable.

**Plan 5 dependency: ModConflictEntry**
- Plan 5 Task 1 must promote `ModConflictEntry` as a normal row with `rustCrate: classic-config-core`, `nodeExport: JsModConflictEntry`, `nodeKind: interface`.
- After Plan 5, `config.deferred` should drop from 1 to 0.

**Plan 6 tripwires still active:**
- `test_tier2_definition_removed_after_plan_6` -- xfail strict; flips to passing when Plan 6 deletes `tierDefinitions.tier2`.
- `test_tier1_contract_total_baseline_floor` -- currently `>= 261`; now 361 after Plan 3. Plans 4-5 raise it further.

## Self-Check: PASSED

Verification commands executed 2026-04-10T00:24:34Z:

- `bun run parity:gate:local` -> **Tier-1 parity gate passed** (dts:freshness:check + gate)
- `bun run test:bun` -> **956 pass, 0 fail**
- `bun run test:node` -> **11/11 pass**
- `python -m pytest tools/node_api_parity/tests/ -q` -> **26 passed, 1 xfailed**
- `git log --oneline -2` -> `28e8ff75` (Task 2), `3b7d7a2f` (Task 1)
- Proxy row count: **11** (exact match)
- Normal row count: **23** (exact match)
- Total new rows: **34**
- config deferred: **1** (ModConflictEntry only, Issue 4 carve-out)
- No Rust source changes: `git diff HEAD~2 -- ClassicLib-rs/business-logic/ ClassicLib-rs/node-bindings/classic-node/src/` -> empty

---
*Phase: 04-node-tier-collapse*
*Completed: 2026-04-10*
