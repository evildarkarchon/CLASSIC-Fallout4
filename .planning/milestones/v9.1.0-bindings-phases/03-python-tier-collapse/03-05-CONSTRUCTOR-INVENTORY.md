# Plan 05 Constructor Inventory — scanlog Wave 3b (report sub-module)

**Plan:** 03-05-scanlog-wave3b-report-standalone
**Purpose:** Verify the exact `#[pymethods]` constructor and method signatures for every PyO3 report wrapper class BEFORE authoring contract rows, stubs, or tests, so test scaffolding cannot silently drift from the real runtime surface (same discipline as Wave 3a's "divergence" fixes).

**Source of truth:** `ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs` (361 lines, all 5 `#[pyclass]` wrappers).
**Core source of truth:** `ClassicLib-rs/business-logic/classic-scanlog-core/src/report.rs` (756 lines).

All 5 report classes are:
- Already `pub use`d at `classic-scanlog-core/src/lib.rs` line 66: `pub use report::{ReportComposer, ReportFragment, ReportGenerator, StringPool};` (A3 confirmed — `pub use` not needed).
- Already registered in `classic-scanlog-py/src/lib.rs` `#[pymodule]` lines 238-242 and 312-316 (no Pitfall 4 gate risk).
- Already declared in `classic-scanlog-py/classic_scanlog.pyi` lines 983-1334 (no stub additions needed — verified by Task 2 predicate).

> **R9 note:** `PyParallelReportProcessor` has NO `-core` counterpart. It's a pure `-py` convenience class (`pub struct PyParallelReportProcessor;` — empty marker type with only a `combine_fragments` staticmethod). Same pattern as `CancellationToken` from Wave 3a. Its contract rows pair with a `-core` proxy symbol via the same `py_class_to_core_symbol` mapping pattern from Wave 3a.

## 1. StringPool (PyStringPool)

- **Rust wrapper file:** `classic-scanlog-py/src/report.rs:9-52`
- **`#[pyclass(name = "StringPool")]`** — Python-facing name: `StringPool`
- **`inner: StringPool`** — wraps `classic_scanlog_core::StringPool` (core line 22)
- **`#[derive(Clone)]`**

### Signatures

| Method | Signature | Notes |
|---|---|---|
| `new` | `#[new] fn new() -> Self` | Zero-arg constructor. Also has `Default` impl calling `new()`. |
| `intern` | `fn intern(&self, s: String) -> String` | Interns single string, returns interned copy. |
| `intern_batch` | `fn intern_batch(&self, py: Python<'_>, strings: Vec<String>) -> Vec<String>` | GIL-releasing batch intern; `py` arg is PyO3-injected, not Python-visible. |
| `get_stats` | `fn get_stats(&self) -> (usize, usize, usize, usize)` | Returns `(total_strings, unique_strings, memory_saved, current_size)` per core impl. |
| `clear` | `fn clear(&self)` | Clears pool. |

### Does `StringPool` have `__len__`?
**NO.** There is no `__len__` magic method on the Python wrapper, and no `len()` method on the `-core` StringPool either (verified from `report.rs:22-82`). The clear/pool-state verification in tests must use `get_stats()` (which returns a tuple whose elements can be inspected) or re-intern and call `get_stats()` again, NOT `len(pool)`.

### Contract rows (from deferred backlog)

7 rows total:
1. `classic_scanlog.StringPool` (class)
2. `classic_scanlog.StringPool.__init__` (method)
3. `classic_scanlog.StringPool.intern` (method)
4. `classic_scanlog.StringPool.intern_batch` (method)
5. `classic_scanlog.StringPool.get_stats` (method)
6. `classic_scanlog.StringPool.clear` (method)
7. rust-only proxy: `StringPool` (class marker — paired with Python `StringPool`)

## 2. ReportFragment (PyReportFragment)

- **Rust wrapper file:** `classic-scanlog-py/src/report.rs:54-119`
- **`#[pyclass(name = "ReportFragment")]`** — Python-facing name: `ReportFragment`
- **`inner: ReportFragment`** — wraps `classic_scanlog_core::ReportFragment`
- **`#[derive(Clone)]`**

### Signatures

| Method | Signature | Notes |
|---|---|---|
| `new` | `#[new] #[pyo3(signature = (lines=None))] fn new(lines: Option<Vec<String>>) -> Self` | Optional `lines` arg. Calls `ReportFragment::from_lines(lines)` or `ReportFragment::empty()`. |
| `empty` | `#[staticmethod] fn empty() -> Self` | Static factory for empty fragment. |
| `from_lines` | `#[staticmethod] fn from_lines(lines: Vec<String>) -> Self` | Static factory from list of lines. |
| `with_header` | `fn with_header(&self, header_lines: Vec<String>) -> Self` | Returns NEW fragment with header prepended. |
| `combine` | `fn combine(&self, other: &PyReportFragment) -> Self` | Returns NEW fragment joining self+other. |
| `to_list` | `fn to_list(&self) -> Vec<String>` | Converts fragment to `list[str]`. |
| `len` | `fn len(&self) -> usize` | Number of lines. **NOTE:** this is a regular method `fragment.len()`, NOT `__len__`. Python `len(fragment)` would raise TypeError. |
| `is_empty` | `fn is_empty(&self) -> bool` | Returns True iff zero lines. |

### Contract rows (from deferred backlog)

10 rows total:
1. `classic_scanlog.ReportFragment` (class)
2. `classic_scanlog.ReportFragment.__init__` (method)
3. `classic_scanlog.ReportFragment.empty` (method / staticmethod)
4. `classic_scanlog.ReportFragment.from_lines` (method / staticmethod)
5. `classic_scanlog.ReportFragment.with_header` (method)
6. `classic_scanlog.ReportFragment.combine` (method)
7. `classic_scanlog.ReportFragment.to_list` (method)
8. `classic_scanlog.ReportFragment.len` (method)
9. `classic_scanlog.ReportFragment.is_empty` (method)
10. rust-only proxy: `ReportFragment` (class marker — paired with Python `ReportFragment`)

## 3. ReportComposer (PyReportComposer)

- **Rust wrapper file:** `classic-scanlog-py/src/report.rs:121-178`
- **`#[pyclass(name = "ReportComposer")]`** — Python-facing name: `ReportComposer`
- **`inner: ReportComposer`** — wraps `classic_scanlog_core::ReportComposer`
- **NO `#[derive(Clone)]`** — not cloneable.

### Signatures

| Method | Signature | Notes |
|---|---|---|
| `new` | `#[new] fn new() -> Self` | Zero-arg constructor. Default impl present. |
| `add` | `fn add(&mut self, fragment: PyReportFragment)` | Mutable — requires Python `fragment` to be cloneable (it is, via `#[derive(Clone)]`). |
| `add_many` | `fn add_many(&mut self, fragments: Vec<PyReportFragment>)` | Batch add; fragments consumed by value via clone. |
| `compose` | `fn compose(&self) -> Vec<String>` | **NOTE:** PyO3 wrapper returns `Vec<String>` (calling `.compose().to_list()` internally), NOT `ReportFragment`. Return type is `list[str]`. |
| `compose_optimized` | `fn compose_optimized(&self) -> Vec<String>` | Same — returns `list[str]`. |
| `build_string` | `fn build_string(&self) -> String` | Single composed string. |
| `fragment_count` | `fn fragment_count(&self) -> usize` | Number of accumulated fragments. |
| `pool_stats` | `fn pool_stats(&self) -> (usize, usize, usize, usize)` | **NAMING:** Python method is `pool_stats` (wrapping core `get_pool_stats()`). |

### Contract rows (from deferred backlog)

10 rows total:
1. `classic_scanlog.ReportComposer` (class)
2. `classic_scanlog.ReportComposer.__init__` (method)
3. `classic_scanlog.ReportComposer.add` (method)
4. `classic_scanlog.ReportComposer.add_many` (method)
5. `classic_scanlog.ReportComposer.compose` (method)
6. `classic_scanlog.ReportComposer.compose_optimized` (method)
7. `classic_scanlog.ReportComposer.build_string` (method)
8. `classic_scanlog.ReportComposer.fragment_count` (method)
9. `classic_scanlog.ReportComposer.pool_stats` (method)
10. rust-only proxy: `ReportComposer` (class marker — paired with Python `ReportComposer`)

## 4. ReportGenerator (PyReportGenerator)

- **Rust wrapper file:** `classic-scanlog-py/src/report.rs:180-330`
- **`#[pyclass(name = "ReportGenerator")]`** — Python-facing name: `ReportGenerator`
- **`inner: ReportGenerator`** — wraps `classic_scanlog_core::ReportGenerator`
- **NO `#[derive(Clone)]`**

### Signatures

| Method | Signature | Notes |
|---|---|---|
| `new` | `#[new] fn new() -> Self` | Zero-arg constructor. Default impl present. |
| `with_config` | `#[staticmethod] fn with_config(classic_version: String, crashgen_name: String) -> Self` | Static factory with version/crashgen metadata. |
| `generate_header` | `fn generate_header(&self, crashlog_filename: String) -> PyReportFragment` | Returns `ReportFragment`. |
| `generate_error_section` | `fn generate_error_section(&self, main_error: String, crashgen_version: String, is_outdated: bool) -> PyReportFragment` | 3 args. |
| `generate_suspect_section_header` | `fn generate_suspect_section_header(&self) -> PyReportFragment` | No args. |
| `generate_suspect_found_footer` | `fn generate_suspect_found_footer(&self, found_suspect: bool) -> PyReportFragment` | Takes bool. |
| `generate_settings_section_header` | `fn generate_settings_section_header(&self) -> PyReportFragment` | No args. |
| `generate_mod_check_header` | `fn generate_mod_check_header(&self, check_type: String) -> PyReportFragment` | Takes check_type string. |
| `generate_plugin_suspect_header` | `fn generate_plugin_suspect_header(&self) -> PyReportFragment` | No args. |
| `generate_formid_section_header` | `fn generate_formid_section_header(&self) -> PyReportFragment` | No args. |
| `generate_record_section_header` | `fn generate_record_section_header(&self) -> PyReportFragment` | No args. |
| `generate_footer` | `fn generate_footer(&self) -> PyReportFragment` | No args. |
| `generate_suspect_section` | `fn generate_suspect_section(&self, py: Python<'_>, found_suspects: Vec<String>) -> PyResult<PyReportFragment>` | **DEPRECATED.** Emits `PyDeprecationWarning`. Still callable. |

### Contract rows (from deferred backlog)

15 rows total:
1. `classic_scanlog.ReportGenerator` (class)
2. `classic_scanlog.ReportGenerator.__init__` (method)
3. `classic_scanlog.ReportGenerator.with_config` (method — staticmethod)
4. `classic_scanlog.ReportGenerator.generate_header` (method)
5. `classic_scanlog.ReportGenerator.generate_error_section` (method)
6. `classic_scanlog.ReportGenerator.generate_suspect_section_header` (method)
7. `classic_scanlog.ReportGenerator.generate_suspect_found_footer` (method)
8. `classic_scanlog.ReportGenerator.generate_settings_section_header` (method)
9. `classic_scanlog.ReportGenerator.generate_mod_check_header` (method)
10. `classic_scanlog.ReportGenerator.generate_plugin_suspect_header` (method)
11. `classic_scanlog.ReportGenerator.generate_formid_section_header` (method)
12. `classic_scanlog.ReportGenerator.generate_record_section_header` (method)
13. `classic_scanlog.ReportGenerator.generate_footer` (method)
14. `classic_scanlog.ReportGenerator.generate_suspect_section` (method — deprecated)
15. rust-only proxy: `ReportGenerator` (class marker — paired with Python `ReportGenerator`)

## 5. ParallelReportProcessor (PyParallelReportProcessor)

- **Rust wrapper file:** `classic-scanlog-py/src/report.rs:332-360`
- **`#[pyclass(name = "ParallelReportProcessor")]`** — Python-facing name: `ParallelReportProcessor`
- **`pub struct PyParallelReportProcessor;`** — **EMPTY marker type.** No `inner` field. Not backed by any `-core` struct.
- **Default impl** — trivial.

### Signatures

| Method | Signature | Notes |
|---|---|---|
| `new` | `#[new] fn new() -> Self` | Zero-arg constructor. Returns unit struct. |
| `combine_fragments` | `#[staticmethod] fn combine_fragments(fragments: Vec<PyReportFragment>) -> PyReportFragment` | Static. Folds fragments via `ReportFragment::empty().combine(...)` loop. |

### R9 NOTE: No `-core` counterpart

`ParallelReportProcessor` is a **pure `-py` convenience class** — same pattern as `CancellationToken` from Wave 3a. There is NO `classic_scanlog_core::ParallelReportProcessor` type. The class exists only as a namespace for the static `combine_fragments` fold.

**Proxy pairing decision:** Per Wave 3a precedent (`py_class_to_core_symbol` mapping), pair `ParallelReportProcessor` and its methods with the nearest `-core` class in the same sub-module — `ReportComposer` (the dominant composition class in `-core::report`). All 3 contract rows pair with `rustSymbol=ReportComposer`.

### Contract rows (from deferred backlog)

3 rows total:
1. `classic_scanlog.ParallelReportProcessor` (class — paired with `ReportComposer`)
2. `classic_scanlog.ParallelReportProcessor.__init__` (method — paired with `ReportComposer`)
3. `classic_scanlog.ParallelReportProcessor.combine_fragments` (method — paired with `ReportComposer`)

## 6. Module-level rust-only marker

Backlog entry `python-deferred-scanlog-331` has `rustSymbols=['report']` and no `bindingIdentifiers`. This is a **bare module marker** row — a sentinel that asserts the `report` module itself is surface-visible in the `-core` lib.rs (already `pub mod report;` at line 39, confirmed). Same pattern as Wave 3a's `orchestrator`/`papyrus`/`version`/`crashgen_registry`/`segment_key`/`error` module markers.

**Proxy pairing:** `rustSymbol=report`, `pythonExportPath=ReportComposer` (nearest Python class in sub-module, Wave 3a convention). ID: `scanlog.report.report@rust`.

## Grand Total

- StringPool: 7 rows (6 Python + 1 rust-only)
- ReportFragment: 10 rows (9 Python + 1 rust-only)
- ReportComposer: 10 rows (9 Python + 1 rust-only)
- ReportGenerator: 15 rows (14 Python + 1 rust-only)
- ParallelReportProcessor: 3 rows (3 Python, 0 rust-only — the class has no -core type)
- Module marker: 1 row (1 rust-only)
- **Total: 46 rows** (41 Python + 5 rust-only)

Distribution check against plan target (plan says 46): **matches** (with the module marker).

## Python-class-to-core-symbol mapping (for row generator)

```python
py_class_to_core_symbol = {
    # Direct matches (Python name == -core name)
    "StringPool": "StringPool",
    "ReportFragment": "ReportFragment",
    "ReportComposer": "ReportComposer",
    "ReportGenerator": "ReportGenerator",
    # Pure -py convenience class (no -core type) — pair with dominant -core class in sub-module
    "ParallelReportProcessor": "ReportComposer",
}
```

## Stub file status

**Already covered, no edits needed.** All 5 classes + every method in the table above are declared in `classic_scanlog.pyi` lines 983-1334. Specifically:

- `StringPool` at line 983 — all 5 methods present (`__init__`, `intern`, `intern_batch`, `get_stats`, `clear`)
- `ReportFragment` at line 1025 — all 9 methods present
- `ReportComposer` at line 1106 — all 8 methods present
- `ReportGenerator` at line 1179 — all 14 methods present (including deprecated `generate_suspect_section`)
- `ParallelReportProcessor` at line 1314 — all 3 entries present

Task 2 is expected to be a **no-op** (verified via `mypy --strict` pass after contract row authoring). If any method is missing from the stub, Task 2 will add it; otherwise, Task 2 is effectively "confirm mypy still passes and commit no stub changes."

## Test scaffolding notes

- **StringPool clear check:** no `__len__`; use `get_stats()` tuple inspection. After `clear()`, all four counters should drop (or at least the unique_strings counter). Alternative: re-intern after clear and assert the returned string equals the input (functional correctness without touching stats).
- **ReportFragment field access:** the wrapper has NO exposed fields — only methods. Use `to_list()` + `len()` + `is_empty()` for inspection. Do NOT attempt `fragment.text` or `fragment.kind` — those don't exist.
- **ReportComposer.compose return type:** **list[str]** at the Python layer (not ReportFragment). The test must assert `isinstance(result, list)` not `isinstance(result, ReportFragment)`. This was a divergence from the plan scaffold's assumption.
- **ReportGenerator.generate_header:** returns `ReportFragment`. Tests can chain `gen.generate_header("test.log").to_list()` to verify non-empty output.
- **ParallelReportProcessor:** `combine_fragments` is a staticmethod, not an instance method. Call `ParallelReportProcessor.combine_fragments([...])`, not `instance.combine_fragments([...])`.
- **`minimal_analysis_result.json` fixture:** plan files_modified lists this fixture, but **NONE of the 5 report classes actually accept an `AnalysisResult` argument.** `ReportGenerator.generate_*` methods take strings/bools. The fixture is unused in Task 3 tests and should NOT be created. This is a plan scaffold artifact from an earlier draft assuming `ReportGenerator.generate(AnalysisResult)` — the real API is fragment-based.

## Plan scaffold divergences identified

Recorded here BEFORE any contract/test work, same discipline as Wave 3a:

1. **`minimal_analysis_result.json` is not needed.** None of the 5 report classes take `AnalysisResult` as input. The fixture path in `files_modified` is obsolete and should be omitted from Task 3's fixture creation.
2. **`ReportComposer.compose()` returns `list[str]`, not `ReportFragment`.** Plan Task 3 scaffold speculated `compose([]) -> str`; actual is `list[str]`.
3. **`StringPool` has no `__len__`.** Plan Task 3 scaffold's "len check after clear" must fall back to `get_stats()` tuple comparison.
4. **`ReportFragment` has no `text` or `kind` fields.** Plan Task 3 scaffold's `fragment.text/kind` hasattr check should use `to_list()`/`len()` instead.
5. **`ParallelReportProcessor` has no `-core` counterpart.** Must pair with `ReportComposer` in the row generator (Wave 3a precedent).
6. **`ReportGenerator` does NOT have a `generate(AnalysisResult)` method.** The plan Task 3 scaffold's `generator.generate(result)` is speculation — actual API is `generate_header(filename)`, `generate_error_section(error, version, bool)`, etc.
7. **`ReportGenerator.generate_suspect_section` is deprecated** but still callable — tests can exercise it behind a `warnings.catch_warnings()` filter to verify the deprecation path.
8. **The 46th row is a bare `['report']` module marker** (python-deferred-scanlog-331), NOT a ParallelReportProcessor.combine_fragments variant.
