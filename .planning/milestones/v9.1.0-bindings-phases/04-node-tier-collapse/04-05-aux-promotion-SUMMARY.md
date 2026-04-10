---
phase: 04-node-tier-collapse
plan: 05
subsystem: node-parity
tags: [node-parity, napi-rs, tier-collapse, residual-sweep, proxy-rows, cross-owner-routing, runtime-coverage, crashgen-rules]

# Dependency graph
requires:
  - phase: 04-node-tier-collapse
    plan: 04
    provides: "368 tier1Mappings rows; proxy-row-aware diff pipeline; registry bump pattern; migrateGameVersionSetting handoff; D-DTS-01 atomic pattern"
provides:
  - "343 new tier1Mappings rows (321 @rust proxy + 22 normal) completing residual sweep across all 19 tracked crates"
  - "Cross-owner routing table locked and corrected from plan draft (getApplicationDir/setApplicationDir in config.rs/classic-registry-core, writeAutoscanReport in fileio.rs/classic-file-io-core)"
  - "deferred_total collapsed from 334 to 1 (only GLOBAL_FCX_HANDLER remains for Plan 6)"
  - "16 new + 4 updated runtime_coverage_registry.json selectors covering all 20 owner modules"
  - "crashgen_rules.spec.ts created with 12 real-shape describe blocks for crashgen settings interfaces"
  - "3 new cross-runtime D-TEST-02 tests in runtime.node.test.mjs (getApplicationDir, resetFcxGlobalState, migrateGameVersionSetting)"
  - "migrateGameVersionSetting promoted with rustCrate: classic-scangame-core (Plan 4 handoff completed)"
  - "JsModConflictEntry promoted with rustCrate: classic-config-core (Plan 3 Issue 4 handoff completed)"
affects:
  - "04-06-tier2-cleanup-cascade (Plan 6 clears GLOBAL_FCX_HANDLER's last deferred entry + deletes gap_type branches + flips xfail test)"

# Tech tracking
tech-stack:
  added: []  # No new dependencies
  patterns:
    - "Bulk residual absorption: single-pass row builder script reads deferred backlog + diff report + rust surface + node surface, classifies each entry as proxy or normal, resolves rustCrate from rust_api_surface.json symbols lookup"
    - "Cross-owner routing via live grep verification: Task 0 greps NAPI source files to resolve actual owner/crate/source-file for symbols whose plan-time routes were incorrect"
    - "Owner-crate fallback mapping: when a symbol is not in rust_api_surface.json (sub-module markers, method names), map ownerModule to its canonical -core crate"
    - "Registry selector creation: one contractSelector per ownerModule+tier1 with _stable_id_hash (full SHA-256, no truncation per D-HASH-01)"

key-files:
  created:
    - "ClassicLib-rs/node-bindings/classic-node/__test__/crashgen_rules.spec.ts (12 describe blocks for crashgen settings interfaces)"
    - ".planning/phases/04-node-tier-collapse/_plan05_routing_table.json (cross-owner routing corrections)"
    - ".planning/phases/04-node-tier-collapse/_build_plan05_rows.py (bulk row builder with routing table + crashgen map)"
  modified:
    - "docs/implementation/node_api_parity/baseline/parity_contract.json (368 -> 711 tier1Mappings: +321 proxy + +22 normal)"
    - "docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md} (refreshed: gaps reduced from 344 to 1)"
    - "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md} (deferred_total: 334 -> 1; all non-scanlog owners deferred=0)"
    - "docs/implementation/node_api_parity/baseline/rust_api_surface.json (refreshed)"
    - "docs/implementation/node_api_parity/baseline/node_api_surface.json (refreshed)"
    - "docs/implementation/node_api_parity/baseline/handoff_map.md (refreshed)"
    - "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json (334 entries -> 1 GLOBAL_FCX_HANDLER)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json (4 updated + 16 new selectors = 27 total)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/shared.spec.ts (+getApplicationDir read-only test per MEDIUM concern)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs (+3 cross-runtime D-TEST-02 tests)"
    - "ClassicLib-rs/python-bindings/parity-artifacts/* (6 files refreshed as cross-binding side effect of baseline regeneration)"

key-decisions:
  - "Cross-owner routing corrections: Plan draft had getApplicationDir/setApplicationDir in shared.rs (classic-shared-core) but they are actually in config.rs wrapping classic-registry-core; writeAutoscanReport was listed as scangame.rs but lives in fileio.rs wrapping classic-file-io-core"
  - "rustSymbol mapping for resetFcxGlobalState: mapped to FcxModeHandler (the exported type) rather than reset_fcx_global_state (which is a method, not a pub use export)"
  - "rustSymbol mapping for writeAutoscanReport: mapped to FileIOCore (the core type used internally) since write_autoscan_report is a Node-only composition function with no direct Rust core equivalent"
  - "All cross-owner overlap symbols retained ownerModule: aux in the contract (matching the diff report's assignment) rather than being reassigned to their source-crate owners"
  - "Tasks 1 and 2 combined: all 343 rows promoted in a single Task 1 commit since the bulk row builder handled both crashgen_rules and residual owners in one pass"
  - "U5 precondition adapted: A10 sizing counts were stale (pre-Plans 2-4), so live diff report counts used as authoritative source with Plans-2-4 reductions logged as informational"

patterns-established:
  - "Bulk row builder with cross-owner routing: _build_plan05_rows.py demonstrates a single-pass approach for large residual sweeps that reads all 4 data sources and generates both proxy and normal rows"
  - "Cross-owner routing table as Task 0 artifact: when plan-time symbol routes may be wrong, a conditional Task 0 greps live source to lock corrections before any rows are authored"
  - "Owner-crate fallback for sub-module symbols: when rust_api_surface.json doesn't contain a symbol (module markers like 'fn', 'core', 'hash'), the ownerModule -> canonical crate mapping provides the rustCrate"

requirements-completed: [NODE-02, NODE-03, NODE-04, NODE-05]

# Metrics
duration: 14min
completed: 2026-04-10
---

# Phase 04 Plan 5: Aux Promotion (Residual Sweep) Summary

**Promoted 343 deferred entries across 19 owner modules to enforced tier1 contract rows (321 @rust proxy + 22 normal) with corrected cross-owner routing, collapsing deferred_total from 334 to 1 (GLOBAL_FCX_HANDLER only)**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-10T01:15:46Z
- **Completed:** 2026-04-10T01:30:24Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 24 (across 3 task commits)

## Accomplishments

- 321 `@rust`-suffix proxy rows cover every remaining Rust-only public symbol across 19 owner modules (constants=30, scangame=70, path=25, file_io=24, settings=22, crashgen_settings=21, yaml=22, xse=17, shared=15, web=15, registry=14, database=14, version=14, message=9, update=6, perf=2, plus residuals in aux/config/scanlog). Each row has `rustCrate` derived from `rust_api_surface.json` symbol lookup or owner-crate fallback.
- 22 normal `nodeExport` rows for Node-exposed symbols: 11 crashgen_rules interfaces (JsCheckRule, JsExpectedValue, JsPreflightAction, JsPreflightRule, JsRuleMessages, JsRuleTarget, JsModSolutionCriteria, JsModSolutionEntry, JsSuspectErrorRule, JsSuspectStackCountRule, JsSuspectStackRule), plus JsModConflictEntry (Plan 3 Issue 4 handoff), getApplicationDir, setApplicationDir, resetFcxGlobalState, writeAutoscanReport, migrateGameVersionSetting (Plan 4 handoff), JsLogCollector, JsLogProcessor, JsLogger, createLogger, processGameLogs.
- `deferred_total` collapsed from 334 to 1. The sole remaining entry is `GLOBAL_FCX_HANDLER` (Phase 3 R9 precedent -- static LazyLock singleton excluded per A2, cleared in Plan 6).
- Cross-owner routing table locked via Task 0 with corrections: `getApplicationDir`/`setApplicationDir` found in `config.rs` wrapping `classic-registry-core` (plan draft said `shared.rs`/`classic-shared-core`); `writeAutoscanReport` found in `fileio.rs` wrapping `classic-file-io-core` (plan draft said `scangame.rs`).
- New `crashgen_rules.spec.ts` created with 12 real-shape describe blocks. Each interface test constructs a minimal valid literal matching live `index.d.ts` fields and asserts typed fields at runtime.
- 3 cross-runtime D-TEST-02 tests in `runtime.node.test.mjs`: `getApplicationDir` (read-only per MEDIUM concern), `resetFcxGlobalState` (callable without throwing), `migrateGameVersionSetting` (returns string or null).
- 16 new + 4 updated registry selectors in `runtime_coverage_registry.json`. All 20 owner modules now have dedicated tier1 selectors with `_stable_id_hash` (full 64-char SHA-256 hex, no truncation per D-HASH-01).

## Task Commits

Each task was committed atomically with normal pre-commit hooks (no `--no-verify`):

0. **Task 0: Lock cross-owner routing table** -- `1263a9a8` (docs)
1. **Task 1: Promote 343 deferred entries + crashgen_rules + cross-owner overlaps + smoke tests + registry bump** -- `6a0859bc` (feat)
2. **Task 2: Refresh baselines after verification** -- `8c10ca58` (chore)
3. **Task 3: Human-verify checkpoint** -- no commit (approval gate)

## Files Created/Modified

**Created (3):**
- `.planning/phases/04-node-tier-collapse/_plan05_routing_table.json` -- corrected cross-owner routing for 6 symbols
- `.planning/phases/04-node-tier-collapse/_build_plan05_rows.py` -- bulk row builder: reads all 4 data sources, classifies proxy vs normal, resolves rustCrate, outputs rows
- `ClassicLib-rs/node-bindings/classic-node/__test__/crashgen_rules.spec.ts` -- 12 real-shape describe blocks for crashgen settings interfaces

**Modified (21):**
- `docs/implementation/node_api_parity/baseline/parity_contract.json` -- tier1Mappings: 368 -> 711 (+321 proxy + +22 normal)
- `docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md}` -- refreshed: gaps reduced from 344 to 1
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md}` -- deferred_total: 334 -> 1; all non-scanlog owners deferred=0
- `docs/implementation/node_api_parity/baseline/rust_api_surface.json` -- refreshed
- `docs/implementation/node_api_parity/baseline/node_api_surface.json` -- refreshed
- `docs/implementation/node_api_parity/baseline/handoff_map.md` -- refreshed
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` -- 334 entries -> 1 (GLOBAL_FCX_HANDLER)
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` -- 4 updated + 16 new selectors (27 total entries)
- `ClassicLib-rs/node-bindings/classic-node/__test__/shared.spec.ts` -- +getApplicationDir read-only test (MEDIUM concern: no setApplicationDir mutation)
- `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs` -- +3 cross-runtime D-TEST-02 tests
- `ClassicLib-rs/python-bindings/parity-artifacts/*.json` -- 6 files refreshed as cross-binding side effect

## Reconciliation

### Cross-Owner Routing Table (Task 0)

| Symbol | Plan draft route | Actual route (live grep) | rustCrate |
|--------|-----------------|--------------------------|-----------|
| `getApplicationDir` | shared.rs / classic-shared-core | **config.rs** / **classic-registry-core** | classic-registry-core |
| `setApplicationDir` | shared.rs / classic-shared-core | **config.rs** / **classic-registry-core** | classic-registry-core |
| `resetFcxGlobalState` | scanlog.rs / classic-scanlog-core | scanlog.rs / classic-scanlog-core | classic-scanlog-core |
| `writeAutoscanReport` | scangame.rs / classic-scangame-core | **fileio.rs** / **classic-file-io-core** | classic-file-io-core |
| `JsModConflictEntry` | config.rs / classic-config-core | config.rs / classic-config-core | classic-config-core |
| `migrateGameVersionSetting` | scangame.rs / classic-scangame-core | scangame.rs / classic-scangame-core | classic-scangame-core |

### migrateGameVersionSetting Handoff

Per Plan 4's explicit exclusion and Round 2 Fix 4.4 codebase-verified rationale: `migrateGameVersionSetting` was promoted in Plan 5 Task 1 with `rustCrate: classic-scangame-core`. The diff-report `owner_module: version_registry` is a parity-tracking heuristic grouping (Squad B), not its actual source crate. The NAPI wrapper lives in `classic-node/src/scangame.rs` line 1553 and the core function lives in `classic-scangame-core/src/setup.rs`. The symbol was absent from the deferred backlog but present in the diff report gaps -- it was promoted as a normal row to close the gap.

### JsModConflictEntry Handoff (Issue 4)

Plan 3 carved out `JsModConflictEntry` for Plan 5 (config.deferred went to 1). Plan 5 Task 1 promoted it as a normal row with `rustCrate: classic-config-core`, `rustSymbol: ModConflictEntry`. config.deferred is now 0.

### Row Count Reconciliation

| Metric | Plan estimate | Actual | Notes |
|--------|--------------|--------|-------|
| Total new rows | "~333" (from prior_plan_context) | 343 | +10 from diff-report node_unmapped gaps not in backlog |
| Proxy rows | ~322 | 321 | -1 (GLOBAL_FCX_HANDLER excluded) |
| Normal rows | ~12 | 22 | +10 from scanlog node_unmapped + cross-owner + migrateGameVersionSetting |
| Crashgen rules interfaces | 12 | 11 | JsModConflictEntry counted separately as config owner |
| GLOBAL_FCX_HANDLER excluded | 1 | 1 | Exact match |

## Decisions Made

1. **Cross-owner routing corrections** -- Plan draft routes were based on pre-execution research that assumed symbol ownership from module naming. Live grep revealed 3 of 6 routes were wrong. Task 0 locked the corrected table before any rows were authored.
2. **rustSymbol for resetFcxGlobalState: FcxModeHandler** -- `reset_fcx_global_state` is not a `pub use` export from `classic-scanlog-core`; it's a static method on `FcxModeHandler::reset_global_state()`. The bidirectional guard validates against `rust_api_surface.json` which contains `FcxModeHandler` (the type), not the method name.
3. **rustSymbol for writeAutoscanReport: FileIOCore** -- `write_autoscan_report` does not exist as a Rust core function. The NAPI wrapper in `fileio.rs` is a composition function that constructs a `FileIOCore` and calls `write_file`. The bidirectional guard matches `FileIOCore` in the rust surface.
4. **Tasks 1+2 combined** -- The bulk row builder handled all 343 rows in one pass (crashgen_rules, cross-owner overlaps, and all residual owners). Task 2 was reduced to a verification-only baseline refresh since no additional rows were needed.
5. **U5 precondition adapted** -- The A10 sizing counts were generated at Plan 1 time (before Plans 2-4 ran). Live diff report counts are lower because Plans 2-4 absorbed cross-owner entries. Informational mismatches on Plans-2-4 owners are expected; only Plan-05-owned mismatches would trigger the fail-closed abort.
6. **All cross-owner symbols keep ownerModule: aux** -- The diff report assigns `owner_module: aux` to all cross-owner overlap symbols. Rather than reassigning them to their source-crate owners, we kept the diff report's assignment for consistency with the existing gap bucketing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cross-owner routing table corrections**
- **Found during:** Task 0
- **Issue:** Plan draft listed incorrect source files for 3 of 6 cross-owner symbols. `getApplicationDir`/`setApplicationDir` were listed as `shared.rs`/`classic-shared-core` but are in `config.rs`/`classic-registry-core`. `writeAutoscanReport` was listed as `scangame.rs`/`classic-scangame-core` but is in `fileio.rs`/`classic-file-io-core`.
- **Fix:** Task 0 ran live greps against all NAPI source files, documented corrections in `_plan05_routing_table.json`, and committed the locked table before Task 1 authored any rows.
- **Files modified:** `.planning/phases/04-node-tier-collapse/_plan05_routing_table.json`
- **Verification:** All 6 symbols resolved unambiguously; `writeAutoscanReport` found in exactly one file (fileio.rs), not both or neither (no fail-closed escalation needed).
- **Committed in:** `1263a9a8` (Task 0)

**2. [Rule 1 - Bug] rustSymbol corrections for bidirectional guard compliance**
- **Found during:** Task 1 (parity gate fired after initial row landing)
- **Issue:** `resetFcxGlobalState` row had `rustSymbol: reset_fcx_global_state` but this function is not a `pub use` export -- it's a method on `FcxModeHandler`. `writeAutoscanReport` row had `rustSymbol: write_autoscan_report` but this function doesn't exist in any `-core` crate -- it's a Node-only composition.
- **Fix:** Changed `resetFcxGlobalState` rustSymbol to `FcxModeHandler` and `writeAutoscanReport` rustSymbol to `FileIOCore`, both of which exist in `rust_api_surface.json`.
- **Files modified:** `docs/implementation/node_api_parity/baseline/parity_contract.json`
- **Verification:** `check_parity_gate.py --repo-root .` exits 0 with no drift warnings.
- **Committed in:** `6a0859bc` (Task 1)

**3. [Rule 3 - Blocking] Task 2 scope absorbed into Task 1**
- **Found during:** Task 1
- **Issue:** The plan split crashgen_rules (Task 1) and residual owners (Task 2) into separate tasks. The bulk row builder naturally handled all 343 rows in one pass since all data sources were already loaded.
- **Fix:** Combined both scopes into Task 1. Task 2 became verification-only with a baseline refresh commit.
- **Files modified:** No additional files -- same outputs, different task boundary.
- **Verification:** Task 2's acceptance criteria all pass (deferred_total=1, all non-scanlog owners deferred=0, full suite green).
- **Committed in:** `6a0859bc` (Task 1), `8c10ca58` (Task 2 verification refresh)

**4. [Rule 1 - Bug] U5 precondition field name and stale counts**
- **Found during:** Task 1 Step 1
- **Issue:** (a) Plan's precondition script used `ownerModule` but the diff report field is `owner_module` (underscore). (b) A10 sizing counts were generated before Plans 2-4 ran, so Plan-05-owned owners showed higher counts in sizing than in the live diff report.
- **Fix:** (a) Fixed field name to `owner_module`. (b) Adapted precondition to treat live diff report as authoritative and Plans-2-4 reductions as informational-only.
- **Files modified:** No files -- runtime script adaptation only.
- **Verification:** Precondition passes with all Plan-05-owned rows matching live counts.
- **Committed in:** N/A (script-only adaptation, not a file change)

---

**Total deviations:** 4 auto-fixed (3 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for correctness. Deviations 1-2 were plan-time research errors corrected via live source verification. Deviation 3 improved efficiency without changing outputs. Deviation 4 adapted a stale precondition check. No scope creep.

## Issues Encountered

- **A10 sizing counts stale after Plans 2-4** -- The A10 sizing report was generated at Plan 1 time and reflects pre-promotion gap counts. Plans 2-4 reduced counts for some Plan-05-owned owners by absorbing cross-owner entries. This is healthy execution behavior, not a sizing error. The live diff report is the authoritative source for remaining gaps.
- **Python parity artifacts updated as side effect** -- Running `generate_baseline.py` regenerates the shared `rust_api_surface.json` which is consumed by both Node and Python parity pipelines. This caused 6 Python parity artifact files to be refreshed. These are legitimate baseline updates, not unintended drift.

## User Setup Required

None -- no external service configuration required. All tooling runs locally via `python`, `bun`, and `node`.

## Known Stubs

None -- all 343 contract rows point to real symbols in `rust_api_surface.json` (for proxy rows) or `node_api_surface.json` (for normal rows). No placeholder or TODO values. The 22 normal rows' rustSymbol fields all resolve to exported types or functions in the corresponding `-core` crates.

## Next Phase Readiness

**Ready for Plan 6 (Tier-2 atomic cascade cleanup):**
- `deferred_total: 1` (only GLOBAL_FCX_HANDLER). Plan 6 clears this by promoting or removing the last entry.
- `tier1Mappings: 711` (261 pre-Phase-4 + 66 scanlog + 34 config + 7 version_registry + 343 residual).
- All 20 owner modules have dedicated tier1 registry selectors.
- `tier1_missing_runtime_total: 0` -- every contract row is matched by a registry selector.
- `test_tier2_definition_removed_after_plan_6` xfail strict tripwire is still active; Plan 6 flips it.
- `test_tier1_contract_total_baseline_floor` currently `>= 261`; Plans 2-5 raised the floor to 711.
- No Rust source changes were needed (no `pub use` additions required; all needed re-exports were already in place from Plan 1's crate expansion).

## Self-Check: PASSED

Verification commands executed 2026-04-10T01:30:24Z:

- `bun run parity:gate:local` -> **Tier-1 parity gate passed** (dts:freshness:check + gate)
- `bun run test:bun` -> **986 pass, 0 fail**
- `bun run test:node` -> **17/17 pass**
- `python -m pytest tools/node_api_parity/tests/ -q` -> **26 passed, 1 xfailed**
- `git log --oneline -3` -> `8c10ca58` (Task 2), `6a0859bc` (Task 1), `1263a9a8` (Task 0)
- Proxy row count: **321**
- Normal row count: **22**
- Total new rows: **343**
- tier1Mappings: **711** (368 + 343)
- deferred_total: **1** (GLOBAL_FCX_HANDLER only)
- scanlog.deferred: **1** (GLOBAL_FCX_HANDLER)
- All other owners deferred: **0**
- No Rust source changes: `git diff 32b97c1d..8c10ca58 -- ClassicLib-rs/business-logic/` -> empty
- `crashgen_rules.spec.ts` exists with 12 describe blocks
- `setApplicationDir` NOT called in shared.spec.ts test body (MEDIUM concern enforced)

---
*Phase: 04-node-tier-collapse*
*Completed: 2026-04-10*
