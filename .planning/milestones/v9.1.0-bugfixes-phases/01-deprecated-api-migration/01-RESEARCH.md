# Phase 1: Deprecated API Migration - Research

**Researched:** 2026-04-05
**Domain:** Rust/PyO3 deprecated API migration, Python deprecation warnings, test migration
**Confidence:** HIGH

## Summary

Phase 1 migrates four deprecated API surfaces in the classic-scanlog-core and its Python bindings: (1) `parse_segments_parallel` return type change from positional `list[list[str]]` to named `dict[str, list[str]]`, (2) `generate_suspect_section` delegation to the two-method replacement, (3) `is_outdated` test migration to `check_version_status`, and (4) `PyFormIDAnalyzerCore::new` deprecation warning for legacy `PyDict` format. All replacement APIs already exist in the codebase; the work is rewiring callers, adding `PyErr::warn` deprecation warnings, updating the `.pyi` contract, expanding test coverage, and verifying parity gates pass.

The codebase has `deprecated = "deny"` at the workspace lint level, which means any call site that invokes a `#[deprecated]` method will fail to compile unless it has a surgical `#[allow(deprecated)]` annotation. The Python binding `parse_segments_parallel` already has this annotation. The approach is to rewrite each call site to use the non-deprecated replacement, then remove the `#[allow(deprecated)]` annotation. No workspace-wide lint relaxation is needed.

**Primary recommendation:** Implement migrations in order: DEBT-07 (pure Rust test rewrite, no binding changes), then DEBT-05 (parse_segments_parallel), then DEBT-06 (generate_suspect_section), then DEBT-10 (FormID deprecation warning). Each is independently testable. Run parity gates after DEBT-05, DEBT-06, and DEBT-10.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `parse_segments_parallel` changes its Python return type from `list[list[str]]` to `dict[str, list[str]]` to match the underlying `parse_all_sections_arc` API. The `.pyi` contract updates accordingly. Callers must adapt to named sections instead of positional indexing.
- **D-02:** All three legacy Python methods emit `DeprecationWarning` via `PyErr::warn` when called:
  - `parse_segments_parallel` -> warns to use `parse_all_sections` (the dict-returning method)
  - `generate_suspect_section` -> warns to use `generate_suspect_section_header` + `generate_suspect_found_footer`
  - `PyFormIDAnalyzerCore::new` with legacy `PyDict` for `mods_single` -> warns to use structured `ModSolutionEntry` format
- **D-03:** Warning messages must name the replacement API explicitly so callers know where to migrate.
- **D-04:** The `deprecated = "deny"` workspace lint stays at `deny` throughout the phase. Migration call sites use surgical `#[allow(deprecated)]` annotations that are removed once the underlying call is replaced. No temporary workspace-wide lint relaxation.
- **D-05:** The three `is_outdated` tests are not just rewritten as minimal equivalents -- coverage is expanded to exercise `check_version_status` with VR-specific scenarios and edge cases (e.g., VR-specific `NewerThanKnown`, empty valid lists in VR mode, version between valid entries). The migration is an opportunity to strengthen the test suite.

### Claude's Discretion
- Exact `DeprecationWarning` message wording
- Internal conversion approach for `generate_suspect_section` delegating to header + footer (deriving `bool` from `found_suspects` list)
- Specific VR edge case test scenarios beyond the ones discussed
- Order of migration within the phase (which DEBT item first)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEBT-05 | Migrate Python binding `parse_segments_parallel` caller to wrapper over `parse_all_sections_arc`, update `.pyi` contract | `parse_all_sections_arc` already exists and returns `HashMap<String, Vec<Arc<str>>>`; Python `parse_all_sections` method (parser.rs:192) already returns `dict[str, list[str]]`. Migration rewires `parse_segments_parallel` to call `parse_all_sections_arc` and return dict, plus emits deprecation warning. |
| DEBT-06 | Migrate Python `generate_suspect_section` legacy method to call `generate_suspect_section_header` + `generate_suspect_found_footer` separately | Both replacement methods already exposed in Python bindings (report.rs:245, 255). Legacy method in core (report.rs:655) is NOT formally `#[deprecated]`, just labeled "legacy." Python binding delegates directly to core. Migration rewires Python binding to call header + footer, emits deprecation warning. |
| DEBT-07 | Rewrite tests using `#[allow(deprecated)]` on `CrashgenVersion::is_outdated` to exercise `check_version_status()` instead | Three tests at version.rs:456-484 use `#[allow(deprecated)]` to call `is_outdated`. `check_version_status` already has comprehensive tests at version.rs:500-619 providing patterns to follow. |
| DEBT-10 | Add deprecation warning via `PyErr::warn` when `PyFormIDAnalyzerCore::new` receives legacy `PyDict` format for `mods_single` | `legacy_mod_map_to_entries` conversion function already exists at formid_analyzer.rs:11. Constructor always converts through this path when receiving `PyDict`. Warning insertion point is clear. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyo3 | 0.27.2 (abi3-py312) | Python bindings, `PyErr::warn` for deprecation warnings | Already in workspace dependencies; `pyo3::exceptions::PyDeprecationWarning` is the standard way to emit Python `DeprecationWarning` from Rust |
| classic-scanlog-core | workspace | Business logic for parsing, versioning, report generation | All deprecated methods and their replacements live here |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyo3::exceptions | (bundled with pyo3) | `PyDeprecationWarning` type for `PyErr::warn` | Every deprecation warning call site |
| indexmap | 2.7 | Ordered map conversion for legacy FormID dict | Already used in `pydict_to_indexmap_str_optional` |

No new dependencies are needed. All required libraries are already in the workspace.

## Architecture Patterns

### Recommended Migration Structure
```
ClassicLib-rs/
  business-logic/classic-scanlog-core/src/
    version.rs         # DEBT-07: Rewrite is_outdated tests -> check_version_status tests
    report.rs          # Reference only (core generate_suspect_section stays as-is for Phase 2 removal)
    parser.rs          # Reference only (core parse_segments_parallel stays as-is for Phase 2 removal)
  python-bindings/classic-scanlog-py/
    src/parser.rs      # DEBT-05: Rewrite parse_segments_parallel to return dict + emit warning
    src/report.rs      # DEBT-06: Rewrite generate_suspect_section to delegate + emit warning
    src/formid_analyzer.rs  # DEBT-10: Add deprecation warning in PyFormIDAnalyzerCore::new
    classic_scanlog.pyi     # DEBT-05: Update parse_segments_parallel return type in stub
```

### Pattern 1: PyO3 Deprecation Warning Emission
**What:** Use `PyErr::warn` with `PyDeprecationWarning` to emit Python-visible `DeprecationWarning` from Rust binding code.
**When to use:** Every legacy Python method that callers should migrate away from.
**Example:**
```rust
// Source: PyO3 0.27 official docs (https://pyo3.rs/main/doc/pyo3/struct.pyerr)
use pyo3::exceptions::PyDeprecationWarning;

// Inside a #[pymethods] function that has `py: Python<'py>`:
PyErr::warn(
    py,
    &py.get_type::<PyDeprecationWarning>(),
    c"parse_segments_parallel is deprecated. Use parse_all_sections instead, which returns dict[str, list[str]].",
    1,  // stacklevel=1 makes warning appear to come from the caller
)?;
```

**Key detail:** `PyErr::warn` takes a `&CStr` message (C string literal with `c"..."` syntax, stable since Rust 1.77). The `stacklevel` parameter controls where the warning appears to originate; `1` means "from the immediate caller," which is appropriate for deprecated wrapper methods.

**Key detail:** `PyErr::warn` returns `PyResult<()>`. If the user has `warnings.simplefilter("error")`, the warning becomes an exception. The `?` propagation handles this correctly since all these methods already return `PyResult`.

### Pattern 2: parse_segments_parallel Migration (DEBT-05)
**What:** Rewrite the Python binding to call `parse_all_sections_arc` directly and return a `PyDict` instead of a `PyList` of `PyList`.
**When to use:** DEBT-05 implementation.
**Example:**
```rust
// Current: calls deprecated core method, returns list[list[str]]
#[allow(deprecated)]
#[pyo3(name = "parse_segments_parallel", signature = (lines, chunk_size=None))]
pub fn parse_segments_parallel<'py>(...) -> PyResult<Bound<'py, PyList>> { ... }

// Migrated: calls parse_all_sections_arc, returns dict[str, list[str]], emits warning
#[pyo3(name = "parse_segments_parallel", signature = (lines, chunk_size=None))]
pub fn parse_segments_parallel<'py>(
    &self,
    py: Python<'py>,
    lines: Vec<String>,
    _chunk_size: Option<usize>,
) -> PyResult<Bound<'py, PyDict>> {
    PyErr::warn(
        py,
        &py.get_type::<PyDeprecationWarning>(),
        c"parse_segments_parallel is deprecated. Use parse_all_sections instead.",
        1,
    )?;
    let arc_lines = to_arc_str_vec(&lines);
    let named_sections = without_gil(py, || {
        self.inner.parse_all_sections_arc(&arc_lines)
    });
    let dict = PyDict::new(py);
    for (key, section_lines) in &named_sections {
        let py_lines: Vec<&str> = section_lines.iter().map(|s| s.as_ref()).collect();
        let inner_list = PyList::new(py, py_lines)?;
        dict.set_item(key.as_str(), inner_list)?;
    }
    Ok(dict)
}
```

### Pattern 3: generate_suspect_section Delegation (DEBT-06)
**What:** Rewrite the Python binding to call the two replacement methods internally, emitting a deprecation warning.
**When to use:** DEBT-06 implementation.
**Example:**
```rust
// Migrated: delegates to header + footer, emits warning
pub fn generate_suspect_section(&self, py: Python<'_>, found_suspects: Vec<String>) -> PyResult<PyReportFragment> {
    PyErr::warn(
        py,
        &py.get_type::<PyDeprecationWarning>(),
        c"generate_suspect_section is deprecated. Use generate_suspect_section_header and generate_suspect_found_footer instead.",
        1,
    )?;
    let header = self.inner.generate_suspect_section_header();
    let found_suspect = !found_suspects.is_empty();
    let footer = self.inner.generate_suspect_found_footer(found_suspect);
    Ok(PyReportFragment { inner: header.combine(&footer) })
}
```

**Important:** The legacy `generate_suspect_section` in core produces different header text ("Checking If Log Matches Any Known Crash Suspects") vs the new `generate_suspect_section_header` ("Checking for Known Crash Messages, Errors and Suspects"). The migrated Python binding will emit the NEW text. This is an intentional behavior change toward the canonical format. The core legacy method is NOT being changed (that happens in Phase 2/DEBT-08).

### Pattern 4: FormID Legacy Dict Warning (DEBT-10)
**What:** Detect when the legacy `PyDict` format is being used and emit a warning before conversion.
**When to use:** DEBT-10 implementation.
**Example:**
```rust
// In PyFormIDAnalyzerCore::new, before legacy_mod_map_to_entries call:
if mods_single.is_some() {
    PyErr::warn(
        py,
        &py.get_type::<PyDeprecationWarning>(),
        c"Passing mods_single as dict[str, str] is deprecated. Use structured ModSolutionEntry format instead.",
        1,
    )?;
}
```

**Note:** The constructor currently does not take `py: Python<'_>` as a parameter. In PyO3 0.27, `#[new]` methods can accept `Python<'py>` as the first parameter. This needs to be added to the signature.

### Anti-Patterns to Avoid
- **Relaxing workspace `deprecated = "deny"` lint:** Decision D-04 explicitly forbids this. Keep surgical `#[allow(deprecated)]` and remove them as each call site is migrated.
- **Changing the core Rust deprecated methods:** Phase 1 only changes the Python binding layer and tests. Core deprecated methods are removed in Phase 2 (DEBT-08).
- **Removing `#[allow(deprecated)]` from parser.rs tests in this phase:** The three deprecated parser tests (test_segment_parsing_deprecated_shim, test_segment_parsing_with_patches_first_boundary, test_deprecated_parse_segments_preserves_xse_modules_slot) test the core deprecated methods, not the Python bindings. They stay until Phase 2 (DEBT-08) removes the core methods.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python deprecation warnings from Rust | Custom warning system or `eprintln!` | `PyErr::warn` with `PyDeprecationWarning` | Standard Python warning mechanism; respects `warnings.filterwarnings`, `-W` flags, pytest `recwarn` fixture |
| Dict-returning parse method | New method from scratch | Existing `parse_all_sections_arc` | Already implemented and tested; returns `HashMap<String, Vec<Arc<str>>>` |
| Suspect section header + footer | Re-implementing text generation | Existing `generate_suspect_section_header` + `generate_suspect_found_footer` | Already exposed in Python bindings with correct formatting |

## Common Pitfalls

### Pitfall 1: CStr Literal Syntax
**What goes wrong:** Using `"..."` instead of `c"..."` for `PyErr::warn` message parameter.
**Why it happens:** `PyErr::warn` takes `&CStr`, not `&str`. Forgetting the `c` prefix causes a type error.
**How to avoid:** Always use `c"message"` syntax (Rust 1.77+, MSRV 1.85.0 satisfies this).
**Warning signs:** Compilation error about expected `&CStr`, found `&str`.

### Pitfall 2: Missing `py` Parameter in Constructor
**What goes wrong:** `PyFormIDAnalyzerCore::new` does not currently have `py: Python<'_>` in its signature, so `PyErr::warn` cannot be called.
**Why it happens:** The `#[new]` method was written before deprecation warnings were needed.
**How to avoid:** Add `py: Python<'_>` as the first parameter of the `#[new]` method. PyO3 0.27 supports this for constructors.
**Warning signs:** Cannot call `PyErr::warn` without a `Python` token.

### Pitfall 3: Return Type Change Breaking Parity Gate
**What goes wrong:** Changing `parse_segments_parallel` return type from `list[list[str]]` to `dict[str, list[str]]` causes the parity gate to flag a signature mismatch.
**Why it happens:** The `.pyi` stub file must be updated in the same change as the Rust binding.
**How to avoid:** Update `classic_scanlog.pyi` in the same commit as the Rust binding change, before running the parity gate.
**Warning signs:** Parity gate reports "signature mismatch" for `parse_segments_parallel`.

### Pitfall 4: generate_suspect_section Output Text Change
**What goes wrong:** The migrated `generate_suspect_section` produces different header text than the core legacy method.
**Why it happens:** Core legacy method uses "Checking If Log Matches Any Known Crash Suspects" but `generate_suspect_section_header` uses "Checking for Known Crash Messages, Errors and Suspects."
**How to avoid:** This is an intentional change per the migration. Ensure any tests checking exact output text are updated to expect the new header text.
**Warning signs:** Tests checking string equality of report output fail after migration.

### Pitfall 5: Deprecation Warning in Constructor Breaks warnings.simplefilter("error")
**What goes wrong:** If a Python test or user has `warnings.simplefilter("error")`, the deprecation warning from `PyFormIDAnalyzerCore::new` becomes a hard exception.
**Why it happens:** `PyErr::warn` respects Python's warning filters.
**How to avoid:** This is correct behavior -- it tells users they need to migrate. Tests that construct with legacy format should use `pytest.warns(DeprecationWarning)` or `warnings.catch_warnings()`.
**Warning signs:** Existing tests that construct `FormIDAnalyzerCore` with dict format start failing.

### Pitfall 6: Workspace deprecated=deny and Test Compilation
**What goes wrong:** After removing `#[allow(deprecated)]` from the Python binding's `parse_segments_parallel`, the code won't compile if it still calls the deprecated core method.
**Why it happens:** The workspace lint `deprecated = "deny"` turns deprecation warnings into errors.
**How to avoid:** The migration must change the implementation to call `parse_all_sections_arc` (non-deprecated) BEFORE removing the `#[allow(deprecated)]` annotation. In practice, do both in the same change.
**Warning signs:** Compilation error about use of deprecated method.

## Code Examples

### PyErr::warn with PyDeprecationWarning
```rust
// Source: PyO3 0.27 docs (https://pyo3.rs/main/doc/pyo3/struct.pyerr)
use pyo3::exceptions::PyDeprecationWarning;
use pyo3::prelude::*;

// In a #[pymethods] block:
fn some_deprecated_method(&self, py: Python<'_>) -> PyResult<()> {
    PyErr::warn(
        py,
        &py.get_type::<PyDeprecationWarning>(),
        c"some_deprecated_method is deprecated. Use new_method instead.",
        1,
    )?;
    // ... delegate to new implementation ...
    Ok(())
}
```

### Testing Deprecation Warnings in Python (pytest)
```python
# Source: pytest docs (https://docs.pytest.org/en/stable/how-to/capture-warnings.html)
import warnings
import pytest

def test_parse_segments_parallel_emits_deprecation():
    parser = LogParser()
    with pytest.warns(DeprecationWarning, match="parse_segments_parallel is deprecated"):
        result = parser.parse_segments_parallel(lines)
    # Also verify the result is now a dict
    assert isinstance(result, dict)
    assert "callstack" in result
```

### check_version_status Test Pattern (Existing)
```rust
// Source: ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs:500-619
// Existing test patterns to follow for DEBT-07 expansion:

#[test]
fn test_check_version_status_valid() {
    let current = CrashgenVersion::new(1, 28, 6);
    let valid = vec![
        CrashgenVersion::new(1, 28, 6),
        CrashgenVersion::new(1, 37, 0),
    ];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Valid);
}

// New VR-specific tests to add (DEBT-07 expansion):
// - VR version exactly matching one valid entry
// - VR version newer than all known valid VR versions
// - Empty valid list for VR mode (NoSupportedVersion)
// - Version between two valid entries (should be Outdated)
// - Single valid version in list (edge case)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `parse_segments` / `parse_segments_parallel` (positional Vec) | `parse_all_sections_arc` (named HashMap) | v9.0.0 deprecation | Callers must use string keys instead of integer indices |
| `is_outdated` (single version comparison) | `check_version_status` (list-based) | v0.2.0 deprecation | Supports multiple valid versions per game variant |
| `generate_suspect_section` (monolithic) | `generate_suspect_section_header` + `generate_suspect_found_footer` (composable) | Already available | More granular control over report sections |
| `mods_single` as `dict[str, str]` | Structured `ModSolutionEntry` format | Already available | Richer metadata (criteria, exceptions, name, description) |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | cargo test (Rust), pytest (Python) |
| Config file | `ClassicLib-rs/Cargo.toml` (workspace), `ClassicLib-rs/python-bindings/.venv` (Python) |
| Quick run command | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` |
| Full suite command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && uv run pytest ClassicLib-rs/python-bindings/tests -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-05 | `parse_segments_parallel` returns dict and emits DeprecationWarning | unit (Python) | `uv run pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q` | Needs new test |
| DEBT-06 | `generate_suspect_section` delegates and emits DeprecationWarning | unit (Python) | `uv run pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q` | Needs new test |
| DEBT-07 | `is_outdated` tests replaced with `check_version_status` tests | unit (Rust) | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` | Existing tests to rewrite at version.rs:456-484 |
| DEBT-10 | `PyFormIDAnalyzerCore::new` emits DeprecationWarning for legacy dict | unit (Python) | `uv run pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q` | Needs new test |
| ALL | Python and Node parity gates pass | integration | `python tools/python_api_parity/check_parity_gate.py --repo-root . && cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` | Existing infrastructure |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests`
- **Per wave merge:** `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **Phase gate:** Full suite green + both parity gates passing before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Python deprecation warning smoke tests -- need new test functions in `test_tier1_parity_smoke.py` for DEBT-05, DEBT-06, DEBT-10
- [ ] Python bindings must be rebuilt (`./rebuild_rust.ps1 -Target python -Crates classic-scanlog-py`) before Python tests can run after Rust changes

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** -- All source files read directly:
  - `ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs` (parse_segments_parallel binding)
  - `ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs` (generate_suspect_section binding)
  - `ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs` (PyFormIDAnalyzerCore::new)
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` (is_outdated + check_version_status + tests)
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/report.rs` (core generate_suspect_section)
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` (core deprecated methods)
  - `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` (type stubs)
  - `ClassicLib-rs/Cargo.toml` (workspace lints: `deprecated = "deny"`)
- **PyO3 0.27 official docs** (https://pyo3.rs/main/doc/pyo3/struct.pyerr) -- `PyErr::warn` signature and usage

### Secondary (MEDIUM confidence)
- **PyO3 exceptions docs** (https://pyo3.rs/main/doc/pyo3/exceptions/struct.pydeprecationwarning) -- `PyDeprecationWarning` type exists in `pyo3::exceptions`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in workspace, no new deps needed
- Architecture: HIGH - All replacement APIs already exist; migration is rewiring, not new implementation
- Pitfalls: HIGH - Identified from direct code inspection of actual call sites and Rust lint configuration
- PyO3 warn API: HIGH - Verified signature via official docs, confirmed CStr parameter requirement

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable codebase, no external dependency changes expected)
