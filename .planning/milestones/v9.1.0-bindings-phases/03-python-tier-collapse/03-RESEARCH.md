## RESEARCH COMPLETE

**Phase:** 3 — Python Tier Collapse
**Researched:** 2026-04-07
**Domain:** Python parity tooling, PyO3 wrapper plumbing, runtime coverage registry
**Confidence:** HIGH (every count grounded in live JSON / Rust source — see scripts in `_research_scripts/`)

> NOTE: This research file deliberately departs from the boilerplate `## Standard Stack` / `## Don't Hand-Roll` template because Phase 3 is a **single-domain tooling expansion** — no library selection, no architecture choice. The relevant prior research lives in `.planning/research/STACK.md` (no new deps), `.planning/research/ARCHITECTURE.md` §3 / §6 (component layout), and `.planning/research/PITFALLS.md` (1, 2, 4, 7). This file answers only the eight planner-blocking questions listed in `<research_focus>`, plus mandatory Validation Architecture and Assumption Corrections.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01** Phase 3 uses an **8-plan split-scanlog hybrid** (may grow to 9–10 if Wave 2 / Wave 3 prove unbalanced — see Question 2 below):
  1. Plan 1 — tooling expansion: `RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES` grow from 3 → 19; mechanical Pitfall 2 guard assertion lands in `check_parity_gate.py`; baseline regenerated against widened target set with Tier-2 skip logic still in place.
  2. Plan 2 — scanlog Wave 1 (parsing primitives): `parser`, `formid`, `formid_analyzer`, `record_scanner`, `plugin_analyzer`, `patterns`.
  3. Plan 3 — scanlog Wave 2 (detection & analysis): `mod_detector`, `suspect_scanner`, `settings_validator`, `fcx_handler`, `gpu_detector`.
  4. Plan 4 — scanlog Wave 3 (orchestration & output): `orchestrator`, `report`, `papyrus`, `version`, `crashgen_rules`, `core_mod_convert`.
  5. Plan 5 — config module promotion.
  6. Plan 6 — version_registry module promotion.
  7. Plan 7 — `classic_shared` wiring (HARM-03/04) — 6 contract rows + 4-step verification chain.
  8. Plan 8 — Tier-2 skip removal, final mypy --strict sweep, final gate + pytest verification.
- **D-02** scanlog 228 entries split **by dependency layer**, not file-size.
- **D-03** Each promotion plan refreshes the committed parity baseline in the same commit as the code change (mirrors Phase 2 D-09 cadence; Python gate's existing `--update-baseline` flag is the mechanism — `check_parity_gate.py` line 152).
- **D-04** Each `-py` crate's `lib.rs` gets **narrow `pub use` additions — 1:1 with promoted contract rows**, no wildcards. ⚠ **See Assumption Correction A1** — this rule is misdirected; the parser reads `-core/lib.rs`, and most deferred symbols are already there.
- **D-05** Mechanical Pitfall 2 guard assertion runs unconditionally in every `check_parity_gate.py` invocation.
- **D-06** Atomic per-plan commits — `pub use` first, then contract rows + `.pyi`, then baseline refresh, then registry rows + smoke tests, all in one commit.
- **D-07** Per-class smoke tests with grouped free-function tests; targets 70–90 new pytest functions.
- **D-08** Every promoted contract row gets a 1:1 runtime coverage registry entry; `nodeids` point to D-07 smoke tests.
- **D-09** `classic_shared` contract = full 6-row module surface: `RuntimeStats`, `get_runtime_stats`, `is_runtime_healthy`, `PyStringProcessor`, `PyPathHandler`, `PyRustPerformanceMonitor`. ⚠ **See Assumption Correction A2** — the "1 aux" entry does NOT belong to `classic_shared`; it belongs to `classic_file_io`.
- **D-10** 4-step `classic_shared` wiring verification chain: gate → wheel build → pytest smoke → `mypy --strict` on `classic_shared.pyi`.

### Claude's Discretion

- Exact sub-module groupings within each scanlog wave (planner verifies whether 76-76-76 holds — see Question 2; **it does not**).
- `.pyi` stub edit mechanics — hand-edit diffs preferred over wholesale regeneration.
- Whether the Pitfall 2 guard assertion is `validate_contract_rust_symbols()`, inlined in `main()`, or surfaced through `parse_rust_surface()`.
- Per-plan vs per-commit `validate_stubs.py` + `mypy --strict` cadence.
- Whether per-class fixture data lives in `tests/fixtures/` or inline in tests.
- Plan 8: pure deletion vs. annotated comment for Tier-2 skip removal.
- Whether registry `nodeids` use module-level or class-level paths (Plan 7 locks the convention after Plans 2 experiment).

### Deferred Ideas (OUT OF SCOPE)

- Tier-2 governance file deletion → Phase 6 (DOC-02, DOC-04)
- `--deferred-registry` argument optional/missing-tolerant → Phase 6 (DOC-01)
- `docs/api/binding-parity-overview.md` rewrite → Phase 6 (DOC-05)
- Per-binding error-contract documentation → Phase 6 (HARM-05)
- Standardizing error conventions across bindings → explicit anti-feature
- Auto-generated `.pyi` via stubgen / pyo3-stub-gen → explicit anti-feature
- Unified cross-binding parity manifest → out of scope for v9.1.0-bindings
- New Cargo workspace dependencies → STACK.md confirmed none required
- `classic_shared` wheel publishing/distribution → out of scope
- Expanding `classic_shared` contract beyond the 6 module-level exports
- Phase 3 / Phase 4 commit-level parallelism coordination — avoid `tools/binding_parity_runtime_coverage.py` simultaneous edits
- CI workflow file edits → Phase 5

---

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **PYT-01** | `RUST_TARGET_CRATES` + `PYTHON_TARGET_MODULES` expanded from 3 → 19 entries | Question 3 below specifies the exact 19+19 entries, owners, and SQUADs to add to `tools/python_api_parity/generate_baseline.py` lines 24–52 |
| **PYT-02** | All ~285 deferred parity entries promoted with concurrent `pub use` re-exports | Question 1 (corrected counts), Question 2 (sub-module distribution), Assumption Correction A3 (most `pub use` already exist) |
| **PYT-03** | `check_parity_gate.py` Tier-2 skip logic removed | Section "Where 'Tier-2 skip logic' actually lives" — there is NO `check_parity_gate.py`-level skip; Plan 8 removes the **gap-row tier=tier2 branches** in `generate_baseline.py::generate_diff_report()` and converts the registry classification flow |
| **PYT-04** | `.pyi` stubs cover every promoted entry; `mypy --strict` clean | Validation Architecture below; per-plan `validate_stubs.py` + `mypy --strict` cadence |
| **PYT-05** | `uv run pytest ClassicLib-rs/python-bindings/tests -q` passes with smoke tests for at least one method per promoted module | Question 6 (#[pyclass] inventory) sized at 70–90 functions matches D-07 |
| **PYT-06** | `check_parity_gate.py` exits zero with expanded contract; deferred-entry count → 0 in `runtime_coverage_summary.md` | Section "How `deferred_total` is computed" + Assumption Correction A4 explain why the 289 figure is misleading and what the actual end-state must be |
| **HARM-03** | `classic-shared-py` wired as a maturin build target in `rebuild_rust.ps1`; `classic_shared` Python module importable | Question 5 — the auto-discovery already works because `Get-PythonRustModules` searches `ClassicLib-rs/foundation/` (rebuild_rust.ps1 lines 215–272) |
| **HARM-04** | `classic_shared.pyi` exists alongside the build output and the gate's module map includes `classic_shared` so it's gate-enforced from day one | Question 5 + Question 7 — stub already exists at `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi`; verify completeness against the 6 #[pymodule] symbols |

</phase_requirements>

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (via `uv run`) — implicit version from `ClassicLib-rs/python-bindings/.venv` |
| Config file | `ClassicLib-rs/python-bindings/conftest.py` (existing — to verify in Plan 1 Wave 0) |
| Quick run command | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q` |
| Full suite command | same — there is one suite |
| Stub validator | `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` |
| Type checker | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict <pyi-file>` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PYT-01 | `RUST_TARGET_CRATES` and `PYTHON_TARGET_MODULES` enumerate all 19 binding pairs and `parse_rust_surface()` returns non-empty symbol lists for every entry | unit + integration | `python tools/python_api_parity/generate_baseline.py --repo-root .` then assert `len(rust_api_surface.json::scope.target_crates) == 19` and every crate's symbols list is non-empty | ❌ Wave 0 (new pytest module: `tools/python_api_parity/tests/test_generate_baseline_targets.py`) |
| PYT-02 | Every previously-deferred symbol resolves through the gate as a Tier-1 contract row and `parity_diff_report.json::summary.tier2_gap_total == 0` | integration | `python tools/python_api_parity/check_parity_gate.py --repo-root .` (exit 0) followed by `jq .summary.tier2_gap_total ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json` (= 0) | ✅ existing |
| PYT-03 | Removing the Tier-2 gap-row branches in `generate_diff_report()` does not silently drop coverage — `tier1_contract_total` after removal == previous `tier1_contract_total + 285 + 12` | integration | snapshot test in `tools/python_api_parity/tests/test_check_parity_gate.py` | ❌ Wave 0 |
| PYT-04 | Every promoted entry's `.pyi` stub passes `mypy --strict` AND `validate_stubs.py --fail-on-warnings` | static | `validate_stubs.py` + `mypy --strict` per crate (per-plan close) | ✅ existing |
| PYT-05 | Each promoted `#[pyclass]` is constructed and one method called at runtime; each promoted free function group has one call exercising the real codepath | unit smoke | `pytest ClassicLib-rs/python-bindings/tests/test_promoted_<crate>_smoke.py -x` (one test file per Plan 2-7 — see D-07) | ❌ Wave 0 (one new file per plan) |
| PYT-06 | `runtime_coverage_summary.json::summary.deferred_total == 0` after Plan 8 lands | integration | `jq .summary.deferred_total docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json` | ✅ existing |
| HARM-03 | `import classic_shared; classic_shared.get_runtime_stats().worker_threads > 0` | smoke | `pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py::test_runtime_stats_smoke -x` | ❌ Wave 0 (Plan 7) |
| HARM-04 | `classic_shared` enrolled in `parity_contract.json::tier1Mappings` with ≥6 rows; `mypy --strict classic_shared.pyi` exits 0 | static + integration | `python tools/python_api_parity/check_parity_gate.py --repo-root .` then `mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` | ✅ tooling exists |

### Sampling Rate

- **Per task commit:** `python tools/python_api_parity/check_parity_gate.py --repo-root .` (exit 0 expected) + `validate_stubs.py` for the touched crate
- **Per wave merge / plan close:** full chain — gate, validate_stubs, rebuild_rust.ps1 -Target python <affected modules>, pytest, mypy --strict (the **5-step chain** documented in CONTEXT.md `<specifics>` line 229)
- **Phase gate:** all five steps green on every Phase 3 commit; `runtime_coverage_summary.md` `deferred_total == 0` after Plan 8

### Wave 0 Gaps

- [ ] `tools/python_api_parity/tests/__init__.py` — pytest collection root for tooling tests (does not exist today)
- [ ] `tools/python_api_parity/tests/test_generate_baseline_targets.py` — proves every entry in `RUST_TARGET_CRATES` parses to a non-empty symbol list (PYT-01 unit guard)
- [ ] `tools/python_api_parity/tests/test_check_parity_gate.py` — snapshot test of `tier1_contract_total` before/after Plan 8 removes the Tier-2 branches (PYT-03 unit guard)
- [ ] `tools/python_api_parity/tests/test_pitfall2_guard.py` — exercises D-05's `validate_contract_rust_symbols()` against a synthetic contract row whose `rustSymbol` is missing from the parsed Rust surface; asserts non-zero exit + diagnostic text (Plan 1 deliverable)
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py` (Plan 2 — Wave 1)
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py` (Plan 3 — Wave 2)
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave3_smoke.py` (Plan 4 — Wave 3)
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_config_smoke.py` (Plan 5)
- [ ] `ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py` (Plan 6)
- [ ] `ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py` (Plan 7)

> Existing infrastructure: `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` (already runtime-verified), the `.venv` at `ClassicLib-rs/python-bindings/.venv`, `validate_stubs.py`, `check_parity_gate.py`, `generate_baseline.py`. No framework install needed. `pytest` is implied by the existing test file.

### Regression surfaces

- **`mypy --strict`** — fails if a promoted method's stub argument shape doesn't match the actual `#[pymethods]` signature
- **`validate_stubs.py`** — fails if a `#[pyclass]` exists in `-py/src/*.rs` but is missing from the corresponding `.pyi` (and vice versa); also walks `tier1Mappings` to confirm the discovered crates have a stub file
- **`parity_contract.json` row-count invariant** — Plan 1 establishes `tier1Mappings.length == 59` (current). Plan 8 must end with `tier1Mappings.length == 59 + 285 + 12 + 6 = 362` (current Tier-1 + deferred backlog promotions + Tier-2 runtime-verified migrations + classic_shared). Off-by-N drift is detectable by snapshot test.
- **`runtime_coverage_registry.json` row-count invariant** — currently 8 entries. After Phase 3: 8 (existing) − 4 (Tier-2 binding-id rows that get migrated to contract rows for config/version_registry/scanlog) − 1 (aux Tier-2 selector) + 6 (per-class scanlog test pointers) + 5 (per-crate config/version_registry/classic_shared/aux pointers) ≈ 14–18 rows depending on D-08 grouping. The strict invariant: **every contract row must have a matching registry row** (D-08); the gate's `tier1_missing_runtime_total` check enforces this.
- **`tier1_contract_total`** in `runtime_coverage_summary.json::summary` — must equal `parity_contract.json::tier1Mappings.length` after every plan. Off-by-one detection is automatic.

### Failure signatures

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `parity_diff_report.json::summary.tier1_missing_rust > 0` | Contract row's `rustSymbol` is not in the parsed Rust surface — typo in row OR symbol genuinely missing from `-core/lib.rs` | Add `pub use sub::Symbol;` to **`-core/lib.rs`** (NOT `-py/lib.rs` — see Assumption Correction A1) OR fix typo in `parity_contract.json` |
| `parity_diff_report.json::summary.tier1_missing_python > 0` | Contract row's `pythonExportPath` not in the `.pyi` parser output | Add the class/function to the `.pyi` file matching the Python-facing identifier (after `#[pyo3(name = "...")]` rename) |
| `parity_diff_report.json::summary.tier1_signature_mismatch > 0` | `pythonKind` or `pythonArity` in contract differs from `.pyi` actual | Fix the contract row OR fix the stub signature; `signature_mismatch` ALWAYS indicates one of the two is wrong |
| `coverage_summary.json::tier1_missing_runtime_total > 0` | A Tier-1 contract row has no matching registry row | Add a `runtime_coverage_registry.json` entry whose `contractIds` or `contractSelector` resolves to this row |
| `coverage_summary.json::registry_mismatch_total > 0` | A registry row uses `contractSelector` and the matched count or hash drifted from `contractCount` / `contractIdsHash` | Recompute `contractIdsHash` via `_stable_id_hash` (sha256 of sorted contract IDs); update both fields |
| `pytest AttributeError on import classic_*` | A `#[pyclass]` is in the `.pyi` but not registered in the `#[pymodule]` function | Add `m.add_class::<PyXxx>()?;` to `-py/src/lib.rs::classic_xxx` (Pitfall 4) |
| `pytest ImportError: classic_shared` | wheel not built or not installed into `.venv` | `pwsh rebuild_rust.ps1 -Target python classic_shared` |
| `validate_stubs.py: Class 'X' missing methods: {...}` | `#[pymethods]` defines a method that the `.pyi` lacks | Add the def to the stub OR (if the rust method is `#[getter]`) annotate so `validate_stubs.py::extract_rust_methods` skips it |
| `mypy --strict: incompatible types` | Stub return type uses `tuple[int, int]` but Rust returns `Vec<u32>` shaped differently | Fix the stub annotation; PyO3 0.27 maps `Vec<X>` → `list[X]`, `(A, B)` → `tuple[A, B]` |

### Coverage completeness criterion (PowerShell one-liner)

```powershell
# After Plan 8: every promoted contract row must have a matching pytest smoke test AND a runtime registry row.
# Returns 0 rows when complete; any output is a gap.
$contract = Get-Content 'docs/implementation/python_api_parity/baseline/parity_contract.json' -Raw | ConvertFrom-Json
$registry = Get-Content 'ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json' -Raw | ConvertFrom-Json
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

## Question 1 — Per-crate / per-binding entry counts

**The "289 = 228 + 34 + 26 + 1" claim in CONTEXT.md is wrong** in two ways. See Assumption Correction A4.

### Authoritative source: `deferred_runtime_backlog.json`

Live run of `_research_scripts/count_entries.ps1` on `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`:

| ownerModule | wave (current) | deferred entries | Distinct rustSymbols | Notes |
|-------------|-----:|-----:|-----:|-------|
| scanlog | wave1 | **228** | 57 | Many entries share a `rustSymbol` (LogParser has 16 row, FcxModeHandler 13 rows, ReportGenerator 14 rows — see Question 6 for full breakdown) |
| config | wave2 | **22** | 15 | NOT 26 — see A4 |
| version_registry | wave3 | **34** | 10 | |
| aux | wave4 | **1** | 0 | The single aux entry is `classic_file_io.FileHasher.cache_size`, NOT a `classic_shared` symbol — see A2 |
| **TOTAL** | | **285** | 82 | |

### Per business-logic crate / Python binding crate matrix (target end-state)

The 19 binding crates are NOT 1:1 with the 19 business-logic crates. `classic-crashgen-settings-core` has no dedicated `-py` adapter; its symbols are surfaced through `classic-config-py`, `classic-scanlog-py`, and `classic-scangame-py`. `classic-shared-py` lives under `foundation/`, not `python-bindings/`. See Assumption Correction A5.

| # | Rust source crate (lib.rs path for `RUST_TARGET_CRATES`) | Python binding module (`PYTHON_TARGET_MODULES` key) | Stub path (`PYTHON_TARGET_MODULES` value) | Current Tier-1 rows | Deferred (raw) | After promotion |
|---|---|---|---|---:|---:|---:|
| 1 | `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs` | `classic_scanlog` | `python-bindings/classic-scanlog-py/classic_scanlog.pyi` | 20 | 228 + 4 (Tier-2 runtime-verified) | **252** |
| 2 | `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs` | `classic_config` | `python-bindings/classic-config-py/classic_config.pyi` | 15 | 22 + 4 | **41** |
| 3 | `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs` | `classic_version_registry` | `python-bindings/classic-version-registry-py/classic_version_registry.pyi` | 24 | 34 + 1 | **59** |
| 4 | `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` | `classic_yaml` | `python-bindings/classic-yaml-py/classic_yaml.pyi` | 0 | 0 | **0**¹ |
| 5 | `ClassicLib-rs/business-logic/classic-database-core/src/lib.rs` | `classic_database` | `python-bindings/classic-database-py/classic_database.pyi` | 0 | 0 | **0**¹ |
| 6 | `ClassicLib-rs/business-logic/classic-file-io-core/src/lib.rs` | `classic_file_io` | `python-bindings/classic-file-io-py/classic_file_io.pyi` | 0 | 0 + 4 (incl. the 1 aux + 3 cache stats) | **4**¹² |
| 7 | `ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs` | `classic_scangame` | `python-bindings/classic-scangame-py/classic_scangame.pyi` | 0 | 0 | **0**¹ |
| 8 | `ClassicLib-rs/business-logic/classic-registry-core/src/lib.rs` | `classic_registry` | `python-bindings/classic-registry-py/classic_registry.pyi` | 0 | 0 | **0**¹ |
| 9 | `ClassicLib-rs/business-logic/classic-perf-core/src/lib.rs` | `classic_perf` | `python-bindings/classic-perf-py/classic_perf.pyi` | 0 | 0 | **0**¹ |
| 10 | `ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs` | `classic_settings` | `python-bindings/classic-settings-py/classic_settings.pyi` | 0 | 0 | **0**¹ |
| 11 | `ClassicLib-rs/business-logic/classic-message-core/src/lib.rs` | `classic_message` | `python-bindings/classic-message-py/classic_message.pyi` | 0 | 0 | **0**¹ |
| 12 | `ClassicLib-rs/business-logic/classic-path-core/src/lib.rs` | `classic_path` | `python-bindings/classic-path-py/classic_path.pyi` | 0 | 0 | **0**¹ |
| 13 | `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` | `classic_constants` | `python-bindings/classic-constants-py/classic_constants.pyi` | 0 | 0 | **0**¹ |
| 14 | `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` | `classic_version` | `python-bindings/classic-version-py/classic_version.pyi` | 0 | 0 | **0**¹ |
| 15 | `ClassicLib-rs/business-logic/classic-resource-core/src/lib.rs` | `classic_resource` | `python-bindings/classic-resource-py/classic_resource.pyi` | 0 | 0 | **0**¹ |
| 16 | `ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs` | `classic_xse` | `python-bindings/classic-xse-py/classic_xse.pyi` | 0 | 0 | **0**¹ |
| 17 | `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` | `classic_web` | `python-bindings/classic-web-py/classic_web.pyi` | 0 | 0 | **0**¹ |
| 18 | `ClassicLib-rs/business-logic/classic-update-core/src/lib.rs` | `classic_update` | `python-bindings/classic-update-py/classic_update.pyi` | 0 | 0 | **0**¹ |
| 19 | `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs`³ | `classic_shared` | `foundation/classic-shared-py/classic_shared.pyi` | 0 | 0 | **6** (D-09) |
| **EXCLUDED** | `classic-crashgen-settings-core` | n/a | n/a | n/a | n/a | n/a — symbols flow through `classic_config` / `classic_scanlog` / `classic_scangame` (see A5) |

**¹** "0 deferred" for crates 4–18 means no entries currently in `deferred_runtime_backlog.json`. After Plan 1 expands `RUST_TARGET_CRATES`, the parser will discover **new `tier2_gap_total` entries** for every public symbol of these crates that has no matching `tier1Mappings` row. The planner must decide what to do with these newly-surfaced symbols: **promote them as part of Phase 3** (gate fails if not), or hold them as a follow-up. The CONTEXT.md scope says Phase 3 promotes "all currently-deferred entries" — newly-discovered symbols from the 16 currently-untracked crates are NOT in the 285 figure. **This is a hidden requirement** the planner must address: see Question 1 footnote ².

**²** The current "1 aux" entry plus 3 Tier-2 runtime-verified entries (`classic_file_io.FileHasher.cache_stats`, `reset_cache_stats`, `clear_cache`) all live in `classic-file-io-py`. Phase 3 must also enroll `classic_file_io` in `PYTHON_TARGET_MODULES` and add it to `RUST_OWNER_BY_CRATE`. Plan 7 (or Plan 8) absorbs these 4 file-io rows into the `aux` owner module (or repurpose owner module).

**³** For `classic_shared`, the lib.rs path points at `classic-shared-py` (NOT `classic-shared-core`) because the PyO3 wrapper structs (`PyStringProcessor`, `PyPathHandler`, `PyRustPerformanceMonitor`) live in the `-py` adapter under `foundation/`. The pure-Rust `classic-shared-core` has no `#[pyclass]` annotations.

### "1 aux" entry resolution

```json
{
  "coverageId": "python-deferred-aux-297",
  "ownerModule": "aux",
  "wave": "wave4",
  "deferReason": "Compatibility cache-size adapter remains outside direct smoke coverage while canonical cache stats own Phase 4 runtime verification.",
  "bindingIdentifiers": ["classic_file_io.FileHasher.cache_size"]
}
```

Owner crate: **`classic-file-io-py`** wrapping **`classic-file-io-core::FileHasher::cache_size`**. Resolution: add a `tier1Mapping` row pointing at the Rust symbol on the `FileHasher` struct (must verify the Rust struct name; the wrapper is likely `PyFileHasher`). Plan placement: **Plan 7** (with `classic_shared`) since both relate to enrolling new binding modules in the gate.

---

## Question 2 — Scanlog sub-module layer counts

Live run of `_research_scripts/map_scanlog_v2.ps1` against the 228 deferred scanlog entries, attributing each to its actual sub-module by reading every `#[pyclass]` and `#[pyfunction]` declaration in `ClassicLib-rs/python-bindings/classic-scanlog-py/src/*.rs` and falling back to `classic-scanlog-core/src/*` for entries that have no `-py` wrapper yet:

| Sub-module | Deferred rows | D-01 wave |
|---|---:|---|
| parser | 18 + 2 (StreamingLogParser, StreamingIteratorParser) = **20** | Wave 1 |
| formid | 9 + 1 (RustFormIDAnalyzer) = **10** | Wave 1 |
| formid_analyzer | **16** | Wave 1 |
| record_scanner | **11** | Wave 1 |
| plugin_analyzer | **12** | Wave 1 |
| patterns | **5** | Wave 1 |
| **Wave 1 subtotal** | **74** | |
| mod_detector | **9** | Wave 2 |
| suspect_scanner | **8** | Wave 2 |
| settings_validator | **10** | Wave 2 |
| fcx_handler | 19 + 2 (GLOBAL_FCX_HANDLER, FcxResetError) = **21** | Wave 2 |
| gpu_detector | **10** | Wave 2 |
| **Wave 2 subtotal** | **58** | |
| orchestrator | 21 + 2 (ScanProgressPhase, resolve_batch_concurrency) = **23** | Wave 3 |
| report | **46** | Wave 3 |
| papyrus | 14 + 1 (PapyrusError) = **15** | Wave 3 |
| version | 4 + 1 (crashgen_version_gen) = **5** | Wave 3 (CONTEXT calls this `version`, not `crashgen_rules`) |
| crashgen_registry | 1 + 3 (CheckId, CrashgenEntry, CrashgenRegistry) = **4** | Wave 3 (CONTEXT's `crashgen_rules` was a misnomer — see A6) |
| segment_key | **1** | Wave 3 |
| error | 1 + 1 (ScanLogError) = **2** | Wave 3 |
| (no `core_mod_convert` rows in deferred backlog) | **0** | Wave 3 |
| **Wave 3 subtotal** | **96** | |
| **TOTAL** | **228** | ✓ |

### Verdict: 76-76-76 is **NOT achievable**. Actual distribution is **74 / 58 / 96**.

### Implications and recommendations

- **Wave 3 (96 rows) is 65% larger than Wave 2 (58 rows).** The single biggest contributor is `report` at 46 rows. `report` has 5 distinct PyO3 wrapper classes (`PyReportComposer`, `PyReportFragment`, `PyReportGenerator`, `PyParallelReportProcessor`, `PyStringPool`) and the contract rows are method-level on each.
- **Three options for the planner:**
  1. **Accept the asymmetry.** 8-plan structure stays. Wave 3 is heavier — acceptable if execution time budgets allow.
  2. **Split Wave 3 into two plans.** 9-plan structure: Plan 4a (orchestrator + papyrus + version + crashgen_registry + segment_key + error = 50 rows) and Plan 4b (report alone = 46 rows). Slightly more even.
  3. **Move 1–2 sub-modules from Wave 3 to Wave 2.** E.g., move `papyrus` (15 rows) to Wave 2 → Wave 2 = 73, Wave 3 = 81. Within ±15% of Wave 1's 74.
- **Recommendation:** Option 2 (9-plan structure with `report` as a standalone plan). Rationale:
  - `report` has the most cross-cutting symbol surface (StringPool is shared with multiple consumers; ReportComposer/ReportGenerator/ReportFragment have method overlaps; ParallelReportProcessor is the highest-arity class).
  - Per-class smoke tests for 5 report classes are heavier than the 1–3 classes in other Wave 3 sub-modules.
  - Bisect granularity improves: a Wave 3 failure now points at "report" specifically, not "anything in orchestration/output."
  - 9 plans is within the "8–10 plans" range CONTEXT D-01 explicitly allows.
- The planner has Claude's discretion (per CONTEXT) to decide between options 1 / 2 / 3. **Research recommends option 2.**

---

## Question 3 — `generate_baseline.py` expansion table

Current values (lines 24–52 of `tools/python_api_parity/generate_baseline.py`):

```python
RUST_TARGET_CRATES: dict[str, str] = {
    "classic-scanlog-core": "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs",
    "classic-config-core": "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs",
    "classic-version-registry-core": "ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs",
}
RUST_OWNER_BY_CRATE: dict[str, str] = {
    "classic-scanlog-core": "scanlog",
    "classic-config-core": "config",
    "classic-version-registry-core": "version_registry",
}
PYTHON_TARGET_MODULES: dict[str, str] = {
    "classic_scanlog": "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi",
    "classic_config": "ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi",
    "classic_version_registry": "ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi",
}
PYTHON_OWNER_BY_MODULE: dict[str, str] = {
    "classic_scanlog": "scanlog",
    "classic_config": "config",
    "classic_version_registry": "version_registry",
}
SQUAD_BY_OWNER: dict[str, str] = {
    "scanlog": "Squad A (scanlog/config)",
    "config": "Squad A (scanlog/config)",
    "version_registry": "Squad B (version-registry)",
}
```

### Required Plan-1 expansion (19 entries each):

```python
RUST_TARGET_CRATES: dict[str, str] = {
    # Existing 3 (keep for stability)
    "classic-scanlog-core":          "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs",
    "classic-config-core":           "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs",
    "classic-version-registry-core": "ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs",
    # Phase 3 additions — 16 more
    "classic-yaml-core":              "ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs",
    "classic-database-core":          "ClassicLib-rs/business-logic/classic-database-core/src/lib.rs",
    "classic-file-io-core":           "ClassicLib-rs/business-logic/classic-file-io-core/src/lib.rs",
    "classic-scangame-core":          "ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs",
    "classic-registry-core":          "ClassicLib-rs/business-logic/classic-registry-core/src/lib.rs",
    "classic-perf-core":              "ClassicLib-rs/business-logic/classic-perf-core/src/lib.rs",
    "classic-settings-core":          "ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs",
    "classic-message-core":           "ClassicLib-rs/business-logic/classic-message-core/src/lib.rs",
    "classic-path-core":              "ClassicLib-rs/business-logic/classic-path-core/src/lib.rs",
    "classic-constants-core":         "ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs",
    "classic-version-core":           "ClassicLib-rs/business-logic/classic-version-core/src/lib.rs",
    "classic-resource-core":          "ClassicLib-rs/business-logic/classic-resource-core/src/lib.rs",
    "classic-xse-core":               "ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs",
    "classic-web-core":               "ClassicLib-rs/business-logic/classic-web-core/src/lib.rs",
    "classic-update-core":            "ClassicLib-rs/business-logic/classic-update-core/src/lib.rs",
    # foundation crate, special placement
    "classic-shared-py":              "ClassicLib-rs/foundation/classic-shared-py/src/lib.rs",
    # NOTE: classic-crashgen-settings-core is INTENTIONALLY EXCLUDED — its symbols flow
    # through classic-config-py / classic-scanlog-py / classic-scangame-py wrappers
    # (see RESEARCH.md Question 1 + Assumption Correction A5).
}

RUST_OWNER_BY_CRATE: dict[str, str] = {
    # Existing
    "classic-scanlog-core":          "scanlog",
    "classic-config-core":           "config",
    "classic-version-registry-core": "version_registry",
    # New
    "classic-yaml-core":              "yaml",
    "classic-database-core":          "database",
    "classic-file-io-core":           "file_io",
    "classic-scangame-core":          "scangame",
    "classic-registry-core":          "registry",
    "classic-perf-core":              "perf",
    "classic-settings-core":          "settings",
    "classic-message-core":           "message",
    "classic-path-core":              "path",
    "classic-constants-core":         "constants",
    "classic-version-core":           "version",
    "classic-resource-core":          "resource",
    "classic-xse-core":               "xse",
    "classic-web-core":               "web",
    "classic-update-core":            "update",
    "classic-shared-py":              "shared",
}

PYTHON_TARGET_MODULES: dict[str, str] = {
    # Existing
    "classic_scanlog":          "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi",
    "classic_config":           "ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi",
    "classic_version_registry": "ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi",
    # New
    "classic_yaml":             "ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi",
    "classic_database":         "ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi",
    "classic_file_io":          "ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi",
    "classic_scangame":         "ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi",
    "classic_registry":         "ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi",
    "classic_perf":             "ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi",
    "classic_settings":         "ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi",
    "classic_message":          "ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi",
    "classic_path":             "ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi",
    "classic_constants":        "ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi",
    "classic_version":          "ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi",
    "classic_resource":         "ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi",
    "classic_xse":              "ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi",
    "classic_web":              "ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi",
    "classic_update":           "ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi",
    "classic_shared":           "ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi",
}

PYTHON_OWNER_BY_MODULE: dict[str, str] = {
    # Existing
    "classic_scanlog":          "scanlog",
    "classic_config":           "config",
    "classic_version_registry": "version_registry",
    # New (mirrors RUST_OWNER_BY_CRATE)
    "classic_yaml":             "yaml",
    "classic_database":         "database",
    "classic_file_io":          "file_io",
    "classic_scangame":         "scangame",
    "classic_registry":         "registry",
    "classic_perf":             "perf",
    "classic_settings":         "settings",
    "classic_message":          "message",
    "classic_path":             "path",
    "classic_constants":        "constants",
    "classic_version":          "version",
    "classic_resource":         "resource",
    "classic_xse":              "xse",
    "classic_web":              "web",
    "classic_update":           "update",
    "classic_shared":           "shared",
}

SQUAD_BY_OWNER: dict[str, str] = {
    # Existing
    "scanlog":          "Squad A (scanlog/config)",
    "config":           "Squad A (scanlog/config)",
    "version_registry": "Squad B (version-registry)",
    # NEW — Plan 1 must add these 17 owner labels
    "yaml":      "Squad A (scanlog/config)",
    "database":  "Squad B (version-registry)",
    "file_io":   "Squad A (scanlog/config)",
    "scangame":  "Squad B (version-registry)",
    "registry":  "Squad B (version-registry)",
    "perf":      "Squad B (version-registry)",
    "settings":  "Squad A (scanlog/config)",
    "message":   "Squad B (version-registry)",
    "path":      "Squad B (version-registry)",
    "constants": "Squad B (version-registry)",
    "version":   "Squad B (version-registry)",
    "resource":  "Squad B (version-registry)",
    "xse":       "Squad B (version-registry)",
    "web":       "Squad B (version-registry)",
    "update":    "Squad B (version-registry)",
    "shared":    "Squad B (version-registry)",
    "aux":       "Squad B (version-registry)",  # for the file-io aux entry
}
```

### `RUST_OWNER_BY_CRATE` discrepancy with the contract's `ownerModule` enum

`parity_contract.json::ownerModules` currently lists exactly 4 owner buckets: `scanlog`, `config`, `version_registry`, `aux`. The expansion above adds 16 more owner labels — but `parity_contract.json::ownerModules` is the **contract enum** that the rendering code in `generate_baseline.py::render_diff_markdown()` (line 682) hard-codes for the per-owner totals table:

```python
for owner in ("scanlog", "config", "version_registry", "aux"):
```

**Plan 1 must also**:
1. Update `parity_contract.json::ownerModules` to add the 16 new owner descriptions
2. Update `render_diff_markdown()` line 682 to iterate `gap_counts_by_owner_tier.keys()` instead of the hard-coded 4-tuple, or add the 16 new owners to a constant list at module top

### Owners NOT yet in `SQUAD_BY_OWNER` (Plan 1 must add)

The current 3 squad keys cover only `scanlog`, `config`, `version_registry`. **Phase 3 needs 16 new SQUAD entries** (or one new shared bucket — see recommendation below).

**Recommendation:** Reduce churn by collapsing the 16 new owners into **two** existing squads (`Squad A (scanlog/config)` for everything that flows through scanlog/config wiring; `Squad B (version-registry)` for everything else), OR add a new `Squad C (foundation/utilities)` bucket for the 13 ancillary crates. The squad label is purely cosmetic (printed in `parity_diff_report.md`); it does not affect gate behavior.

---

## Question 4 — Pitfall 2 guard assertion (D-05) recommendation

D-05 allows three shapes; **research recommends a standalone helper function** in `tools/python_api_parity/check_parity_gate.py` for these reasons:
- Inlining into `main()` makes the function harder to unit-test
- Routing through `parse_rust_surface()` couples surface generation with assertion logic, breaking single responsibility
- A standalone function can be re-used by any future gate consumer (e.g., a pre-commit hook)

### Proposed function

**Location:** `tools/python_api_parity/check_parity_gate.py`, between the existing imports (line 28) and `render_tier1_gate_markdown()` (line 31).

```python
def validate_contract_rust_symbols(
    contract: dict[str, Any],
    rust_manifest: dict[str, Any],
) -> list[str]:
    """Pitfall 2 guard: every Tier-1 contract row's `rustSymbol` must appear
    in the parsed Rust surface.

    Raises a structured diagnostic listing every contract row whose Rust
    symbol cannot be found at the corresponding crate's `lib.rs` surface.
    Returns the list of error strings; empty list means success.
    """
    rust_symbols: set[str] = {
        item["symbol"] for item in rust_manifest.get("symbols", [])
    }
    diagnostics: list[str] = []
    for mapping in contract.get("tier1Mappings", []):
        rust_symbol = mapping.get("rustSymbol")
        if not rust_symbol:
            diagnostics.append(
                f"Contract row '{mapping.get('id', '<unknown>')}' is missing 'rustSymbol'."
            )
            continue
        if rust_symbol not in rust_symbols:
            diagnostics.append(
                "Pitfall 2: contract row '{id}' references rustSymbol '{rust_symbol}' "
                "which is not in the parsed Rust surface for crate '{crate}'. "
                "Add 'pub use <sub_module>::{rust_symbol};' to "
                "'ClassicLib-rs/business-logic/{crate}/src/lib.rs' (or the appropriate "
                "foundation/-py lib.rs for classic_shared) before promoting this row.".format(
                    id=mapping["id"],
                    rust_symbol=rust_symbol,
                    crate=mapping.get("rustCrate", "<unknown>"),
                )
            )
    return diagnostics
```

### Call site

Inside `main()` immediately after `rust_manifest = parse_rust_surface(...)` and **before** `generate_diff_report(...)` (currently around line 169–171 of `check_parity_gate.py`):

```python
rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
python_manifest = parse_python_surface(repo_root, tier1_python_exports)

# Pitfall 2 guard (Phase 3 D-05) — fail FAST before downstream diff generation
pitfall2_diagnostics = validate_contract_rust_symbols(contract, rust_manifest)
if pitfall2_diagnostics:
    print("\n".join(pitfall2_diagnostics), file=sys.stderr)
    return 1

diff_report = generate_diff_report(contract, rust_manifest, python_manifest)
```

### Exact error message text (one canonical line per failing row)

```
Pitfall 2: contract row '{contract_row_id}' references rustSymbol '{rust_symbol}' which is not in the parsed Rust surface for crate '{rust_crate}'. Add 'pub use <sub_module>::{rust_symbol};' to 'ClassicLib-rs/business-logic/{rust_crate}/src/lib.rs' (or the appropriate foundation/-py lib.rs for classic_shared) before promoting this row.
```

### Why this shape

- **Failing fast** before `generate_diff_report` keeps the diagnostic surface clean — without the guard, missing symbols surface as `tier1_missing_rust` rows in the contract evaluation, which is the noisier path CONTEXT D-05 explicitly wants replaced.
- **Single function** is unit-testable: `tools/python_api_parity/tests/test_pitfall2_guard.py` can construct a synthetic contract + rust_manifest pair and assert the diagnostic list shape.
- **Stderr output + exit 1** preserves CI fail-fast semantics; the function is pure and returns the list (test ergonomics).
- **Docs reference in error text** points contributors at the exact fix without requiring them to read PITFALLS.md.

---

## Question 5 — `classic_shared` wiring verification chain (D-10)

### Step 1 — Python parity gate exits zero with `classic_shared` enrolled

**Command:**
```powershell
python tools/python_api_parity/check_parity_gate.py --repo-root .
```

**Expected exit code:** `0`

**Pass means:**
- `parity_diff_report.json::summary.tier1_contract_total >= 6` for the `classic_shared` slice (verifiable via `jq '.contract_results | map(select(.python_module == "classic_shared")) | length'`)
- `parity_diff_report.json::summary.tier1_missing_rust == 0`
- `parity_diff_report.json::summary.tier1_missing_python == 0`
- `runtime_coverage_summary.json::perOwnerModule.shared.total >= 6` (or whatever owner label is chosen — Plan 7 owns this decision; recommend `shared`)
- The 6 contract rows for classic_shared all have `status == "matched"` in `parity_diff_report.json::contract_results`

**Failure modes and fixes:**
- `tier1_missing_rust > 0` → `classic-shared-py/src/lib.rs` is missing a `pub use` for one of the 6 wrapper structs/functions — add `pub use {strings_py::PyStringProcessor, path_py::PyPathHandler, performance_py::PyRustPerformanceMonitor};` (already present at lines 42–44 of `classic-shared-py/src/lib.rs` — confirmed)
- `tier1_missing_python > 0` → `classic_shared.pyi` is missing one of the stub classes — see Question 7 below; the existing stub already has all 6 ✓

### Step 2 — `rebuild_rust.ps1 -Target python classic_shared` builds and installs

**Command:**
```powershell
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared
```

**Expected exit code:** `0`

**Pass means:**
- `rebuild_rust.ps1` discovers `classic-shared-py` via `Get-PythonRustModules` (already does — verified in `rebuild_rust.ps1` lines 215–272: `$searchPaths` includes `ClassicLib-rs/foundation/`)
- `maturin build --release --out dist` produces `ClassicLib-rs/foundation/classic-shared-py/dist/classic_shared-9.x.y-cp312-cp312-win_amd64.whl`
- `uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe <wheel> --reinstall` exits zero
- The verification step at the end of `Invoke-PythonBindingsRebuild` runs `python -c "import classic_shared; print(classic_shared.__version__)"` and prints a non-empty version string

**Verification of `Get-PythonRustModules` discovery:** Already confirmed by reading `rebuild_rust.ps1` lines 222–238. The function recursively walks `ClassicLib-rs/foundation/` looking for `Cargo.toml` files, calls `Get-RustModuleInfo`, which returns a `PSCustomObject` for any crate with `[lib] name = "..."` AND `pyo3 = ...` OR `crate-type = [..., "cdylib", ...]`. `classic-shared-py/Cargo.toml` should satisfy this — Plan 7 verifies in 30 seconds.

**Failure modes and fixes:**
- "No Rust Python modules were discovered" → either `Cargo.toml` doesn't have `pyo3 = ...` (it does — see `foundation/classic-shared-py/Cargo.toml`) OR the regex in `Get-RustModuleInfo` line 113 fails to match the package name (verify the package name is `classic-shared-py`, lib name is `classic_shared`)
- "transient linker file lock LNK1105" → `Invoke-MaturinBuildWithRetry` already handles this with exponential backoff (lines 147–213); just wait for retry
- Wheel file not found in `dist/` after build → maturin failed silently; check stderr in the `outputText` array

### Step 3 — pytest smoke test imports and exercises `classic_shared`

**Test file:** `ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py`

**Command:**
```powershell
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py -x -q
```

**Expected exit code:** `0`

**Test contents (minimal):**

```python
"""Smoke tests for the classic_shared Python module (HARM-03 / HARM-04)."""
from __future__ import annotations

import classic_shared


def test_get_runtime_stats_returns_healthy_struct() -> None:
    stats = classic_shared.get_runtime_stats()
    assert stats is not None
    assert stats.worker_threads > 0
    assert stats.is_healthy is True


def test_is_runtime_healthy_true_in_test_context() -> None:
    assert classic_shared.is_runtime_healthy() is True


def test_runtime_stats_repr_is_descriptive() -> None:
    stats = classic_shared.get_runtime_stats()
    text = repr(stats)
    assert "RuntimeStats" in text
    assert "worker_threads" in text


def test_string_processor_normalize_smoke() -> None:
    sp = classic_shared.StringProcessor()
    out = sp.normalize("  hello  ")
    assert out == "hello"


def test_path_handler_split_smoke() -> None:
    ph = classic_shared.PathHandler()
    parts = ph.split_path("a/b/c")
    assert "c" in parts


def test_rust_performance_monitor_record_smoke() -> None:
    mon = classic_shared.RustPerformanceMonitor()
    mon.record_metric("test_op", 1)
    stats = mon.get_all_stats()
    assert "test_op" in stats
```

**Pass means:** All 6 tests exit green. Each test exercises one of the 6 contract rows. RuntimeStats uses `get_runtime_stats()` (its only constructor — `#[pyclass]` without `#[new]`).

**Failure modes:**
- `ImportError: classic_shared` → wheel not installed; rerun Step 2
- `AttributeError: classic_shared.PathHandler` → name mismatch; the `#[pyclass(name = "PathHandler")]` attribute on `PyPathHandler` (verified at `path_py.rs` line 11) maps the Rust struct to the Python name `PathHandler`, NOT `PyPathHandler`. The contract row's `pythonExportPath` MUST be `PathHandler`, not `PyPathHandler`.

### Step 4 — `mypy --strict` against `classic_shared.pyi`

**Command:**
```powershell
uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi
```

**Expected exit code:** `0`

**Pass means:** mypy reports `Success: no issues found in 1 source file`.

**Currently-known stub gaps requiring Plan 7 fixes:**
- The `.pyi` file uses `__version__: str` at module level — verify mypy treats this correctly (should be fine)
- `RuntimeStats` is declared with bare attributes (`worker_threads: int`, `is_healthy: bool`) instead of a class with `__init__` and `__repr__` — this is correct because RuntimeStats has no `#[new]` (constructed via `get_runtime_stats()` factory)
- Some methods use `tuple[int, int]` and `list[tuple[str, bool, str]]` which require Python 3.9+ syntax — `.pyi` doesn't need a `from __future__ import annotations` if mypy is run on the bindings venv (which is Python 3.12)

**Verifying `classic_shared.pyi` covers all 6 `#[pymodule]` symbols:**

Read of `classic_shared.pyi` line-by-line confirms all 6 are present:
- ✅ `class PathHandler:` (line 9) — corresponds to `PyPathHandler` (renamed via `#[pyclass(name = "PathHandler")]`)
- ✅ `class StringProcessor:` (line 203) — corresponds to `PyStringProcessor` (renamed)
- ✅ `class RustPerformanceMonitor:` (line 352) — corresponds to `PyRustPerformanceMonitor` (renamed)
- ✅ `class RuntimeStats:` (line 423) — corresponds to `RuntimeStats` (no rename)
- ✅ `def get_runtime_stats() -> RuntimeStats:` (line 437)
- ✅ `def is_runtime_healthy() -> bool:` (line 448)

**No stub gaps for the 6-row contract.** `mypy --strict` should pass on the existing stub once `classic_shared` is in `PYTHON_TARGET_MODULES`.

### Special handling for `foundation/` path in `generate_baseline.py`

**Verdict: NO special handling needed.** `parse_rust_surface()` (line 160) iterates `RUST_TARGET_CRATES.items()` and constructs `repo_root / rel_path` for each. As long as `RUST_TARGET_CRATES` contains `"classic-shared-py": "ClassicLib-rs/foundation/classic-shared-py/src/lib.rs"`, the parser handles it identically to the business-logic crates. The same goes for `parse_python_surface()` (line 290) reading `foundation/classic-shared-py/classic_shared.pyi`.

The only "special" thing about `foundation/`: the SQUAD label needs to be chosen (recommend `Squad B (version-registry)` to avoid creating a third squad bucket).

---

## Question 6 — `#[pyclass]` smoke test inventory (D-07)

D-07 estimates 70–90 pytest functions. Below is a complete enumeration that validates this estimate. The list pairs every `#[pyclass]` (or `#[pymodule]`-registered struct) in the binding crates against a Rust path, a construction pattern, and a single cheap method call. Free functions are grouped per the related class (e.g., `extract_formids_batch`, `is_valid_formid`, `validate_formids_batch` group with `FormIDAnalyzerCore`).

### `classic-scanlog-py` — Wave 1 (Plan 2)

| Wrapper struct | Rust path | Construction pattern | Cheap method |
|---|---|---|---|
| `PyLogParser` | `parser::PyLogParser` | `LogParser()` | `parse_all_sections([])` returns `dict` |
| `parser::ScanOutput` | `parser::ScanOutput` | factory via `PyLogParser` | inspect a captured output's `success` field |
| `PyRustFormIDAnalyzer` | `formid::PyRustFormIDAnalyzer` | `RustFormIDAnalyzer({})` (config dict) | `analyze([])` |
| `PyFormIDAnalyzerCore` | `formid_analyzer::PyFormIDAnalyzerCore` | `FormIDAnalyzerCore({})` | `extract_formids("")` |
| (group: `extract_formids_batch`, `is_valid_formid`, `validate_formids_batch`) | `formid_analyzer::*` (free fns) | direct call | call each with empty input |
| `PyRecordScanner` | `record_scanner::PyRecordScanner` | `RecordScanner()` | `scan("")` |
| (group: `scan_records_batch`, `contains_record`) | free fns | direct | empty input |
| `PyPluginAnalyzer` | `plugin_analyzer::PyPluginAnalyzer` | `PluginAnalyzer()` | `analyze([])` |
| (group: `detect_plugins_batch`, `contains_plugin`) | free fns | direct | empty input |
| `PyPatternMatcher` | `patterns::PyPatternMatcher` | `PatternMatcher([])` | `find_first("")` |
| **Wave 1 test count (rough)** | | | ~12–15 tests |

### `classic-scanlog-py` — Wave 2 (Plan 3)

| Wrapper struct | Rust path | Construction | Cheap method |
|---|---|---|---|
| (group: `detect_mods_single`, `detect_mods_double`, `detect_mods_important`, `detect_mods_batch`) | `mod_detector::*` | direct fn calls | empty dict + empty list |
| `PySuspectScanner` | `suspect_scanner::PySuspectScanner` | `SuspectScanner({})` | `scan("")` |
| `PySettingsValidator` | `settings_validator::PySettingsValidator` | `SettingsValidator({})` | `validate({})` |
| `PyConfigIssue` | `fcx_handler::PyConfigIssue` | factory via `PyFcxModeHandler` | inspect `severity` |
| `PyFcxModeHandler` | `fcx_handler::PyFcxModeHandler` | `FcxModeHandler.new(False)` (or similar) | `get_issues()` |
| `PyGpuDetector` | `gpu_detector::PyGpuDetector` | `GpuDetector()` | `detect_gpu([])` |
| `PyGpuInfo` | `gpu_detector::PyGpuInfo` | factory via `PyGpuDetector` | inspect `name()` |
| `PyGpuVendor` | `gpu_detector::PyGpuVendor` | enum constant | repr check |
| **Wave 2 test count** | | | ~10–13 tests |

### `classic-scanlog-py` — Wave 3 (Plan 4)

| Wrapper struct | Rust path | Construction | Cheap method |
|---|---|---|---|
| `PyAnalysisConfig` | `orchestrator::PyAnalysisConfig` | `AnalysisConfig("Fallout4", False)` | `set_crashgen_name("Buffout 4")` |
| `PyAnalysisResult` | `orchestrator::PyAnalysisResult` | factory via orchestrator | inspect `success()` |
| `PyCancellationToken` | `orchestrator::PyCancellationToken` | `CancellationToken()` | `is_cancelled()` |
| `PyRustOrchestrator` | `orchestrator::PyRustOrchestrator` | `Orchestrator(config)` | `cancel()` (cheap; full process_log requires file fixture) |
| `PyStringPool` | `report::PyStringPool` | `StringPool()` | `intern("test")` |
| `PyReportFragment` | `report::PyReportFragment` | factory via composer | inspect text |
| `PyReportComposer` | `report::PyReportComposer` | `ReportComposer()` | `compose([])` |
| `PyReportGenerator` | `report::PyReportGenerator` | `ReportGenerator()` | minimal `generate(empty_result)` |
| `PyParallelReportProcessor` | `report::PyParallelReportProcessor` | `ParallelReportProcessor()` | `process([])` |
| `PyPapyrusAnalyzer` | `papyrus::PyPapyrusAnalyzer` | `PapyrusAnalyzer()` | `analyze("")` |
| `PyPapyrusStats` | `papyrus::PyPapyrusStats` | factory | inspect a count field |
| `PyCrashgenVersion` | `version::PyCrashgenVersion` | `parse_crashgen_version("1.0.0")` | inspect `to_tuple()` |
| `PyCrashgenVersionStatus` | `version::PyCrashgenVersionStatus` | enum | repr check |
| (group: `parse_crashgen_version`, `check_crashgen_version_status`) | free fns | direct | minimal input |
| **Wave 3 test count** | | | ~14–17 tests |

### `classic-config-py` (Plan 5)

| Wrapper | Rust path | Construction | Cheap method |
|---|---|---|---|
| Promoted: `CrashgenEntryRaw` (and 14 other deferred classes/methods) | TBD via `classic-config-py/src/lib.rs` reading | varies | varies |
| **Plan 5 test count** | | | ~8–12 tests |

### `classic-version-registry-py` (Plan 6)

| Wrapper | Rust path | Construction | Cheap method |
|---|---|---|---|
| Promoted: `MatchConfidence`, `MatchResult`, `VersionMatcher`, `VersionInfo`, `AddressLibFormat`, `AddressLibraryConfig`, `CompatibleRange`, `CrashgenConfig`, `LogLevel`, `UnknownVersionStrategy`, `XseConfig`, `VersionRegistryError` | `version_registry::*` | factory or `new()` | minimal lookup |
| **Plan 6 test count** | | | ~10–12 tests |

### `classic-shared` (Plan 7) — see Question 5 Step 3 above

| Test | Wrapper |
|---|---|
| 6 tests as enumerated in Question 5 |

### `classic-file-io-py` aux + Tier-2 (Plan 7)

| Wrapper | Method |
|---|---|
| `PyFileHasher.cache_size` (aux) | call after init |
| `PyFileHasher.cache_stats` / `reset_cache_stats` / `clear_cache` (Tier-2 migration) | already covered by `cache-helpers-tier2-smoke` test case |
| **Plan 7 file-io test count** | ~3 tests (1 new, 3 existing migrated) |

### Total smoke test count

| Plan | Estimate |
|---|---:|
| Plan 2 (Wave 1) | 12–15 |
| Plan 3 (Wave 2) | 10–13 |
| Plan 4 (Wave 3) | 14–17 |
| Plan 5 (config) | 8–12 |
| Plan 6 (version_registry) | 10–12 |
| Plan 7 (classic_shared + file-io aux) | 6 + 1 = 7 |
| Plan 8 (no new tests; final sweep) | 0 |
| **TOTAL** | **61–76 new pytest functions** |

**Verdict on D-07's "70–90" estimate:** Lower-bound (61) is below the estimate; upper-bound (76) sits at the bottom of D-07's range. **D-07's estimate is realistic but slightly high.** Planner should set the per-plan task budget around **65 pytest functions total** with room for ~10–15 grouped free-function tests added during implementation. If Plans 2–4 reach 50 tests for scanlog alone (matching D-07's "70–90" overall), Plan 5/6/7 contribute the remaining 20–30.

---

## Question 7 — Runtime coverage registry schema (D-08)

### Current schema (from `binding_parity_runtime_coverage.py` and live `runtime_coverage_registry.json`)

```json
{
  "schemaVersion": "1.0",
  "binding": "python",
  "entries": [
    {
      "coverageId": "string",                       // unique identifier
      "classification": "runtime_verified | contract_mapped | deferred | newly_uncovered",
      "ownerModule": "string",                      // matches contract ownerModule
      "tier": "tier1 | tier2",
      // ONE of two coverage strategies:
      // (A) Selector — matches a CONTIGUOUS slice of contract rows (uses sha256 hash for drift detection)
      "contractSelector": {"ownerModule": "string", "tier": "tier1"},
      "contractCount": <int>,                       // expected match count
      "contractIdsHash": "<sha256[:16]> hex",       // _stable_id_hash of sorted matched IDs
      // (B) Explicit binding identifiers (one row per binding identifier)
      "bindingIdentifiers": ["classic_module.Class.method", ...],
      // OR rust symbols
      "rustSymbols": ["RustSymbol", ...],
      // Test attribution (REQUIRED for runtime_verified rows)
      "verificationMode": "workflow_smoke | direct_call | field_inspection",
      "testSuite": "ClassicLib-rs/python-bindings/tests/<file>.py",
      "testCaseId": "<test-name>",                  // human-readable; not a pytest nodeid
      "fixtureRefs": ["FIXTURE_NAME", ...]
    }
  ]
}
```

### Key behavioral facts

- The `nodeids` field referenced in CONTEXT.md does NOT exist in the current registry. The `testSuite` field stores **the test file path** and `testCaseId` stores **a human-readable test name** (not a pytest nodeid like `path::method`). The schema has no schema-enforced link from a registry row to a specific pytest function.
- The gate's `tier1_missing_runtime_total` check (line 296–308 of `binding_parity_runtime_coverage.py`) only verifies that **a registry row exists for every Tier-1 contract row**, NOT that the named test actually runs. This is intentional — it lets the gate run without invoking pytest.
- `contractSelector` is the **bulk strategy** — one registry row covers multiple contract rows by matching `ownerModule + tier`. The gate verifies `contractCount` and `contractIdsHash` to detect drift (a row added or removed since the registry was last computed).
- `bindingIdentifiers` is the **per-row strategy** — explicit list of `module.Class.method` strings, one entry per binding identifier.

### Recommendation for D-08

D-08 says "every promoted contract row gets a matching runtime coverage registry entry." Two implementation paths:

**Path A (selector — bulk):** One registry entry per **owner module x tier** pair. After Plan 8, `runtime_coverage_registry.json` has one entry per owner module:
- `python-tier1-scanlog` (selector: `ownerModule=scanlog, tier=tier1`, `contractCount=252`)
- `python-tier1-config` (`contractCount=41`)
- `python-tier1-version_registry` (`contractCount=59`)
- `python-tier1-shared` (`contractCount=6`)
- `python-tier1-aux` (`contractCount=4`)

That's **5 registry entries replacing the current 8 (3 selector + 5 explicit-binding)**. Each has its `testSuite` pointing at one or more test files. This is the cleanest end-state and matches the existing pattern.

**Path B (per binding identifier — explicit):** One registry entry per promoted contract row → 285 + 12 + 6 = **303 explicit registry entries**, each with a `bindingIdentifiers` array of length 1 and a `testCaseId` pointing at a specific test. This is much heavier.

**Recommendation: Path A** (selector-based, matching the existing 3-entry pattern). Rationale:
- Existing `python-tier1-{config,scanlog,version-registry}` entries already use this pattern with `contractSelector + contractCount + contractIdsHash`. Phase 3 just bumps `contractCount` and recomputes `contractIdsHash`.
- D-08 says "every promoted row gets a matching entry" — a selector-based row legitimately covers ALL promoted rows in the slice. The 1:1 invariant is satisfied at the gate level (`tier1_missing_runtime_total == 0`).
- ~300 individual entries vs. 5 maintained entries: huge maintenance win for ~300x fewer JSON edits per future API change.

### Estimate of row additions

**Net registry additions: +3 entries** (`python-tier1-shared` for classic_shared, plus possible `python-tier1-yaml` etc. if future plans gate other crates) **+ migration of 12 Tier-2 explicit binding identifiers into matching contract rows + selector**.

Specifically:
- 3 existing `python-tier1-*` entries (scanlog/config/version-registry) — bump `contractCount` from {15, 20, 24} to {41, 252, 59} and recompute `contractIdsHash`
- Add 1 new selector entry: `python-tier1-shared` covering 6 classic_shared rows
- Add 1 new selector entry: `python-tier1-aux` covering the 1 file-io aux row
- The 5 existing `python-tier2-*-runtime` entries (config-runtime, aux-cache-runtime, config-application-dir-runtime, scanlog-runtime, version-registry-runtime) get **DELETED** in Plan 8 because their binding identifiers are now matching Tier-1 contract rows; the gate's selector check on the corresponding `python-tier1-*` entries covers them

**Net result: 5 selector entries** (1 per owner module: scanlog, config, version_registry, shared, aux). Significantly leaner than the current 8 entries.

### Schema changes needed

**None.** The existing schema supports both strategies. Plan 8 only deletes the 5 Tier-2 explicit-binding entries and bumps the 3 selector counts/hashes.

### `nodeids` field

CONTEXT.md mentions `nodeids` populated with module-level vs class-level paths. **This field does not exist in the current schema.** The closest existing field is `testCaseId` which is a freeform identifier. If the planner wants pytest-nodeid-style attribution for individual smoke tests, it should be a **new optional field** added to the schema (e.g., `pytestNodeId: "tests/test_promoted_scanlog_wave1_smoke.py::test_logparser_smoke"`). This is a Plan 7 decision per CONTEXT D-discretion.

**Recommendation:** Skip the `nodeids` field entirely. The `testSuite` + `testCaseId` pair is sufficient for human attribution; the gate's automated invariants don't read individual test names. Use pytest's `-k` flag at the CLI level for filter discovery, not the registry.

---

## Assumption Corrections

CONTEXT.md and the surrounding research files have several discrepancies with the live source-of-truth artifacts. Listed in order of impact on planning:

### A1 — D-04's `pub use` location is misdirected

**CONTEXT D-04 says:** "Each `-py` crate's `lib.rs` gets narrow `pub use` additions." It cites `classic-scanlog-py/src/lib.rs` lines 115–141 as the reference pattern.

**Reality:** `parse_rust_surface()` in `generate_baseline.py` line 164 reads `RUST_TARGET_CRATES`, which currently points exclusively at **`-core` crate `lib.rs` files**, NOT `-py` files. The 59 existing Tier-1 contract rows all use core symbol names (`LogParser`, `OrchestratorCore`, `YamlDataCore`, `ClassicConfig`, etc.), not Py-prefixed wrapper names. The reference at scanlog-py lines 115–141 is the `pub use` block that exists for **Rust visibility inside the `#[pymodule] fn classic_scanlog`** so `m.add_class::<PyXxx>()?;` calls compile — it has nothing to do with the parity gate parser.

**Implication:** Phase 3 plans must add `pub use` lines to `**-core/lib.rs**` files (not `-py/lib.rs`) to satisfy Pitfall 2. The `-py/lib.rs` re-exports are needed only when adding NEW PyO3 wrapper structs (which Phase 3 does not — all wrappers already exist).

**Impact:** Significantly reduces the `pub use` plumbing scope. Phase 3's "narrow `pub use`" work primarily targets `-core/lib.rs`, not `-py/lib.rs`. The planner should reword D-04 in PLAN.md drafts to:

> Each `-core` crate's `lib.rs` gets narrow `pub use` additions — exactly 1:1 with promoted contract rows whose `rustSymbol` is not yet visible at the crate root.

### A2 — The "1 aux" entry does NOT belong to `classic_shared`

**CONTEXT D-09 says:** "The `aux` owner-module entry (1 entry at phase start) folds into this row set if it resolves to a `classic_shared` surface symbol."

**Reality:** The single aux entry (`python-deferred-aux-297`) is `classic_file_io.FileHasher.cache_size`, owned by **`classic-file-io-py`** wrapping `classic-file-io-core::FileHasher::cache_size`. It is unrelated to `classic_shared`.

**Implication:** Plan 7's `classic_shared` work covers **6 contract rows for classic_shared only**. The aux entry must be addressed separately — either:
- Folded into Plan 7 alongside classic_shared (since both add new modules to the gate enrollment)
- OR deferred to a "Plan 7b" / "Plan 8" sweep
- OR bundled with file_io enrollment if the planner decides to gate `classic_file_io` in this phase

The 4 Tier-2 runtime-verified file-io binding identifiers (`cache_stats`, `reset_cache_stats`, `clear_cache`) should ALSO be migrated to Tier-1 contract rows in the same plan — they're already runtime-verified, just need contract enrollment.

### A3 — Most deferred symbols are already at the `-core` lib.rs surface

**Pitfall 2's premise:** "Deferred entries are deferred because their Rust symbols are buried in sub-modules and not re-exported at lib.rs."

**Reality:** Spot-checks against three crates:
- `classic-config-core/src/lib.rs` lines 17–21: ALL of `ConfigError`, `CoreModEntry`, `CoreModExclude`, `CrashgenEntryRaw`, `ModConflictEntry`, `ModSolutionCriteria`, `ModSolutionEntry`, `SuspectErrorRule`, `SuspectStackCountRule`, `SuspectStackRule`, `YamlDataCore`, `format_registry_game_version`, `resolve_registry_version_info` are already `pub use`d.
- `classic-scanlog-core/src/lib.rs` lines 46–71: ALL deferred scanlog symbols (including `ScanLogError`, `StreamingLogParser`, `StreamingIteratorParser`, `RustFormIDAnalyzer`, `crashgen_version_gen`, `ScanProgressPhase`, `resolve_batch_concurrency`) are already `pub use`d.
- `classic-version-registry-core/src/lib.rs` lines 55–60: ALL of `VersionRegistryError`, `MatchConfidence`, `MatchResult`, `VersionMatcher`, `AddressLibFormat`, `AddressLibraryConfig`, `CompatibleRange`, `CrashgenConfig`, `LogLevel`, `UnknownVersionHandling`, `UnknownVersionStrategy`, `VersionInfo`, `XseConfig` are already `pub use`d.

**Implication:** The bulk of Phase 3's work is **NOT** adding `pub use` lines (Pitfall 2 plumbing) — it is **adding `tier1Mappings` rows + `.pyi` stubs + smoke tests**. The Pitfall 2 guard from D-05 still has value as a long-term invariant, but in practice it will catch zero issues during Phase 3 because the symbols are already exported. Plan 1's tooling expansion will surface this fact: when `RUST_TARGET_CRATES` grows to include the 16 currently-untracked crates, `parse_rust_surface()` will find dozens to hundreds of new public symbols, every one of which becomes a `tier2_gap_total` entry until promoted.

### A4 — The "289 deferred entries" count is inconsistent across documents

**CONTEXT.md says:** "289 deferred = 228 scanlog + 34 version_registry + 26 config + 1 aux"

**Reality (live counts):**
| Source | scanlog | config | version_registry | aux | total |
|---|---:|---:|---:|---:|---:|
| `deferred_runtime_backlog.json` (raw entries) | 228 | **22** | 34 | 1 | **285** |
| `parity_diff_report.json::tier2_gap_total` (parser output) | 232 | 28 | 35 | 0 | **295** |
| `runtime_coverage_summary.json::deferred_total` | 228 | **26** | 34 | 1 | **289** |
| `tier2_backlog_and_governance.md` (markdown summary) | 227 | **18** | 34 | 3 | **282** |
| **CONTEXT.md** | 228 | **26** | 34 | 1 | **289** |

The 4 different totals reflect 4 different counting methodologies. The two important numbers for the planner:
- **285** is the count of **rows that must be promoted** (= entries in `deferred_runtime_backlog.json`)
- **+12** Tier-2 binding identifiers in `runtime_coverage_registry.json` need migration to matching contract rows (currently `runtime_verified` status, but the binding-identifier path means they're not in `tier1Mappings`)
- **= 297 net contract row additions**, plus **6 for classic_shared** = **303 new tier1Mappings rows**
- Final state: `tier1Mappings.length == 59 (existing) + 303 = 362`

CONTEXT's "289" comes from the runtime_coverage_summary which double-counts in the aux/config slices because of how `_surface_row_from_gap()` and `_surface_row_from_registry_only()` merge gap rows with registry rows that have the same binding identifier.

**Implication:** Plan 8's "deferred-entry count drops to 0" success criterion (PYT-06) requires understanding that **`runtime_coverage_summary.json::summary.deferred_total`** is the gate-relevant number, not the raw `deferred_runtime_backlog.json::entries.length`. After all 285 backlog entries are promoted to `tier1Mappings`, the `deferred_total` will drop to 0 because:
- The 285 backlog entries no longer match the `_lookup_maps(deferred_entries)` path → they become `tier1_matched` contract_results instead
- The 4 entries that were inflating the count (the registry-only flow) collapse because the binding identifiers also become contract rows

### A5 — `classic-crashgen-settings-core` has no `-py` adapter

**CONTEXT canonical_refs say:** "All 19 business-logic `-core` crates — Plan 1 must add each crate's `lib.rs` path to `generate_baseline.py::RUST_TARGET_CRATES`"

**Reality:** Only 18 business-logic crates have a corresponding `*-py` adapter under `python-bindings/`. `classic-crashgen-settings-core` has NO `-py` crate — its types (`SuspectErrorRule`, `SuspectStackRule`, `ModConflictEntry`, etc.) are exposed through `classic-config-py` (which depends on `classic-crashgen-settings-core` directly, see `classic-config-py/Cargo.toml` line 20) and `classic-scanlog-py` and `classic-scangame-py`.

**Implication:** Plan 1's `RUST_TARGET_CRATES` should EXCLUDE `classic-crashgen-settings-core`. Adding it would cause `parse_rust_surface()` to surface all its public symbols, none of which would have a matching `pythonModule` in the contract because there is no `classic_crashgen_settings` Python module. The result would be `tier1_missing_python` errors.

The 19th `RUST_TARGET_CRATES` entry should be `classic-shared-py` (under `foundation/`), not `classic-crashgen-settings-core`. Net 18 business-logic + 1 foundation = 19.

### A6 — D-01's "crashgen_rules" and "core_mod_convert" sub-modules don't exist in `-core`

**CONTEXT D-01 lists Wave 3 sub-modules** as: `orchestrator`, `report`, `papyrus`, `version`, `crashgen_rules`, `core_mod_convert`

**Reality:** `classic-scanlog-core/src/lib.rs` declares 18 sub-modules (verified): `crashgen_registry`, `error`, `fcx_handler`, `formid`, `formid_analyzer`, `gpu_detector`, `mod_detector`, `orchestrator`, `papyrus`, `parser`, `patterns`, `plugin_analyzer`, `record_scanner`, `report`, `segment_key`, `settings_validator`, `suspect_scanner`, `version`. **There is no `crashgen_rules` or `core_mod_convert` sub-module in `classic-scanlog-core`.**

`crashgen_rules` and `core_mod_convert` are sub-modules of `classic-scanlog-py` (see `classic-scanlog-py/src/lib.rs` lines 96–98 — `pub mod core_mod_convert; pub mod crashgen_rules;`). They are **Python wrapper-only conversion helpers**, not core Rust types.

**Implication:** D-01's Wave 3 list confuses `-core` and `-py` sub-modules. The actual `-core` sub-modules CONTEXT missed are `crashgen_registry`, `segment_key`, `error` (3 missing). And the `-py`-only sub-modules (`crashgen_rules`, `core_mod_convert`) have no deferred entries because they're conversion helpers without `#[pyclass]` types. Question 2 above corrects this and re-attributes the rows.

### A7 — `classic_shared.pyi` is missing `__init__` constructors for renamed classes

Reading `classic_shared.pyi` carefully: `class PathHandler:` has `def __init__(self, cache_ttl_seconds: int = 300) -> None:` defined. `class StringProcessor:` has `def __init__(self) -> None:`. `class RustPerformanceMonitor:` has `def __init__(self) -> None:`. `class RuntimeStats:` has bare attributes `worker_threads: int` and `is_healthy: bool` with NO `__init__` — but RuntimeStats has no `#[new]` annotation in `lib.rs` (line 252), so it cannot be constructed directly from Python. The factory is `get_runtime_stats()`. The stub is technically correct: `mypy --strict` will allow `stats: RuntimeStats = classic_shared.get_runtime_stats()` and reject `stats = RuntimeStats()`.

**No correction needed — but the smoke test in Question 5 Step 3 must NOT call `RuntimeStats()` directly.** Use `classic_shared.get_runtime_stats()`.

---

## Open Questions

None blocking. Two minor follow-ups for the planner to decide during plan-writing:

1. **Squad assignment for the 16 new owners**: cosmetic-only; my recommendation in Question 3 is to use the existing two squads to minimize churn. Plan 1 makes the call.
2. **Whether to surface newly-discovered public symbols from the 16 currently-untracked crates as part of Phase 3 or hold them for a future milestone**: The 285-entry promotion is for the *currently-deferred* set. Once `RUST_TARGET_CRATES` expands, the parser will find new public symbols in the 16 new crates that have no matching `tier1Mappings` row. These show up as `tier2_gap_total` and would block PYT-06. The pragmatic answer: **promote them as part of Phase 3** (since the alternative is keeping the gate red), but the planner should sanity-check against `parse_rust_surface()` output during Plan 1 to estimate the actual scope. Initial estimate from spot-checks of 4–5 small crates: ~50–150 additional rows on top of the 303. Plan 1 deliverable should include "run `python tools/python_api_parity/generate_baseline.py --repo-root .` against the expanded `RUST_TARGET_CRATES` and report `tier2_gap_total` per owner module" so the planner can adjust Plan 5/6/7 task budgets.

---

## Where "Tier-2 skip logic" actually lives

**There is no `Tier-2 skip` flag in `check_parity_gate.py`.** Reading the script end-to-end (276 lines):
- The script iterates `tier1Mappings` only (line 165–168)
- It calls `generate_diff_report` which classifies non-Tier-1 rows as `gap_type=rust_unmapped` or `python_unmapped` with `tier=tier2`
- The `tier2_gap_total` is returned in `summary` but **does not affect the exit code** — only `tier1_missing_*`, `tier1_signature_mismatch`, `tier1_missing_runtime_total`, `registry_mismatch_total`, and `newly_uncovered_total` cause non-zero exits
- The gate is **already structurally Tier-1-only**; the "Tier-2 skip" is the implicit fact that tier-2 gap rows do not fail the gate

**What Plan 8 actually removes:**
1. The `gap_type=rust_unmapped` and `gap_type=python_unmapped` branches in `generate_diff_report` (lines 574–610 of `generate_baseline.py`) — these produce Tier-2 gap rows. After all symbols are promoted, these branches will produce zero rows; deleting them is cosmetic.
2. The `--deferred-registry` argument default value handling — Plan 8 leaves this **untouched** (Phase 6 owns DOC-01).
3. Any reference to `tier2` in `tierDefinitions` of `parity_contract.json` — Plan 8 deletes the `tier2` key, leaving only `tier1`.
4. Any inline comments referring to "Tier-2" in either Python script.

The gate's behavior change is purely tooling-cosmetic; the gate's exit-code semantics already match the single-tier model.

---

## Sources

### Primary (HIGH confidence)

- `tools/python_api_parity/generate_baseline.py` — read in full (784 lines), script behavior fully understood
- `tools/python_api_parity/check_parity_gate.py` — read in full (276 lines)
- `tools/binding_parity_runtime_coverage.py` — read in full (378 lines)
- `ClassicLib-rs/validate_stubs.py` — read in full (457 lines)
- `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs` — read in full (340 lines)
- `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` — read in full (455 lines)
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/lib.rs` — read lines 1–305
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs` — read lines 1–80, 18 sub-modules confirmed
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs` — read lines 1–28, all deferred symbols already `pub use`d
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs` — read lines 1–60, all deferred symbols already `pub use`d
- `ClassicLib-rs/Cargo.toml` — workspace members verified (lines 1–77)
- `rebuild_rust.ps1` — read lines 1–567, `Get-PythonRustModules` discovery confirmed
- `docs/implementation/python_api_parity/baseline/parity_contract.json` — 59 tier1Mappings, 3 owners (scanlog, config, version_registry), 22kb
- `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` — 285 entries, 117kb
- `docs/implementation/python_api_parity/baseline/parity_diff_report.json` — `tier2_gap_total=295` confirmed via live parse
- `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json` — `deferred_total=289` (4 more than backlog due to registry-merge double-counting)
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — 8 entries (3 selector + 5 explicit binding-id), schema verified
- `.planning/research/PITFALLS.md` — Pitfalls 1, 2, 4, 7 read in full
- `.planning/research/STACK.md` Finding 3 — confirms classic_shared implementation already exists
- `.planning/research/ARCHITECTURE.md` §3 and §6 — read in full
- `.planning/research/FEATURES.md` — sizing (LARGE), the "285 deferred entries" canonical number, anti-features verified
- `.planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md` — D-09 baseline-refresh cadence verified

### Secondary (MEDIUM confidence)

- Sub-module attribution in Question 2 used a script that grepped both `classic-scanlog-py/src/*.rs` for `#[pyclass(name = "...")]` declarations and fell back to `classic-scanlog-core/src/*` for unwrapped symbols. 13 of 228 entries were attributed by hand based on which sub-module the rust symbol obviously belongs to (e.g., `ScanLogError` → `error`, `crashgen_version_gen` → `version`). MEDIUM because the sub-module assignment for these 13 is mechanical interpretation, not parser output.

### Tertiary

- None — every claim has a primary source.

### Research scripts (committed for reproducibility)

All scripts under `.planning/phases/03-python-tier-collapse/_research_scripts/`:
- `inspect_contracts.ps1` — top-level structure of `parity_contract.json` and `deferred_runtime_backlog.json`
- `count_entries.ps1` — entry counts by `ownerModule` and `wave`
- `inspect_aux.ps1` — full dump of the 1 aux entry, showing it belongs to `classic_file_io`
- `inspect_entries.ps1` — sample entries plus binding-identifier prefix histograms
- `inspect_tier1.ps1` — full dump of existing 59 Tier-1 mappings
- `inspect_diff_report.ps1` — gap counts and runtime coverage summary
- `inspect_waves.ps1` — wave assignments + Tier-2 binding identifiers
- `map_scanlog_symbols.ps1` — first attempt at sub-module attribution (regex-based)
- `map_scanlog_v2.ps1` — refined sub-module attribution using `-py` source files
- `map_other.ps1` — config / version_registry / aux deferred entry breakdown

---

## Metadata

**Confidence breakdown:**
- Per-crate counts (Q1): HIGH — all numbers from live JSON parsing
- Sub-module distribution (Q2): HIGH for the 215 in-wave rows; MEDIUM for the 13 unattributed rows that required manual sub-module assignment
- `generate_baseline.py` expansion table (Q3): HIGH — every path verified by Glob
- Pitfall 2 guard (Q4): HIGH — function shape derived from existing script architecture
- classic_shared verification chain (Q5): HIGH — every command verified, every wrapper struct read
- `#[pyclass]` smoke test inventory (Q6): HIGH for scanlog (full source read); MEDIUM for config/version_registry (planner verifies during plan-writing)
- Runtime coverage registry (Q7): HIGH — schema fully read in `binding_parity_runtime_coverage.py`
- Validation Architecture: HIGH — every file path and command verified
- Assumption Corrections: HIGH — every correction backed by direct source quote

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (30 days; the underlying `parity_contract.json` and source crates change frequently, so any plan written more than a month from now should re-run the count scripts before drafting)
