---
phase: 3
slug: python-tier-collapse
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-07
populated: 2026-04-07
audited: 2026-04-09
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `03-RESEARCH.md` §Validation Architecture (lines 83–168).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `uv run`) — implicit version from `ClassicLib-rs/python-bindings/.venv` |
| **Config file** | `ClassicLib-rs/python-bindings/conftest.py` (existing — verify in Plan 1 Wave 0) |
| **Quick run command** | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q` |
| **Full suite command** | same — there is one suite |
| **Stub validator** | `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` |
| **Type checker** | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict <pyi-file>` |
| **Estimated runtime** | ~30–60 seconds (pytest smoke tests) + ~5–10 seconds (parity gate) |

---

## Sampling Rate

- **After every task commit:** `python tools/python_api_parity/check_parity_gate.py --repo-root .` (exit 0 expected) + `validate_stubs.py` for the touched crate
- **After every plan close:** full 5-step chain — (1) gate, (2) validate_stubs, (3) `rebuild_rust.ps1 -Target python <affected>`, (4) pytest, (5) `mypy --strict` on updated stubs
- **Before `/gsd:verify-work`:** all five steps green on every Phase 3 commit; `runtime_coverage_summary.json::summary.deferred_total == 0` after Plan 9
- **Max feedback latency:** ~60 seconds (pytest + gate combined)

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| PYT-01 | `RUST_TARGET_CRATES` / `PYTHON_TARGET_MODULES` enumerate all 19 binding pairs (18 business-logic + classic-shared-py); `parse_rust_surface()` returns non-empty symbol lists for every entry | unit + integration | `python tools/python_api_parity/generate_baseline.py --repo-root .` then assert `len(rust_api_surface.json::scope.target_crates) == 19` and every crate's symbols list is non-empty | Wave 0 (Plan 01) |
| PYT-02 | Every previously-deferred symbol resolves through the gate as a Tier-1 contract row; `parity_diff_report.json::summary.tier2_gap_total == 0` (eventually removed entirely in Plan 09) | integration | `python tools/python_api_parity/check_parity_gate.py --repo-root .` (exit 0) | existing |
| PYT-03 | Removing Tier-2 gap-row branches from `generate_diff_report()` does not silently drop coverage — `tier1_contract_total` after Plan 9 == previous + 285 + 12 | integration | snapshot test in `tools/python_api_parity/tests/test_check_parity_gate.py` | Wave 0 (Plan 01) |
| PYT-04 | Every promoted entry's `.pyi` stub passes `mypy --strict` AND `validate_stubs.py --fail-on-warnings` | static | `validate_stubs.py` + `mypy --strict` per crate (per-plan close) | existing |
| PYT-05 | Each promoted `#[pyclass]` is constructed and one method called at runtime; each promoted free-function group has one call exercising the real codepath | unit smoke | `pytest ClassicLib-rs/python-bindings/tests/test_promoted_<crate>_smoke.py -x` (one file per Plan 2–8) | Wave 0 (8 new files) |
| PYT-06 | `runtime_coverage_summary.json::summary.deferred_total == 0` after Plan 9 lands | integration | `jq .summary.deferred_total docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json` | existing |
| HARM-03 | `import classic_shared; classic_shared.get_runtime_stats().worker_threads > 0` | smoke | `pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py::test_get_runtime_stats_returns_healthy_struct -x` | Wave 0 (Plan 08) |
| HARM-04 | `classic_shared` enrolled in `parity_contract.json::tier1Mappings` with exactly 6 rows; `mypy --strict classic_shared.pyi` exits 0 | static + integration | `check_parity_gate.py --repo-root .` + `mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` | tooling exists |

---

## Per-Task Verification Map

*Populated by gsd-planner during PLAN.md creation (2026-04-07).*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-00 | 01 | 1 | HARM-03, HARM-04 | pre-audit | `test -f .planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md && grep 'STATUS: PASS' .planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md` | Wave 0 (audit generated) | green |
| 03-01-01 | 01 | 1 | PYT-01, PYT-03 | unit | `pytest tools/python_api_parity/tests -q --collect-only` (TDD RED expected) | Wave 0 (this task creates) | green |
| 03-01-02 | 01 | 1 | PYT-01 | static | `python -c "from tools.python_api_parity.generate_baseline import RUST_TARGET_CRATES; assert len(RUST_TARGET_CRATES) == 19"` | existing | green |
| 03-01-03 | 01 | 1 | PYT-03 | unit | `pytest tools/python_api_parity/tests/test_pitfall2_guard.py -v` | Wave 0 from 03-01-01 | green |
| 03-01-04 | 01 | 1 | PYT-01, PYT-03 | integration | `python tools/python_api_parity/check_parity_gate.py --repo-root .` (gate exits 0 with 59 Tier-1 rows + Pitfall 2 guard) | existing | green |
| 03-02-00 | 02 | 2 | PYT-05 | pre-verify | Verify Wave 1 constructor signatures from -py source; write to 03-02-CONSTRUCTOR-INVENTORY.md | Wave 0 | green |
| 03-02-01 | 02 | 2 | PYT-02 | static | `python -c "import json; c=json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); assert len(c['tier1Mappings']) >= 133"` | existing | green |
| 03-02-02 | 02 | 2 | PYT-04 | static | `mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` | existing | green |
| 03-02-03 | 02 | 2 | PYT-05 | smoke | `pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py -q` | Wave 0 (this task creates) | green |
| 03-02-04 | 02 | 2 | PYT-02, PYT-04, PYT-05 | integration | 5-step verification chain (gate, validate_stubs, rebuild_rust, pytest, mypy) | existing | green |
| 03-03-00 | 03 | 3 | PYT-05 | pre-verify | Verify Wave 2 constructor signatures + create conftest.py FCX reset fixture | Wave 0 | green |
| 03-03-01 | 03 | 3 | PYT-02 | static | `python -c "import json; c=json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); assert len(c['tier1Mappings']) >= 190"` | existing | green |
| 03-03-02 | 03 | 3 | PYT-04 | static | `mypy --strict classic_scanlog.pyi` | existing | green |
| 03-03-03 | 03 | 3 | PYT-05 | smoke | `pytest test_promoted_scanlog_wave2_smoke.py -q` | Wave 0 (this task creates) | green |
| 03-03-04 | 03 | 3 | PYT-02, PYT-04, PYT-05 | integration | 5-step verification chain | existing | green |
| 03-04-00 | 04 | 4 | PYT-05 | pre-verify | Verify Wave 3a constructor signatures + ScanProgressPhase variant names + CrashgenRegistry methods | Wave 0 | green |
| 03-04-01 | 04 | 4 | PYT-02 | static | `python -c "import json; c=json.loads(...); assert len(c['tier1Mappings']) >= 240"` | existing | green |
| 03-04-02 | 04 | 4 | PYT-04 | static | `mypy --strict classic_scanlog.pyi` | existing | green |
| 03-04-03 | 04 | 4 | PYT-05 | smoke | `pytest test_promoted_scanlog_wave3a_smoke.py -q` | Wave 0 (this task creates) | green |
| 03-04-04 | 04 | 4 | PYT-02, PYT-04, PYT-05 | integration | 5-step verification chain | existing | green |
| 03-05-00 | 05 | 5 | PYT-05 | pre-verify | Verify report sub-module constructor signatures (5 wrappers) | Wave 0 | green |
| 03-05-01 | 05 | 5 | PYT-02 | static | `python -c "import json; c=json.loads(...); assert len(c['tier1Mappings']) >= 286"` | existing | green |
| 03-05-02 | 05 | 5 | PYT-04 | static | `mypy --strict classic_scanlog.pyi` | existing | green |
| 03-05-03 | 05 | 5 | PYT-05 | smoke | `pytest test_promoted_scanlog_report_smoke.py -q` | Wave 0 (this task creates) | green |
| 03-05-04 | 05 | 5 | PYT-02, PYT-04, PYT-05 | integration | 5-step verification chain | existing | green |
| 03-06-01 | 06 | 6 | PYT-02 | static | `python -c "import json; c=json.loads(...); assert len(c['tier1Mappings']) >= 312"` | existing | green |
| 03-06-02 | 06 | 6 | PYT-04 | static | `mypy --strict classic_config.pyi` | existing | green |
| 03-06-03 | 06 | 6 | PYT-05 | smoke | `pytest test_promoted_config_smoke.py -q` | Wave 0 (this task creates) | green |
| 03-06-04 | 06 | 6 | PYT-02, PYT-04, PYT-05 | integration | 5-step verification chain | existing | green |
| 03-07-01 | 07 | 7 | PYT-02 | static | `python -c "import json; c=json.loads(...); assert len(c['tier1Mappings']) >= 347"` | existing | green |
| 03-07-02 | 07 | 7 | PYT-04 | static | `mypy --strict classic_version_registry.pyi` | existing | green |
| 03-07-03 | 07 | 7 | PYT-05 | smoke | `pytest test_promoted_version_registry_smoke.py -q` | Wave 0 (this task creates) | green |
| 03-07-04 | 07 | 7 | PYT-02, PYT-04, PYT-05 | integration | 5-step verification chain | existing | green |
| 03-08-00 | 08 | 8 | HARM-03, HARM-04, PYT-05 | pre-verify | Verify classic_shared method names from .pyi + file_io static-method nature; write 03-08-METHOD-INVENTORY.md | Wave 0 | green |
| 03-08-01 | 08 | 8 | HARM-03, HARM-04 | static | `python -c "import json; c=json.loads(...); shared=[m for m in c['tier1Mappings'] if m.get('ownerModule')=='shared']; assert len(shared)==6"` | existing | green |
| 03-08-02 | 08 | 8 | HARM-04, PYT-04 | static | `mypy --strict classic_shared.pyi classic_file_io.pyi` | existing | green |
| 03-08-03 | 08 | 8 | HARM-03, PYT-05 | smoke | `pytest test_classic_shared_smoke.py test_promoted_file_io_aux_smoke.py -q` | Wave 0 (this task creates) | green |
| 03-08-04 | 08 | 8 | HARM-03, HARM-04, PYT-02 | integration | D-10 4-step wiring chain + 5-step verification chain | existing | green |
| 03-09a-01 | 09a | 9 | PYT-02, PYT-06 | discovery | Read parity_diff_report.json::gaps tier2 filter; fail-closed wrapper existence check; inventory or BLOCKERS.md | existing | green |
| 03-09a-02 | 09a | 9 | PYT-02, PYT-04, PYT-05 | integration | Promote residuals (contract + stub + tests); file_io excluded per R3 | Wave 0 (test_promoted_residuals_smoke.py) | green |
| 03-09a-03 | 09a | 9 | PYT-02 | integration | Add per-owner python-tier1-<owner> selector entries (excluding file_io) | existing | green |
| 03-09a-04 | 09a | 9 | PYT-02, PYT-04 | integration | 4-step verification chain (no mypy sweep — deferred to 09b) | existing | green |
| 03-09b-01 | 09b | 10 | PYT-03 | unit | Delete gap_type=rust_unmapped/python_unmapped branches in generate_baseline.py lines 574-610 | existing | green |
| 03-09b-02 | 09b | 10 | PYT-03 | unit | tier2_gap_total cascade cleanup + tierDefinitions.tier2 deletion + xfail flip | existing | green |
| 03-09b-03 | 09b | 10 | PYT-03 | cosmetic | Inline Tier-2 comment sweep | existing | green |
| 03-09b-04 | 09b | 10 | PYT-04, PYT-06 | integration | Full 5-step chain + mypy --strict over all 19 stubs + validate_stubs.py + PYT-06 coverage completeness one-liner | existing | green |

*Status legend: pending / green / red / flaky*

---

## Wave 0 Requirements

Files that must be created before promotion work begins (Plan 1 absorbs the tooling tests; Plans 2–8 absorb their respective smoke test files):

- [x] `tools/python_api_parity/tests/__init__.py` — pytest collection root for tooling tests
- [x] `tools/python_api_parity/tests/test_generate_baseline_targets.py` — proves every entry in `RUST_TARGET_CRATES` parses to a non-empty symbol list (PYT-01 unit guard) **[Plan 1]**
- [x] `tools/python_api_parity/tests/test_check_parity_gate.py` — snapshot test of `tier1_contract_total` before/after Plan 9 removes Tier-2 branches (PYT-03 unit guard) **[Plan 1]**
- [x] `tools/python_api_parity/tests/test_pitfall2_guard.py` — exercises D-05's `validate_contract_rust_symbols()` against a synthetic contract row whose `rustSymbol` is missing; asserts non-zero exit + diagnostic text **[Plan 1]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py` **[Plan 2 — Wave 1: 74 rows]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py` **[Plan 3 — Wave 2: 58 rows]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py` **[Plan 4 — Wave 3a orchestration: ~50 rows]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_report_smoke.py` **[Plan 5 — Wave 3b report: ~46 rows]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py` **[Plan 6 — 26 rows (22 deferred + 4 Tier-2 migrations)]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py` **[Plan 7 — 35 rows (34 deferred + 1 Tier-2 migration)]**
- [x] `ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py` **[Plan 8 — classic_shared 6 rows]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py` **[Plan 8 — file_io aux + cache helpers, 5 rows]**
- [x] `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` **[Plan 9a — A10 residuals from 14 untracked crates, excluding file_io]**
- [x] `.planning/phases/03-python-tier-collapse/03-01-PITFALL4-AUDIT.md` **[Plan 01 Task 0 — pre-phase audit]**
- [x] `.planning/phases/03-python-tier-collapse/03-02-CONSTRUCTOR-INVENTORY.md` **[Plan 02 Task 0 — Wave 1 signatures]**
- [x] `.planning/phases/03-python-tier-collapse/03-03-CONSTRUCTOR-INVENTORY.md` **[Plan 03 Task 0 — Wave 2 signatures]**
- [x] `.planning/phases/03-python-tier-collapse/03-04-CONSTRUCTOR-INVENTORY.md` **[Plan 04 Task 0 — Wave 3a signatures]**
- [x] `.planning/phases/03-python-tier-collapse/03-05-CONSTRUCTOR-INVENTORY.md` **[Plan 05 Task 0 — report signatures]**
- [x] `.planning/phases/03-python-tier-collapse/03-08-METHOD-INVENTORY.md` **[Plan 08 Task 0 — classic_shared + file_io method names (R5/R11/R13 verification)]**
- [x] `tools/python_api_parity/tests/conftest.py` **[Plan 01 Task 1 — central sys.path bootstrap for tooling tests]**
- [x] `tools/python_api_parity/tests/test_owner_render_drift.py` **[Plan 01 — drift guard]**
- [x] `ClassicLib-rs/python-bindings/tests/conftest.py` **[Plan 03 — FCX state reset fixture]**

**Existing infrastructure (reusable):**
- `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` (already runtime-verified)
- `ClassicLib-rs/python-bindings/.venv` with pytest
- `validate_stubs.py`, `check_parity_gate.py`, `generate_baseline.py`

---

## Regression Surfaces

1. **`mypy --strict`** — fails if a promoted method's stub argument shape doesn't match the actual `#[pymethods]` signature
2. **`validate_stubs.py`** — fails if a `#[pyclass]` exists in `-py/src/*.rs` but is missing from the corresponding `.pyi` (and vice versa); also walks `tier1Mappings` to confirm discovered crates have a stub file
3. **`parity_contract.json` row-count invariant** — Plan 1 establishes `tier1Mappings.length == 59` (current). Plan 9 must end with `tier1Mappings.length == 59 + 285 + 12 + 6 + A10 residuals = ~410-510` (current Tier-1 + deferred backlog promotions + Tier-2 runtime-verified migrations + classic_shared + newly-surfaced symbols from 14 untracked crates). Off-by-N drift is detectable by snapshot test.
4. **`runtime_coverage_registry.json` row-count invariant** — currently 8 entries. After Phase 3: ~14-18 selector rows depending on D-08 grouping. The strict invariant: every contract row must have a matching registry row (D-08); the gate's `tier1_missing_runtime_total` check enforces this.
5. **`tier1_contract_total`** in `runtime_coverage_summary.json::summary` — must equal `parity_contract.json::tier1Mappings.length` after every plan. Off-by-one detection is automatic.

---

## Failure Signatures

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `parity_diff_report.json::summary.tier1_missing_rust > 0` | Contract row's `rustSymbol` not in the parsed Rust surface — typo OR symbol missing from `-core/lib.rs` | Add `pub use sub::Symbol;` to **`-core/lib.rs`** (NOT `-py/lib.rs` — see A1) OR fix typo in `parity_contract.json` |
| `parity_diff_report.json::summary.tier1_missing_python > 0` | Contract row's `pythonExportPath` not in the `.pyi` parser output | Add the class/function to the `.pyi` file matching the Python-facing identifier (after `#[pyo3(name = "...")]` rename) |
| `parity_diff_report.json::summary.tier1_signature_mismatch > 0` | `pythonKind` or `pythonArity` in contract differs from `.pyi` actual | Fix the contract row OR fix the stub signature |
| `coverage_summary.json::tier1_missing_runtime_total > 0` | A Tier-1 contract row has no matching registry row | Add a `runtime_coverage_registry.json` entry whose `contractIds` or `contractSelector` resolves to this row |
| `coverage_summary.json::registry_mismatch_total > 0` | A registry row uses `contractSelector` and the matched count or hash drifted | Recompute `contractIdsHash` via `_stable_id_hash` (sha256 of sorted contract IDs); update both fields |
| `pytest AttributeError on import classic_*` | A `#[pyclass]` is in the `.pyi` but not registered in the `#[pymodule]` function | Add `m.add_class::<PyXxx>()?;` to `-py/src/lib.rs::classic_xxx` (Pitfall 4) |
| `pytest ImportError: classic_shared` | wheel not built or not installed into `.venv` | `pwsh rebuild_rust.ps1 -Target python classic_shared` |
| `validate_stubs.py: Class 'X' missing methods` | `#[pymethods]` defines a method the `.pyi` lacks | Add the def to the stub OR annotate so `validate_stubs.py::extract_rust_methods` skips it |
| `mypy --strict: incompatible types` | Stub return type doesn't match Rust shape | Fix the stub annotation; PyO3 0.27 maps `Vec<X>` -> `list[X]`, `(A, B)` -> `tuple[A, B]` |

---

## Coverage Completeness Criterion (PowerShell one-liner)

After Plan 9, every promoted contract row must have a matching pytest smoke test AND a runtime registry row. Returns 0 rows when complete; any output is a gap:

```powershell
$contract = Get-Content 'docs/implementation/python_api_parity/baseline/parity_contract.json' -Raw | ConvertFrom-Json
$diff = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
$contract.tier1Mappings | Where-Object {
    $row = $_
    -not ($diff.trackedSurface | Where-Object {
        $_.trackedType -eq 'contract_row' -and $_.contractId -eq $row.id -and $_.classification -eq 'runtime_verified'
    })
} | ForEach-Object { "MISSING_RUNTIME: $($_.id) ($($_.rustSymbol) -> $($_.pythonModule).$($_.pythonExportPath))" }
```

The gate's existing `tier1_missing_runtime_total` count is the same data via a different path; this script is the human-readable accompaniment.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `rebuild_rust.ps1 -Target python classic_shared` actually produces a wheel and installs it into the venv | HARM-03, HARM-04 | Wheel build is PowerShell-driven, not pytest-accessible | Run the command in a PowerShell session; confirm exit 0 and that `ClassicLib-rs/python-bindings/.venv/Lib/site-packages/classic_shared*` exists |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (per-task verification map populated 2026-04-07)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (11 files listed above)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** audited 2026-04-09 — all tasks green, no gaps

---

## Validation Audit 2026-04-09

| Metric | Count |
|--------|-------|
| Total tasks | 48 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Status: green | 48 |
| Status: red | 0 |

### Live Verification Results

| Check | Result |
|-------|--------|
| `pytest tools/python_api_parity/tests -q` | 16 passed (0.12s) |
| `pytest ClassicLib-rs/python-bindings/tests -q` | 391 passed (0.70s) |
| `check_parity_gate.py --repo-root .` | Tier-1 parity gate passed (exit 0) |
| `validate_stubs.py --fail-on-warnings` | 18/18 crates, 0 errors, 0 warnings |
| `mypy --strict` (19 stubs) | Success: no issues found in 19 source files |
| `deferred_total` | 0 |
| `tier1_contract_total` | 1098 |
| `newly_uncovered_total` | 0 |
| `registry_mismatch_total` | 0 |
| `tierDefinitions` keys | tier1 (single tier) |
| `03-01-PITFALL4-AUDIT.md` | STATUS: PASS |

### Requirement Coverage

| Req ID | Status | Key Evidence |
|--------|--------|--------------|
| PYT-01 | COVERED | 19 crates enrolled, generate_baseline_targets tests green |
| PYT-02 | COVERED | Parity gate exits 0, 1098 tier1Mappings, tier2 removed |
| PYT-03 | COVERED | tier2_definition_removed + tier2_gap_total_removed tests green |
| PYT-04 | COVERED | mypy --strict 19/19 stubs, validate_stubs 18/18 crates |
| PYT-05 | COVERED | 391 binding tests pass (all 9 smoke test files exist + green) |
| PYT-06 | COVERED | deferred_total=0, newly_uncovered_total=0 |
| HARM-03 | COVERED | test_classic_shared_smoke 25 tests pass (runtime_stats verified) |
| HARM-04 | COVERED | 61 shared rows enrolled, mypy --strict classic_shared.pyi passes |

