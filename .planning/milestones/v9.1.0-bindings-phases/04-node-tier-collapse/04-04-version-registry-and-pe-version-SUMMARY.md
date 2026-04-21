---
phase: 04-node-tier-collapse
plan: 04
subsystem: node-parity
tags: [node-parity, napi-rs, tier-collapse, pe-version, version-registry, rust-source, real-shape-tests, runtime-coverage]

# Dependency graph
requires:
  - phase: 04-node-tier-collapse
    plan: 03
    provides: "361 tier1Mappings rows; proxy-row-aware diff pipeline; registry bump pattern; deferred backlog regeneration pattern"
provides:
  - "7 new tier1Mappings rows (3 PE-version + 4 version_registry) covering all version_registry deferred entries + HARM-01/02 PE-version parity"
  - "pub use is_valid_executable_path re-export in classic-version-core/src/lib.rs (A6 prerequisite)"
  - "JsPeVersion struct + extractPeVersion + isValidPePath NAPI wrappers in classic-node/src/version.rs"
  - "index.d.ts regenerated with 3 new exports (D-DTS-01 atomic pattern demonstrated)"
  - "version_registry.deferred dropped to 0 in runtime_coverage_summary.json"
  - "14 new bun:test assertions + 3 new cross-runtime D-TEST-02 node:test assertions"
  - "First plan in Phase 4 that modifies Rust source AND regenerates index.d.ts"
affects:
  - "04-05-aux-promotion (migrateGameVersionSetting handoff: NOT promoted in Plan 4 -- Plan 5 owns it as a scangame-core routed symbol)"
  - "04-06-tier2-cleanup-cascade (Plan 6 clears remaining deferred entries + deletes gap_type branches)"

# Tech tracking
tech-stack:
  added: []  # No new dependencies
  patterns:
    - "D-DTS-01 atomic Rust+index.d.ts commit pattern: Rust source edit and bun run build regeneration committed atomically in the same commit"
    - "U1 cross-binding regression probe: after modifying Rust public surface, BOTH Node AND Python parity gates are verified green before committing"
    - "A6 lib.rs re-export as intra-plan prerequisite: Task 1 pub use commit lands BEFORE Task 2 NAPI wrappers (bidirectional guard dependency)"
    - "Pre-Step 6a rustSymbol locking via live grep: every contract row's rustSymbol and rustCrate verified from actual source before authoring (no guessing)"
    - "u16-to-u32 widening for NAPI: Rust PE version components are u16 but NAPI exposes u32 (standard NAPI convention for numeric types)"

key-files:
  created: []
  modified:
    - "ClassicLib-rs/business-logic/classic-version-core/src/lib.rs (pub use pe_version::is_valid_executable_path added to line 43)"
    - "ClassicLib-rs/node-bindings/classic-node/src/version.rs (+55 lines: JsPeVersion struct + extract_pe_version + is_valid_pe_path NAPI wrappers)"
    - "ClassicLib-rs/node-bindings/classic-node/index.d.ts (regenerated: +extractPeVersion, +isValidPePath, +JsPeVersion interface)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts (+2 describe blocks with PE-version tests including Windows kernel32.dll integration)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/version_registry.spec.ts (+4 describe blocks for crashgen registry/rules/check functions)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs (+3 cross-runtime D-TEST-02 tests)"
    - "ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json (node-tier1-version-registry: contractCount 55 -> 62, contractIdsHash recomputed)"
    - "docs/implementation/node_api_parity/baseline/parity_contract.json (361 -> 368 tier1Mappings: +3 PE-version + +4 version_registry)"
    - "docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md} (refreshed: version_registry gaps reduced)"
    - "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md} (version_registry.deferred -> 0; deferred_total 342 -> 334)"
    - "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json (version_registry entries removed: 4 -> 0)"

key-decisions:
  - "rustSymbol mapping for JsCrashgenRegistryEntry: mapped to CrashgenConfig@classic-version-registry-core (closest core type that the NAPI struct wraps; no exact core CrashgenRegistryEntry exists)"
  - "rustSymbol mapping for checkCrashgenConfigWithRules and checkCrashgenFullWithRules: mapped to CrashgenCheckOrchestrator@classic-scangame-core (NAPI functions compose JsCrashgenChecker which delegates to the orchestrator)"
  - "rustSymbol mapping for JsCrashgenSettingsRules: mapped to CrashgenSettingsRules@classic-crashgen-settings-core (exact match via lib.rs grep)"
  - "version-pe-shape row restored per D1 adjudication: PeVersionResult -> JsPeVersion interface row prevents deferred_total regression from parse_node_surface() standalone interface emission"
  - "migrateGameVersionSetting NOT promoted: its actual source is classic-scangame-core (not classic-version-registry-core), making it a Plan 5 cross-owner reconciliation target"
  - "Registry bump strategy: update existing node-tier1-version-registry selector (contractCount 55 -> 62) rather than creating a Plan-4-specific entry"

patterns-established:
  - "Rust source + index.d.ts atomic commit: when a plan adds NAPI wrappers, the Rust edit and bun run build output are committed atomically in one commit"
  - "Intra-plan prerequisite commit: A6 pub use re-export committed separately BEFORE NAPI wrappers to satisfy bidirectional guard dependency ordering"
  - "U1 cross-binding regression probe: standard practice for any plan that modifies Rust public surface"
  - "Pre-Step 6a grep-locking: all rustSymbol/rustCrate values must be verified via live source grep before contract row authoring"

requirements-completed: [NODE-02, NODE-04, NODE-05, HARM-01, HARM-02]

# Metrics
duration: 39min
completed: 2026-04-10
---

# Phase 04 Plan 4: Version Registry + PE-Version Summary

**Added extractPeVersion/isValidPePath/JsPeVersion NAPI exports to classic-node, promoted 4 version_registry deferred entries to tier1, and demonstrated the first Rust-source-modifying plan in Phase 4 with atomic index.d.ts regeneration (D-DTS-01)**

## Performance

- **Duration:** 39 min
- **Started:** 2026-04-10T00:29:55Z
- **Completed:** 2026-04-10T01:09:38Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 23 (across 2 task commits)

## Accomplishments

- Added `pub use pe_version::is_valid_executable_path` to `classic-version-core/src/lib.rs` (A6 prerequisite), verified with `cargo check` and U1 cross-binding regression probe confirming both Node and Python parity gates stay green.
- Added JsPeVersion struct, `extract_pe_version`, and `is_valid_pe_path` NAPI wrappers to `classic-node/src/version.rs` (~55 lines). PE version components widened from u16 to u32 per NAPI convention. `index.d.ts` regenerated atomically via `bun run build` (D-DTS-01 pattern).
- 7 new tier1Mappings rows: 3 PE-version (`version-pe-extract`, `version-pe-is-valid-path`, `version-pe-shape` per D1 adjudication) + 4 version_registry (`JsCrashgenRegistryEntry`, `JsCrashgenSettingsRules`, `checkCrashgenConfigWithRules`, `checkCrashgenFullWithRules`). All rows carry grep-verified `rustCrate` and `rustSymbol` fields (Pre-Step 6a locking).
- `version_registry.deferred` dropped to 0 in `runtime_coverage_summary.json`. `deferred_total` reduced from 342 to 334.
- 14 new bun:test tests: 7 PE-version tests (isValidPePath + extractPeVersion including Windows kernel32.dll integration) + 7 version_registry tests (interface shape assertions + function callability). 3 new cross-runtime D-TEST-02 tests in `runtime.node.test.mjs`.
- Human-verified PE-version parity: Node `extractPeVersion` and Python `extract_pe_version` return identical version components for `kernel32.dll`.

## Task Commits

Each task was committed atomically with normal pre-commit hooks (no `--no-verify`):

1. **Task 1: A6 prerequisite + U1 cross-binding probe** -- `90383d80` (feat)
2. **Task 2: NAPI wrappers + 7 contract rows + smoke tests + registry bump** -- `459dbf68` (feat)
3. **Task 3: Human-verify checkpoint** -- no commit (approval gate)

## Files Created/Modified

**Created (0):** No new files created.

**Modified (23):**
- `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` -- pub use re-export extended with `is_valid_executable_path`
- `ClassicLib-rs/node-bindings/classic-node/src/version.rs` -- +55 lines: JsPeVersion struct + 2 NAPI wrapper functions
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` -- regenerated with extractPeVersion, isValidPePath, JsPeVersion exports
- `ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts` -- +2 describe blocks (isValidPePath + extractPeVersion with Windows integration)
- `ClassicLib-rs/node-bindings/classic-node/__test__/version_registry.spec.ts` -- +4 describe blocks (crashgen registry/rules shapes + check functions)
- `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs` -- +3 cross-runtime D-TEST-02 tests
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` -- node-tier1-version-registry: contractCount 55 -> 62, contractIdsHash recomputed
- `docs/implementation/node_api_parity/baseline/parity_contract.json` -- tier1Mappings: 361 -> 368
- `docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md}` -- refreshed
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md}` -- version_registry.deferred: 0; deferred_total: 342 -> 334
- `docs/implementation/node_api_parity/baseline/rust_api_surface.json` -- includes is_valid_executable_path
- `docs/implementation/node_api_parity/baseline/node_api_surface.json` -- includes extractPeVersion, isValidPePath, JsPeVersion
- `docs/implementation/node_api_parity/baseline/handoff_map.md` -- refreshed
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` -- version_registry entries: 4 -> 0

## Reconciliation

### Pre-Step 6a rustSymbol/rustCrate Locking

| nodeExport | rustSymbol (locked) | rustCrate (locked) | Source verification |
|---|---|---|---|
| `JsCrashgenRegistryEntry` | `CrashgenConfig` | `classic-version-registry-core` | No core `CrashgenRegistryEntry` struct exists; `CrashgenConfig` is the closest core type in `classic-version-registry-core/src/models.rs:229` |
| `JsCrashgenSettingsRules` | `CrashgenSettingsRules` | `classic-crashgen-settings-core` | Exact match at `classic-crashgen-settings-core/src/lib.rs:226` |
| `checkCrashgenConfigWithRules` | `CrashgenCheckOrchestrator` | `classic-scangame-core` | NAPI wrapper in scangame.rs:832 composes `JsCrashgenChecker` which delegates to the orchestrator |
| `checkCrashgenFullWithRules` | `CrashgenCheckOrchestrator` | `classic-scangame-core` | NAPI wrapper in scangame.rs:1337 directly calls `CrashgenCheckOrchestrator::check_with_rules` |

### migrateGameVersionSetting Handoff

Per Round 2 Fix 4.4 codebase-verified rationale: `migrateGameVersionSetting` was NOT promoted in Plan 4. Its diff-report `owner_module: version_registry` is a parity-tracking HEURISTIC grouping (Squad B), not its actual source crate. The NAPI wrapper lives in `classic-node/src/scangame.rs` (not `src/version_registry.rs`) and the core function lives in `classic-scangame-core/src/setup.rs`. Plan 5 owns this symbol as a cross-owner reconciliation target.

## Decisions Made

1. **rustSymbol for JsCrashgenRegistryEntry: CrashgenConfig** -- No core `CrashgenRegistryEntry` struct exists in any `-core` crate (confirmed via recursive grep). `CrashgenConfig` from `classic-version-registry-core` is the closest core type that the NAPI struct wraps. Follows the Plan 3 pattern: use the core type the NAPI wrapper delegates to.
2. **rustCrate split across 3 crates** -- The 4 version_registry rows span 3 distinct crates: `classic-version-registry-core` (registry entry), `classic-crashgen-settings-core` (settings rules), and `classic-scangame-core` (check functions). This is accurate to the source and follows the "live grep is authoritative" principle.
3. **version-pe-shape row restored per D1 adjudication** -- Iteration-1 plan-checker's Issue 9 drop was mechanically wrong. `parse_node_surface()` emits a standalone `{ export: "JsPeVersion", kind: "interface" }` entry, so without the contract row, JsPeVersion becomes a new deferred backlog entry (precedented by `node-deferred-aux-108`).
4. **Registry bump: existing selector** -- Updated `node-tier1-version-registry` selector (contractCount 55 -> 62) rather than creating a Plan-4-specific entry.
5. **migrateGameVersionSetting excluded** -- Its actual source is `classic-scangame-core`, not `classic-version-registry-core`. Plan 5 owns the cross-owner reconciliation.

## Deviations from Plan

None -- plan executed as written. The rustSymbol/rustCrate values were locked via grep per Pre-Step 6a (planned procedure, not a deviation). The deferred_runtime_backlog.json regeneration required running `generate_deferred_backlog.py` explicitly after the contract rows landed, which is the established pattern from Plans 2-3.

## Issues Encountered

- **Node parity gate exit code 1 after Task 1 A6 re-export** -- Expected behavior: adding `is_valid_executable_path` to the Rust surface creates a "Newly uncovered Node surfaces: 1" gap. This is by design (Task 1 is a prerequisite; Task 2 resolves the gap with the NAPI wrapper). Python gate confirmed green (U1 probe passed).
- **deferred_runtime_backlog.json required explicit regeneration** -- `generate_baseline.py` does not regenerate the deferred backlog; `generate_deferred_backlog.py` must be run separately. Without this step, `version_registry.deferred` showed 4 (stale data) instead of 0. After regeneration, deferred dropped to 0 as expected.

## User Setup Required

None -- no external service configuration required. All tooling runs locally via `python`, `bun`, `node`, and `cargo`.

## Known Stubs

None -- all 7 contract rows point to real symbols in both `rust_api_surface.json` and `node_api_surface.json`. The NAPI wrappers delegate directly to core functions with no placeholder logic.

## Next Phase Readiness

**Ready for Plan 5 (aux-promotion):**
- tier1Mappings total: 368. Plan 5 appends to this file.
- `deferred_runtime_backlog.json` has 334 entries remaining (down from 342 post-Plan 3). Plan 5 targets the remaining owner modules.
- `migrateGameVersionSetting` handoff documented: Plan 5 Task 1 must route it to `rustCrate: classic-scangame-core` (NOT `classic-version-registry-core`).
- The D-DTS-01 atomic Rust+index.d.ts commit pattern is established. Plan 5 can reuse it if it adds NAPI wrappers.
- The test scaffold pattern (real-shape describe blocks + cross-runtime D-TEST-02) is established and reusable.

**Plan 6 tripwires still active:**
- `test_tier2_definition_removed_after_plan_6` -- xfail strict; flips to passing when Plan 6 deletes `tierDefinitions.tier2`.
- `test_tier1_contract_total_baseline_floor` -- currently `>= 261`; now 368 after Plan 4. Plan 5 raises it further.

## Self-Check: PASSED

Verification commands executed 2026-04-10T01:09:38Z:

- `bun run parity:gate:local` -> **Tier-1 parity gate passed** (dts:freshness:check + gate)
- `bun run test:bun` -> **970 pass, 0 fail**
- `bun run test:node` -> **14/14 pass**
- `python -m pytest tools/node_api_parity/tests/ -q` -> **26 passed, 1 xfailed**
- `git log --oneline -2` -> `459dbf68` (Task 2), `90383d80` (Task 1)
- PE-version row count: **3** (version-pe-extract, version-pe-is-valid-path, version-pe-shape)
- version_registry row count: **4** (JsCrashgenRegistryEntry, JsCrashgenSettingsRules, checkCrashgenConfigWithRules, checkCrashgenFullWithRules)
- Total new rows: **7**
- tier1Mappings: **368** (361 + 7)
- version_registry.deferred: **0**
- deferred_total: **334** (342 - 8)
- Rust source changes: `git diff 090dc7e9..459dbf68 -- ClassicLib-rs/business-logic/classic-version-core/src/lib.rs ClassicLib-rs/node-bindings/classic-node/src/version.rs` -> confirms both files modified

---
*Phase: 04-node-tier-collapse*
*Completed: 2026-04-10*
