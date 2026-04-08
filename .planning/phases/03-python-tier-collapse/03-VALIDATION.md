---
phase: 3
slug: python-tier-collapse
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
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
| PYT-01 | `RUST_TARGET_CRATES` / `PYTHON_TARGET_MODULES` enumerate all 19 binding pairs (18 business-logic + classic-shared-py); `parse_rust_surface()` returns non-empty symbol lists for every entry | unit + integration | `python tools/python_api_parity/generate_baseline.py --repo-root .` then assert `len(rust_api_surface.json::scope.target_crates) == 19` and every crate's symbols list is non-empty | ❌ Wave 0 |
| PYT-02 | Every previously-deferred symbol resolves through the gate as a Tier-1 contract row; `parity_diff_report.json::summary.tier2_gap_total == 0` | integration | `python tools/python_api_parity/check_parity_gate.py --repo-root .` (exit 0) + `jq .summary.tier2_gap_total docs/implementation/python_api_parity/baseline/parity_diff_report.json` (= 0) | ✅ existing |
| PYT-03 | Removing Tier-2 gap-row branches from `generate_diff_report()` does not silently drop coverage — `tier1_contract_total` after Plan 9 == previous + 285 + 12 | integration | snapshot test in `tools/python_api_parity/tests/test_check_parity_gate.py` | ❌ Wave 0 |
| PYT-04 | Every promoted entry's `.pyi` stub passes `mypy --strict` AND `validate_stubs.py --fail-on-warnings` | static | `validate_stubs.py` + `mypy --strict` per crate (per-plan close) | ✅ existing |
| PYT-05 | Each promoted `#[pyclass]` is constructed and one method called at runtime; each promoted free-function group has one call exercising the real codepath | unit smoke | `pytest ClassicLib-rs/python-bindings/tests/test_promoted_<crate>_smoke.py -x` (one file per Plan 2–8) | ❌ Wave 0 (6 new files) |
| PYT-06 | `runtime_coverage_summary.json::summary.deferred_total == 0` after Plan 9 lands | integration | `jq .summary.deferred_total docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json` | ✅ existing |
| HARM-03 | `import classic_shared; classic_shared.get_runtime_stats().worker_threads > 0` | smoke | `pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py::test_runtime_stats_smoke -x` | ❌ Wave 0 (Plan 8) |
| HARM-04 | `classic_shared` enrolled in `parity_contract.json::tier1Mappings` with ≥6 rows; `mypy --strict classic_shared.pyi` exits 0 | static + integration | `check_parity_gate.py --repo-root .` + `mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` | ✅ tooling exists |

---

## Per-Task Verification Map

*Populated by gsd-planner during PLAN.md creation. The planner fills one row per task with the appropriate `{N}-{plan}-{task}` ID.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| — | — | — | — | — | *planner populates* | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Files that must be created before promotion work begins (Plan 1 absorbs the tooling tests; Plans 2–8 absorb their respective smoke test files):

- [ ] `tools/python_api_parity/tests/__init__.py` — pytest collection root for tooling tests
- [ ] `tools/python_api_parity/tests/test_generate_baseline_targets.py` — proves every entry in `RUST_TARGET_CRATES` parses to a non-empty symbol list (PYT-01 unit guard) **[Plan 1]**
- [ ] `tools/python_api_parity/tests/test_check_parity_gate.py` — snapshot test of `tier1_contract_total` before/after Plan 9 removes Tier-2 branches (PYT-03 unit guard) **[Plan 1]**
- [ ] `tools/python_api_parity/tests/test_pitfall2_guard.py` — exercises D-05's `validate_contract_rust_symbols()` against a synthetic contract row whose `rustSymbol` is missing; asserts non-zero exit + diagnostic text **[Plan 1]**
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py` **[Plan 2 — Wave 1: 74 rows]**
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py` **[Plan 3 — Wave 2: 58 rows]**
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py` **[Plan 4 — Wave 3a orchestration: ~50 rows]**
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_report_smoke.py` **[Plan 5 — Wave 3b report: ~46 rows]**
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py` **[Plan 6 — 22 rows]**
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py` **[Plan 7 — 34 rows]**
- [ ] `ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py` **[Plan 8 — classic_shared 6 rows + file_io aux 5 rows]**

**Existing infrastructure (reusable):**
- `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` (already runtime-verified)
- `ClassicLib-rs/python-bindings/.venv` with pytest
- `validate_stubs.py`, `check_parity_gate.py`, `generate_baseline.py`

---

## Regression Surfaces

1. **`mypy --strict`** — fails if a promoted method's stub argument shape doesn't match the actual `#[pymethods]` signature
2. **`validate_stubs.py`** — fails if a `#[pyclass]` exists in `-py/src/*.rs` but is missing from the corresponding `.pyi` (and vice versa); also walks `tier1Mappings` to confirm discovered crates have a stub file
3. **`parity_contract.json` row-count invariant** — Plan 1 establishes `tier1Mappings.length == 59` (current). Plan 9 must end with `tier1Mappings.length == 59 + 285 + 12 + 6 = 362` (current Tier-1 + deferred backlog promotions + Tier-2 runtime-verified migrations + classic_shared). Off-by-N drift is detectable by snapshot test.
4. **`runtime_coverage_registry.json` row-count invariant** — currently 8 entries. After Phase 3: ≈14–18 rows depending on D-08 grouping. The strict invariant: every contract row must have a matching registry row (D-08); the gate's `tier1_missing_runtime_total` check enforces this.
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
| `mypy --strict: incompatible types` | Stub return type doesn't match Rust shape | Fix the stub annotation; PyO3 0.27 maps `Vec<X>` → `list[X]`, `(A, B)` → `tuple[A, B]` |

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (planner fills during PLAN.md)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (10 files listed above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
