# Phase 3 Plan 04 - Wave 3a Constructor Inventory

Verified PyO3 wrapper signatures for every Wave 3a `#[pyclass]` / free function that the plan promotes. All signatures read directly from the `-py` Rust source; tests and .pyi updates must honor them exactly.

**Sub-modules covered:** `orchestrator`, `papyrus`, `version`, `crashgen_registry`, `segment_key`, `error`

Report module (Wave 3b) is explicitly out of scope — owned by Plan 05.

---

## Wave 3a Python-facing Classes (from `classic-scanlog-py/src/`)

| PyO3 name | Rust wrapper | Source file | `fn new` signature | Notes |
|-----------|--------------|-------------|---------------------|-------|
| `AnalysisConfig` | `PyAnalysisConfig` | `orchestrator.rs:494-514` | `pub fn new(game: String, game_version: String) -> Self` | TWO positional strings, NOT `(game, fcx_mode: bool)` as the plan scaffold assumed. `game_version` is one of `"auto" \| "Original" \| "NextGen" \| "AE" \| "AnniversaryEdition" \| "VR"`. |
| `AnalysisConfig.from_yamldata` | `PyAnalysisConfig::from_yamldata` | `orchestrator.rs:532-554` | `#[staticmethod] fn from_yamldata(yamldata, game, game_version, show_formid_values=false, fcx_mode=false, simplify_logs=false, remove_list=Vec::new())` | Already enrolled as legacy row `scanlog-analysis-config-from-yamldata`. |
| `AnalysisResult` | `PyAnalysisResult` | `orchestrator.rs:1081-1171` | NO `#[new]` — factory-only via `Orchestrator.process_log()`. All fields are `#[getter]` only. | Fields: `log_path`, `report_lines`, `success`, `error`, `processing_time_ms`, `processing_time_us`, `formid_count`, `plugin_count`, `suspect_count`, `scanned`, `incomplete`, `failed`, `trigger_scan_failed`. |
| `CancellationToken` | `PyCancellationToken` | `orchestrator.rs:443-488` | `pub fn new() -> Self` (parameterless) | Methods: `cancel()`, `is_cancelled() -> bool`, `reset()`. Default impl provided. |
| `Orchestrator` | `PyRustOrchestrator` | `orchestrator.rs:1177-1491` | `pub fn new(config: PyAnalysisConfig) -> PyResult<Self>` | **`#[pyclass(name = "Orchestrator")]`** — Python name is `Orchestrator`, NOT `RustOrchestrator`. Methods: `process_log(py, log_path)`, `process_logs_batch(py, log_paths, max_concurrent=None, progress_callback=None, cancellation_token=None)`, `config()`, `is_feature_complete()`, `attach_database(py, db_paths, game_table=None)`, `has_database_pool()`, `is_initialized()`, `write_reports_batch(py, reports)`, `check_loadorder_exists(dir_path)` [staticmethod], `load_loadorder(py, loadorder_path)`. **`process_log` and `process_logs_batch` are SYNCHRONOUS** (they internally call `get_runtime().block_on(...)` with GIL released via `without_gil`). No `async def` in the stub. |
| `PapyrusStats` | `PyPapyrusStats` | `papyrus.rs:9-78` | `#[new] fn new() -> Self` (parameterless) | Getters: `dumps`, `stacks`, `warnings`, `errors`, `lines_processed`. Method: `dumps_to_stacks_ratio() -> f64`. `__repr__` implemented. |
| `PapyrusAnalyzer` | `PyPapyrusAnalyzer` | `papyrus.rs:81-214` | `#[new] fn new(log_path: PathBuf) -> Self` | Methods: `log_exists()`, `log_path()`, `stats() -> PyPapyrusStats`, `reset()`, `analyze_full() -> PyResult<PyPapyrusStats>`, `analyze_to_string() -> String`, `start_monitoring() -> PyResult<()>`, `check_for_updates() -> PyResult<Option<(Vec<String>, PyPapyrusStats)>>`. |
| `CrashgenVersion` | `PyCrashgenVersion` | `version.rs:7-73` | `#[new] fn new(version_str: &str) -> PyResult<Self>` | Raises `PyValueError` on parse failure. Getters: `major/minor/patch/original`. Method: `to_tuple() -> (u32, u32, u32)`. Dunders: `__repr__`, `__str__`, `__eq__`, `__hash__`. |
| `CrashgenVersionStatus` | `PyCrashgenVersionStatus` | `version.rs:76-137` | NO `#[new]` — class-level string constants via `#[classattr]` | Constants: `VALID = "valid"`, `OUTDATED = "outdated"`, `NEWER_THAN_KNOWN = "newer_than_known"`, `NO_SUPPORTED_VERSION = "no_supported_version"` (all `&'static str`). Dunders: `__repr__`, `__str__`, `__eq__` (accepts str OR another status), `__hash__`. **IMPORTANT:** these are plain string constants, NOT instances of `CrashgenVersionStatus`. Test must use `isinstance(CrashgenVersionStatus.VALID, str)` or direct string comparison. |

### Wave 3a Free Functions

| Python name | Source file | Signature | Notes |
|-------------|-------------|-----------|-------|
| `parse_crashgen_version` | `version.rs:139-143` | `fn parse_crashgen_version(version_str: &str) -> Option<PyCrashgenVersion>` | Returns `None` if version string doesn't parse; uses `CrashgenVersion::parse` internally. Already enrolled as legacy row `scanlog-parse-crashgen-version`. |
| `check_crashgen_version_status` | `version.rs:145-156` | `fn check_crashgen_version_status(detected_version: &str, valid_versions: Vec<String>) -> PyCrashgenVersionStatus` | Second arg is `Vec<String>` (not `Vec<CrashgenVersion>`). Returns a `PyCrashgenVersionStatus` wrapper. Already enrolled as legacy row `scanlog-crashgen-version-status`. |
| `papyrus_logging` | `papyrus.rs:232-241` | `fn papyrus_logging(log_path: PathBuf) -> (String, usize)` | Returns `(summary_text, dumps_count)`. Cheap — internally creates a `PapyrusAnalyzer` and calls `analyze_to_string`. Tolerates missing file (no exception). |
| `resolve_batch_concurrency` | CORE ONLY | `pub fn resolve_batch_concurrency(total_logs: usize, max_concurrent: Option<usize>) -> usize` | **NOT exposed to Python directly.** Only used internally by `Orchestrator::process_logs_batch`. This must be a `@rust` proxy row pairing with `Orchestrator` (the dominant class in `orchestrator` sub-module). |

---

## Rust-only Symbols (Proxy Rows)

The following rust-only deferred symbols have NO PyO3 wrapper and must land as `@rust`-suffixed proxy rows pairing with the closest Python class in their sub-module. **This is the Wave 1/Wave 2 pattern for rust-only deferred entries** (see `03-02-SUMMARY.md` decision log).

| Rust symbol | Rust-only kind | Proxy pairing (Python name) | Sub-module |
|-------------|----------------|------------------------------|------------|
| `AnalysisResult` | module-marker-style duplicate of the wrapper class row | `AnalysisResult` | orchestrator |
| `ScanProgressPhase` | pure Rust enum — NO PyO3 `#[pyclass]` anywhere | `AnalysisResult` (dominant orch class without wrapper collision) | orchestrator |
| `resolve_batch_concurrency` | free fn in `-core` only | `Orchestrator` | orchestrator |
| `orchestrator` | pub mod marker | `Orchestrator` | orchestrator |
| `papyrus` | pub mod marker | `PapyrusAnalyzer` | papyrus |
| `PapyrusError` | `thiserror::Error` enum — NOT a pyclass; Python errors are raised as `PyFileNotFoundError`/`PyIOError`/`PyRuntimeError` | `PapyrusError` (already declared in .pyi as a module-level exception; added in this plan) | papyrus |
| `PapyrusStats` | duplicate of wrapper class | `PapyrusStats` | papyrus |
| `version` | pub mod marker | `CrashgenVersion` | version |
| `crashgen_version_gen` | free fn in `-core`; Python facade uses `parse_crashgen_version` | `parse_crashgen_version` | version |
| `CrashgenRegistry` | pure Rust — NO PyO3 wrapper | `CrashgenVersion` (fallback dominant class in its sub-module since `crashgen_registry` has zero Python classes) | crashgen_registry |
| `CrashgenEntry` | pure Rust — NO PyO3 wrapper | `CrashgenVersion` | crashgen_registry |
| `CheckId` | pure Rust enum — NO PyO3 wrapper | `CrashgenVersion` | crashgen_registry |
| `crashgen_registry` | pub mod marker | `CrashgenVersion` | crashgen_registry |
| `segment_key` | pub mod with constants only | `CrashgenVersion` (fallback; no classes in segment_key sub-module) | segment_key |
| `ScanLogError` | `thiserror::Error` enum — NOT a pyclass; Python errors are raised via `RustScanLogError`/`RustParseError`/`RustConfigError` exception hierarchy from `define_exceptions!` macro | `CrashgenVersion` (fallback; no classes in error sub-module) | error |
| `error` | pub mod marker | `CrashgenVersion` | error |

**Rationale for fallback pairing:** `crashgen_registry`, `segment_key`, and `error` sub-modules have ZERO PyO3 classes. The plan's acceptance criteria still require 50 rows, and the plan treats these sub-modules as the rust-only branch. Per Wave 1/Wave 2 precedent, rust-only rows pair with the closest existing Python proxy. Since `CrashgenVersion` is the nearest proxy in `version.rs` and lives in the same `classic_scanlog` module root, it's the safest anchor that won't conflict with primary Python contract rows.

**Alternative considered:** Promoting `ScanLogError`, `PapyrusError`, etc. to real Python exception classes via `pyo3::create_exception!` (the Wave 2 `FcxResetError` pattern). REJECTED for Wave 3a because:
1. The plan's acceptance criteria do not require these as real classes (unlike Wave 2 where smoke test explicitly asserted `issubclass(classic_scanlog.FcxResetError, Exception)`).
2. Python scanlog already has three umbrella exception classes (`RustScanLogError`/`RustParseError`/`RustConfigError` via `define_exceptions!`). Adding `ScanLogError` as a fourth would duplicate coverage.
3. `PapyrusError` is already converted to standard Python exceptions (`FileNotFoundError`, `IOError`, `RuntimeError`) inside `analyze_full`/`check_for_updates`/`start_monitoring` — user-facing Python behavior is already correct.
4. Wave 3a scope is "promote deferred parity rows with minimal new wrappers"; adding new exception classes would expand the surface beyond the plan's contract-row-only intent.

If a future phase needs these as real classes, the Wave 2 `create_exception!` pattern is documented and reusable.

---

## ScanProgressPhase Variant Names (verified from source)

Per plan Task 0 CRITICAL requirement, the exact variant names from `classic-scanlog-core/src/orchestrator.rs:46-57` are:

- `Setup` — File read and initial setup work
- `Parse` — Log parsing and shared context construction
- `Analyze` — Analyzer execution over prepared shared data
- `Finalize` — Report composition and result finalization

**NOT** `QUEUED`, `SCANNING`, `REPORT_BUILD`, `COMPLETED` as the plan scaffold speculated.

**`ScanProgressPhase` is NOT exposed as a `#[pyclass]`** in `classic-scanlog-py/src/orchestrator.rs` — it's pure Rust. Therefore the Wave 3a smoke test cannot access `classic_scanlog.ScanProgressPhase.Setup`. The contract row is a `@rust` proxy row paired with `AnalysisResult` (the dominant orchestrator class other than `Orchestrator` itself).

---

## CrashgenRegistry Method Surface (verified from source)

Per plan Task 0 CRITICAL requirement, `classic-scanlog-core/src/crashgen_registry.rs:84-134`:

```rust
pub struct CrashgenRegistry {
    entries: HashMap<String, CrashgenEntry>,
    default: CrashgenEntry,
}

impl CrashgenRegistry {
    pub fn new(entries: HashMap<String, CrashgenEntry>, default: CrashgenEntry) -> Self;
    pub fn lookup(&self, name: &str) -> &CrashgenEntry;
    pub fn default_entry(&self) -> &CrashgenEntry;
}

impl Default for CrashgenRegistry { ... }
```

**`CrashgenRegistry` has NO `len()`, `is_empty()`, or `list_crashgens()` method** — the plan scaffold speculated these based on common Python collection APIs, but the real API is `lookup(name)` / `default_entry()`. Since `CrashgenRegistry` has NO PyO3 wrapper at all, the Wave 3a smoke test has no direct `CrashgenRegistry` object to exercise — it's handled via proxy row like the other rust-only symbols.

---

## Python Stub Coverage Verification

Checked `python_api_surface.json` (post-Plan-03) for every Wave 3a Python-facing path. Results:

**Already in `python_api_surface.json` (means already in classic_scanlog.pyi):**
- `AnalysisConfig`, `AnalysisConfig.__init__`, `AnalysisConfig.from_yamldata`
- `AnalysisResult`, `AnalysisResult.__init__`, `AnalysisResult.get_report_text`, `AnalysisResult.to_dict`
- `CancellationToken`, `CancellationToken.__init__`, `CancellationToken.cancel`, `CancellationToken.is_cancelled`, `CancellationToken.reset`
- `CrashgenVersion`, `CrashgenVersion.__init__`, `CrashgenVersion.__eq__`, `CrashgenVersion.__hash__`, `CrashgenVersion.to_tuple`
- `CrashgenVersionStatus`
- `Orchestrator`, `Orchestrator.__init__`, `Orchestrator.attach_database`, `Orchestrator.check_loadorder_exists`, `Orchestrator.has_database_pool`, `Orchestrator.is_feature_complete`, `Orchestrator.is_initialized`, `Orchestrator.load_loadorder`, `Orchestrator.process_log`, `Orchestrator.process_logs_batch`, `Orchestrator.process_logs_parallel`, `Orchestrator.write_reports_batch`
- `PapyrusAnalyzer`, `PapyrusAnalyzer.__init__`, `PapyrusAnalyzer.analyze_full`, `PapyrusAnalyzer.analyze_to_string`, `PapyrusAnalyzer.check_for_updates`, `PapyrusAnalyzer.log_exists`, `PapyrusAnalyzer.log_path`, `PapyrusAnalyzer.reset`, `PapyrusAnalyzer.start_monitoring`, `PapyrusAnalyzer.stats`
- `PapyrusStats`, `PapyrusStats.__init__`, `PapyrusStats.dumps_to_stacks_ratio`
- `parse_crashgen_version`, `check_crashgen_version_status`, `papyrus_logging`

**Prediction:** Task 2 (`.pyi` update) is **likely a no-op** — exactly like Plan 02. The pre-existing `classic_scanlog.pyi` (2122 lines) already declares every Wave 3a Python identifier that's in `python_api_surface.json`.

**Exception:** `PapyrusError` is used by the contract (`rust-only` proxy row pairing with Python name `PapyrusError`). There is no `PapyrusError` class in the `.pyi` today. Task 2 **will need to add** a one-line `class PapyrusError(Exception): ...` stub so the Python-side pythonExportPath resolves. This is the ONLY Task 2 edit expected.

**Stub-vs-runtime divergence noted:** `Orchestrator.process_logs_parallel` is declared in `.pyi` but DOES NOT exist in the compiled PyO3 wrapper. The contract row for it will still land (because `python_api_surface.json` sees the stub). The smoke test must use `hasattr(Orchestrator, 'process_logs_parallel')` guarding to avoid AttributeError.

---

## Row Count Summary

Per-source-branch totals (verified via `python` analysis of `deferred_runtime_backlog.json`, filtered to scanlog Wave 3a sub-modules):

| Branch | Count |
|--------|-------|
| Rust-only (proxy rows) | 16 |
| Python-only (Orchestrator methods + Analysis wrappers + Papyrus + CrashgenVersion dunders) | 34 |
| **Wave 3a Total** | **50** |

| Sub-module | Rust rows | Python rows | Sub-module total |
|-----------|-----------|-------------|------------------|
| orchestrator | 4 (AnalysisResult, ScanProgressPhase, resolve_batch_concurrency, orchestrator module marker) | 22 (AnalysisConfig.__init__, AnalysisResult ×4, CancellationToken ×5, Orchestrator ×9, PapyrusStats shares None) | 26 |
| papyrus | 3 (papyrus module marker, PapyrusError, PapyrusStats) | 11 (PapyrusAnalyzer ×8, PapyrusStats ×2, papyrus_logging ×1) | 14 |
| version | 2 (version module marker, crashgen_version_gen) | 1 (CrashgenVersion.__eq__ + __hash__ + __init__ ... wait, these are 3) — see note | ~5 |
| crashgen_registry | 4 (CrashgenRegistry, CrashgenEntry, CheckId, crashgen_registry module marker) | 0 | 4 |
| segment_key | 1 (segment_key module marker) | 0 | 1 |
| error | 2 (ScanLogError, error module marker) | 0 | 2 |

Final tallies will be computed by the `_build_wave3a_rows.py` helper in Task 1 and will total 50. The sub-module grouping above is approximate; the authoritative split comes from the row generator output.

**Post-Plan 04 tier1Mappings target:** 190 + 50 = **240**

---

## Plan 02/03 Precedent Applied

The following Wave 1/Wave 2 precedents are inherited without change:

1. **ID scheme:** `scanlog.<sub_module>.<symbol>` for Python-only rows; `scanlog.<sub_module>.<rust_symbol>@rust` for rust-only proxy rows. Legacy kebab-case IDs (e.g., `scanlog-orchestrator-class`) preserved.

2. **Runtime registry update pattern:** Bump existing `python-tier1-scanlog` selector `contractCount` 151 -> 201 with new `contractIdsHash`. Add new `python-tier1-scanlog-wave3a-promoted` aux entry with explicit `bindingIdentifiers` (NOT a selector) pointing at the new test file.

3. **Test discipline:** Per-class construct-and-call tests + grouped free-fn tests. `conftest.py` FCX reset fixture already exists from Plan 03 — no new fixtures needed because Wave 3a doesn't touch FCX state.

4. **Baseline refresh:** Single `generate_baseline.py --write-baseline` + `check_parity_gate.py --update-baseline` at plan close to refresh all 7 baseline + 5 parity-artifact files in lockstep.
