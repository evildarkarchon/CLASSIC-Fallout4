---
phase: 03-python-tier-collapse
plan: 01
subsystem: testing
tags: [python, parity-gate, pyo3, binding-tooling, pytest]

# Dependency graph
requires:
  - phase: 02-cxx-bridge-surface-expansion
    provides: completed CXX parity gate tooling pattern that informed the Python Pitfall 2 guard shape
provides:
  - Expanded Python parity tooling tracks 19 crates (18 -core business logic + classic-shared-py foundation) instead of the previous 3
  - _OWNER_RENDER_ORDER constant derived from RUST_OWNER_BY_CRATE values (eliminates hard-coded owner tuples)
  - validate_contract_rust_symbols() Pitfall 2 guard in check_parity_gate.py fails fast on missing pub use at crate root
  - Central tools/python_api_parity/tests/conftest.py sys.path bootstrap (no per-file sys.path.insert pollution)
  - 15-test Wave 0 tooling test suite (14 pass + 1 strict=True xfail for Plan 9b tier2 removal)
  - Pre-phase Pitfall 4 audit report (125 pyclass registrations verified; 1 dead-code orphan documented)
  - A10 sizing report — machine-readable per-owner tier2 gap counts for downstream plan budgeting
  - Expanded deferred_runtime_backlog.json and tier2_wave_manifest.json covering all 19 owners (1202 entries)
  - Refreshed parity baseline under docs/implementation/python_api_parity/baseline/ reflecting the 19-crate surface
affects: [03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08, 03-09a, 03-09b]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pitfall 2 guard: validate rustSymbol references against parsed surface before diff generation"
    - "Centralized conftest.py sys.path bootstrap for tool-script pytest suites"
    - "Module-level _OWNER_RENDER_ORDER constant derived from owner dict values (drift-proof rendering)"
    - "Strict=True xfail as an invariant-assertion mechanism for future-plan validation"
    - "Pitfall 4 audit walks `pub mod` reachability graph before classifying #[pyclass] declarations"

key-files:
  created:
    - .planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md
    - .planning/phases/03-python-tier-collapse/03-01-A10-sizing.json
    - tools/python_api_parity/tests/__init__.py
    - tools/python_api_parity/tests/conftest.py
    - tools/python_api_parity/tests/test_generate_baseline_targets.py
    - tools/python_api_parity/tests/test_check_parity_gate.py
    - tools/python_api_parity/tests/test_pitfall2_guard.py
    - tools/python_api_parity/tests/test_owner_render_drift.py
  modified:
    - tools/python_api_parity/generate_baseline.py
    - tools/python_api_parity/check_parity_gate.py
    - tools/python_api_parity/generate_wave_manifest.py
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.md
    - docs/implementation/python_api_parity/baseline/rust_api_surface.json
    - docs/implementation/python_api_parity/baseline/python_api_surface.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
    - docs/implementation/python_api_parity/governance/tier2_wave_manifest.json

key-decisions:
  - "Pitfall 4 audit walks pub mod reachability graph first, classifies orphan files as Known Exclusions (dead code), not as blocking registration failures"
  - "ScanOutput was correctly detected after handling path-qualified m.add_class::<parser::ScanOutput>() calls (last :: segment becomes class name)"
  - "TestClass in classic-scanlog-py/src/test_class.rs is an orphan (file not declared in lib.rs); documented in the audit as a Known Exclusion and intentionally left in place"
  - "_OWNER_RENDER_ORDER uses tuple(RUST_OWNER_BY_CRATE.values()) + ('aux',) — any new crate automatically propagates to the rendered gap table"
  - "Pitfall 2 guard runs in main() between parse_rust_surface() and generate_diff_report(); failure prints actionable remediation to stderr and returns 1"
  - "Squad labels (Squad C/D/E/F/G) introduced for the 16 new owners, keeping the existing Squad A/B labels stable for pre-Phase-3 continuity"
  - "Deferred backlog regenerated via generate_wave_manifest.py (not hand-edited) — the tool's WAVE_BY_OWNER dict was expanded from 4 to 20 entries and the hard-coded Squad A/Squad B ternary was replaced with a SQUAD_BY_OWNER dict"

patterns-established:
  - "Pattern: Pre-phase audit scripts write committed markdown reports under .planning/phases/<phase>/ before any source changes land"
  - "Pattern: Orphan source files (not reachable from lib.rs pub mod chain) are classified as dead code, not as contract failures"
  - "Pattern: Tool-internal rendering order constants are derived from the primary ownership dict, not hard-coded tuples"
  - "Pattern: Deferred backlog generator owns wave/squad assignment dicts as module-level constants, aligned with generate_baseline.py SQUAD_BY_OWNER"

requirements-completed: [PYT-01, PYT-03]

# Metrics
duration: 13min
completed: 2026-04-08
---

# Phase 3 Plan 01: Tooling Expansion Summary

**Python parity tooling now tracks 19 crates (18 -core + classic-shared-py) with a Pitfall 2 guard on the parity gate, and the deferred backlog was expanded from 285 to 1202 entries to surface the 1212 tier-2 gaps that downstream Phase 3 plans must close**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-08T10:54:40Z
- **Completed:** 2026-04-08T11:07:46Z
- **Tasks:** 5 (Task 0 audit + Tasks 1-4 implementation)
- **Files modified:** 20 (8 created + 12 modified; excludes ephemeral parity-artifact timestamp drift)

## Accomplishments

- **Pitfall 4 audit (Task 0):** Walked the `pub mod` reachability graph for all 17 `-py` crates with `#[pyclass]` declarations plus `classic-shared-py`. Found 125 reachable classes, all correctly registered via `m.add_class::<>()`. One orphan (`TestClass` in unreachable `test_class.rs`) is documented under Known Exclusions and left in place as dead code not compiled into the crate.
- **Pitfall 2 guard (Task 3):** Added `validate_contract_rust_symbols()` to `check_parity_gate.py` that runs between `parse_rust_surface()` and `generate_diff_report()`. Catches missing `pub use` at crate root with an actionable remediation message instead of burying it as `missing_rust` drift noise.
- **19-crate expansion (Task 2):** Grew `RUST_TARGET_CRATES`, `PYTHON_TARGET_MODULES`, `RUST_OWNER_BY_CRATE`, `PYTHON_OWNER_BY_MODULE`, and `SQUAD_BY_OWNER` in `generate_baseline.py`. Introduced `_OWNER_RENDER_ORDER` module-level constant derived from `RUST_OWNER_BY_CRATE.values()` + `'aux'`, and replaced the hard-coded owner tuple in `render_diff_markdown()` with iteration over this constant.
- **Wave 0 test scaffolding (Task 1):** 6 new test files under `tools/python_api_parity/tests/` with a central `conftest.py` for sys.path bootstrap. 14 tests pass and 1 strict=True xfail asserts the Plan 9b invariant that `tierDefinitions.tier2` will be removed.
- **Baseline refresh (Task 4):** All 8 baseline artifacts refreshed for the 19-crate surface. `parity_contract.json.ownerModules` grew from 4 to 20 entries (hand-edit, verified stable after `--write-baseline` re-run). A10 sizing captured at `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json`.
- **Gate green (verification):** `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0 with 59 Tier-1 rows still matched, 0 drift, 0 newly uncovered, and 1202 deferred entries covering all 19 owners.

## Task Commits

Each task was committed atomically:

1. **Task 0: Pre-phase Pitfall 4 audit** — `f70505e8` (Docs)
2. **Task 1: Wave 0 tooling test scaffolding (TDD RED)** — `42059836` (Test)
3. **Task 2: Expand RUST_TARGET_CRATES + owner drift guard** — `7ea5afad` (Feat)
4. **Task 3: Pitfall 2 guard validate_contract_rust_symbols()** — `90c41562` (Feat)
5. **Task 4: Baseline refresh + A10 sizing + deferred backlog expansion** — `602027cf` (Feat)

## Files Created/Modified

### Created

- `.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md` — pre-phase audit enumerating all 126 `#[pyclass]` declarations across 17 -py crates + classic-shared-py with PASS/ORPHAN classification
- `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json` — machine-readable per-owner tier2 gap counts (total 1212 across 19 owners) for downstream Plan 6/7/8/9a budget adjustments
- `tools/python_api_parity/tests/__init__.py` — empty package marker
- `tools/python_api_parity/tests/conftest.py` — central sys.path bootstrap (replaces per-file sys.path.insert pollution)
- `tools/python_api_parity/tests/test_generate_baseline_targets.py` — 9 guards: RUST_TARGET_CRATES count (19), PYTHON_TARGET_MODULES count (19), classic-shared-py inclusion, classic-crashgen-settings-core exclusion (A5), non-empty parsing for every crate, .pyi file existence on disk, owner/squad dict consistency
- `tools/python_api_parity/tests/test_check_parity_gate.py` — 2 guards: tier1 row floor (exactly 59 at Plan 01 snapshot) + strict=True xfail on tier2 removal (fires when Plan 9b removes `tierDefinitions.tier2`)
- `tools/python_api_parity/tests/test_pitfall2_guard.py` — 3 guards: pass when all symbols present, fail when rustSymbol missing, fail when rustSymbol field absent from contract row
- `tools/python_api_parity/tests/test_owner_render_drift.py` — 1 drift guard that `_OWNER_RENDER_ORDER` is derived from `RUST_OWNER_BY_CRATE.values() | {'aux'}` (no divergence)

### Modified

- `tools/python_api_parity/generate_baseline.py` — 5 dicts grown from 3 to 19/20 entries (RUST_TARGET_CRATES, RUST_OWNER_BY_CRATE, PYTHON_TARGET_MODULES, PYTHON_OWNER_BY_MODULE, SQUAD_BY_OWNER); new `_OWNER_RENDER_ORDER` module-level tuple; `render_diff_markdown()` iterates `_OWNER_RENDER_ORDER` instead of a hard-coded owner tuple
- `tools/python_api_parity/check_parity_gate.py` — new `validate_contract_rust_symbols()` helper (58 lines); wired into `main()` between `parse_rust_surface()` and `generate_diff_report()` with stderr print + exit 1 on failure
- `tools/python_api_parity/generate_wave_manifest.py` — `WAVE_BY_OWNER` expanded from 4 to 20 entries (waves 5-20); `WAVE_LABELS` gains matching labels; new `SQUAD_BY_OWNER` module-level dict replacing the hard-coded Squad A/Squad B ternary; `main()` uses `SQUAD_BY_OWNER.get(owner_module, 'Squad B')` for owner assignment
- `docs/implementation/python_api_parity/baseline/parity_contract.json` — `ownerModules` dict grown from 4 to 20 entries (scanlog, config, version_registry, aux preserved; 16 new: yaml, database, file_io, scangame, registry, perf, settings, message, path, constants, version, resource, xse, web, update, shared); `tier1Mappings` preserved at 59 rows
- `docs/implementation/python_api_parity/baseline/rust_api_surface.json` — `scope.target_crates` grows from 3 to 19
- `docs/implementation/python_api_parity/baseline/python_api_surface.json` — 19 .pyi modules parsed
- `docs/implementation/python_api_parity/baseline/parity_diff_report.{json,md}` — refreshed gap counts
- `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.{json,md}` — refreshed coverage classification (0 newly_uncovered after deferred backlog expansion)
- `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` — regenerated from refreshed diff report; 285 → 1202 entries covering all 19 owners
- `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json` — regenerated to match

## Decisions Made

- **Pitfall 4 audit handles path-qualified add_class calls:** initial audit failed on `m.add_class::<parser::ScanOutput>()` because the regex only matched bare names. Rewrote the script to take the last `::` segment as the class name. Separately, the audit walks the `pub mod` reachability graph so orphan files (like `test_class.rs` declared in unused `mod.rs`) are classified as ORPHAN (dead code) rather than MISSING (blocking).
- **Orphan dead code is NOT fixed during Plan 01:** `TestClass` in `classic-scanlog-py/src/test_class.rs` is not compiled into the crate because neither `lib.rs` nor any reachable module declares `pub mod test_class;`. Rather than deleting the file (scope creep) or adding a registration (would wire dead code into the crate), the Pitfall 4 audit documents it as a Known Exclusion. Cleanup is out of Plan 01 scope.
- **SQUAD_BY_OWNER duplicated between tools:** Both `generate_baseline.py` and `generate_wave_manifest.py` now carry their own `SQUAD_BY_OWNER` dict. Duplicating 19 lines was judged cheaper than adding a cross-tool module import that would widen the tooling surface. A future refactor can extract a shared constants module if drift proves problematic.
- **Wave labels use sequential `wave5`–`wave20` numbering:** Preserves existing `wave1`–`wave4` for historical continuity. The numeric label is cosmetic only — the real promotion schedule is governed by the Phase 3 plan sequence (Plans 02–09b), not by the wave manifest.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pitfall 4 audit script regex did not handle path-qualified `m.add_class::<>()` calls**

- **Found during:** Task 0 initial audit run
- **Issue:** The plan-provided PowerShell audit script pattern `m\.add_class::<(\w+)>` only matches bare class names. `classic-scanlog-py/src/lib.rs` uses `m.add_class::<parser::ScanOutput>()?;` with a path-qualified form, which the regex did not capture as a registration for `ScanOutput`. The first audit run reported STATUS: FAIL with `ScanOutput` and `TestClass` as missing registrations, which is a false positive for `ScanOutput`.
- **Fix:** Rewrote `.pitfall4-audit.ps1` to:
  1. Use regex `m\.add_class::<([\w:]+)>` (allows `::` path separators in the capture group)
  2. Take the last `::` segment of the captured path as the class name (`parser::ScanOutput` → `ScanOutput`)
  3. Walk the `pub mod` / `mod` declaration graph starting at `lib.rs` to determine which source files are REACHABLE and compiled into the crate
  4. Classify unreachable-file `#[pyclass]` declarations as `ORPHAN` (dead code) rather than `MISSING` (blocking)
- **Files modified:** scratch script (removed after audit complete); audit output now lives at `.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md`
- **Verification:** Re-run audit shows 125 REGISTERED + 0 MISSING + 1 ORPHAN (`TestClass` in the orphan `test_class.rs`); STATUS: PASS
- **Committed in:** `f70505e8` (Task 0 commit)

**2. [Rule 3 - Blocking] Parity gate failed with 901 newly_uncovered after crate expansion**

- **Found during:** Task 4 initial gate run
- **Issue:** The plan's Task 4 acceptance criteria says the gate must exit 0 after the 19-crate expansion, asserting only that "existing 59 Tier-1 rows still pass." In reality, expanding `RUST_TARGET_CRATES` from 3 to 19 causes `build_coverage_summary()` to see ~901 previously-invisible Rust symbols from the 16 new crates, classifying each as `newly_uncovered` because no entry in `deferred_runtime_backlog.json` or the runtime coverage registry matches them. The gate then exits 1 with `Newly uncovered Python surfaces detected: 901`. Without remediation, the gate cannot reach the green state the plan requires.
- **Fix:** Expanded `tools/python_api_parity/generate_wave_manifest.py` to know about all 19 owners:
  1. `WAVE_BY_OWNER` grew from 4 to 20 entries (waves 5–20 for the new owners)
  2. `WAVE_LABELS` gained matching labels
  3. New `SQUAD_BY_OWNER` module-level dict replaces the hard-coded `"Squad A" if owner in {"scanlog", "config"} else "Squad B"` ternary; assigns Squads C–G to the new owners matching `generate_baseline.py::SQUAD_BY_OWNER`
  4. Re-ran `generate_wave_manifest.py --repo-root .` to regenerate `deferred_runtime_backlog.json` (285 → 1202 entries) and `tier2_wave_manifest.json` from the refreshed diff report
- **Files modified:** `tools/python_api_parity/generate_wave_manifest.py`, `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`, `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json`
- **Verification:** `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0 with `Tier-1 parity gate passed.`; 59 Tier-1 rows matched, 0 drift, 0 newly_uncovered, 1212 total tier-2 gaps all tracked in the deferred backlog
- **Committed in:** `602027cf` (Task 4 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - Blocking)
**Impact on plan:** Both fixes were essential to deliver Plan 01's acceptance criteria. Neither is scope creep — fix 1 corrected a false-positive in an audit script, and fix 2 propagated the 19-crate expansion into the downstream governance tooling that the plan assumed would "just work." The plan's own blocker-concerns section flagged the deferred-tolerance issue for Phase 6 but did not anticipate that the gate green state in Plan 01 would require the same backlog regeneration.

## Issues Encountered

- **False-positive in Pitfall 4 audit initial run:** The plan's PowerShell audit script could not distinguish between `m.add_class::<FooStruct>()` and `m.add_class::<parser::FooStruct>()`. Resolved by rewriting the regex and adding `pub mod` reachability tracking. See Deviation 1.
- **1202 deferred entries vs 901 newly_uncovered discrepancy:** The runtime coverage summary's `newly_uncovered` classification is based on binding-identifier or rust-symbol lookup against the runtime registry. The deferred backlog entry count (1202) differs from newly_uncovered (901) because the backlog generator includes BOTH rust_unmapped and python_unmapped gap types, while `newly_uncovered` counts only registry-lookup misses. Both counts are internally consistent; no further action needed.

## Sizing Report (A10 — required for downstream plan budgets)

Per-owner tier-2 gap totals from `docs/implementation/python_api_parity/baseline/parity_diff_report.json`, captured in machine-readable form at `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json`:

| Owner              | Tier-2 gaps | Plan that will close them                      |
|--------------------|------------:|-------------------------------------------------|
| scanlog            |         232 | Plans 02-05 (Waves 1/2/3a/3b, already budgeted) |
| scangame           |         218 | Plan 09a residual (new, needs budget)           |
| file_io            |         106 | Plan 08 + Plan 09a residual                     |
| path               |          85 | Plan 09a residual (new)                         |
| shared             |          66 | Plan 08 (classic_shared helpers)                |
| constants          |          59 | Plan 09a residual (new)                         |
| message            |          53 | Plan 09a residual (new)                         |
| database           |          46 | Plan 09a residual (new)                         |
| resource           |          40 | Plan 09a residual (new)                         |
| xse                |          40 | Plan 09a residual (new)                         |
| registry           |          39 | Plan 09a residual (new)                         |
| settings           |          39 | Plan 09a residual (new)                         |
| yaml               |          37 | Plan 09a residual (new)                         |
| version_registry   |          35 | Plan 07 (already budgeted) + residual           |
| web                |          29 | Plan 09a residual (new)                         |
| config             |          28 | Plan 06 (already budgeted)                      |
| version            |          28 | Plan 09a residual (new)                         |
| perf               |          16 | Plan 09a residual (new)                         |
| update             |          16 | Plan 09a residual (new)                         |
| **TOTAL**          |    **1212** |                                                 |

**Downstream budget alert:** The plan's test_check_parity_gate.py progression comments budget Plans 02-08 for scanlog (Waves 1-3b), config, version_registry, shared, and file_io — a total of approximately 299 rows (59 + 74 + 57 + 50 + 46 + 26 + 35 + 11 = 358). The remaining ~913 tier-2 gaps across scangame/path/constants/message/database/resource/xse/registry/settings/yaml/web/version/perf/update will land in **Plan 09a residual cleanup** and need explicit task budgeting during plan-phase execution.

**Key sizing surprises:**
- **scangame (218 gaps)** is larger than scanlog (232) and will likely dominate Plan 09a — if Plan 09a was scoped assuming a smaller residual, it needs re-planning.
- **shared (66 gaps)** is larger than the 11-row estimate in the test_check_parity_gate.py progression comments. Plan 08 budget needs to grow or shared coverage needs to split across Plan 08 + Plan 09a.
- **path (85 gaps)** has no dedicated plan in the current sequence.

## Next Phase Readiness

- Phase 3 tooling scaffolding is complete. Plan 02 (scanlog Wave 1) can now promote tier-2 rows using the expanded `RUST_TARGET_CRATES` and the Pitfall 2 guard will catch any missing `pub use` at crate root with actionable remediation.
- The test_check_parity_gate.py snapshot floor remains at 59; Plans 02-09a will bump this as each wave lands.
- `_OWNER_RENDER_ORDER` drift guard is active — any future crate additions to `RUST_TARGET_CRATES` must also extend `RUST_OWNER_BY_CRATE` or the drift test fails.
- The tier2_wave_manifest.json + deferred_runtime_backlog.json are now the single source of truth for which symbols Phase 3 needs to resolve. Downstream plans should consult these artifacts when selecting promotion batches.
- **Plan 09a residual budget must be re-planned** to account for the 913 gaps across 13 owners the current plan sequence does not explicitly budget.

## Self-Check: PASSED

Verification performed after SUMMARY.md draft:

**Files created check:**
- `.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md` — FOUND
- `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json` — FOUND
- `tools/python_api_parity/tests/__init__.py` — FOUND
- `tools/python_api_parity/tests/conftest.py` — FOUND
- `tools/python_api_parity/tests/test_generate_baseline_targets.py` — FOUND
- `tools/python_api_parity/tests/test_check_parity_gate.py` — FOUND
- `tools/python_api_parity/tests/test_pitfall2_guard.py` — FOUND
- `tools/python_api_parity/tests/test_owner_render_drift.py` — FOUND

**Commits check:**
- `f70505e8` Docs(03-01): Add Phase 3 Plan 01 Pitfall 4 audit report — FOUND
- `42059836` Test(03-01): Add Wave 0 tooling test scaffolding (TDD RED) — FOUND
- `7ea5afad` Feat(03-01): Expand Python parity tooling to 19 crates + owner drift guard — FOUND
- `90c41562` Feat(03-01): Add validate_contract_rust_symbols() Pitfall 2 guard — FOUND
- `602027cf` Feat(03-01): Refresh parity baseline for 19 crates + A10 sizing report — FOUND

**Verification commands (from plan success criteria):**
- `python tools/python_api_parity/check_parity_gate.py --repo-root .` — EXIT 0 (Tier-1 parity gate passed)
- `python -m pytest tools/python_api_parity/tests -q` — 14 passed, 1 xfailed
- `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` — EXIT 0 (3/3 crates passed, 0/0 errors)

---
*Phase: 03-python-tier-collapse*
*Completed: 2026-04-08*
