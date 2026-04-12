---
phase: 02-crashgen-config-merge
plan: 02
subsystem: tooling-and-docs
tags: [node-parity, python-parity, cxx-parity, docs-consolidation, deviation]

requires:
  - phase: 02-crashgen-config-merge
    plan: 01
    provides: 17-crate business-logic topology (post-Phase-2 baseline with classic-crashgen-settings-core absorbed into classic-config-core)
provides:
  - Node parity generator tooling aligned with 17-crate business-logic topology
  - API docs consolidated (crashgen rule model section inside classic-config-core.md)
  - Node baseline parity contract reparented (crashgen_settings owner -> config owner)
  - Runtime coverage registry aligned with post-merge topology (node-tier1-crashgen-settings deleted, node-tier1-config updated to 107 rows)
  - All 3 parity gates (CXX, Python, Node) green with zero drift
affects: [phase-03 constants merge, phase-04 gate validation]

tech-stack:
  added: []
  patterns:
    - "Owner-reparent pattern reused from Phase 1 (tools/parity_contract_merge_owner.py) — no manual JSON editing"
    - "Python wheel rebuild before Python parity gate (D-12 / research Section 5) to avoid stale-wheel drift"

key-files:
  created:
    - .planning/phases/02-crashgen-config-merge/deferred-items.md
  modified:
    - tools/node_api_parity/generate_baseline.py
    - tools/node_api_parity/tests/test_generate_baseline_targets.py
    - docs/api/classic-config-core.md
    - docs/api/README.md
    - docs/api/binding-parity-overview.md
    - docs/api/classic-scanlog-core.md
    - docs/api/classic-scangame-core.md
    - docs/RUST_DOCUMENTATION_INDEX.md
    - CLAUDE.md
    - .planning/PROJECT.md
    - .planning/codebase/ARCHITECTURE.md
    - .planning/codebase/STRUCTURE.md
    - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json
    - docs/implementation/node_api_parity/baseline/parity_contract.json
    - docs/implementation/node_api_parity/baseline/parity_diff_report.json
    - docs/implementation/node_api_parity/baseline/parity_diff_report.md
    - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json
    - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md
    - ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json
    - ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md
    - ClassicLib-rs/python-bindings/parity-artifacts/python_api_surface.json
    - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
    - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md
    - ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json
  deleted:
    - docs/api/classic-crashgen-settings-core.md

key-decisions:
  - "Used tools/parity_contract_merge_owner.py to reparent 21 crashgen_settings rows to config owner (Phase 1 precedent) — not a baseline regeneration, but a structural owner-reparent required by the generator cleanup"
  - "Reduced test floor from >= 19 to >= 17 instead of plan-stated 18: actual post-Phase-2 count is 17 (pre-edit floor was stale — the plan's >= 19 floor had already drifted from actual 18 pre-Phase-2)"
  - "Skipped editing .planning/REQUIREMENTS.md per M5 — CGEN-01/02/03 lines describe the pre-merge crate name but they are requirement statements protected by the verifier workflow"

patterns-established:
  - "When a workspace crate is deleted, the Node parity tooling cleanup is: (1) remove from generate_baseline.py dicts, (2) remove tests asserting the crate's presence, (3) reparent orphan rows in baseline parity_contract.json via parity_contract_merge_owner.py, (4) update runtime_coverage_registry.json entries, (5) regenerate artifacts via gate run"

requirements-completed: [CGEN-01, CGEN-02, CGEN-03]

duration: ~40 min
completed: 2026-04-11
---

# Phase 2 Plan 2: Crashgen-Config Merge Tooling + Docs Summary

**Node parity generator tooling cleaned up, API docs consolidated into classic-config-core.md, Node parity baseline contract reparented from crashgen_settings owner to config owner, all 3 parity gates (CXX, Python, Node) green with zero drift.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3 of 3 (all completed)
- **Files modified:** 24 (23 modified, 1 deleted, 1 created)

## Task Commits

1. **Task 1: Node parity generator tooling update** — `58274042` (Update) — removed classic-crashgen-settings-core from RUST_TARGET_CRATES, RUST_OWNER_BY_CRATE, SQUAD_BY_OWNER, deleted two crashgen-specific test functions, reduced floor to 17
2. **Task 2: API doc consolidation + D-15 cross-ref sweep** — `5c7bf726` (Docs) — merged classic-crashgen-settings-core.md into classic-config-core.md as a Crashgen rule model section, updated README index, binding-parity-overview, classic-scanlog-core, classic-scangame-core, RUST_DOCUMENTATION_INDEX, CLAUDE.md (17 pure Rust crates), PROJECT.md, ARCHITECTURE.md, STRUCTURE.md
3. **Task 3 deviation fix: Reparent Node baseline contract** — `57d93ef1` (Chore) — used parity_contract_merge_owner.py to reparent 21 rows from crashgen_settings owner to config owner, updated runtime_coverage_registry.json, regenerated Node + Python parity artifacts

## Parity Gate Results

All three gates exit 0 with zero drift (verify-only per D-12).

| Gate   | Command                                                               | Exit | Notes                                                                                    |
| ------ | --------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------- |
| CXX    | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`      | 0    | Zero drift vs committed baseline                                                         |
| Python | `python tools/python_api_parity/check_parity_gate.py --repo-root .`   | 0    | tier1_contract_total=1098, tier1_matched=1098, total_gaps=0, tier1_gap_total=0           |
| Node   | `bun run parity:gate:local`                                           | 0    | Required baseline reparent first (deviation #1); tier1_contract_total=705, tier1_matched=705 |

### Python wheel refresh (before Python gate)

- `./rebuild_rust.ps1 -Target python` exited 0
- All 18 Python binding crates rebuilt and installed into `ClassicLib-rs/python-bindings/.venv`
- This step is load-bearing per research Section 5: the Python parity gate reads the installed wheel's exported symbols, so a stale wheel would compare against pre-Phase-2 surface and produce false drift

## Final State

### API docs

- `docs/api/classic-crashgen-settings-core.md` deleted
- `docs/api/classic-config-core.md` gained a new `## Crashgen rule model` section with all rule types, evaluation flow, and an updated usage example using `classic_config_core::` imports
- `docs/api/README.md` numbered index shortened by one entry; config-core description extended to note the absorbed rule model
- `docs/api/binding-parity-overview.md` fold entry reflects Phase 2 absorption

### CLAUDE.md crate count

- Old: "18 pure Rust crates (v9.1.0 Phase 1 merge: yaml-core absorbed into settings-core, 19 -> 18)"
- New: "17 pure Rust crates (v9.1.0 Phase 1 merge: yaml-core -> settings-core, 19 -> 18; v9.1.0 Phase 2 merge: classic-crashgen-settings-core -> classic-config-core via `classic_config_core::crashgen_rules::*`, 18 -> 17)"

### Node baseline parity contract (post-reparent)

- 21 rows reparented: `ownerModule` crashgen_settings -> config (via `tools/parity_contract_merge_owner.py`)
- 28 rustCrate field updates (classic-crashgen-settings-core -> classic-config-core)
- 0 squad updates needed (crashgen_settings owner was not referenced in squads.ownerModules)
- 0 top-level ownerModules deletions (crashgen_settings was never a top-level module entry)
- Row id uniqueness verified post-merge
- Config owner row count: 86 -> 107

### Runtime coverage registry

- `node-tier1-crashgen-settings` entry deleted
- `node-tier1-config` contractCount: 86 -> 107, contractIdsHash refreshed to `5979e7195066a913fd0e5e84f3eccd8fa335d994b09aa2c66d6a093f77a6e399`
- Added note field documenting the Phase 2 absorption

## Files swept during D-15 cross-reference cleanup

Active in-scope files (non-archived, non-phase-working):

- CLAUDE.md — crate count updated to 17
- docs/api/README.md — index + bullet list cleaned
- docs/api/classic-config-core.md — absorbed rule model section added
- docs/api/classic-crashgen-settings-core.md — deleted
- docs/api/binding-parity-overview.md — per-crate row folded
- docs/api/classic-scanlog-core.md — 3 references updated to point at classic-config-core#crashgen-rule-model
- docs/api/classic-scangame-core.md — 4 references updated similarly
- docs/RUST_DOCUMENTATION_INDEX.md — entry removed/redirected
- .planning/PROJECT.md — Phase 2 marked complete, 19 -> 17 crate count note
- .planning/codebase/ARCHITECTURE.md — 18 -> 17 business-logic count, 18 -> 17 python binding count
- .planning/codebase/STRUCTURE.md — classic-crashgen-settings-core directory line removed

Skipped per D-15 scope rules:

- `.planning/milestones/v9.1.0-bindings-phases/**` — archived milestone plans
- `.planning/milestones/v9.1.0-bugfixes-phases/**` — archived milestone plans
- `.planning/phases/02-crashgen-config-merge/02-*.md` — input context (plan/research/context files for the current phase itself)
- `AGENTS.md` — M6 dropped from files_modified (no crashgen matches found at plan time, verified at execution time)

## Historical references preserved (not edited)

- `.planning/ROADMAP.md` — Phase 2 narrative lines describe the work being done this phase (historical, not stale)
- `.planning/REQUIREMENTS.md` — CGEN-01/02/03 requirement statements reference the pre-merge crate name as part of the goal description (protected per M5 — checkbox state unchanged, and the text names the pre-merge crate as a requirement subject)
- `.planning/phases/02-crashgen-config-merge/02-01-SUMMARY.md` — wave 1 historical summary
- CLAUDE.md line 281 — Phase 1 historical "19 to 18" sentence preserved and extended

## CGEN checkbox protection (M5)

`git diff HEAD .planning/REQUIREMENTS.md` returns zero diff — no checkbox lines were touched by this plan. REQUIREMENTS.md was not even staged. CGEN-01/02/03 state is verifier-managed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test floor reduced to 17 instead of plan-stated 18**
- **Found during:** Task 1 Step C (pytest suite run)
- **Issue:** Plan M3 said "reduce floor by exactly 1 from pre-edit 19 to 18". Actual pre-edit count was 18 (the `>= 19` floor was already stale from a prior drift), so after removing classic-crashgen-settings-core the actual count is 17. Floor set to >= 17 to match ground truth and keep the tripwire useful.
- **Fix:** `test_rust_target_crates_floor_is_nineteen` renamed to `test_rust_target_crates_floor_is_seventeen`; floor constant 19 -> 17; docstring updated.
- **Committed in:** `58274042` (Task 1 commit)

**2. [Rule 3 - Blocking] Reparent Node baseline parity_contract.json owner from crashgen_settings to config**
- **Found during:** Task 3 Node parity gate first run (`bun run parity:gate:local`)
- **Issue:** After removing the `crashgen_settings` entry from `SQUAD_BY_OWNER` in generate_baseline.py (Task 1), the gate crashed with `KeyError: 'crashgen_settings'` at `generate_diff_report()` because `docs/implementation/node_api_parity/baseline/parity_contract.json` still had 21 tier1 rows tagged with `ownerModule: crashgen_settings`. The plan's "verify-only" intent applies to DRIFT, but this was a STRUCTURAL incompatibility introduced by the tooling cleanup — not a drift condition.
- **Fix:** Used the Phase 1 precedent helper `tools/parity_contract_merge_owner.py` to reparent the 21 rows from `crashgen_settings` -> `config` owner (also updating their `rustCrate` field from classic-crashgen-settings-core -> classic-config-core). This is the same mechanical fix Phase 1 used when yaml owner was reparented to settings owner (see commit `0f81d043`). The 21 rows already had valid Node counterparts; only the owner tag needed to follow the crate merge.
- **Additional step:** Deleted the orphaned `node-tier1-crashgen-settings` entry from `runtime_coverage_registry.json` and updated the `node-tier1-config` entry's `contractCount` (86 -> 107) and `contractIdsHash` to match the reparented contract.
- **Files modified:** `docs/implementation/node_api_parity/baseline/parity_contract.json`, `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json`, plus gate-regenerated artifacts in `docs/implementation/node_api_parity/baseline/` and `ClassicLib-rs/python-bindings/parity-artifacts/`
- **Verification:** All 3 gates exit 0 after the reparent
- **Committed in:** `57d93ef1` (Task 3 deviation commit)
- **Note:** The plan's acceptance criterion "no baseline files were regenerated" is technically violated. However, this follows the explicit Phase 1 precedent (commit `0f81d043` reparented yaml owner across parity contracts) — the reparent is a structural alignment, not a drift-masking regeneration.

### Out-of-scope pre-existing issues (deferred, NOT fixed)

**test_tier1_contract_total_baseline_floor — pre-existing tier1Mappings floor regression**
- **Discovered:** Task 1 pytest run of `tools/node_api_parity/tests/`
- **Issue:** `tier1Mappings regressed below Phase 4 floor: 705 < 711` — pre-existing, unrelated to Plan 02-02
- **Action:** Logged to `.planning/phases/02-crashgen-config-merge/deferred-items.md`, NOT fixed here
- **Scope rationale:** No files touched by this plan affect `parity_contract.json` row totals. The 6-row gap predates this plan and belongs to future contract-refresh work in Phase 4.

## Verification Results

| Check | Result |
|---|---|
| `Select-String tools/node_api_parity/generate_baseline.py -Pattern 'classic-crashgen-settings-core\|crashgen_settings'` | 0 matches |
| `Select-String tools/node_api_parity/tests/test_generate_baseline_targets.py -Pattern 'classic-crashgen-settings-core\|Amendment A1'` | 0 matches |
| `Test-Path docs/api/classic-crashgen-settings-core.md` | False (deleted) |
| `Select-String docs/api/classic-config-core.md -Pattern 'Crashgen rule model'` | 1 match |
| `Select-String docs/api/README.md -Pattern 'classic-crashgen-settings-core'` | 0 matches |
| `Select-String docs/api/binding-parity-overview.md -Pattern 'classic-crashgen-settings-core'` | 0 matches |
| `Select-String docs/api/classic-scanlog-core.md,docs/api/classic-scangame-core.md,docs/RUST_DOCUMENTATION_INDEX.md -Pattern 'classic_crashgen_settings_core\|classic-crashgen-settings-core'` | 0 matches |
| `Select-String CLAUDE.md -Pattern '17 pure Rust crates'` | 1 match |
| `Select-String CLAUDE.md -Pattern '18 pure Rust crates'` | 0 matches |
| `git diff HEAD .planning/REQUIREMENTS.md` | empty (CGEN checkboxes protected) |
| CXX parity gate | PASS (exit 0, zero drift) |
| `./rebuild_rust.ps1 -Target python` | PASS (18/18 modules) |
| Python parity gate | PASS (tier1_gap_total=0, total_gaps=0) |
| Node parity gate | PASS (tier1_contract_total=705, tier1_matched=705, after reparent deviation) |

## Self-Check: PASSED

- Task commits `58274042`, `5c7bf726`, `57d93ef1` present in `git log --oneline -5`.
- `docs/api/classic-config-core.md` contains the `Crashgen rule model` section (verified via Grep).
- `docs/api/classic-crashgen-settings-core.md` does not exist (verified via git status showing `D` and status after commit showing clean).
- All three parity gates exit 0 after the reparent deviation was applied.
- `.planning/REQUIREMENTS.md` untouched (not staged, not committed by this plan).

## Next Phase Readiness

- Phase 2 complete: source-level merge (plan 02-01) + tooling/docs cleanup (this plan).
- Pattern captured for Phase 3 constants merge: when a crate is absorbed into another, the Node baseline parity_contract.json requires a `parity_contract_merge_owner.py` reparent in the SAME cleanup wave as the generator-dict removal, otherwise the gate crashes on the orphaned owner. Phase 3 should plan this reparent as an explicit task, not a deviation.
- Phase 2 ready for `/gsd:verify-work`.

---
*Phase: 02-crashgen-config-merge*
*Completed: 2026-04-11*
