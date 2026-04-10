---
phase: 04-node-tier-collapse
plan: 01
subsystem: infra
tags: [node-parity, napi-rs, python-tooling, pytest, tier-collapse, a10-sizing, bidirectional-guard, h1-fail-closed]

# Dependency graph
requires:
  - phase: 03-python-tier-collapse
    provides: "validate_contract_rust_symbols precedent (Phase 3 Pitfall 2 guard); Phase 3 Plan 01 A10 sizing precedent; deferred_runtime_backlog regeneration pattern"
provides:
  - "RUST_TARGET_CRATES expanded from 10 to 19 crates (matches Phase 3 set PLUS classic-crashgen-settings-core per A1)"
  - "RUST_FULL_INVENTORY_CRATES filter and include_rust_symbol() helper deleted; every tracked crate now yields full public symbols"
  - "Bidirectional validate_contract_surface() guard with H1 fail-closed rejection of 7 malformed row shapes (None, empty-string, wrong-type)"
  - "A10 sizing report (JSON+MD) with dual-source primary (parity_diff_report.gaps) + cross (runtime_coverage_summary.deferred) reconciliation"
  - "Wave 0 pytest scaffold: 26 tests + 1 xfail covering target crates, guard diagnostics, baseline floor, Plan 6 cleanup tripwire"
  - "Environment smoke: bun run build + napi-build + tsc + dts:freshness:check verified green on first attempt from PowerShell"
  - "Deferred backlog regenerated from 109 → 454 entries across 20 owners (vs original 4 owners)"
  - "Rust surface grew from 148 → 605 symbols across all 19 crates"
affects:
  - "04-02-scanlog-promotion"
  - "04-03-config-promotion"
  - "04-04-version-registry-and-pe-version"
  - "04-05-aux-promotion (needs scope expansion: 374 rows across 16 owner labels)"
  - "04-06-tier2-cleanup-cascade"

# Tech tracking
tech-stack:
  added: []  # No new dependencies — pytest + json/pathlib stdlib only
  patterns:
    - "Bidirectional H1 fail-closed guard (5-shape + 2-exotic rejection before surface lookups)"
    - "Dual-source A10 sizing: primary from live diff gaps, cross from coverage summary"
    - "Owner label discipline: no default-to-aux fallback; every target crate must have explicit label"
    - "parse_rust_surface() isolated-crate testing via RUST_TARGET_CRATES monkey-patch"

key-files:
  created:
    - "tools/node_api_parity/tests/__init__.py"
    - "tools/node_api_parity/tests/conftest.py"
    - "tools/node_api_parity/tests/test_generate_baseline_targets.py"
    - "tools/node_api_parity/tests/test_validate_contract_surface.py"
    - "tools/node_api_parity/tests/test_check_parity_gate.py"
    - ".planning/phases/04-node-tier-collapse/04-01-A10-sizing.json"
    - ".planning/phases/04-node-tier-collapse/04-01-A10-sizing.md"
  modified:
    - "tools/node_api_parity/generate_baseline.py (RUST_TARGET_CRATES 10 → 19; RUST_FULL_INVENTORY_CRATES / include_rust_symbol deleted; RUST_OWNER_BY_CRATE + SQUAD_BY_OWNER extended to 20 owners)"
    - "tools/node_api_parity/check_parity_gate.py (validate_contract_surface guard + wiring in main())"
    - "docs/implementation/node_api_parity/baseline/rust_api_surface.json (148 → 605 symbols)"
    - "docs/implementation/node_api_parity/baseline/node_api_surface.json (refreshed)"
    - "docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md} (128 → 480 gaps)"
    - "docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md} (deferred_total 109 → 454, newly_uncovered 0 → 339 → 0)"
    - "docs/implementation/node_api_parity/baseline/handoff_map.md (refreshed for 20 owners)"
    - "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json (Rule 3 regeneration: 109 → 454 entries)"

key-decisions:
  - "Plan scaffold's scanlog['deferred_primary'] ∈ (66, 67) acceptance criterion was stale; actual primary count is 71 (raw 72 minus 1 for GLOBAL_FCX_HANDLER). Documented per-owner delta between primary and cross sources."
  - "Delete inventory filter without relocating tier-labeling: parse_rust_surface still writes 'tier': 'tier1/tier2' labels for backward compat; Plan 6 sweeps these as vestigial."
  - "Rule 3 auto-fix — regenerate deferred_runtime_backlog.json mid-Task-1 because the 10→19 expansion produced 339 newly_uncovered rows that failed the gate's zero-drift assertion. This is the Phase 4 analogue of Phase 3 Plan 01's wave-manifest + backlog regeneration."
  - "Rule 2 auto-fix — replaced render_diff_markdown() hard-coded owner tuple with dynamic iteration; the pre-existing ('scanlog', 'config', 'version_registry', 'aux') tuple silently dropped 15 new owners."
  - "Left tier2_wave_manifest.json stale (generate_deferred_backlog.py tolerates missing wave info); Plan 6 deletes the file entirely per DOC-02/03/04."
  - "All 15 new owner labels routed to 'Squad B' in SQUAD_BY_OWNER to preserve the existing two-squad shape; squad label is not load-bearing for gate exit code."

patterns-established:
  - "H1 fail-closed pattern: walk every tier1Mappings row, reject 7 malformed shapes before surface lookups, only @rust-suffix rows may omit nodeExport."
  - "Dual-source A10 sizing: PRIMARY from parity_diff_report.gaps (load-bearing per U2), CROSS from runtime_coverage_summary.deferred, document per-owner delta explicitly."
  - "Wave 0 pytest scaffold for tier-collapse milestones: test_generate_baseline_targets (crate inventory) + test_validate_contract_surface (guard) + test_check_parity_gate (floor + xfail snapshot)."

requirements-completed: [NODE-01]

# Metrics
duration: 15min
completed: 2026-04-09
---

# Phase 04 Plan 1: Tooling Expansion + Bidirectional Guard + A10 Sizing + Env Smoke Summary

**Expanded Node parity tooling from 10 to 19 tracked crates, added H1 fail-closed bidirectional validate_contract_surface guard, published dual-source A10 sizing report (472 primary / 454 cross deferred across 20 owners), and verified bun run build env smoke succeeds end-to-end.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-09T23:01:54Z
- **Completed:** 2026-04-09T23:17:22Z
- **Tasks:** 3
- **Files modified:** 15 (7 created, 8 modified)

## Accomplishments

- `RUST_TARGET_CRATES` expanded 10 → 19 entries (matches Phase 3's Python set PLUS `classic-crashgen-settings-core` per research amendment A1). New entries: `classic-yaml-core`, `classic-version-core`, `classic-web-core`, `classic-crashgen-settings-core`, `classic-update-core`, `classic-xse-core`, `classic-database-core`, `classic-scangame-core`, `classic-constants-core`.
- `RUST_FULL_INVENTORY_CRATES` set and `include_rust_symbol()` helper deleted, along with all 4 callsites inside `parse_rust_surface()`. Every tracked crate now produces full public-symbol output unconditionally. Rust surface grew from 148 → 605 symbols.
- `RUST_OWNER_BY_CRATE` extended to 19 entries with distinct owner labels matching Phase 3's A5 shape: `scanlog`, `config`, `version_registry`, `shared`, `perf`, `registry`, `file_io`, `path`, `settings`, `message`, `yaml`, `version`, `web`, `crashgen_settings`, `update`, `xse`, `database`, `scangame`, `constants`. No silent default-to-aux fallback.
- `SQUAD_BY_OWNER` extended to cover all 20 possible owners (including the legacy `aux` bucket) so `render_handoff_markdown()` never KeyErrors.
- `validate_contract_surface(contract, rust_manifest, node_manifest)` added to `check_parity_gate.py` and wired into `main()` unconditionally. Rejects 7 malformed row shapes with explicit diagnostics before performing surface lookups (3 original H1 shapes + 4 Round 2 Fix 1.1 exotic-value shapes: non-string / empty-string for both `rustSymbol` and `nodeExport`). Only `@rust`-suffix rows may omit `nodeExport`.
- Dual-source A10 sizing report published at `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}`. Primary total: **472** (PARITY_DIFF_REPORT.gaps, GLOBAL_FCX_HANDLER filtered). Cross total: **454** (RUNTIME_COVERAGE_SUMMARY.deferred_total). Reconciliation delta: **+18** (runtime-verified gap rows folded into verified bucket by cross source). Owners tracked: **20** (was 4).
- Wave 0 pytest scaffold landed: 26 passing tests + 1 strict xfail across `test_generate_baseline_targets.py` (9 tests), `test_validate_contract_surface.py` (15 tests), and `test_check_parity_gate.py` (2 passing + 1 xfail).
- `bun run build` end-to-end smoke test passed on first attempt from PowerShell (no `use_msvc_from_git_bash.sh` intervention required). `napi build --release --platform` produced the native `.node` file, `tsc -p tsconfig.json` produced `dist/cli/*.js`, `bun run dts:freshness:check` exited 0 against the committed `index.d.ts`.
- `bun run parity:gate:local` exits 0 end-to-end.

## Task Commits

Each task was committed atomically with normal pre-commit hooks (no `--no-verify`):

1. **Task 1: Expand RUST_TARGET_CRATES from 10 to 19 + delete inventory filter + extend owner/squad maps** — `1b087c32` (refactor)
2. **Task 2: Add bidirectional validate_contract_surface guard with H1 fail-closed malformed-row rejection** — `63626c8e` (feat)
3. **Task 3: bun run build env smoke + A10 sizing report (dual-source per U2) + xfail baseline floor test** — `8b7921bb` (feat)

## Files Created/Modified

**Created (7):**
- `tools/node_api_parity/tests/__init__.py` — empty package marker
- `tools/node_api_parity/tests/conftest.py` — pytest bootstrap (mirrors `python_api_parity/tests/conftest.py`)
- `tools/node_api_parity/tests/test_generate_baseline_targets.py` — 9 tests for `RUST_TARGET_CRATES` invariants
- `tools/node_api_parity/tests/test_validate_contract_surface.py` — 15 tests for the H1 fail-closed guard
- `tools/node_api_parity/tests/test_check_parity_gate.py` — 2 passing + 1 xfail (Plan 6 tripwire)
- `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` — dual-source sizing data
- `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.md` — human-readable sizing table + 3-way reconciliation + spec file inventory

**Modified (8):**
- `tools/node_api_parity/generate_baseline.py` — `RUST_TARGET_CRATES` 10 → 19; `RUST_FULL_INVENTORY_CRATES` / `include_rust_symbol` deleted; `RUST_OWNER_BY_CRATE` + `SQUAD_BY_OWNER` extended; Rule 2 auto-fix in `render_diff_markdown()` for dynamic owner iteration
- `tools/node_api_parity/check_parity_gate.py` — `validate_contract_surface()` added + wired into `main()`
- `docs/implementation/node_api_parity/baseline/rust_api_surface.json` — 148 → 605 symbols
- `docs/implementation/node_api_parity/baseline/node_api_surface.json` — refreshed (no content change, Node source untouched)
- `docs/implementation/node_api_parity/baseline/parity_diff_report.{json,md}` — 128 → 480 gaps (473 tier2 + 0 tier1_drift)
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.{json,md}` — tracked_surface_total 402 → 741, deferred_total 109 → 454, newly_uncovered_total 0 → 0 (after Rule 3 backlog regeneration)
- `docs/implementation/node_api_parity/baseline/handoff_map.md` — refreshed for 20 owners
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` — 109 → 454 entries (Rule 3 auto-fix)

## Decisions Made

1. **`>= 19` not `== 19` floor semantics** — Plan 5's A10 residual absorption may add a 20th crate; tight equality is hostile to future discovery. The floor is the load-bearing semantic.
2. **Distinct owner labels per Phase 3 A5** — `shared`, `perf`, `registry` kept distinct rather than collapsed to `aux`. Plan 5 will phase out the legacy `aux` bucket as rows migrate to distinct labels.
3. **`crashgen_settings` as explicit owner label** — no default-to-aux fallback. A row with no explicit owner would fail-loud.
4. **All 15 new owners assigned to Squad B** — preserves the two-squad shape; squad label is not load-bearing for gate exit code per CONTEXT Claude's Discretion.
5. **Left `tier2_wave_manifest.json` stale (not regenerated)** — `generate_deferred_backlog.py` tolerates missing wave info (falls back to `wave=null`). Plan 6 deletes the wave manifest file entirely per DOC-02/03/04.
6. **Reverted timestamp-only baseline churn in Task 3 commit** — running `--update-baseline` in Task 3 produced pure-timestamp diffs with no content change. Reverted per project guide ("ignore pure-timestamp diffs where possible").

## Deviations from Plan

Three deviations auto-handled during Task 1; all directly caused by the RUST_TARGET_CRATES expansion and captured in the Task 1 commit.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Regenerate deferred_runtime_backlog.json**
- **Found during:** Task 1 (after running `generate_baseline.py` + `check_parity_gate.py --update-baseline`)
- **Issue:** Expanding tracked crates from 10 to 19 surfaced 339 new `rust_unmapped` gap rows that had no matching entry in `deferred_runtime_backlog.json`. The runtime coverage summary classified them as `newly_uncovered_total=339`, which tripped the `check_parity_gate.py` `newly_uncovered_total > 0` exit condition. The gate would not have exited 0 without handling this.
- **Fix:** Ran `python tools/node_api_parity/generate_deferred_backlog.py --repo-root .` to regenerate the backlog from the refreshed diff report. Entries grew 109 → 454 across all 20 owners. `newly_uncovered_total` dropped from 339 → 0 and the gate exited 0.
- **Files modified:** `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`
- **Verification:** `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0.
- **Committed in:** `1b087c32` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Dynamic owner iteration in render_diff_markdown()**
- **Found during:** Task 1 (noticed while scanning `generate_baseline.py` for hard-coded owner references)
- **Issue:** `render_diff_markdown()` contained a hard-coded tuple `("scanlog", "config", "version_registry", "aux")` for the per-owner gap counts table. With the 10 → 19 crate expansion adding 15 new owner labels, the table would silently drop 15 rows. This is a correctness bug.
- **Fix:** Replaced the hard-coded tuple with `sorted(diff_report.get("gap_counts_by_owner_tier", {}))` so every owner that appears in the diff report is rendered.
- **Files modified:** `tools/node_api_parity/generate_baseline.py`
- **Verification:** Refreshed `parity_diff_report.md` shows all 20 owners in the "Gap Counts By Owner/Tier" section.
- **Committed in:** `1b087c32` (Task 1 commit)

**3. [Rule 1 - Bug] Plan scaffold's scanlog['deferred_primary'] ∈ (66, 67) assertion was stale**
- **Found during:** Task 3 (when generating the sizing JSON)
- **Issue:** The plan file's acceptance criterion expected `scanlog['deferred_primary']` in `(66, 67)`. The actual PRIMARY count is 71 (raw 72 from `parity_diff_report.gaps[]` minus 1 for GLOBAL_FCX_HANDLER). The 66/67 values matched the CROSS source (`runtime_coverage_summary.perOwnerModule.scanlog.deferred = 67`) minus 1, not the PRIMARY source. The plan writer assumed the two sources had equivalent counts; they don't, because `runtime_coverage_summary` subtracts runtime-verified rows before counting.
- **Fix:** Used the correct PRIMARY count (71) and documented the per-owner delta explicitly in the sizing report (both JSON and MD). The delta is attributed to 4 scanlog gap rows already covered by runtime registry entries.
- **Files modified:** `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}`
- **Verification:** Sizing MD includes a dedicated "Primary vs Cross Reconciliation" section with per-owner attribution.
- **Committed in:** `8b7921bb` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 missing critical, 1 bug-in-plan-scaffold)
**Impact on plan:** All three fixes were essential for correctness and gate greenness. No scope creep — every fix was directly caused by the task's own changes (RUST_TARGET_CRATES expansion). The `scanlog` count deviation is a documentation-accuracy correction, not a code change.

## Issues Encountered

- **`parse_rust_surface()` signature mismatch** — The plan's test-scaffold example showed `parse_rust_surface({crate: path}, repo_root=repo_root)` but the live signature is `parse_rust_surface(repo_root, tier1_rust_symbols)`. I verified the real signature first (per the "verify APIs before testing" rule) and wrote the isolated-crate test using `RUST_TARGET_CRATES` monkey-patch instead of the plan's invented kwargs. Resolved without any production code change.
- **CRLF whitespace churn on `ClassicLib-rs/node-bindings/classic-node/index.d.ts`** — Pre-existing benign churn that `bun run build` would have overwritten with fresh content. Left untouched per the project-specific guidance (Windows CRLF handling). `dts:freshness:check` exits 0 against the committed file.
- **Timestamp-only baseline diffs after running `--update-baseline` in Task 3** — Reverted 4 files (`parity_diff_report.{json,md}`, `runtime_coverage_summary.{json,md}`) that only had `generated_at_utc` changes with no content diff. This keeps the Task 3 commit focused on the A10 sizing report.

## User Setup Required

None — no external service configuration required. All tooling runs locally via `python` and `bun`.

## Next Phase Readiness

**Ready for Plans 2-5:**
- Bidirectional `validate_contract_surface()` guard is live. Every row authored in Plans 2-5 will be checked on every gate invocation for both `rustSymbol ∈ rust_surface` and `nodeExport ∈ node_surface`, with H1 fail-closed diagnostics on 7 malformed row shapes.
- A10 sizing report is published at `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}`. Plans 2-5 read this to size task budgets. The primary source is load-bearing per U2.
- `bun run build` env is verified healthy. The executor's Node/napi-rs/MSVC chain works end-to-end with no intervention.
- Wave 0 pytest scaffold exists. Plans 2-5 extend `test_generate_baseline_targets.py` as they add crates; Plan 6 flips the `test_tier2_definition_removed_after_plan_6` xfail.

**Flag for Plan 5 author:** The A10 sizing reveals **374 rows across 16 owner labels** destined for Plan 05, versus the original Plan 05 skeleton estimate of 7-12 aux rows. The Plan 05 author MUST re-scope before executing. See `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.md` § "Task Budget Summary" and § "Notes for Plan 6".

**Flag for Plan 4 author:** `classic-version-core` is already in `RUST_TARGET_CRATES` as owner `version`. Plan 4 Task 1's `pub use pe_version::is_valid_executable_path;` re-export pre-flight is still an intra-plan prerequisite (the guard will fire if the re-export is missing when PE-version contract rows land in Task 2).

**Plan 6 tripwires active:**
- `test_tier2_definition_removed_after_plan_6` — xfail strict; flips to passing when Plan 6 deletes `tierDefinitions.tier2`.
- `test_tier1_contract_total_baseline_floor` — currently `>= 261`; Plans 2-5 raise this floor as they promote rows.

## Self-Check: PASSED

Verification commands executed 2026-04-09T23:17:22Z:

- `python -m pytest tools/node_api_parity/tests/ -q` → **26 passed, 1 xfailed** (expected)
- `python tools/node_api_parity/check_parity_gate.py --repo-root .` → **Tier-1 parity gate passed**
- `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` → **Tier-1 parity gate passed**
- `cd ClassicLib-rs/node-bindings/classic-node && bun run build` → **exit 0** (napi release build + tsc succeed)
- `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` → **exit 0** (index.d.ts freshness check passed)
- `Test-Path .planning/phases/04-node-tier-collapse/04-01-A10-sizing.json` → **True**
- `Test-Path .planning/phases/04-node-tier-collapse/04-01-A10-sizing.md` → **True**
- `git log --oneline -3` → 3 commits `8b7921bb`, `63626c8e`, `1b087c32`, all with the Phase 4 Plan 1 prefix.

---
*Phase: 04-node-tier-collapse*
*Completed: 2026-04-09*
