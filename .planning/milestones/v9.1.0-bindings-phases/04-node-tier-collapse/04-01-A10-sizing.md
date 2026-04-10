# Phase 4 Plan 1 — A10 Sizing Report (dual-source per U2)

**Generated:** 2026-04-09 (Phase 4 Plan 1 Task 3)
**Primary source:** `docs/implementation/node_api_parity/baseline/parity_diff_report.json::gaps`
**Cross-validation source:** `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json::perOwnerModule`

> This report is consumed by Plans 2-5 to size their task budgets before starting. The **primary** source (U2 fix) is the live diff inventory, NOT the coverage summary alone. Per-owner counts derive from filtering `gaps[]` by `owner_module`, then excluding the single `GLOBAL_FCX_HANDLER` entry per Phase 3 R9 precedent (A2).

---

## Headline Numbers

| Metric | Value |
|---|---:|
| Tier-1 contract total (existing) | 261 |
| Primary total deferred (parity_diff_report.json::gaps, GLOBAL_FCX_HANDLER filtered) | **472** |
| Cross total deferred (runtime_coverage_summary.json::summary.deferred_total) | **454** |
| Backlog total entries (deferred_runtime_backlog.json::entries) | **454** |
| Primary - Cross delta | **+18** |
| Owners tracked | **20** |
| New crates added in Plan 1 | 9 |
| Total RUST_TARGET_CRATES after Plan 1 | 19 |

### Primary vs Cross Reconciliation (load-bearing per U2)

The 18-entry primary-vs-cross delta is not a bug — it comes from gaps that `runtime_coverage_summary.json` reclassifies from "deferred" to "runtime_verified" because the `runtime_coverage_registry.json` already references them via `bindingIdentifiers`/`rustSymbols`. The raw gap count in `parity_diff_report.json` sees every gap row; the coverage summary subtracts runtime-verified rows before counting. Plans 2-5 should use the **primary** count to size task budgets because the gap rows need to be lifted out of the backlog regardless of runtime-verified status.

Per-owner delta attribution:

| Owner | Primary (gaps) | Cross (deferred) | Delta | Attribution |
|---|---:|---:|---:|---|
| `scanlog` | 71 | 67 | +4 | 4 gap rows already runtime_verified via scanlog registry entries |
| `config` | 35 | 26 | +9 | 9 gap rows already runtime_verified via config registry entries |
| `version_registry` | 5 | 4 | +1 | 1 gap row already runtime_verified |
| `aux` | 16 | 12 | +4 | 4 gap rows already runtime_verified (older tier2-aux runtime entries) |
| **all other owners** | 386 | 345 | — | delta=0 per owner (new crates have no registry entries yet) |

### 3-way backlog reconciliation (Step 2.6; Issue 12 + U2 fix)

| Source | Count | Canonical role |
|---|---:|---|
| `parity_diff_report.gaps[]` (tier2 only) | 473 | **PRIMARY** (per U2). Live diff inventory includes runtime-verified rows. |
| `deferred_runtime_backlog.entries[]` | 454 | Backlog is the post-filter projection: subtracts any rows already in the runtime registry. |
| `runtime_coverage_summary.summary.deferred_total` | 454 | Matches backlog because the summary counts the `deferred` classification after registry-matching. |

Plan 5 uses the PRIMARY count (472 after GLOBAL_FCX_HANDLER filter) when sizing residual absorption. Plan 6's NODE-06 landing criterion is `deferred_total == 0` from the SUMMARY (454 → 0) — that's the **exit** criterion, not the task-budget source.

---

## Per-Owner Deferred Row Breakdown

| Owner | Primary (gaps) | Cross (deferred) | Delta | Tier-1 current | Plan | Notes |
|---|---:|---:|---:|---:|---|---|
| `scanlog` | 71 | 67 | +4 | 16 | 04-02 | Scanlog full Tier-2 promotion (+58 Rust-only `@rust` proxy rows). Plan D-PLAN-02: one plan, no sub-module slicing. |
| `config` | 35 | 26 | +9 | 50 | 04-03 | Config Tier-2 promotion. 22 are `crashgen_settings` typed rows today and are reclassified below. |
| `version_registry` | 5 | 4 | +1 | 55 | 04-04 | Plus **3** HARM-01/02 PE-version rows added in Plan 04-04 Task 2 (`extractPeVersion` + `isValidPePath` + `JsPeVersion` return shape). |
| `version` | 16 | 16 | 0 | 0 | 04-04 | New owner from 10→19 crate expansion (A1). PE-version work lives in this crate's `pe_version` submodule. |
| `aux` | 16 | 12 | +4 | 140 | 04-05 | Legacy "aux" bucket from pre-expansion shape. Plans 2-5 will phase out this label as owners migrate to distinct labels. |
| `constants` | 30 | 30 | 0 | 0 | 04-05 | New owner (A1/A5). All 30 rows are rust_unmapped. |
| `crashgen_settings` | 22 | 22 | 0 | 0 | 04-05 | New owner (A1). Direct `classic-node/src/crashgen_rules.rs` binding. **Plan 5 creates `crashgen_rules.spec.ts`** (see Spec File Inventory). |
| `database` | 17 | 17 | 0 | 0 | 04-05 | New owner (A5). |
| `file_io` | 26 | 26 | 0 | 0 | 04-05 | New distinct owner (A5 — was "aux" pre-expansion). |
| `message` | 9 | 9 | 0 | 0 | 04-05 | New distinct owner (A5). |
| `path` | 26 | 26 | 0 | 0 | 04-05 | New distinct owner (A5). |
| `perf` | 2 | 2 | 0 | 0 | 04-05 | New distinct owner (A5). Very small surface. |
| `registry` | 14 | 14 | 0 | 0 | 04-05 | New distinct owner (A5). |
| `scangame` | 83 | 83 | 0 | 0 | 04-05 | **Largest new owner.** 83 deferred rows. Plan 5 should size accordingly. |
| `settings` | 23 | 23 | 0 | 0 | 04-05 | New distinct owner (A5). |
| `shared` | 15 | 15 | 0 | 0 | 04-05 | New distinct owner (A5). |
| `update` | 7 | 7 | 0 | 0 | 04-05 | New owner (A5). |
| `web` | 15 | 15 | 0 | 0 | 04-05 | New owner (A5). |
| `xse` | 17 | 17 | 0 | 0 | 04-05 | New owner (A5). |
| `yaml` | 23 | 23 | 0 | 0 | 04-05 | New owner (A5). |

**Residual candidates (rolled up to Plan 04-05):** `aux`, `constants`, `crashgen_settings`, `database`, `file_io`, `message`, `path`, `perf`, `registry`, `scangame`, `settings`, `shared`, `update`, `web`, `xse`, `yaml`

---

## Task Budget Summary

Plan-skeleton estimates (from D-PLAN-01) vs actual primary counts:

| Plan | Owner | Skeleton estimate | Actual primary | Surplus/deficit |
|---|---|---:|---:|---:|
| 04-02 | scanlog | 67 (58 `@rust` + 9 direct) | **71** | **+4** (4 runtime-verified rows still need promotion) |
| 04-03 | config | 23-26 (12 `@rust` + 14 direct) | **35** | **+9** |
| 04-04 | version_registry | 4 (direct) + 3 HARM rows | **5** + 3 HARM = **8** | **+1** |
| 04-04 | version | ~16 (A1 inclusion) | **16** | 0 |
| 04-05 | aux roll-up (everything else) | 7-12 | **374** | **+362** |

The biggest deviation from the plan skeleton is the Plan 05 aux roll-up: the skeleton estimated 7-12 aux rows, but the A10 sizing reveals **374 rows across 16 distinct new owners** (largest: `scangame=83`, `constants=30`, `path=26`, `file_io=26`, `yaml=23`, `settings=23`, `crashgen_settings=22`, `xse=17`, `database=17`, `scanlog=16`, `web=15`, `shared=15`, `registry=14`, `message=9`, `update=7`, `perf=2`).

**Action required before Plan 5 is written:** The Plan 5 author MUST re-scope the plan to cover all 16 owner labels or split into multiple plans. The current Plan 05 skeleton at `.planning/phases/04-node-tier-collapse/04-05-aux-promotion-PLAN.md` was drafted before this sizing pass ran.

---

## Spec File Inventory (Step 2.5 — Issue 10 fix)

Enumeration of `ClassicLib-rs/node-bindings/classic-node/__test__/*.spec.ts` files (20 present as of 2026-04-09):

```
cli.spec.ts, config.spec.ts, constants.spec.ts, database.spec.ts, fileio.spec.ts,
message.spec.ts, parity_tier1.spec.ts, path.spec.ts, regression_drift.spec.ts,
resource.spec.ts, scangame.spec.ts, scanlog.spec.ts, settings.spec.ts,
shared.spec.ts, update.spec.ts, version.spec.ts, version_registry.spec.ts,
web.spec.ts, xse.spec.ts, yaml.spec.ts
```

Per-owner spec file mapping:

| Owner | Expected spec file | Status |
|---|---|---|
| `scanlog` | `scanlog.spec.ts` | EXISTS |
| `config` | `config.spec.ts` | EXISTS |
| `version_registry` | `version_registry.spec.ts` | EXISTS |
| `version` | `version.spec.ts` | EXISTS |
| `constants` | `constants.spec.ts` | EXISTS |
| `crashgen_settings` | `crashgen_rules.spec.ts` | **MISSING — Plan 5 creates** |
| `database` | `database.spec.ts` | EXISTS |
| `file_io` | `fileio.spec.ts` | EXISTS |
| `message` | `message.spec.ts` | EXISTS |
| `path` | `path.spec.ts` | EXISTS |
| `perf` | (no dedicated spec file today) | N/A — Plan 5 may append to `shared.spec.ts` or create `perf.spec.ts` |
| `registry` | (no dedicated spec file today) | N/A — Plan 5 may append to `shared.spec.ts` or create `registry.spec.ts` |
| `scangame` | `scangame.spec.ts` | EXISTS |
| `settings` | `settings.spec.ts` | EXISTS |
| `shared` | `shared.spec.ts` | EXISTS |
| `update` | `update.spec.ts` | EXISTS |
| `web` | `web.spec.ts` | EXISTS |
| `xse` | `xse.spec.ts` | EXISTS |
| `yaml` | `yaml.spec.ts` | EXISTS |

**D-TEST-01 compliance:** Plans 2-5 should append new `describe` blocks to the existing `<module>.spec.ts` files rather than create sibling spec files. `crashgen_rules.spec.ts` is the only intentional new spec file (Plan 5 Task 1 creates it).

---

## Notes for Plan 6 (Tier-2 Cleanup Cascade)

Phase 4 Plan 1 landed these invariants that Plan 6 must preserve or cleanly strip:

- `RUST_FULL_INVENTORY_CRATES` set and `include_rust_symbol()` helper are deleted from `generate_baseline.py`. **Plan 6 does not need to re-delete them.**
- `tier='tier2'` label assignments at the `parse_rust_surface()` entry-building sites still exist (pre-existing lines inside `parse_rust_surface`). **Plan 6 sweeps these** as part of the Tier-2 dead-code removal.
- `validate_contract_surface()` bidirectional guard is wired into `check_parity_gate.py::main()`. **Plan 6 keeps this guard** — it is the replacement for the deleted Tier-2 classification logic.
- `deferred_runtime_backlog.json` was regenerated from 109 → 454 entries during Plan 1 Task 1. **Plan 6's target end-state is 0 entries** (empty `entries[]` array). Per Phase 3 Plan 09b empirical evidence, emptying the backlog drives `deferred_total` from 454 → 0 even after gap rows are removed.
- `tier2_wave_manifest.json` was NOT regenerated in Plan 1 (Phase 3 Plan 01 regenerated it; Phase 4 deferred the regeneration because `generate_deferred_backlog.py` falls back to wave=null when the manifest has no entry for a gap). **Plan 6 deletes the wave manifest file entirely** (DOC-02/03/04 per CONTEXT Deferred Ideas).
