# Phase 3 Plan 03 — Wave 2 Constructor Inventory

**Date:** 2026-04-08
**Purpose:** Verified `#[pymethods] fn new` (and equivalent factory / enum) signatures for every Wave 2 `#[pyclass]` wrapper so that the smoke suite in `test_promoted_scanlog_wave2_smoke.py` uses real constructors, not guesses.

All signatures below were read directly from the `classic-scanlog-py/src/*.rs` source files.

## Verified signatures

| PyO3 name | Rust wrapper | Source file | Constructor signature | Notes |
|-----------|--------------|-------------|------------------------|-------|
| `SuspectScanner` | `PySuspectScanner` | `suspect_scanner.rs` | `PySuspectScanner::new(suspect_error_rules: &Bound<PyAny>, suspect_stack_rules: &Bound<PyAny>) -> PyResult<Self>` | Accepts two sequences of dicts (error rules + stack rules). Empty `[]` / `[]` is valid and produces an empty scanner. Each dict has required string/int fields; empty list path never touches them. |
| `SettingsValidator` | `PySettingsValidator` | `settings_validator.rs` | `PySettingsValidator::new(crashgen_name: String, crashgen_entry: &Bound<PyAny>) -> Self` | Accepts crashgen name + dict-like entry. If `crashgen_entry` is a dict the keys `display_section`, `ignore_keys`, `checks`, `settings_rules` are read optionally (all default-safe). An empty dict `{}` is valid. |
| `FcxModeHandler` | `PyFcxModeHandler` | `fcx_handler.rs` | `PyFcxModeHandler::new(fcx_mode: bool) -> Self` | Single boolean. Previous plan sketch guessed `ignore_missing: bool` — the real parameter is `fcx_mode`. `FcxModeHandler(False)` is the no-op safe constructor. Do NOT call `check_fcx_mode()` in tests because it touches the shared filesystem and global state. |
| `ConfigIssue` | `PyConfigIssue` | `fcx_handler.rs` | `PyConfigIssue::new(file_path, section: Option<String>, setting, current_value, recommended_value, description, severity: String = "warning") -> Self` | 6 required + 1 optional string args. Has a direct constructor (NOT only via `FcxModeHandler.get_detected_issues()`). Python signature: `ConfigIssue(file_path, section, setting, current_value, recommended_value, description, severity="warning")`. |
| `GpuDetector` | `PyGpuDetector` | `gpu_detector.rs` | `PyGpuDetector::new() -> Self` | Zero-arg constructor. Unit struct internally. `GpuDetector()` always works. |
| `GpuInfo` | `PyGpuInfo` | `gpu_detector.rs` | `PyGpuInfo::new() -> Self` | Zero-arg constructor. Wraps empty `GpuInfo::new()` inner. Fields filled via `#[getter]` access after the detector populates one through `extract_gpu_info(...)`. |
| `GpuVendor` | `PyGpuVendor` | `gpu_detector.rs` | `PyGpuVendor::new(vendor_name: String) -> Self` | **Important**: this is a wrapper `#[pyclass]`, not a real Python enum. You construct an instance by passing a vendor-name string (`"AMD"`, `"NVIDIA"`, `"INTEL"`, anything else -> `Unknown`). There are NO `NVIDIA`/`AMD`/`INTEL`/`UNKNOWN` class-level attributes on `PyGpuVendor`. Test must call `GpuVendor("AMD")` etc., NOT `GpuVendor.AMD`. |
| `FcxResetError` | — (new exception) | `classic-scanlog-py/src/lib.rs` (added Plan 03 Task 1) | `pyo3::create_exception!(classic_scanlog, FcxResetError, PyException)` | No direct Python wrapper previously existed. Plan 03 Task 1 adds a real Python exception class via `create_exception!` and registers it on the module. The existing `FcxModeHandler.reset_fcx_checks()` classmethod is updated to raise this typed exception instead of `PyRuntimeError` for non-`Unnecessary` variants. |

## Free functions (mod_detector — no constructor)

| Python name | Rust symbol | Source file | Signature |
|-------------|-------------|-------------|-----------|
| `detect_mods_single` | `mod_detector::detect_mods_single` | `mod_detector.rs` | `(yaml_dict: dict, crashlog_plugins: dict) -> list[str]` |
| `detect_mods_double` | `mod_detector::detect_mods_double` | `mod_detector.rs` | `(entries: list[dict], crashlog_plugins: dict) -> list[str]` — each entry must have `mod_a`, `mod_b`, `name_a`, `name_b`, `description`, `fix` keys (+ optional `link`); empty `[]` is valid |
| `detect_mods_important` | `mod_detector::detect_mods_important` | `mod_detector.rs` | `(entries: list[dict], crashlog_plugins: dict, user_gpu: str \| None = None, xse_modules: set[str] = set()) -> list[str]` |
| `detect_mods_batch` | `mod_detector::detect_mods_batch` | `mod_detector.rs` | `(yaml_dict: dict, crashlog_plugins_list: list[dict]) -> list[list[str]]` |

## GLOBAL_FCX_HANDLER exclusion (R9)

`GLOBAL_FCX_HANDLER` is a `pub static LazyLock<Mutex<FcxModeHandler>>` in `classic-scanlog-core::fcx_handler`. `LazyLock` statics are **not** first-class Python module attributes — PyO3 has no way to expose a `LazyLock<Mutex<T>>` as an importable object without wrapping it in a factory function.

**Decision:** Exclude from `tier1Mappings`. Per-scan reset behavior is already covered by `FcxModeHandler.reset_fcx_checks()` (classmethod) which internally calls `FcxModeHandler::reset_global_state()`. No external consumer needs direct access to the static — they should call the classmethod. This matches R9 in the plan and drops the Wave 2 row count from 58 to 57.

## FCX state reset fixture API

Verified from `classic-scanlog-py/src/fcx_handler.rs:352-361`:

```rust
#[classmethod]
fn reset_fcx_checks(_cls: &Bound<'_, PyType>) -> PyResult<()> {
    match FcxModeHandler::reset_global_state() {
        Ok(()) | Err(FcxResetError::Unnecessary) => Ok(()),
        Err(error) => Err(PyRuntimeError::new_err(format!(
            "failed to reset FCX global state: {error}"
        ))),
    }
}
```

This is the API surface for `conftest.py`'s autouse fixture. Python usage:

```python
import classic_scanlog
classic_scanlog.FcxModeHandler.reset_fcx_checks()
```

Plan 03 Task 1 retrofits the non-`Unnecessary` branch to raise the new typed `FcxResetError` exception class (same string body) so runtime callers can catch it specifically.
