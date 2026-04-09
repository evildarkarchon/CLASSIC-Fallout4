# Plan 08 Method Inventory (R5/R11/R13 verification)

**Purpose:** Ground-truth verified inventory of every symbol Plan 08 promotes to Tier-1.
Read before authoring contract rows, stubs, or tests. Avoids plan-scaffold guess-work.

**Source of truth:**

- `classic-shared-py` Rust source: `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs` (+ submodules `path_py.rs`, `strings_py.rs`, `performance_py.rs`, `exceptions.rs`, etc.)
- `classic-shared-py` stub: `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` (VERIFIED: all 6 `#[pymodule]` symbols already declared; stub is A8-complete)
- `classic-file-io-py` Rust source: `ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs` (+ full `-py` src tree for other classes)
- `classic-file-io-py` stub: `ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi` (VERIFIED: already covers FileHasher + all other PyO3 classes — stub is complete)
- Python surface parser output: `docs/implementation/python_api_parity/baseline/python_api_surface.json` (42 shared exports, 70 file_io exports)
- Rust surface parser output: `docs/implementation/python_api_parity/baseline/rust_api_surface.json` (24 `classic-shared-py` symbols, 36 `classic-file-io-core` symbols — 35 of those are `rust_unmapped` gaps)

---

## R3 Scope Correction (Plan 08 ground-truth)

The plan scaffold said Plan 08 owns 11 rows (6 shared + 5 file_io). The **actual** gap surface per the fresh parity parser is:

| Domain | python_unmapped | rust_unmapped | Total |
|---|---|---|---|
| shared | 42 | 23 | **65** |
| file_io | 70 | 35 | **105** |
| **Plan 08 total** | **112** | **58** | **170** |

Projected final `tier1Mappings.length` = 349 + 170 = **519** (NOT 358 as plan scaffold claimed).

Per R3: Plan 08 owns ALL file_io rows surfaced by the parser. Plan 09a residual promotion explicitly excludes file_io. shared is symmetrically an atomic unit for this plan.

---

## classic_shared Inventory (A8 — stub already complete)

### #[pymodule] surface (6 top-level symbols from `src/lib.rs:322-338`)

```rust
#[pymodule]
fn classic_shared(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyStringProcessor>()?;       // -> Python name: StringProcessor
    m.add_class::<PyPathHandler>()?;            // -> Python name: PathHandler
    m.add_class::<PyRustPerformanceMonitor>()?; // -> Python name: RustPerformanceMonitor
    m.add_class::<RuntimeStats>()?;             // (no rename) RuntimeStats
    m.add_function(wrap_pyfunction!(get_runtime_stats, m)?)?;
    m.add_function(wrap_pyfunction!(is_runtime_healthy, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
```

### PathHandler (`#[pyclass(name = "PathHandler")]` → verified from `classic_shared.pyi`)

- `__init__(cache_ttl_seconds: int = 300)` — parameterless with default
- `cache_metrics() -> tuple[int, int, float]`
- `cache_stats() -> tuple[int, int]`
- `cleanup_cache() -> None`
- `clear_cache() -> None`
- `common_prefix(paths: list[str]) -> str | None`
- `get_extension(path: str) -> str | None`
- `get_filename(path: str) -> str | None`
- `get_parent(path: str) -> str | None`
- `is_absolute(path: str) -> bool`
- `join_paths(base: str, components: list[str]) -> str`
- `normalize_path(path: str) -> str` — **NOT `normalize` (R11 correction)**
- `split_path(path: str) -> list[str]`
- `split_path_fast(path: str) -> list[str]`
- `to_absolute(path: str, base: str | None = None) -> str`
- `validate_paths_batch(paths: list[str]) -> list[tuple[str, bool, str]]`
- `validate_paths_batch_fast(paths: list[str]) -> list[tuple[str, bool, str]]`

### StringProcessor (`#[pyclass(name = "StringProcessor")]`)

- `__init__() -> None` — parameterless
- `clear_pool() -> None`
- `common_prefix(strings: list[str]) -> str`
- `intern(s: str) -> str`
- `intern_batch(strings: list[str]) -> list[str]`
- `join_lines(lines: list[str], separator: str) -> str`
- `normalize(s: str) -> str`
- `pool_stats() -> int`
- `process_batch(strings: list[str], operation: str) -> list[str]`
- `process_batch_fast(strings: list[str], operation: str) -> list[str]`
- `split_lines(text: str) -> list[str]`
- `split_lines_fast(text: str) -> list[str]`

### RustPerformanceMonitor (`#[pyclass(name = "RustPerformanceMonitor")]`)

- `__init__() -> None` — parameterless
- `clear_metrics() -> None`
- `get_all_stats() -> dict[str, dict[str, object]]`
- `get_operation_stats(operation: str) -> dict[str, object] | None`
- `record_metric(operation: str, duration_ms: int, bytes_processed: int | None = None) -> None`
  **R11 NOTE:** takes 3 positional args. Test must pass all three or rely on the default for `bytes_processed`.
- `start_timer(operation: str) -> dict[str, object]`
- `stop_timer(timer_info: dict[str, object], bytes_processed: int | None = None) -> None`

### RuntimeStats (`#[pyclass]`, lib.rs:252 area)

- **NO `#[new]`** — cannot be constructed directly from Python. Use `get_runtime_stats()` factory.
- Bare attributes (not methods):
  - `worker_threads: int`
  - `is_healthy: bool`
- **R11 CLARIFICATION:** `is_healthy` is a bare attribute, NOT a method. Assertion is `assert stats.is_healthy is True` (no parens).

### Module-level free functions

- `get_runtime_stats() -> RuntimeStats` — factory for RuntimeStats (the only way to obtain one)
- `is_runtime_healthy() -> bool`

### classic-shared-py rust-only symbols (23 unmapped, all in `classic-shared-py` crate)

These are `pub use` re-exports, modules, or function items at the crate root that have no direct Python counterpart. They pair with the nearest Python class via the `@rust`-suffix proxy pattern (Wave 1 / Plan 06 / Plan 07 precedent).

From `rust_api_surface.json::symbols[crate=='classic-shared-py']`:

| Symbol | Kind | Proxy pair |
|---|---|---|
| ClassicError | reexport | RuntimeStats (nearest top-level class) |
| ClassicResult | reexport | RuntimeStats |
| PathLike | reexport | PathHandler |
| PyPathHandler | reexport | PathHandler (class alias) |
| PyRustPerformanceMonitor | reexport | RustPerformanceMonitor |
| PyStringProcessor | reexport | StringProcessor |
| ResultExt | reexport | RuntimeStats |
| ToPyErr | reexport | RuntimeStats |
| error_convert | module | RuntimeStats |
| exceptions | module | RuntimeStats |
| get_runtime | reexport | RuntimeStats (runtime-adjacent) |
| indexmap_utils | module | RuntimeStats |
| path | module | PathHandler |
| path_py | module | PathHandler |
| performance_py | module | RustPerformanceMonitor |
| pyany_to_indexmap_str | reexport | RuntimeStats |
| pyany_to_indexmap_vecstr | reexport | RuntimeStats |
| pydict_to_indexmap_str | reexport | RuntimeStats |
| pydict_to_indexmap_str_optional | reexport | RuntimeStats |
| pydict_to_indexmap_vecstr | reexport | RuntimeStats |
| resolve_python_entry_dir | function | RuntimeStats |
| strings_py | module | StringProcessor |
| to_py_err | function | RuntimeStats |

Note: `RuntimeStats` appears in `rust_api_surface.json` as a `struct` but also as a gap — that's because the Python surface parser sees `RuntimeStats` (which is `Tier-2` currently) but the contract has zero `ownerModule='shared'` rows, so the rust-side `RuntimeStats` counts as `rust_unmapped` too. It will be a regular Python row (not @rust-suffixed) and the rust_unmapped gap will be satisfied through its rustSymbol.

---

## classic_file_io Inventory (stub already complete)

### #[pymodule] surface (from `classic-file-io-py/src/lib.rs`, cross-referenced to stub)

Classes exposed by PyO3:

1. **FileIOCore** — async file I/O core with `#[new]` constructor
2. **FileHasher** (`PyFileHasher`) — **NO `#[new]`, all methods are `#[staticmethod]`** (R13 critical)
3. **DDSHeader** — DDS texture header with `from_bytes` factory (no `#[new]`)
4. **EncodingDetector** — `#[new]` parameterless
5. **FileGenerator** — `#[new]` takes `FileGeneratorConfig`
6. **FileGeneratorConfig** — `#[new]` takes 3 strings
7. **PyLogCollector** (`LogCollector`) — `#[new]` takes paths
8. **PyLineStreamer** — async iterator, obtained via `FileIOCore.stream_lines()`
9. **PySyncLineStreamer** — sync iterator, obtained via `FileIOCore.stream_lines_sync()`
10. **FileHasherCacheStats** — TypedDict (stub-only, not a runtime class)

Module-level free functions:

- `generate_ignore_file_async(content: str) -> bool` (async)
- `generate_local_yaml_async(content: str, game_name: str) -> bool` (async)

Exception classes:

- `RustFileIOError` (base)
- `RustFileIOIOError`
- `RustFileIOParseError`

### FileHasher (R13 — VERIFIED staticmethod nature)

Source: `ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs` lines 30-180.

```rust
#[pyclass(name = "FileHasher", module = "classic_file_io")]
pub struct PyFileHasher;  // Empty unit struct. NO #[new].

#[pymethods]
impl PyFileHasher {
    #[staticmethod] fn hash_file(path: &str) -> PyResult<String> { ... }
    #[staticmethod] fn hash_files_parallel<'py>(py: Python<'py>, paths: Vec<String>) -> PyResult<Bound<'py, PyDict>> { ... }
    #[staticmethod] fn hash_files_to_map<'py>(py: Python<'py>, paths: Vec<String>) -> PyResult<Bound<'py, PyDict>> { ... }
    #[staticmethod] fn clear_cache() { ... }
    #[staticmethod] fn cache_size() -> usize { ... }
    #[staticmethod] fn cache_stats(py: Python<'_>) -> PyResult<Py<PyAny>> { ... }
    #[staticmethod] fn reset_cache_stats() { ... }
}
```

**ALL 7 methods are `#[staticmethod]`** — call via class, not instance. Attempting `FileHasher()` raises `TypeError` because there is no constructor.

### R13 test pattern correction

**WRONG:**
```python
hasher = classic_file_io.FileHasher()  # TypeError — no __init__
hasher.cache_size()
```

**CORRECT:**
```python
# Static methods — call via class, not instance
initial = classic_file_io.FileHasher.cache_size()
classic_file_io.FileHasher.clear_cache()
assert classic_file_io.FileHasher.cache_size() == 0
```

### R13 cache_size semantics

Verified from `classic-file-io-core/src/hash.rs:308`:

```rust
pub fn cache_size() -> usize {
    Self::cache_stats().size  // HASH_CACHE.len() — ENTRY COUNT, NOT BYTES
}
```

After `clear_cache()`, `cache_size() == 0` is correct behavior. Do NOT assert non-zero.

### classic_file_io python-only gap bindings (70 per python_api_surface)

Classes + methods tracked as gaps (each is a contract row in Plan 08):

- `DDSHeader` class + 6 methods (from_bytes, has_mipmaps, has_power_of_2_dimensions, has_valid_bc_dimensions, is_bc_compressed, is_reasonable_size)
- `EncodingDetector` class + `__init__`, `detect_encoding`
- `FileGenerator` class + `__init__`, `config`, `generate_all_files_async`, `generate_ignore_file_async`, `generate_local_yaml_async`, `ignore_file_path`, `local_yaml_path`
- `FileGeneratorConfig` class + `__init__`
- `FileHasher` class + `cache_size`, `cache_stats`, `clear_cache`, `hash_file`, `hash_files_parallel`, `hash_files_to_map`, `reset_cache_stats` (7 methods — all static)
- `FileHasherCacheStats` (TypedDict)
- `FileIOCore` class + `__init__` + 21 methods (append_file, clear_cache, file_exists, get_file_info, get_file_size, py_read_multiple_files, py_walk_directory, py_write_multiple_files, read_bytes, read_dds_header, read_dds_headers_batch, read_file, read_file_mmap, read_file_with_encoding, read_lines, stream_lines, stream_lines_sync, write_bytes, write_file, write_lines)
- `PyLineStreamer` class + `__aiter__`, `__anext__`
- `PyLogCollector` class + `__init__`, `collect_all`, `collect_crash_logs`, `copy_from_xse_folder`, `crash_logs_dir`, `move_from_base_folder`, `pastebin_dir`
- `PySyncLineStreamer` class + `__iter__`, `__next__`
- `RustFileIOError`, `RustFileIOIOError`, `RustFileIOParseError` (3 exception classes)
- Module-level `generate_ignore_file_async`, `generate_local_yaml_async` functions

### classic_file_io rust-only gap symbols (35 per rust_api_surface, all `classic-file-io-core`)

| Symbol | Kind | Proxy pair |
|---|---|---|
| BackupInfo | reexport | FileIOCore (nearest top-level class in stub) |
| BackupManager | reexport | FileIOCore |
| BackupType | reexport | FileIOCore |
| CRASH_AUTOSCAN_PATTERN | reexport | FileIOCore |
| CRASH_LOG_PATTERN | reexport | FileIOCore |
| DDSAnalyzer | reexport | DDSHeader |
| DDSHeader | reexport | DDSHeader (direct) |
| DDSIssue | reexport | DDSHeader |
| EncodingDetector | reexport | EncodingDetector (direct) |
| FileGenerator | reexport | FileGenerator (direct) |
| FileGeneratorConfig | reexport | FileGeneratorConfig (direct) |
| FileHasher | reexport | FileHasher (direct) |
| FileIOCore | reexport | FileIOCore (direct) |
| FileIOError | reexport | RustFileIOError |
| FileOperation | reexport | FileIOCore |
| FileOperationResult | reexport | FileIOCore |
| GameFilesManager | reexport | FileIOCore |
| GameTarget | reexport | FileIOCore |
| LogCollector | reexport | PyLogCollector (direct) |
| RejectedInput | reexport | FileIOCore |
| TargetedResolution | reexport | FileIOCore |
| backup | module | FileIOCore |
| calculate_similarity | reexport | FileIOCore |
| core | module | FileIOCore |
| dds | module | DDSHeader |
| encoding | module | EncodingDetector |
| game_files | module | FileIOCore |
| generate_ignore_file | reexport | `generate_ignore_file_async` (module-level) |
| generate_local_yaml | reexport | `generate_local_yaml_async` (module-level) |
| generation | module | FileGenerator |
| hash | module | FileHasher |
| log_collection | module | PyLogCollector |
| resolve_targeted_inputs | reexport | FileIOCore |
| similarity | module | FileIOCore |
| similarity_ratio | reexport | FileIOCore |

---

## Python gap path → Rust symbol resolution rules

For Plan 08 contract rows, each python_unmapped gap must map to a rust_symbol. Rules:

1. **Class rows** (e.g. `PathHandler`): `rustSymbol = PyPathHandler` (the `#[pyclass(name="X")]` source type)
2. **Method rows** (e.g. `PathHandler.normalize_path`): `rustSymbol = PyPathHandler` (same class, the method lives on the Python side of the contract; Rust just exposes the class)
3. **Module-level functions** (e.g. `get_runtime_stats`): `rustSymbol = get_runtime_stats`
4. **Exception classes** (e.g. `RustFileIOError`): `rustSymbol = FileIOError` (the `-core` error type)
5. **Rust-only symbols**: `id = <owner>.<sub>.<symbol>@rust`, `rustSymbol = <symbol>`, `pythonExportPath = <nearest-class>` (proxy pair pattern)

For `classic_shared`, the sub-module routing matches file origin:

- `PathHandler.*` → `shared.path.*`
- `StringProcessor.*` → `shared.strings.*`
- `RustPerformanceMonitor.*` → `shared.performance.*`
- `RuntimeStats`, `get_runtime_stats`, `is_runtime_healthy` → `shared.runtime.*`
- rust-only path/path_py/PathLike → `shared.path.<sym>@rust`
- rust-only strings_py/PyStringProcessor → `shared.strings.<sym>@rust`
- rust-only performance_py/PyRustPerformanceMonitor → `shared.performance.<sym>@rust`
- rust-only error/exceptions/indexmap_utils/etc. → `shared.runtime.<sym>@rust`

For `classic_file_io`, sub-module routing matches the `-core` file origin:

- `FileIOCore.*` → `file_io.core.*`
- `FileHasher.*` → `file_io.hash.*`
- `DDSHeader.*` → `file_io.dds.*`
- `EncodingDetector.*` → `file_io.encoding.*`
- `FileGenerator*.*`, `generate_*_async` → `file_io.generation.*`
- `PyLogCollector.*`, `PyLineStreamer.*`, `PySyncLineStreamer.*` → `file_io.log_collection.*`
- `RustFileIO*Error` → `file_io.error.*`
- `FileHasherCacheStats` (TypedDict) → `file_io.hash.*`

---

## Anti-hasattr rule (R1) for smoke tests

Every smoke test must assert on a **real value** obtained through a **real call chain**. No `try/except AttributeError: pass` fallbacks. No `hasattr(...)` guards that bypass assertions. If a class is factory-only (like `RuntimeStats`), obtain an instance via its factory (`get_runtime_stats()`) and exercise its attributes.

Reference: Plan 07 deviation #6 (plan-scaffold hasattr tests rewritten to singleton-fetched factory pattern).
