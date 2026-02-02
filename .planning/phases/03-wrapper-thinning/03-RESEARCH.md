# Phase 3: Wrapper Thinning - Research

**Researched:** 2026-02-02
**Domain:** Python-to-Rust migration via PyO3, wrapper pattern thinning
**Confidence:** HIGH

## Summary

Phase 3 targets three fat Python wrappers in `ClassicLib/integration/rust/` that contain business logic that should live in Rust `-core` crates. The wrappers are: `file_io_rust.py` (937 lines), `parser_rust.py` (320 lines), and `formid_rust.py` (325 lines). The goal is to reduce them to pure marshalling adapters (file_io under 200 lines, parser and formid each under 150 lines).

The good news: the Rust side already has comprehensive `-core` crates (`classic-file-io-core` and `classic-scanlog-core`) with the PyO3 `-py` binding layers (`classic-file-io-py` and `classic-scanlog-py`) already following the thin adapter pattern. The Python wrappers are fat because they contain: (1) fallback logic and error handling, (2) business logic like `_parse_crash_header`, segment boundary definitions, plugin caching with MD5 hashing, and (3) the `SyncWrapper` inner class with full API duplication.

**Primary recommendation:** Systematically move each piece of business logic from the Python wrappers into the Rust `-core` crates, expose it through the `-py` binding layer, then reduce the Python wrapper to: import, detect, call Rust, convert types. The existing crate structure already supports this -- no new crates needed.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Workspace)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyO3 | 0.27.2 | Python-Rust bindings | Already used, workspace-pinned |
| pyo3-async-runtimes | 0.27.0 | Async bridge for PyO3 | Already used for `future_into_py` |
| Tokio | 1.49.0 | Async runtime | Single runtime via `get_runtime()` |
| classic-shared-py | local | PathLike, without_gil, exceptions | Already provides shared patterns |
| classic-shared-core | local | get_runtime(), ClassicError | Foundation for all -core crates |

### Supporting (Already in Workspace)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| thiserror | 2.0 | Error derive macros | All error types in -core crates |
| dashmap | 6.1 | Concurrent hash maps | Plugin caching in Rust |
| rayon | 1.10 | Parallel iteration | Batch operations |
| tracing | (add) | Structured logging | Internal Rust logging per CONTEXT.md |

### No New Dependencies Needed
This phase uses the existing workspace dependency set. The only potential addition is `tracing` if not already present (for Rust-side internal logging as specified in CONTEXT.md decisions).

**Installation:** N/A -- all dependencies already in `rust/Cargo.toml` workspace.

## Architecture Patterns

### Existing Three-Layer Architecture (Follow Exactly)
```
rust/
├── foundation/
│   ├── classic-shared-core/     # get_runtime(), ClassicError
│   └── classic-shared-py/       # PathLike, without_gil, define_exceptions!
├── business-logic/
│   ├── classic-file-io-core/    # FileIOCore (already has all file ops)
│   └── classic-scanlog-core/    # LogParser, FormIDAnalyzer, FormIDAnalyzerCore
└── python-bindings/
    ├── classic-file-io-py/      # PyFileIOCore (already thin)
    └── classic-scanlog-py/      # PyLogParser, PyFormIDAnalyzer
```

### Pattern 1: Thin Python Wrapper (Target Pattern)
**What:** Python wrapper does ONLY: detect availability, convert types, call Rust, return result.
**When to use:** Every function in every wrapper after migration.
**Example of what the wrappers should look like after thinning:**
```python
# AFTER thinning - pure marshalling
class FileIOCore:
    def __init__(self, encoding="utf-8", errors="ignore"):
        self._rust_core = None
        self._python_core = None
        if RUST_AVAILABLE and _rust_io:
            self._rust_core = _rust_io(encoding=encoding, errors=errors, cache_size=100, max_concurrent_io=50)
        if not self._rust_core:
            from ClassicLib.integration.python.file_io_py import PythonFileIO
            self._python_core = PythonFileIO(encoding, errors)

    async def read_file(self, path: Path | str) -> str:
        if self._rust_core:
            return await self._rust_core.read_file(str(path))
        return await self._python_core.read_file(path)
```

### Pattern 2: Rust PyO3 Async Binding (Existing Pattern -- Follow It)
**What:** Use `future_into_py` for async methods, `without_gil` for blocking methods.
**Example (from classic-file-io-py/src/core.rs):**
```rust
// Async method: returns Python coroutine
pub fn py_read_file<'py>(&self, py: Python<'py>, path: PathLike) -> PyResult<Bound<'py, PyAny>> {
    let inner = self.inner.clone();
    let path_buf: PathBuf = path.into();
    future_into_py(py, async move {
        inner.read_file(&path_buf).await.map_err(to_pyerr)
    })
}

// Sync blocking method: releases GIL
pub fn read_dds_header(&self, py: Python<'_>, path: PathLike) -> PyResult<Option<(u32, u32)>> {
    let path_buf: PathBuf = path.into();
    without_gil(py, || {
        get_runtime().block_on(async { /* ... */ })
    })
}
```

### Pattern 3: Error Mapping (Existing Pattern)
**What:** Each `-py` crate has a `to_pyerr` function mapping core errors to Python exceptions.
**Example (from classic-file-io-py/src/lib.rs):**
```rust
pub fn to_pyerr(err: classic_file_io_core::FileIOError) -> PyErr {
    match err {
        FileIOError::IoError(e) => RustFileIOIOError::new_err(format!("I/O error: {}", e)),
        FileIOError::NotFound(s) => RustFileIOIOError::new_err(format!("File not found: {}", s)),
        FileIOError::DDSError(s) => RustFileIOParseError::new_err(format!("DDS error: {}", s)),
        // ...
    }
}
```

### Pattern 4: Exception Hierarchy (Existing Pattern)
**What:** Each `-py` crate defines 3-tier exceptions using `define_exceptions!` macro.
```rust
define_exceptions!(
    module: classic_file_io,
    base: RustFileIOError,
    io: RustFileIOIOError,
    parse: RustFileIOParseError
);
```
Python side catches these via `ClassicLib/integration/exceptions.py` hierarchy.

### Anti-Patterns to Avoid
- **Business logic in Python wrapper:** The `_parse_crash_header` method in `parser_rust.py` duplicates logic that should be in Rust `LogParser.parse_complete()`.
- **Python-side caching:** The MD5-based `_plugin_cache_key` in `formid_rust.py` should move to Rust.
- **hasattr() feature detection:** The `hasattr(self._rust_parser, "parse_complete")` checks in Python should be removed -- the Rust side should always expose the optimized method.
- **SyncWrapper inner class:** The entire `SyncWrapper` in `file_io_rust.py` (lines 889-937) is boilerplate that should be eliminated.
- **Multi-layer fallback chains:** Three-deep fallback (Rust core -> Rust simple -> Python) in `formid_rust.py` should be simplified to Rust -> Python only.

## Codebase Analysis: What Business Logic Lives Where

### file_io_rust.py (937 lines -> target 200)

**Logic that STAYS in Python wrapper (marshalling only):**
- `__init__`: Rust detection, fallback creation (~15 lines)
- Each method: `if rust: call rust else: call python` (~3-5 lines each)
- `is_rust_accelerated` property (~2 lines)

**Logic that is ALREADY in Rust (just remove Python duplication):**
- All core read/write operations (read_file, write_file, etc.) -- Rust `-py` already exposes these
- DDS header operations -- already in Rust
- Directory walking -- already in Rust
- Batch operations -- already in Rust
- File metadata operations -- already in Rust

**Logic to ELIMINATE (not move, just remove):**
- `_ensure_path` helper (Rust PathLike handles this)
- `_get_rust_exception_types` and all exception tuple construction (lines 90-119) -- Python wrapper should not catch Rust exceptions and re-raise; let them propagate
- Manual fallback logic in each method body (the `if self._rust_core: try/except: ...` chains)
- `SyncWrapper` inner class (lines 889-937) -- this is `create_file_io_sync()` creating a wrapper of a wrapper
- `get_rust_file_io()` convenience function
- `read_crash_log` and `write_crash_report` methods (lines 804-840) -- these are business logic (trailing whitespace stripping, .md extension conversion) that should be in Rust or in a higher-level Python module

**Functions with embedded business logic to MOVE to Rust:**
- `read_crash_log`: Strips trailing empty lines -- move to Rust `-core`
- `write_crash_report`: Converts path suffix to `.md` -- move to Rust `-core`

### parser_rust.py (320 lines -> target 150)

**Logic that STAYS:**
- `__init__`: Rust detection (~15 lines)
- `find_segments`: call Rust, return result (~5 lines)
- `extract_section`: call Rust, return result (~5 lines)
- `is_rust_accelerated` property (~2 lines)

**Logic to MOVE to Rust:**
- `_parse_crash_header` static method (lines 279-307): Header parsing logic that is duplicated from Python -- this is already in Rust's `LogParser.parse_crash_header()` but the Python wrapper has its own version as a fallback path
- Segment boundary definitions (lines 166-173): These hardcoded boundary tuples should be defined in Rust, not constructed in Python
- Segment post-processing: `[[line.strip() for line in segment] for segment in segments]` -- Rust `parse_complete` already does trimming

**Logic to ELIMINATE:**
- `hasattr(self._rust_parser, "parse_complete")` feature detection (line 164) -- always use `parse_complete`, it exists in current Rust
- Legacy multiple-FFI-call path (lines 191-212) -- `parse_complete` is the only path
- Exception tuple construction (lines 63-87)
- All the try/except/fallback chains in each method

### formid_rust.py (325 lines -> target 150)

**Logic that STAYS:**
- `__init__`: Rust detection (~15 lines)
- `extract_formids`: call Rust, return result (~5 lines)
- `formid_match`: call Rust, return result (~5 lines)
- `extract_formids_batch`: call Rust, return result (~5 lines)
- `is_rust_accelerated` property (~2 lines)

**Logic to MOVE to Rust:**
- Plugin caching with MD5 key (lines 238-246): `hashlib.md5(str(sorted(plugins.items())).encode()).hexdigest()` should be Rust-side
- ReportFragment creation from result lines (lines 253-257): Rust should return structured report data

**Logic to ELIMINATE:**
- Multi-path initialization: `FormIDAnalyzerCore` vs `FormIDAnalyzer` vs Python (lines 128-162) -- use one Rust path
- `hasattr` feature detection for `extract_formids_nocopy`, `process_formids_cached`, `cache_plugins` (multiple lines)
- Exception tuple construction (lines 61-90)
- On-demand Python analyzer creation (lines 214-217, 275-279)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path conversion Python->Rust | Manual `str(path)` everywhere | `PathLike` from `classic-shared-py` | Already handles pathlib.Path, str, os.PathLike |
| GIL release for blocking ops | Manual `py.detach()` calls | `without_gil(py, \|\| {...})` | Already in classic-shared-py, tested |
| Async Rust -> Python coroutine | Manual coroutine creation | `future_into_py(py, async move {...})` | pyo3-async-runtimes handles all edge cases |
| Exception hierarchy creation | Manual `create_exception!` calls | `define_exceptions!` + `register_exceptions!` macros | Already in classic-shared-py |
| Error conversion to PyErr | Manual match in each crate | `to_pyerr` function per crate | Existing pattern, keeps error mapping centralized |
| Golden file test framework | Custom comparison code | pytest with file fixtures | Standard pytest parametrize + tmp_path + snapshot comparison |

**Key insight:** The project already has all the infrastructure for thin wrappers. The `-py` crates already follow the thin adapter pattern. The problem is purely that the Python wrapper layer duplicated logic instead of delegating.

## Common Pitfalls

### Pitfall 1: Breaking the Fallback Chain
**What goes wrong:** Moving logic to Rust and removing the Python fallback path simultaneously.
**Why it happens:** Desire to clean up aggressively; forgetting that CONTEXT.md mandates fallback preservation until Phase 5.
**How to avoid:** Thin the wrapper but KEEP the `if self._rust_core: ... else: python_fallback` structure. The Python fallback module (`ClassicLib/integration/python/`) must continue to work.
**Warning signs:** Tests pass only when Rust is available; `CLASSIC_DISABLE_RUST=1` breaks everything.

### Pitfall 2: Changing Return Types Without Updating Callers
**What goes wrong:** Rust returns a different structure (e.g., dict vs tuple) and callers break.
**Why it happens:** Rust APIs may use different conventions than Python originals.
**How to avoid:** CONTEXT.md says "callers are updated in this phase" -- but golden file tests must capture the CURRENT output format FIRST. If Rust returns different format, update both the `-py` binding AND the callers. Do not change just one.
**Warning signs:** Integration tests failing after wrapper thinning.

### Pitfall 3: Exception Type Mismatch After Thinning
**What goes wrong:** Python code catches `RustParseError` or `RustIOError` but the thinned wrapper lets raw Rust exceptions propagate with different types.
**Why it happens:** The fat wrappers catch Rust exceptions and re-raise or fall back; after thinning, exception types change.
**How to avoid:** Verify all callers' exception handling. The Rust `-py` crates already map to custom exception types (`RustFileIOError`, etc.) -- make sure the Python `ClassicLib/integration/exceptions.py` hierarchy matches.
**Warning signs:** Uncaught exceptions in production paths.

### Pitfall 4: Golden File Format Sensitivity
**What goes wrong:** Golden files compared with exact string match fail due to path separators, timestamps, floating-point precision, or encoding differences.
**Why it happens:** Windows vs Unix path separators, locale-dependent formatting.
**How to avoid:** Normalize paths in golden file output (use forward slashes), strip timestamps, use approximate float comparison. Define a golden file comparison utility.
**Warning signs:** Golden tests pass on one OS but fail on another.

### Pitfall 5: Forgetting to Test with Rust Disabled
**What goes wrong:** The Python fallback path rots because all testing is done with Rust active.
**Why it happens:** Rust is always built in dev environment.
**How to avoid:** Run test suite with `CLASSIC_DISABLE_RUST=1` as part of CI/verification.
**Warning signs:** `get_rust_file_io()` returns None but nobody tested that path.

### Pitfall 6: SyncWrapper Removal Breaking GUI Code
**What goes wrong:** Removing `create_file_io_sync()` and `SyncWrapper` breaks GUI code that depends on synchronous file I/O.
**Why it happens:** GUI workers use `SyncWrapper` through `create_file_io_sync()`.
**How to avoid:** Check all callers of `create_file_io_sync()` before removing. Either update GUI code to use async or keep a minimal sync adapter. Search for `create_file_io_sync` in all Python files.
**Warning signs:** GUI file operations hang or crash.

## Code Examples

### Example 1: Target Thin Wrapper Pattern (file_io_rust.py after thinning)
```python
"""Rust-accelerated FileIOCore wrapper -- thin marshalling adapter."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Any
from ClassicLib.integration.factory import detect_component

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

RUST_AVAILABLE, _rust_io = detect_component("classic_file_io", "FileIOCore")

class FileIOCore:
    """Thin adapter: type conversion + Rust delegation only."""

    def __init__(self, encoding: str = "utf-8", errors: str = "ignore") -> None:
        self._rust_core = None
        self._python_core = None
        if RUST_AVAILABLE and _rust_io:
            self._rust_core = _rust_io(encoding=encoding, errors=errors,
                                        cache_size=100, max_concurrent_io=50)
        if not self._rust_core:
            from ClassicLib.integration.python.file_io_py import PythonFileIO
            self._python_core = PythonFileIO(encoding, errors)

    @property
    def is_rust_accelerated(self) -> bool:
        return self._rust_core is not None

    async def read_file(self, path: Path | str) -> str:
        if self._rust_core:
            return await self._rust_core.read_file(str(path))
        return await self._python_core.read_file(path)

    # ... each method follows same 3-line pattern
```

### Example 2: Golden File Test Pattern
```python
"""Golden file test for FileIOCore migration."""
import json
import pytest
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden_files"

@pytest.fixture
def capture_golden(request):
    """Capture Python implementation output as golden file."""
    golden_path = GOLDEN_DIR / f"{request.node.name}.json"
    def _capture(output):
        if not golden_path.exists():
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(json.dumps(output, indent=2, default=str))
        return json.loads(golden_path.read_text())
    return _capture

@pytest.mark.unit
async def test_read_crash_log_golden(capture_golden, tmp_path):
    """Verify Rust read_crash_log matches Python original."""
    # Setup
    log_file = tmp_path / "crash.log"
    log_file.write_text("line1\nline2\n\n\n")

    # Get Python baseline
    from ClassicLib.integration.python.file_io_py import PythonFileIO
    py_io = PythonFileIO()
    py_result = await py_io.read_lines(log_file)
    # Apply business logic that was in Python wrapper
    while py_result and not py_result[-1].strip():
        py_result.pop()
    golden = capture_golden(py_result)

    # Verify Rust matches
    from ClassicLib.integration.rust.file_io_rust import FileIOCore
    rust_io = FileIOCore()
    rust_result = await rust_io.read_crash_log(log_file)
    assert rust_result == golden
```

### Example 3: Collect-and-Continue in Rust
```rust
// In classic-file-io-core - batch operation with partial success
pub async fn read_multiple_files(
    &self,
    paths: Vec<PathBuf>,
) -> Vec<(PathBuf, Result<String, FileIOError>)> {
    let mut results = Vec::with_capacity(paths.len());
    for path in paths {
        let result = self.read_file(&path).await;
        results.push((path, result));
    }
    results
    // Caller gets ALL results, can inspect individual errors
}
```

### Example 4: Moving Business Logic to Rust -core
```rust
// In classic-file-io-core/src/core.rs - add crash log specific operations

/// Read crash log and strip trailing empty lines.
///
/// This ensures consistent output regardless of how the crash log
/// was generated (some generators add trailing newlines).
pub async fn read_crash_log(&self, path: &Path) -> Result<Vec<String>, FileIOError> {
    let mut lines = self.read_lines(path).await?;
    // Strip trailing empty lines for consistency
    while lines.last().is_some_and(|l| l.trim().is_empty()) {
        lines.pop();
    }
    Ok(lines)
}

/// Write crash report to markdown file.
///
/// Converts the output path to .md extension and writes the report.
pub async fn write_crash_report(
    &self,
    path: &Path,
    report_lines: Vec<String>,
) -> Result<PathBuf, FileIOError> {
    let report_path = path.with_extension("md");
    let content = report_lines.join("");  // Lines already have newlines
    self.write_file(&report_path, &content).await?;
    Ok(report_path)
}
```

## Specific Migration Inventory

### file_io_rust.py: Function-by-Function Analysis

| Function | Lines | Status in Rust | Migration Action |
|----------|-------|---------------|------------------|
| `__init__` | 20 | N/A | Simplify, keep |
| `_ensure_path` | 8 | PathLike handles this | Remove |
| `_get_rust_exception_types` | 20 | N/A | Remove |
| `read_file` | 14 | Already in Rust | Thin to 3 lines |
| `read_lines` | 12 | Already in Rust | Thin to 3 lines |
| `stream_lines` | 20 | Already in Rust | Thin to 5 lines |
| `stream_lines_sync` | 18 | Already in Rust | Thin to 3 lines |
| `read_bytes` | 12 | Already in Rust | Thin to 3 lines |
| `read_file_mmap` | 10 | Already in Rust | Thin to 3 lines |
| `read_file_with_encoding` | 10 | Already in Rust | Thin to 3 lines |
| `write_file` | 14 | Already in Rust | Thin to 3 lines |
| `write_lines` | 16 | Already in Rust | Thin to 3 lines |
| `write_bytes` | 14 | Already in Rust | Thin to 3 lines |
| `append_file` | 16 | Already in Rust | Thin to 3 lines |
| `read_dds_header` | 18 | Already in Rust | Thin to 3 lines |
| `read_dds_headers_batch` | 14 | Already in Rust | Thin to 3 lines |
| `walk_directory` | 30 | Already in Rust | Thin to 3 lines |
| `read_multiple_files` | 24 | Already in Rust | Thin to 3 lines |
| `write_multiple_files` | 16 | Already in Rust | Thin to 3 lines |
| `file_exists` | 6 | Already in Rust | Thin to 2 lines |
| `get_file_size` | 10 | Already in Rust | Thin to 2 lines |
| `get_file_info` | 10 | Already in Rust | Thin to 2 lines |
| `read_crash_log` | 6 | **Move to Rust** | Add to -core, thin to 3 lines |
| `write_crash_report` | 8 | **Move to Rust** | Add to -core, thin to 3 lines |
| `clear_cache` | 3 | Already in Rust | Thin to 2 lines |
| `SyncWrapper` class | 48 | N/A | Check callers, remove or keep minimal |
| `get_rust_file_io` | 5 | N/A | Remove (use factory) |
| `create_file_io_sync` | 10 | N/A | Check callers, potentially remove |
| Exception boilerplate | ~30 | N/A | Remove entirely |
| Module docstring | 62 | N/A | Reduce to 5 lines |

**Estimated thinned size:** ~180 lines (21 methods x ~5 lines + init + imports + SyncWrapper if kept)

### parser_rust.py: Function-by-Function Analysis

| Function | Lines | Status in Rust | Migration Action |
|----------|-------|---------------|------------------|
| `__init__` | 18 | N/A | Simplify, keep |
| `find_segments` | 74 | **parse_complete in Rust** | Thin to 5 lines |
| `extract_section` | 26 | Already in Rust | Thin to 3 lines |
| `_parse_crash_header` | 28 | Already in Rust (`parse_crash_header`) | Remove entirely |
| Exception boilerplate | ~25 | N/A | Remove |
| Module docstring | 47 | N/A | Reduce to 5 lines |

**Estimated thinned size:** ~60 lines

### formid_rust.py: Function-by-Function Analysis

| Function | Lines | Status in Rust | Migration Action |
|----------|-------|---------------|------------------|
| `__init__` | 45 | N/A | Simplify to ~15 lines |
| `extract_formids` | 42 | Already in Rust | Thin to 5 lines |
| `formid_match` | 46 | **Move caching to Rust** | Thin to 5 lines |
| `extract_formids_batch` | 18 | Already in Rust | Thin to 5 lines |
| Exception boilerplate | ~30 | N/A | Remove |
| Module docstring | 45 | N/A | Reduce to 5 lines |

**Estimated thinned size:** ~70 lines

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hasattr()` feature detection | Direct method calls (known API) | This phase | Eliminates legacy code paths |
| Multiple FFI calls per operation | Single `parse_complete()` call | Already done in Rust | Python wrapper still has legacy path |
| Python-side MD5 plugin caching | Rust-side caching | This phase | Eliminates Python business logic |
| 3-tier Rust class detection | Single Rust class per wrapper | This phase | Simplifies init |

**Deprecated/outdated:**
- Legacy `extract_section` multi-call path in `parser_rust.py` -- `parse_complete` supersedes this
- `FormIDAnalyzer` simple class -- `FormIDAnalyzerCore` is the current optimized version
- `SyncWrapper` in `file_io_rust.py` -- may be unused or replaceable

## Open Questions

1. **SyncWrapper callers**
   - What we know: `create_file_io_sync()` creates a `SyncWrapper` for GUI workers
   - What's unclear: How many callers use this function? Can they be migrated to async?
   - Recommendation: Search for `create_file_io_sync` and `SyncWrapper` across codebase before removing. If callers exist, keep a minimal version.

2. **formid_match return type**
   - What we know: Rust `process_formids_cached` returns `Vec<String>`, Python creates `ReportFragment.from_lines()`
   - What's unclear: Should `ReportFragment` creation move to Rust, or should the Python wrapper do this conversion?
   - Recommendation: Keep `ReportFragment` creation in Python (it's a Python-only concern). Rust returns `Vec<String>`, Python converts. This is marshalling, not business logic.

3. **Segment boundary definitions**
   - What we know: `find_segments` constructs boundary tuples in Python (lines 166-173) using `xse_acronym`
   - What's unclear: Should these move to Rust or stay as parameters?
   - Recommendation: Keep as parameters passed from Python to Rust. The boundaries are caller-provided configuration, not business logic. The Python wrapper just passes them through.

4. **tracing crate integration**
   - What we know: CONTEXT.md specifies Rust uses tracing for internal logging
   - What's unclear: Whether tracing is already set up in the workspace
   - Recommendation: Check if tracing is in workspace deps. If not, add it. Low priority for this phase.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** - Direct reading of all three wrapper files, all Rust -core and -py crates, factory module, exceptions module, and shared infrastructure
- `ClassicLib/integration/rust/file_io_rust.py` - 937 lines analyzed
- `ClassicLib/integration/rust/parser_rust.py` - 320 lines analyzed
- `ClassicLib/integration/rust/formid_rust.py` - 325 lines analyzed
- `rust/python-bindings/classic-file-io-py/src/core.rs` - Existing thin adapter pattern (485 lines)
- `rust/python-bindings/classic-scanlog-py/src/parser.rs` - Existing thin adapter pattern (299 lines)
- `rust/Cargo.toml` - PyO3 0.27.2, pyo3-async-runtimes 0.27.0, Tokio 1.49.0

### Secondary (MEDIUM confidence)
- PyO3 0.27 async patterns -- verified via existing codebase usage of `future_into_py` and `pyo3-async-runtimes`
- Error mapping patterns -- verified via existing `to_pyerr` functions in each -py crate

### Tertiary (LOW confidence)
- Golden file testing approach -- standard pytest pattern, not verified against a specific framework

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies already in workspace, versions confirmed from Cargo.toml
- Architecture: HIGH - Existing three-layer pattern well-established, multiple crates follow it
- Migration inventory: HIGH - Direct analysis of every function in all three wrappers
- Pitfalls: HIGH - Based on actual codebase patterns observed
- Golden file testing: MEDIUM - Standard pytest approach, no project-specific golden file infrastructure exists yet

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (stable -- no external dependency changes expected)
