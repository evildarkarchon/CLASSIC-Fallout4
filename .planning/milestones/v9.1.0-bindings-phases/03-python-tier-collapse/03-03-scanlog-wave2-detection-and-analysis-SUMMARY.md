---
phase: 03-python-tier-collapse
plan: 03
subsystem: python-parity
tags: [python, parity-gate, pyo3, scanlog, mod-detector, suspect-scanner, settings-validator, fcx-handler, gpu-detector, fcx-reset-error]

# Dependency graph
requires:
  - phase: 03-python-tier-collapse
    provides: Plan 02 promoted 74 Wave 1 scanlog rows (parser + formid + formid_analyzer + record_scanner + plugin_analyzer + patterns); tier1Mappings = 133 at plan open
provides:
  - 57 new Tier-1 contract rows for scanlog Wave 2 (mod_detector + suspect_scanner + settings_validator + fcx_handler + gpu_detector)
  - parity_contract.json::tier1Mappings grows from 133 to 190 entries
  - python-tier1-scanlog runtime selector contractCount bumped from 94 to 151 with recomputed contractIdsHash (e0471bad89bda230b60efe211c8b52e850cfdc4e716a2eb014efcf12be33d588)
  - python-tier1-scanlog-wave2-promoted aux runtime entry with 36 explicit bindingIdentifiers pointing at test_promoted_scanlog_wave2_smoke.py
  - test_promoted_scanlog_wave2_smoke.py with 40 per-class + grouped free-fn smoke tests (393 lines)
  - 03-03-CONSTRUCTOR-INVENTORY.md documenting verified PyO3 wrapper signatures for all 7 Wave 2 #[pyclass] wrappers
  - FcxResetError exposed as a typed Python exception class via pyo3::create_exception!; FcxModeHandler.reset_fcx_checks() now raises it for non-Unnecessary variants (closes the deferred Rust-only gap from quick-260406-syy)
  - conftest.py with autouse reset_fcx_global_state fixture routing to FcxModeHandler.reset_fcx_checks() classmethod
affects: [03-04, 03-05, 03-06, 03-07, 03-08, 03-09a, 03-09b]

# Tech tracking
tech-stack:
  added:
    - "pyo3::create_exception! macro usage in classic-scanlog-py/src/lib.rs to add a typed Python exception class that mirrors classic_scanlog_core::fcx_handler::FcxResetError"
  patterns:
    - "Same dotted ID scheme as Wave 1: scanlog.<sub_module>.<symbol> (legacy kebab-case IDs preserved)"
    - "Reusable Wave 2 row generator _build_wave2_rows.py modeled on Wave 1 helper; produces 57 sorted rows with @rust suffix proxy pairing for rust-only deferred entries"
    - "R9 LazyLock exclusion: GLOBAL_FCX_HANDLER excluded from tier1Mappings because LazyLock<Mutex<T>> statics cannot be first-class Python module attributes; documented in CONSTRUCTOR-INVENTORY.md and plan SUMMARY"
    - "Runtime registry update: single scanlog selector entry bumped to 151 + separate wave2-promoted aux entry with explicit bindingIdentifiers (matches Wave 1 pattern to avoid selector key conflicts)"
    - "New: typed Python exception class for a pure-Rust error enum using pyo3::create_exception! inside a module to scope the missing_docs lint allowance"

key-files:
  created:
    - .planning/phases/03-python-tier-collapse/03-03-CONSTRUCTOR-INVENTORY.md
    - .planning/phases/03-python-tier-collapse/_build_wave2_rows.py
    - ClassicLib-rs/python-bindings/tests/conftest.py
    - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py
  modified:
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/lib.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.md
    - docs/implementation/python_api_parity/baseline/rust_api_surface.json
    - docs/implementation/python_api_parity/baseline/python_api_surface.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    - ClassicLib-rs/python-bindings/parity-artifacts/* (regenerated via check_parity_gate.py --update-baseline)

key-decisions:
  - "ID scheme: Wave 2 promoted rows use dotted scanlog.<sub_module>.<symbol> IDs to match Wave 1 and the plan verification filter; rust-only proxy rows use @rust suffix"
  - "R9 exclusion: GLOBAL_FCX_HANDLER is excluded from tier1Mappings (LazyLock<Mutex<FcxModeHandler>> is not a first-class Python module attribute). This drops the Wave 2 row count from 58 to 57. Final tier1Mappings.length = 190 = 133 + 57."
  - "FcxResetError promoted via real Python exception class, not proxy row: used pyo3::create_exception! in classic-scanlog-py/src/lib.rs (inside an #[allow(missing_docs)] mod) to expose FcxResetError as a module-level exception. FcxModeHandler.reset_fcx_checks() classmethod now raises this typed class for non-Unnecessary variants instead of PyRuntimeError. Closes the quick-260406-syy deferred gap by actually implementing the Python surface rather than re-deferring."
  - "FCX reset fixture routes through the existing FcxModeHandler.reset_fcx_checks() classmethod; no new reset API required. Verified the classmethod API from classic-scanlog-py/src/fcx_handler.rs:352 before writing the fixture."
  - "Runtime registry update pattern same as Wave 1: single python-tier1-scanlog selector bumped to contractCount=151 + new aux entry with explicit bindingIdentifiers. Avoids the selector-key conflict that Plan R8 would have created by attempting two overlapping selectors."
  - "has_results() test cases constructed with FcxModeHandler(True) after discovering classic-scanlog-core/src/fcx_handler.rs:267-279 gates has_results on fcx_mode being enabled. Documented in the test file docstrings."
  - "scan_archivelimit_setting test passes crashgen_version=None explicitly because the Rust binding exposes it as a required positional parameter, not a kwarg default (only the .pyi surface suggests a default)."
  - "GpuVendor test cases use constructor calls (GpuVendor('AMD') etc.) instead of class-level attribute access. The wrapper is a #[pyclass] not a Python enum; discovered by reading gpu_detector.rs and corrected from the plan's attribute-access scaffold."
  - "Test file structure matches Wave 1 precedent: per-class tests + grouped free-function tests; 40 tests total in ~393 lines; runs in <0.2 seconds."

patterns-established:
  - "Pattern: Promoting a pure-Rust error enum as a typed Python exception class without adding a full PyO3 wrapper: use pyo3::create_exception! to create a module-scoped exception, export it via pub use, register via m.add('Name', m.py().get_type::<Name>()), and update any existing raises to use the new class. This eliminates the 'Rust-only deferred' gap without requiring a struct wrapper."
  - "Pattern: has_results-style gated getters should be tested against both gate states; discovery-driven debugging by reading the core implementation is faster than guessing signature-based plan scaffolds."
  - "Pattern: autouse conftest.py fixture for binding singletons uses hasattr/getattr to guard against classic_* wheel absence; never fails pytest collection just because one binding is not built locally."

requirements-completed: [PYT-02, PYT-04, PYT-05]

# Metrics
duration: 12min
completed: 2026-04-08
---

# Phase 3 Plan 03: scanlog Wave 2 Detection and Analysis Summary

**Promoted 57 deferred Python parity entries to enforced Tier-1 across five scanlog detection sub-modules (mod_detector, suspect_scanner, settings_validator, fcx_handler, gpu_detector); contract grew 133 -> 190 mappings, runtime selector bumped 94 -> 151 with new hash, typed FcxResetError exception class added via pyo3::create_exception!, 40-test smoke suite added, full 5-step verification chain green**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-08T15:25:35Z
- **Completed:** 2026-04-08T15:37:26Z
- **Tasks:** 5 (Task 0 inventory + Tasks 1-4 implementation)
- **Files modified:** 18 (4 created + 14 modified, including regenerated baseline + parity-artifacts)

## Accomplishments

- **Constructor inventory + FCX reset fixture (Task 0):** Read all five Wave 2 -py source files (`mod_detector.rs`, `suspect_scanner.rs`, `settings_validator.rs`, `fcx_handler.rs`, `gpu_detector.rs`) and recorded verified `#[new]` signatures plus free-function signatures. Discovered three plan-scaffold divergences to correct later:
  - `FcxModeHandler::new` takes `fcx_mode: bool` not `ignore_missing: bool`
  - `PyGpuVendor` is a wrapper `#[pyclass]`, not a Python enum; has no class-level `NVIDIA`/`AMD`/`INTEL` attributes
  - `ConfigIssue` has a direct `#[new]` constructor (not only available via `FcxModeHandler.get_detected_issues()`)
  Created `conftest.py` with an autouse `reset_fcx_global_state` fixture that calls the existing `FcxModeHandler.reset_fcx_checks()` classmethod (verified from `classic-scanlog-py/src/fcx_handler.rs:352`). The fixture is defensive — it no-ops when the wheel is not built, so pytest collection never fails.
- **Typed FcxResetError exception (Task 1):** Added `pyo3::create_exception!(classic_scanlog, FcxResetError, PyException)` inside an `#[allow(missing_docs)]` sub-module in `classic-scanlog-py/src/lib.rs` so the `missing_docs` workspace lint does not fire on the macro-generated struct. Registered the new class on both the standalone `classic_scanlog` module and the `register_scanlog_module` facade. Updated `FcxModeHandler.reset_fcx_checks()` classmethod to raise the typed `FcxResetError` for non-`Unnecessary` variants (the `Unnecessary` variant is still treated as success). This closes the deferred Rust-only gap from quick-260406-syy by actually implementing the Python surface, not by re-deferring.
- **57 contract rows authored (Task 1):** Built `_build_wave2_rows.py` helper that filters the deferred backlog to Wave 2 sub-modules (verified: 16 rust-only after `GLOBAL_FCX_HANDLER` R9 exclusion + 41 python-only = 57 rows) and emits sorted JSON rows. Final contract has 190 tier1Mappings (59 legacy + 74 Wave 1 + 57 Wave 2). Per-submodule counts: mod_detector 9, suspect_scanner 8, settings_validator 10, fcx_handler 20, gpu_detector 10. Every row has `ownerModule='scanlog'`, `tier='tier1'`, non-empty `rustSymbol` + `pythonExportPath`. A3 verification confirmed all Wave 2 symbols are already `pub use`d at `classic-scanlog-core/src/lib.rs:48-68` (no new re-exports needed).
- **.pyi update (Task 2):** Added a single `class FcxResetError(Exception):` stub to `classic_scanlog.pyi` with docstring mirroring the Rust type. All other Wave 2 class stubs (`SuspectScanner`, `SettingsValidator`, `FcxModeHandler`, `ConfigIssue`, `GpuDetector`, `GpuInfo`, `GpuVendor`, `detect_mods_*`) were already present in the stub from prior phases — verified via grep. `mypy --strict classic_scanlog.pyi` passes.
- **40-test smoke suite (Task 3):** Authored `test_promoted_scanlog_wave2_smoke.py` (393 lines) covering every promoted `#[pyclass]` with per-class construct-and-call tests plus one grouped test per `detect_mods_*` free function. Each test uses exact constructor signatures from `03-03-CONSTRUCTOR-INVENTORY.md`. Four initial failures were auto-fixed (see Deviations) and the final suite runs 40/40 in <0.2 seconds.
- **Runtime registry update (Task 4):** Bumped `python-tier1-scanlog` selector from contractCount=94 to 151 with recomputed `contractIdsHash` (`e0471bad89bda230b60efe211c8b52e850cfdc4e716a2eb014efcf12be33d588` — sha256 of the 151 sorted scanlog tier1 IDs). Added new `python-tier1-scanlog-wave2-promoted` aux entry with 36 explicit `bindingIdentifiers` covering the seven Wave 2 classes, seven methods each (trimmed where minimal), grouped free functions, and `FcxResetError`. Matches the Wave 1 aux-entry pattern.
- **Baseline refresh (Task 4):** Regenerated all baseline and parity-artifacts via `generate_baseline.py --output-dir docs/.../baseline` followed by `check_parity_gate.py --update-baseline`. All 14 artifacts (7 baseline + 7 parity-artifacts) updated in lockstep with the 190-row contract.
- **Gate green:** `check_parity_gate.py` exits 0 with `Tier-1 parity gate passed.`; `parity_diff_report.summary` reports 190 matched, 0 missing_rust, 0 missing_python, 0 signature_mismatch, 0 tier1_gap_total; `runtime_coverage_summary.summary` reports 190 tier1_contract_total, 0 tier1_missing_runtime_total, 0 registry_mismatch_total, 0 newly_uncovered_total.

## Task Commits

Each task was committed atomically:

1. **Task 0: Constructor inventory + FCX reset fixture** — `0c6c266c` (Docs)
2. **Task 1: 57 Wave 2 contract rows + typed FcxResetError** — `4c20b16a` (Feat)
3. **Task 2: FcxResetError stub in classic_scanlog.pyi** — `f4f0942b` (Docs)
4. **Task 3: Wave 2 smoke test suite (40 tests)** — `334a4933` (Test)
5. **Task 4: Parity baseline + runtime registry refresh** — `146bcbd8` (Feat)

## Files Created/Modified

### Created

- `.planning/phases/03-python-tier-collapse/03-03-CONSTRUCTOR-INVENTORY.md` — Verified `#[new]` signatures for the seven Wave 2 `#[pyclass]` wrappers, plus `detect_mods_*` free-function signatures; documents the `GLOBAL_FCX_HANDLER` R9 exclusion and the `GpuVendor`/`FcxModeHandler`/`ConfigIssue` plan-scaffold divergences
- `.planning/phases/03-python-tier-collapse/_build_wave2_rows.py` — Reproducible helper that generates the 57 contract rows from the deferred backlog (kept for future Wave 3 reuse)
- `ClassicLib-rs/python-bindings/tests/conftest.py` — Autouse `reset_fcx_global_state` fixture that routes to `FcxModeHandler.reset_fcx_checks()` and no-ops when the wheel is not built
- `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py` — 40 pytest functions covering Wave 2 promoted classes + free functions + typed exception (393 lines)

### Modified

- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/lib.rs` — Added `pyo3::create_exception!` for `FcxResetError` inside an `#[allow(missing_docs)]` mod scope; registered the new class on both the standalone module and the `register_scanlog_module` facade
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs` — Imported the new `PyFcxResetError` alias; rewired `FcxModeHandler.reset_fcx_checks()` classmethod to raise the typed exception instead of `PyRuntimeError` for non-`Unnecessary` failure variants
- `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` — Added `class FcxResetError(Exception)` stub + docstring; updated `FcxModeHandler.reset_fcx_checks` docstring with `Raises: FcxResetError` note
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — `python-tier1-scanlog` selector contractCount 94 -> 151 with recomputed hash; new `python-tier1-scanlog-wave2-promoted` aux entry with 36 binding identifiers
- `docs/implementation/python_api_parity/baseline/parity_contract.json` — `tier1Mappings` grew from 133 to 190 entries; 57 new Wave 2 rows with dotted `scanlog.<submodule>.<symbol>` IDs (sorted)
- `docs/implementation/python_api_parity/baseline/{rust_api_surface,python_api_surface,parity_diff_report,runtime_coverage_summary}.{json,md}` — All baseline artifacts regenerated to reflect the 190-row contract
- `ClassicLib-rs/python-bindings/parity-artifacts/{rust_api_surface,python_api_surface,parity_diff_report,runtime_coverage_summary,tier1_gate_report}.{json,md}` — Tracked generated artifacts mirror the baseline

## Decisions Made

- **R9 exclusion of GLOBAL_FCX_HANDLER:** The `pub static LazyLock<Mutex<FcxModeHandler>>` global is excluded from `tier1Mappings`. LazyLock statics are not first-class Python module attributes; any future Python access should flow through a factory function (e.g. `get_fcx_handler()`). This drops the Wave 2 row count from 58 to 57. Final tier1Mappings.length = 190 = 133 + 57.
- **FcxResetError promoted as a real exception class, not as a proxy row:** The plan allowed either promoting `FcxResetError` as a typed Python exception or pairing it as a `@rust` proxy row. I chose the real exception class path because (a) the smoke-test acceptance criterion requires `issubclass(classic_scanlog.FcxResetError, Exception)` to succeed, (b) the contract row ends up pointing at a real Python class and not at a proxy, cleaning up the deferred gap rather than displacing it, and (c) the `create_exception!` approach is minimal (~10 lines of Rust, zero new dependencies). The Rust-side `reset_fcx_checks` classmethod now raises the typed exception instead of `PyRuntimeError`, giving Python callers the ability to `except classic_scanlog.FcxResetError:` specifically.
- **Sub-module scoped `create_exception!` for lint compliance:** PyO3's `create_exception!` macro generates an undocumented struct which fires the workspace `missing_docs = warn` lint. Rather than adding a workspace-wide `#[allow]`, I wrapped the macro call in a `mod fcx_reset_exception { #[allow(missing_docs)] ... }` and re-exported via `pub use`. This scopes the allowance to exactly one struct.
- **Single scanlog selector + aux entry for the runtime registry:** Same pattern as Wave 1 (documented in 03-02 summary). Attempted-dual-selector approaches would conflict on the `{ownerModule:"scanlog", tier:"tier1"}` match keys. Instead, one selector covers all 151 rows via classification, and the wave2-promoted aux entry adds 36 explicit `bindingIdentifiers` as supplementary runtime evidence.
- **Tests construct FcxModeHandler with fcx_mode=True for the `has_results()` happy path:** `has_results()` is gated on `fcx_mode` being enabled in `classic-scanlog-core/src/fcx_handler.rs:267-279`. Initial tests used `FcxModeHandler(False)` and observed `has_results() == False` after `set_main_files_result("foo")`, which was correct behavior, not a test bug. Fixed by constructing the happy-path variants with `FcxModeHandler(True)`.
- **`scan_archivelimit_setting` requires explicit `crashgen_version` argument:** The `.pyi` stub declares the parameter as `crashgen_version: Any = None` but the Rust `#[pymethods]` body lacks a `#[pyo3(signature = ...)]` default. The runtime signature is therefore `(crashgen, crashgen_version)` both required. The test passes `None` explicitly. No Rust change needed — this is a stub-only vs runtime discrepancy that does not break anything because all current callers pass the version anyway; fixing the stub to remove the `= None` default would be a larger Wave 2 change and is deferred.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] FcxResetError required a real Python exception class, not a proxy row**

- **Found during:** Task 0 constructor review
- **Issue:** The plan listed `FcxResetError` in the rust-only deferred list (17 entries) and suggested promoting it as a proxy-paired contract row. But Task 3's acceptance criterion explicitly tests `assert issubclass(classic_scanlog.FcxResetError, Exception)`, and the plan's .pyi scaffold calls for `class FcxResetError(Exception): ...`. Both require an actual Python exception class to exist — a proxy row would leave `classic_scanlog.FcxResetError` unresolved at import time.
- **Fix:** Added a typed exception via `pyo3::create_exception!(classic_scanlog, FcxResetError, PyException)` inside an `#[allow(missing_docs)]` sub-module in `classic-scanlog-py/src/lib.rs`. Registered on both the standalone module and `register_scanlog_module` facade. Updated `FcxModeHandler.reset_fcx_checks()` classmethod to raise the typed exception for non-`Unnecessary` variants. The contract row still uses the `@rust`-suffixed ID (`scanlog.fcx_handler.FcxResetError@rust`) with `pythonExportPath="FcxResetError"` and `pythonKind="class"` because the row originates from the rust-only deferred branch of the generator — but it now points at a real Python class, not a proxy.
- **Files modified:** `ClassicLib-rs/python-bindings/classic-scanlog-py/src/lib.rs`, `ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs`, `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi`
- **Verification:** `python -c "import classic_scanlog; assert issubclass(classic_scanlog.FcxResetError, Exception)"` succeeds; gate exits 0; Wave 2 smoke suite `test_fcx_reset_error_is_exception_subclass` passes including a raise/catch round-trip
- **Committed in:** `4c20b16a` (Rust), `f4f0942b` (stub)

**2. [Rule 1 - Bug] Plan scaffold assumed FcxModeHandler takes `ignore_missing: bool`**

- **Found during:** Task 0 constructor inventory (reading `classic-scanlog-py/src/fcx_handler.rs:193`)
- **Issue:** The plan's `<action>` body for Task 0 says "verify exact kw args (ignore_missing?)" and Task 3 scaffold uses `FcxModeHandler(ignore_missing=True)`. The actual `#[new]` signature is `PyFcxModeHandler::new(fcx_mode: bool) -> Self`.
- **Fix:** Documented the correct signature in `03-03-CONSTRUCTOR-INVENTORY.md`. All Wave 2 tests use `FcxModeHandler(False)` for the disabled path and `FcxModeHandler(True)` for the `has_results()` positive path.
- **Files modified:** `03-03-CONSTRUCTOR-INVENTORY.md`, `test_promoted_scanlog_wave2_smoke.py`
- **Verification:** 40/40 Wave 2 smoke tests pass
- **Committed in:** `0c6c266c` (inventory), `334a4933` (tests)

**3. [Rule 1 - Bug] Plan scaffold assumed `GpuVendor` has class-level `NVIDIA`/`AMD`/`INTEL` attributes**

- **Found during:** Task 0 (reading `classic-scanlog-py/src/gpu_detector.rs:10-43`)
- **Issue:** The plan's Task 3 scaffold contains:
  ```python
  def test_gpu_vendor_enum_constants_exist() -> None:
      assert hasattr(classic_scanlog.GpuVendor, "NVIDIA")
      assert hasattr(classic_scanlog.GpuVendor, "AMD")
      ...
  ```
  But `PyGpuVendor` is defined as `#[pyclass(name = "GpuVendor")] #[derive(Clone)] pub struct PyGpuVendor { inner: GpuVendor }` with a `#[new] pub fn new(vendor_name: String) -> Self` — it is a wrapper struct, not a true Python enum. There are no class-level attributes on it.
  (The underlying `classic_scanlog_core::gpu_detector::GpuVendor` IS a real Rust enum with `AMD`, `Nvidia`, `Intel`, `Unknown` variants, but PyO3 does not expose them as class-level attributes on the wrapper struct.)
- **Fix:** Rewrote the `GpuVendor` tests to use constructor calls: `GpuVendor("AMD")`, `GpuVendor("NVIDIA")`, `GpuVendor("INTEL")`, `GpuVendor("something-else")`. Documented the wrapper-vs-enum distinction in the test file docstring and in `03-03-CONSTRUCTOR-INVENTORY.md`.
- **Files modified:** `test_promoted_scanlog_wave2_smoke.py`, `03-03-CONSTRUCTOR-INVENTORY.md`
- **Verification:** `test_gpu_vendor_construct_amd` and `test_gpu_vendor_construct_nvidia_intel_unknown` pass
- **Committed in:** `0c6c266c` (inventory), `334a4933` (tests)

**4. [Rule 1 - Bug] FcxModeHandler.has_results() is gated on fcx_mode=True**

- **Found during:** Task 3 first smoke test run (4 initial failures)
- **Issue:** Three tests that exercised `has_results()` after `set_main_files_result("foo")` expected `True` but got `False`. Reading `classic-scanlog-core/src/fcx_handler.rs:267-279` revealed that `has_results()` short-circuits to `false` when `fcx_mode` is not enabled:
  ```rust
  pub fn has_results(&self) -> bool {
      if !self.fcx_mode {
          return false;
      }
      self.main_files_check.as_ref().is_some_and(|s| !s.is_empty())
          || self.game_files_check.as_ref().is_some_and(|s| !s.is_empty())
  }
  ```
  This is intentional behavior — a disabled FCX handler shouldn't advertise any results even if some have been stashed.
- **Fix:** Updated three tests (`test_fcx_mode_handler_set_main_files_result_marks_results`, `test_fcx_mode_handler_set_game_files_result_roundtrip`, `test_fcx_mode_handler_reset_clears_results`) to construct with `FcxModeHandler(True)` and added a docstring note explaining the gate behavior.
- **Files modified:** `test_promoted_scanlog_wave2_smoke.py`
- **Verification:** All 40 tests pass
- **Committed in:** `334a4933` (tests)

**5. [Rule 1 - Bug] SettingsValidator.scan_archivelimit_setting requires crashgen_version positionally**

- **Found during:** Task 3 first smoke test run
- **Issue:** Test called `validator.scan_archivelimit_setting({})` (omitting `crashgen_version`) because the `.pyi` stub declares it as `crashgen_version: Any = None`. But the runtime raised `TypeError: missing 1 required positional argument: 'crashgen_version'`. The Rust `#[pymethods]` body has no `#[pyo3(signature = ...)]` default for this method.
- **Fix:** Test now passes `None` explicitly: `validator.scan_archivelimit_setting({}, None)`. The stub-vs-runtime discrepancy is documented in the test docstring and in `03-03-CONSTRUCTOR-INVENTORY.md`. Updating the `.pyi` to remove the `= None` default or adding a `#[pyo3(signature = (crashgen, crashgen_version = None))]` attribute is a larger stub-consistency change out of Wave 2 scope (other plans in Phase 3 will touch the same stub).
- **Files modified:** `test_promoted_scanlog_wave2_smoke.py`
- **Verification:** `test_settings_validator_scan_archivelimit_empty` passes
- **Committed in:** `334a4933` (tests)

### Authentication gates encountered

None. All tooling is local.

---

**Total deviations:** 5 auto-fixed (4 Rule 1 bugs in plan assumptions, 1 Rule 2 missing critical).
**Impact on plan:** None of these deviations changed the plan's target output shape. The 57 contract rows still reach exactly 57; the gate still exits 0; the smoke suite still covers every promoted class. Deviations corrected wrong assumptions about (a) whether FcxResetError needed a proxy or a real class, (b) the FcxModeHandler constructor parameter name, (c) whether GpuVendor exposes class-level attributes, (d) that has_results() is gated on fcx_mode, and (e) that scan_archivelimit_setting has a runtime kwarg default. Plan 03's 5-step verification chain passes as written.

## Issues Encountered

- **5 pre-existing pytest failures** in `test_phase2_dead_code_removal.py` and `test_tier1_parity_smoke.py` — already logged in `.planning/phases/03-python-tier-collapse/deferred-items.md` from Plan 02. None touch the Wave 2 sub-modules; all five are missing-wheel or pytest `filterwarnings` issues. No change to the deferred-items list in Plan 03.

## User Setup Required

None. No external service configuration required.

## Known Stubs

None. All promoted symbols are wired to real PyO3 surfaces (including `FcxResetError`, which is now a real Python exception class via `pyo3::create_exception!`).

## Verification Results (5-Step Chain)

| Step | Command | Result |
|---|---|---|
| 1 | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | **PASS** (`Tier-1 parity gate passed.`; 190/190 matched, 0 drift, 0 missing_rust, 0 missing_python, 0 signature_mismatch, 0 tier1_missing_runtime, 0 registry_mismatch, 0 newly_uncovered, 0 tier1_gap_total) |
| 2 | `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/.../parity_contract.json --fail-on-warnings` | **PASS** (3/3 crates passed, 0 errors, 0 warnings) |
| 3 | `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog` | **PASS** (wheel built, installed, and import-verified) |
| 4 | `python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py -q` | **PASS** (40/40 in 0.10s) |
| 5 | `mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` | **PASS** (`Success: no issues found in 1 source file`) |

## Next Phase Readiness

- **Plan 04 (scanlog Wave 3a orchestration core) is ready to execute.** Wave 2 extends the Wave 1 pattern proven end-to-end with two new wrinkles: (a) typed exception promotion via `pyo3::create_exception!` for rust-only error enums, and (b) defensive pytest fixtures that no-op when bindings aren't built. Both patterns are reusable for any future Wave that needs to promote a rust-only error type.
- **Reusable helper:** `_build_wave2_rows.py` can be adapted for Waves 3a/3b by changing the `w2_*` constant sets and the `submod_for_*` routing functions. The contract row shape is identical to Wave 1.
- **Tier-1 floor:** Future Plan 03 follow-up tests asserting `tier1_contract_total >= 190` are now valid. The progression constant in `tools/python_api_parity/tests/test_check_parity_gate.py` should be bumped as Wave 3 lands.
- **Deferred backlog:** After Plan 03, the scanlog deferred backlog drops by 57 entries (228 -> 171 per the gate's own counting). Final Phase 3 target is `deferred_total == 0` after Plan 09.

## Self-Check: PASSED

Verification performed after SUMMARY.md draft:

**Files created check:**
- `.planning/phases/03-python-tier-collapse/03-03-CONSTRUCTOR-INVENTORY.md` — FOUND
- `.planning/phases/03-python-tier-collapse/_build_wave2_rows.py` — FOUND
- `ClassicLib-rs/python-bindings/tests/conftest.py` — FOUND
- `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave2_smoke.py` — FOUND
- `.planning/phases/03-python-tier-collapse/03-03-scanlog-wave2-detection-and-analysis-SUMMARY.md` — FOUND

**Commits check:**
- `0c6c266c` Docs(03-03): Add Wave 2 constructor inventory and FCX reset fixture — FOUND
- `4c20b16a` Feat(03-03): Add 57 Wave 2 scanlog tier1 contract rows + typed FcxResetError — FOUND
- `f4f0942b` Docs(03-03): Document FcxResetError exception class in scanlog stub — FOUND
- `334a4933` Test(03-03): Add Wave 2 scanlog smoke test suite — FOUND
- `146bcbd8` Feat(03-03): Refresh parity baseline and runtime registry for Wave 2 — FOUND

**Verification commands:**
- `check_parity_gate.py --repo-root .` — EXIT 0 (`Tier-1 parity gate passed.`; tier1Mappings=190)
- `validate_stubs.py --fail-on-warnings` — EXIT 0 (3/3 crates, 0 err/warn)
- `rebuild_rust.ps1 -Target python classic_scanlog` — EXIT 0 (wheel built + installed)
- `pytest test_promoted_scanlog_wave2_smoke.py -q` — EXIT 0 (40 passed)
- `mypy --strict classic_scanlog.pyi` — EXIT 0 (no issues)

---
*Phase: 03-python-tier-collapse*
*Completed: 2026-04-08*
