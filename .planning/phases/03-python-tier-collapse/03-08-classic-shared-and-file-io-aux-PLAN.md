---
phase: 03-python-tier-collapse
plan: 08
type: execute
wave: 8
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-07]
files_modified:
  - ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi
  - ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi
  - ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py
  - ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  - .planning/phases/03-python-tier-collapse/03-08-METHOD-INVENTORY.md
  - docs/implementation/python_api_parity/baseline/parity_contract.json
  - docs/implementation/python_api_parity/baseline/parity_contract.md
  - docs/implementation/python_api_parity/baseline/parity_diff_report.json
  - docs/implementation/python_api_parity/baseline/parity_diff_report.md
  - docs/implementation/python_api_parity/baseline/rust_api_surface.json
  - docs/implementation/python_api_parity/baseline/python_api_surface.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/tier1_gate_report.md
autonomous: true
requirements: [HARM-03, HARM-04, PYT-02, PYT-04, PYT-05]
must_haves:
  truths:
    - "classic_shared module is enrolled in parity_contract.json with exactly 6 tier1Mapping rows: PathHandler, StringProcessor, RustPerformanceMonitor, RuntimeStats, get_runtime_stats, is_runtime_healthy"
    - "R3: Plan 08 owns ALL classic_file_io contract rows discovered by parse_rust_surface() after the Plan 01 RUST_TARGET_CRATES expansion — not just the 5 explicitly-enumerated rows. Plan 09a residual promotion explicitly excludes classic-file-io-core."
    - "R2: python-deferred-aux-297 lives in deferred_runtime_backlog.json:3702 (VERIFIED), NOT in runtime_coverage_registry.json. Plan 08 does NOT delete that ID from runtime_coverage_registry.json — the deferred backlog file is governed by Phase 6 DOC-02/DOC-04, not Phase 3."
    - "R13: cache_size() returns entry count (HASH_CACHE.len()) — VERIFIED from classic-file-io-core/src/hash.rs:308. After clear_cache(), cache_size() == 0 is correct."
    - "R13: PyFileHasher methods are ALL #[staticmethod] — tests MUST call `classic_file_io.FileHasher.method()` NOT `classic_file_io.FileHasher().method()`. PyFileHasher has NO #[new] constructor."
    - "rebuild_rust.ps1 -Target python classic_shared produces a wheel and installs it into ClassicLib-rs/python-bindings/.venv (no script changes needed per A8 — Get-PythonRustModules already searches foundation/)"
    - "test_classic_shared_smoke.py imports classic_shared, calls get_runtime_stats() returning a non-None RuntimeStats with worker_threads > 0, and verifies all 6 surface symbols are accessible (RuntimeStats constructed via factory, NOT directly per A8)"
    - "mypy --strict classic_shared.pyi exits 0 (stub already complete per A8 — verify only)"
    - "python-deferred-aux-297 (classic_file_io.FileHasher.cache_size) and 4 Tier-2 runtime-verified FileHasher cache helpers (cache_stats, reset_cache_stats, clear_cache, plus the cache_size canonical) are all promoted to tier1Mappings as 5 file_io rows"
    - "classic_file_io.pyi covers PyFileHasher cache helpers; mypy --strict clean"
    - "5-step verification chain exits 0; tier1Mappings.length == 358 (347 + 6 classic_shared + 5 file_io; R9 propagation). Plan 08 may add MORE file_io rows beyond 5 if the post-refresh gap scan surfaces more — R3 Plan 08 owns ALL file_io."
  artifacts:
    - path: "ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi"
      provides: "Stub already exists per A8 — Plan 08 verifies completeness, not edits"
      contains: "class PathHandler:"
    - path: "ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi"
      provides: "Stub entries for PyFileHasher cache helper methods (5 rows)"
      contains: "class FileHasher:"
    - path: "ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py"
      provides: "6 smoke tests (one per #[pymodule] symbol, RuntimeStats via factory)"
      min_lines: 50
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py"
      provides: "Smoke tests for FileHasher cache_size + 4 cache helper methods"
      min_lines: 30
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length = 358; new selector entries python-tier1-shared and python-tier1-file_io"
  key_links:
    - from: "test_classic_shared_smoke.py"
      to: "classic_shared module wheel installed in .venv"
      via: "import classic_shared; classic_shared.get_runtime_stats()"
      pattern: "classic_shared\\.get_runtime_stats"
    - from: "test_promoted_file_io_aux_smoke.py"
      to: "classic_file_io.FileHasher cache helpers"
      via: "FileHasher().cache_stats() / cache_size() / reset_cache_stats() / clear_cache()"
      pattern: "classic_file_io\\.FileHasher"
---

<objective>
Wire `classic_shared` as a gate-enrolled Python binding (HARM-03, HARM-04) and promote the 1 aux entry + 4 Tier-2 runtime-verified `FileHasher` cache helpers from `classic-file-io-py`. Per A2, the 1 aux entry (`python-deferred-aux-297`) is `classic_file_io.FileHasher.cache_size`, NOT a `classic_shared` symbol — so it lands in this plan as a `classic-file-io-py` enrollment sub-scope alongside `classic_shared`.

Per A8, the wiring prerequisites for `classic_shared` are already in place:
- `Get-PythonRustModules` in `rebuild_rust.ps1` already searches `ClassicLib-rs/foundation/`
- `classic_shared.pyi` already covers all 6 module symbols
- `RuntimeStats` has no `#[new]` — smoke test must call `get_runtime_stats()` factory, not `RuntimeStats()`

The wiring chain (D-10) is therefore PURE VERIFICATION — no script edits expected. If a step fails, fix inside this plan (do not defer).

Output:
- 6 contract rows for classic_shared (PathHandler, StringProcessor, RustPerformanceMonitor, RuntimeStats, get_runtime_stats, is_runtime_healthy)
- 5 contract rows for classic_file_io (FileHasher.cache_size aux + 4 cache helper migrations)
- New `test_classic_shared_smoke.py` with 6 tests
- New `test_promoted_file_io_aux_smoke.py` with 5 tests
- Updated `classic_file_io.pyi` covering the 5 cache helper rows
- New selector entries `python-tier1-shared` (count=6) and `python-tier1-file_io` (count=5) in runtime_coverage_registry.json
- DELETE the `python-tier2-aux-cache-runtime` entry from `runtime_coverage_registry.json` (R2: `python-deferred-aux-297` lives in `deferred_runtime_backlog.json`, NOT the registry — Plan 08 does NOT delete it; Phase 6 owns that file)
- Refreshed parity baseline per D-03 cadence
- 4-step D-10 wiring verification chain exits 0
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-python-tier-collapse/03-CONTEXT.md
@.planning/phases/03-python-tier-collapse/03-RESEARCH.md
@.planning/phases/03-python-tier-collapse/03-VALIDATION.md
@.planning/phases/03-python-tier-collapse/03-07-SUMMARY.md
@./CLAUDE.md

<interfaces>
<!-- classic_shared 6-symbol surface (verified A8) -->

From ClassicLib-rs/foundation/classic-shared-py/src/lib.rs lines 322-338:
```rust
#[pymodule]
fn classic_shared(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyStringProcessor>()?;       // -> Python name: StringProcessor
    m.add_class::<PyPathHandler>()?;            // -> Python name: PathHandler
    m.add_class::<PyRustPerformanceMonitor>()?; // -> Python name: RustPerformanceMonitor
    m.add_class::<RuntimeStats>()?;             // (no rename) RuntimeStats
    m.add_function(wrap_pyfunction!(get_runtime_stats, m)?)?;  // free fn
    m.add_function(wrap_pyfunction!(is_runtime_healthy, m)?)?; // free fn
    Ok(())
}
```

CRITICAL per A8: RuntimeStats has no #[new] (line 252 of classic-shared-py/src/lib.rs). It cannot be constructed directly from Python. The smoke test MUST use:
```python
stats = classic_shared.get_runtime_stats()  # CORRECT — factory
# NOT: stats = classic_shared.RuntimeStats()  # WRONG — no constructor
```

The 6 contract rows (per D-09):
1. id="shared.PathHandler", rustSymbol="PyPathHandler", pythonExportPath="PathHandler"
2. id="shared.StringProcessor", rustSymbol="PyStringProcessor", pythonExportPath="StringProcessor"
3. id="shared.RustPerformanceMonitor", rustSymbol="PyRustPerformanceMonitor", pythonExportPath="RustPerformanceMonitor"
4. id="shared.RuntimeStats", rustSymbol="RuntimeStats", pythonExportPath="RuntimeStats"
5. id="shared.get_runtime_stats", rustSymbol="get_runtime_stats", pythonExportPath="get_runtime_stats"
6. id="shared.is_runtime_healthy", rustSymbol="is_runtime_healthy", pythonExportPath="is_runtime_healthy"

<!-- file_io aux + cache helpers (5 rows total) -->

The single aux entry from deferred_runtime_backlog.json:
- coverageId="python-deferred-aux-297"
- bindingIdentifiers=["classic_file_io.FileHasher.cache_size"]

The 4 Tier-2 runtime-verified cache helpers (from runtime_coverage_registry.json):
- classic_file_io.FileHasher.cache_size (canonical, currently aux)
- classic_file_io.FileHasher.cache_stats
- classic_file_io.FileHasher.reset_cache_stats
- classic_file_io.FileHasher.clear_cache

The 5 file_io contract rows:
1. id="file_io.FileHasher.cache_size", rustSymbol="FileHasher::cache_size" (verify exact rust path)
2. id="file_io.FileHasher.cache_stats"
3. id="file_io.FileHasher.reset_cache_stats"
4. id="file_io.FileHasher.clear_cache"
5. id="file_io.FileHasher" (the class itself if not already enrolled — verify against existing tier1Mappings)
</interfaces>
</context>

<tasks>


<task type="auto">
  <name>Task 0: Verify classic_shared method names from .pyi + file_io FileHasher static-method nature (R5/R11/R13 — pre-Task-3 verification)</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-08-METHOD-INVENTORY.md
  </files>
  <read_first>
    - ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi (VERIFIED: PathHandler.normalize_path (NOT normalize), PathHandler.split_path, PathHandler.clear_cache, PathHandler.cache_stats, StringProcessor.normalize, StringProcessor.intern, RustPerformanceMonitor.record_metric(operation: str, duration_ms: int, bytes_processed: int | None = None), RuntimeStats.is_healthy is a BARE ATTRIBUTE not a method)
    - ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs (VERIFIED: PyFileHasher is `pub struct PyFileHasher;` with NO #[new] — all methods are #[staticmethod]: hash_file, hash_files_parallel, clear_cache, cache_size, cache_stats, reset_cache_stats. Tests MUST call `classic_file_io.FileHasher.cache_size()` NOT `classic_file_io.FileHasher().cache_size()`.)
    - ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs (VERIFIED: cache_size() returns HASH_CACHE.len() — entry count, not bytes. After clear_cache(), size == 0 is correct. Lines 264-310.)
  </read_first>
  <action>
    R5/R11/R13 — Write verified method inventory to `.planning/phases/03-python-tier-collapse/03-08-METHOD-INVENTORY.md`. This file is read by Tasks 2-3 before authoring the stub and tests. Contents:

    ```markdown
    # Plan 08 Method Inventory (R5/R11/R13 verification)

    ## classic_shared (verified from classic_shared.pyi)

    ### PathHandler
    - `__init__(cache_ttl_seconds: int = 300)` — takes a keyword arg, NOT parameterless
    - `normalize_path(path: str) -> str` — NOT `normalize` (Claude's original guess was wrong)
    - `split_path(path: str) -> list[str]` — exists; takes single path arg
    - `clear_cache() -> None`
    - `cache_stats() -> tuple[int, int]`
    - `cleanup_cache() -> None`
    - `validate_paths_batch(paths: list[str]) -> list[tuple[str, bool, str]]`
    - `join_paths(base: str, components: list[str]) -> str`
    - `get_filename(path: str) -> str | None`
    - `get_extension(path: str) -> str | None`
    - `get_parent(path: str) -> str | None`
    - `is_absolute(path: str) -> bool`
    - `to_absolute(path: str, base: str | None = None) -> str`
    - `common_prefix(paths: list[str]) -> str | None`
    - `validate_paths_batch_fast(paths: list[str]) -> ...`
    - `cache_metrics() -> tuple[int, int, float]`
    - `split_path_fast(path: str) -> list[str]`

    ### StringProcessor
    - `__init__() -> None` — parameterless
    - `intern(s: str) -> str`
    - `process_batch(strings: list[str], operation: str) -> list[str]`
    - `common_prefix(strings: list[str]) -> str`
    - `split_lines(text: str) -> list[str]`
    - `join_lines(lines: list[str], separator: str) -> str`
    - `pool_stats() -> int`
    - `clear_pool() -> None`
    - `intern_batch(strings: list[str]) -> list[str]`
    - `process_batch_fast(strings: list[str], operation: str) -> list[str]`
    - `split_lines_fast(text: str) -> list[str]`
    - `normalize(s: str) -> str`

    ### RustPerformanceMonitor
    - `__init__() -> None` — parameterless
    - `start_timer(operation: str) -> dict[str, object]`
    - `stop_timer(timer_info: dict, bytes_processed: int | None = None) -> None`
    - `get_all_stats() -> dict[str, dict[str, object]]`
    - `get_operation_stats(operation: str) -> dict[str, object] | None`
    - `clear_metrics() -> None`
    - `record_metric(operation: str, duration_ms: int, bytes_processed: int | None = None) -> None`
      **NOTE (R11): takes 3 positional args, not `("test_op", 1)`. Test must use `mon.record_metric("test_op", 1, None)` or provide all args.**

    ### RuntimeStats
    - NO `__init__` (no `#[new]` — confirmed A8)
    - Bare attributes: `worker_threads: int`, `is_healthy: bool` — **R11 CLARIFICATION: `is_healthy` is a bare bool ATTRIBUTE, not a method. Test: `assert stats.is_healthy is True` (no parens).**

    ### Module-level functions
    - `get_runtime_stats() -> RuntimeStats` — factory for RuntimeStats
    - `is_runtime_healthy() -> bool`

    ## classic_file_io.FileHasher (R13 — VERIFIED staticmethod nature)

    Source: `ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs` lines 30-180.

    `#[pyclass(name = "FileHasher", module = "classic_file_io")] pub struct PyFileHasher;`
    — Empty struct. NO `#[new]`. ALL methods are `#[staticmethod]`.

    ### FileHasher (ALL static — call as `classic_file_io.FileHasher.method()`, NOT `classic_file_io.FileHasher().method()`)
    - `hash_file(path: str) -> str` — static
    - `hash_files_parallel(paths: list[str]) -> dict[str, str | None]` — static
    - `hash_files_to_map(paths: list[str]) -> dict` — static
    - `clear_cache() -> None` — static
    - `cache_size() -> int` — static, returns HASH_CACHE.len() (entry count per R13)
    - `cache_stats(py) -> dict` — static; returns dict with keys: hits, misses, hit_rate, size, capacity
    - `reset_cache_stats() -> None` — static

    R13 semantics: `cache_size()` returns HASH_CACHE entry count. After `clear_cache()`, `cache_size() == 0` is the correct assertion. NOT bytes.

    ## R13 Test Pattern Correction

    WRONG (old Plan 08 Task 3 scaffold):
    ```python
    hasher = classic_file_io.FileHasher()  # TypeError — no __init__
    hasher.cache_size()
    ```

    CORRECT:
    ```python
    # Static methods — call via class, not instance
    initial = classic_file_io.FileHasher.cache_size()
    classic_file_io.FileHasher.clear_cache()
    assert classic_file_io.FileHasher.cache_size() == 0
    ```
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "if (-not (Test-Path '.planning/phases/03-python-tier-collapse/03-08-METHOD-INVENTORY.md')) { Write-Error 'Inventory missing'; exit 1 }; $c = Get-Content '.planning/phases/03-python-tier-collapse/03-08-METHOD-INVENTORY.md' -Raw; if ($c -notmatch 'normalize_path' -or $c -notmatch 'staticmethod') { Write-Error 'Inventory incomplete'; exit 1 }; Write-Host 'OK'"</automated>
  </verify>
  <acceptance_criteria>
    - `03-08-METHOD-INVENTORY.md` exists
    - File lists every classic_shared method name verified from classic_shared.pyi
    - File documents PyFileHasher as #[staticmethod]-only (no __init__)
    - File clarifies R13: cache_size() returns entries, not bytes
    - File clarifies R11: RuntimeStats.is_healthy is a bare attribute, not a method
    - File clarifies R11: PathHandler.normalize_path NOT normalize; RustPerformanceMonitor.record_metric takes 3 args
  </acceptance_criteria>
  <done>Method inventory written; Tasks 2-3 can use verified names without guessing.</done>
</task>
<task type="auto">
  <name>Task 1: Author 6 classic_shared + 5 classic_file_io contract rows</name>
  <files>
    docs/implementation/python_api_parity/baseline/parity_contract.json
  </files>
  <read_first>
    - ClassicLib-rs/foundation/classic-shared-py/src/lib.rs (full file — confirm 6 symbols, RuntimeStats has no #[new])
    - ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi (full file — verify A8 completeness)
    - ClassicLib-rs/business-logic/classic-file-io-core/src/lib.rs (find FileHasher cache_size/cache_stats/reset_cache_stats/clear_cache exports)
    - ClassicLib-rs/business-logic/classic-file-io-core/src/hasher.rs (or wherever FileHasher lives — source of truth)
    - ClassicLib-rs/python-bindings/classic-file-io-py/src/lib.rs (PyO3 wrapper layout)
    - ClassicLib-rs/python-bindings/classic-file-io-py/src/*.rs (FileHasher wrapper — likely PyFileHasher)
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (find python-deferred-aux-297)
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (find python-tier2-aux-cache-runtime and similar entries)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 5" (lines 547-687)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A2" (aux belongs to file_io, not classic_shared)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A8" (classic_shared.pyi already complete)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"D-09" (6-row classic_shared contract)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"D-10" (4-step verification chain)
  </read_first>
  <action>
    Step 1: Author 6 classic_shared tier1Mapping rows. The exact rows (per D-09 + A8):

    ```json
    {
      "id": "shared.PathHandler",
      "rustSymbol": "PyPathHandler",
      "rustCrate": "classic-shared-py",
      "rustKind": "struct",
      "pythonModule": "classic_shared",
      "pythonExportPath": "PathHandler",
      "pythonKind": "class",
      "pythonArity": null,
      "ownerModule": "shared",
      "tier": "tier1"
    },
    {
      "id": "shared.StringProcessor",
      "rustSymbol": "PyStringProcessor",
      "rustCrate": "classic-shared-py",
      "rustKind": "struct",
      "pythonModule": "classic_shared",
      "pythonExportPath": "StringProcessor",
      "pythonKind": "class",
      "pythonArity": null,
      "ownerModule": "shared",
      "tier": "tier1"
    },
    {
      "id": "shared.RustPerformanceMonitor",
      "rustSymbol": "PyRustPerformanceMonitor",
      "rustCrate": "classic-shared-py",
      "rustKind": "struct",
      "pythonModule": "classic_shared",
      "pythonExportPath": "RustPerformanceMonitor",
      "pythonKind": "class",
      "pythonArity": null,
      "ownerModule": "shared",
      "tier": "tier1"
    },
    {
      "id": "shared.RuntimeStats",
      "rustSymbol": "RuntimeStats",
      "rustCrate": "classic-shared-py",
      "rustKind": "struct",
      "pythonModule": "classic_shared",
      "pythonExportPath": "RuntimeStats",
      "pythonKind": "class",
      "pythonArity": null,
      "ownerModule": "shared",
      "tier": "tier1"
    },
    {
      "id": "shared.get_runtime_stats",
      "rustSymbol": "get_runtime_stats",
      "rustCrate": "classic-shared-py",
      "rustKind": "function",
      "pythonModule": "classic_shared",
      "pythonExportPath": "get_runtime_stats",
      "pythonKind": "function",
      "pythonArity": 0,
      "ownerModule": "shared",
      "tier": "tier1"
    },
    {
      "id": "shared.is_runtime_healthy",
      "rustSymbol": "is_runtime_healthy",
      "rustCrate": "classic-shared-py",
      "rustKind": "function",
      "pythonModule": "classic_shared",
      "pythonExportPath": "is_runtime_healthy",
      "pythonKind": "function",
      "pythonArity": 0,
      "ownerModule": "shared",
      "tier": "tier1"
    }
    ```

    R3 STEP — Plan 08 owns ALL file_io contract rows (not just 5). After authoring the 6 classic_shared rows and 5 initial file_io rows, run `generate_baseline.py --write-baseline` and check `parity_diff_report.json::gaps` for any remaining `owner_module == 'file_io'` tier2 gap rows. If any exist, add contract rows + stub updates + tests for them in the SAME atomic commit. Plan 08 claims ALL file_io rows; Plan 09a's residual promotion explicitly excludes file_io.

    Step 2: Author AT LEAST 5 classic_file_io tier1Mapping rows (the initial 5 enumerated) PLUS any additional file_io residuals discovered by the post-refresh gap scan. Verify exact `rustSymbol` paths from `classic-file-io-core/src/hash.rs` and the `-py` wrapper.

    NOTE: PyFileHasher methods are ALL #[staticmethod] (verified from classic-file-io-py/src/hash.rs). The `pythonExportPath` values should reflect static-method semantics:
    - `file_io.FileHasher` (class row) — pythonExportPath: `FileHasher`
    - `file_io.FileHasher.cache_size` — pythonExportPath: `FileHasher.cache_size` (static, called as class method)
    - similarly for cache_stats, reset_cache_stats, clear_cache, hash_file, hash_files_parallel, hash_files_to_map Approximate shape:

    ```json
    {
      "id": "file_io.FileHasher",
      "rustSymbol": "FileHasher",
      "rustCrate": "classic-file-io-core",
      "rustKind": "struct",
      "pythonModule": "classic_file_io",
      "pythonExportPath": "FileHasher",
      "pythonKind": "class",
      "pythonArity": null,
      "ownerModule": "file_io",
      "tier": "tier1"
    },
    {
      "id": "file_io.FileHasher.cache_size",
      "rustSymbol": "FileHasher",
      "rustCrate": "classic-file-io-core",
      "rustKind": "struct",
      "pythonModule": "classic_file_io",
      "pythonExportPath": "FileHasher.cache_size",
      "pythonKind": "method",
      "pythonArity": 0,
      "ownerModule": "file_io",
      "tier": "tier1"
    },
    // Similar rows for cache_stats, reset_cache_stats, clear_cache
    ```

    NOTE: If the parser uses dotted notation for `pythonExportPath` like `FileHasher.cache_size`, follow the existing convention from prior plans. If methods are stored as separate rows per the existing pattern, mirror that.

    Step 3: Insert 11 total rows (6 classic_shared + 5 file_io) into `parity_contract.json::tier1Mappings`. Final length: 347 + 11 = 358.

    Step 4: Do NOT regenerate baseline yet — Task 4 handles atomic refresh.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); shared = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'shared']; file_io = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'file_io']; print(f'shared: {len(shared)}, file_io: {len(file_io)}'); assert len(shared) == 6; assert len(file_io) >= 5"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 358`
    - Exactly 6 rows have `ownerModule == 'shared'` (PathHandler, StringProcessor, RustPerformanceMonitor, RuntimeStats, get_runtime_stats, is_runtime_healthy)
    - At least 5 rows have `ownerModule == 'file_io'` covering FileHasher + cache_size + cache_stats + reset_cache_stats + clear_cache
    - All shared rows use the renamed Python names (PathHandler not PyPathHandler) — verify against #[pyclass(name = "...")] declarations
  </acceptance_criteria>
  <done>11 new contract rows authored (6 shared + 5 file_io).</done>
</task>

<task type="auto">
  <name>Task 2: Verify classic_shared.pyi completeness; update classic_file_io.pyi with FileHasher cache helpers</name>
  <files>
    ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi
    ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi
  </files>
  <read_first>
    - ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi (full file — verify A8: all 6 symbols already present)
    - ClassicLib-rs/foundation/classic-shared-py/src/lib.rs (lines 320-340 — verify the 6 #[pymodule] adds match the stub)
    - ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi (full file — likely empty or sparse)
    - ClassicLib-rs/python-bindings/classic-file-io-py/src/*.rs (find PyFileHasher #[pymethods])
  </read_first>
  <action>
    Step 1: Verify `classic_shared.pyi` is complete per A8. Read the full file. Confirm all 6 symbols are declared:
    - `class PathHandler:` (line ~9)
    - `class StringProcessor:` (line ~203)
    - `class RustPerformanceMonitor:` (line ~352)
    - `class RuntimeStats:` (line ~423) — must NOT have a constructible `__init__` (RuntimeStats has no #[new])
    - `def get_runtime_stats() -> RuntimeStats:` (line ~437)
    - `def is_runtime_healthy() -> bool:` (line ~448)

    If any are missing, add them. If all present, NO EDIT — A8 confirmed.

    Step 2: Update `classic_file_io.pyi` to add stub entries for `FileHasher` and its cache methods. Per R13's Task 0 verified inventory, `PyFileHasher` is an empty struct with **NO `#[new]` constructor** — all methods are `#[staticmethod]`. The stub MUST reflect this: use `@staticmethod` decorators and do NOT include `def __init__`. Preserve existing stub content and add:

    ```python
    """Type stubs for classic_file_io PyO3 bindings."""
    from __future__ import annotations

    class FileHasher:
        """File content hasher with bounded cache. All methods are static — FileHasher is not instantiable."""

        @staticmethod
        def hash_file(path: str) -> str:
            """Compute hash of a file's contents."""
            ...

        @staticmethod
        def cache_size() -> int:
            """Returns the current cache entry count (compatibility adapter for HASH_CACHE.len())."""
            ...

        @staticmethod
        def cache_stats() -> dict[str, int]:
            """Returns canonical cache statistics: hits, misses, evictions, etc."""
            ...

        @staticmethod
        def reset_cache_stats() -> None:
            """Reset cache statistics counters."""
            ...

        @staticmethod
        def clear_cache() -> None:
            """Evict all cached entries."""
            ...
    ```

    Verify exact method signatures and return types against the Task 0 `03-08-METHOD-INVENTORY.md` output. If `cache_stats()` returns a typed `CacheStats` struct rather than a dict, use that type instead. Do NOT add a `def __init__` — the source has no `#[new]` and the stub must match.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_shared.pyi` contains all 6 surface symbols (PathHandler, StringProcessor, RustPerformanceMonitor, RuntimeStats, get_runtime_stats, is_runtime_healthy)
    - `classic_shared.pyi::class RuntimeStats` does NOT have a constructible `__init__` (or has only default attributes)
    - `classic_file_io.pyi::class FileHasher` does NOT contain `def __init__` — `PyFileHasher` has no `#[new]` per Task 0 method inventory
    - `classic_file_io.pyi` contains `class FileHasher:` with `@staticmethod`-decorated `hash_file`, `cache_size`, `cache_stats`, `reset_cache_stats`, `clear_cache` methods
    - `mypy --strict` exits 0 for both stub files
  </acceptance_criteria>
  <done>classic_shared.pyi verified per A8; classic_file_io.pyi updated with FileHasher cache helpers; mypy clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_classic_shared_smoke.py and test_promoted_file_io_aux_smoke.py</name>
  <files>
    ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py
    ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py
  </files>
  <read_first>
    - ClassicLib-rs/foundation/classic-shared-py/src/lib.rs (full file)
    - ClassicLib-rs/python-bindings/classic-file-io-py/src/*.rs (FileHasher wrapper signatures)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 5 — Step 3" (lines 591-647) — paste-ready test bodies
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"D-10 step 3" (test must call get_runtime_stats(), NOT RuntimeStats())
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Assumption Correction A8" (RuntimeStats has no #[new])
  </read_first>
  <behavior>
    test_classic_shared_smoke.py — 6 tests, one per #[pymodule] symbol:
    - test_get_runtime_stats_returns_healthy_struct (HARM-03 / D-10 step 3)
    - test_is_runtime_healthy_true_in_test_context
    - test_runtime_stats_repr_is_descriptive
    - test_string_processor_normalize_smoke
    - test_path_handler_split_smoke
    - test_rust_performance_monitor_record_smoke

    test_promoted_file_io_aux_smoke.py — 5 tests for FileHasher cache helpers:
    - test_file_hasher_construct
    - test_file_hasher_cache_size_after_construct
    - test_file_hasher_cache_stats_returns_dict
    - test_file_hasher_reset_cache_stats_smoke
    - test_file_hasher_clear_cache_smoke
  </behavior>
  <action>
    Create `test_classic_shared_smoke.py` (paste verbatim from RESEARCH Q5 Step 3 with adaptations):

    ```python
    """Smoke tests for the classic_shared Python module (HARM-03 / HARM-04, Phase 3 Plan 08).

    CRITICAL: RuntimeStats has no #[new] constructor in classic-shared-py/src/lib.rs::RuntimeStats.
    Tests MUST call get_runtime_stats() factory, NOT RuntimeStats() directly.
    """
    from __future__ import annotations

    import classic_shared


    def test_get_runtime_stats_returns_healthy_struct() -> None:
        # HARM-03 / D-10 step 3 — gate-relevant assertion
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
        # Verify exact normalize semantics from PyStringProcessor::normalize
        assert isinstance(out, str)


    def test_path_handler_split_smoke() -> None:
        """R11: verified from classic_shared.pyi — split_path exists, takes single arg."""
        ph = classic_shared.PathHandler()  # default cache_ttl_seconds=300
        parts = ph.split_path("a/b/c")
        assert isinstance(parts, list)
        assert len(parts) >= 1


    def test_path_handler_normalize_path_smoke() -> None:
        """R11: method is `normalize_path` NOT `normalize` (verified from classic_shared.pyi)."""
        ph = classic_shared.PathHandler()
        result = ph.normalize_path("  /tmp/test  ")
        assert isinstance(result, str)


    def test_rust_performance_monitor_record_smoke() -> None:
        """R11: record_metric takes 3 positional args (operation, duration_ms, bytes_processed).

        Verified signature from classic_shared.pyi line 408-413:
            def record_metric(self, operation: str, duration_ms: int, bytes_processed: int | None = None)
        """
        mon = classic_shared.RustPerformanceMonitor()
        mon.record_metric("test_op", 1, None)  # NOT record_metric("test_op", 1) — need all args or rely on default
        stats = mon.get_all_stats()
        assert isinstance(stats, dict)
        # "test_op" may or may not appear depending on metric aggregation
    ```

    Create `test_promoted_file_io_aux_smoke.py`:

    ```python
    """Smoke tests for Phase 3 Plan 08 — classic-file-io-py FileHasher cache helpers.

    Covers the 1 aux entry (cache_size) plus 4 Tier-2 runtime-verified migrations
    (cache_stats, reset_cache_stats, clear_cache, the canonical cache_size).
    """
    from __future__ import annotations

    import classic_file_io


    def test_file_hasher_class_exists_without_constructor() -> None:
        """R13: PyFileHasher has NO #[new] — instance construction raises TypeError.

        Verified from classic-file-io-py/src/hash.rs line 30:
            #[pyclass(name = "FileHasher", module = "classic_file_io")]
            pub struct PyFileHasher;
        """
        assert classic_file_io.FileHasher is not None
        # Attempting to instantiate raises TypeError (no constructor)


    def test_file_hasher_cache_size_static_call() -> None:
        """R13: cache_size() is a #[staticmethod] — call via class, not instance.

        Verified from classic-file-io-py/src/hash.rs line 157-160:
            #[staticmethod]
            fn cache_size() -> usize { FileHasher::cache_size() }
        """
        size = classic_file_io.FileHasher.cache_size()
        assert isinstance(size, int)
        assert size >= 0


    def test_file_hasher_cache_stats_returns_dict() -> None:
        """R13: cache_stats() static — returns dict with keys hits/misses/hit_rate/size/capacity.

        Verified from classic-file-io-py/src/hash.rs line 163-173.
        """
        stats = classic_file_io.FileHasher.cache_stats()
        assert isinstance(stats, dict)
        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats


    def test_file_hasher_reset_cache_stats_smoke() -> None:
        """R13: reset_cache_stats() static — returns None, preserves entries, resets counters."""
        classic_file_io.FileHasher.reset_cache_stats()
        stats = classic_file_io.FileHasher.cache_stats()
        # After reset, hits and misses should be 0 (entries may still exist)
        assert stats["hits"] == 0
        assert stats["misses"] == 0


    def test_file_hasher_clear_cache_resets_entries_to_zero() -> None:
        """R13: clear_cache() removes all entries. cache_size() returns entries (not bytes).

        Verified from classic-file-io-core/src/hash.rs line 308:
            pub fn cache_size() -> usize { Self::cache_stats().size }
        where cache_stats.size == HASH_CACHE.len() — entry count, not bytes.
        """
        classic_file_io.FileHasher.clear_cache()
        size = classic_file_io.FileHasher.cache_size()
        assert size == 0, (
            "After clear_cache(), cache_size() must be 0 (entry count, not bytes). "
            "Verified from classic-file-io-core/src/hash.rs line 308."
        )
    ```

    Executor notes:
    - Verify exact method names from `classic-shared-py/src/strings_py.rs`, `path_py.rs`, `performance_py.rs` — if `normalize`, `split_path`, `record_metric` don't match, adapt
    - Verify FileHasher constructor signature from `classic-file-io-py/src/*.rs` — may take a config arg
    - The classic_shared wheel must be built and installed BEFORE pytest runs (Task 4 Step 5 handles this)
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_file_io; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `test_classic_shared_smoke.py` exists with 6 test functions
    - `test_promoted_file_io_aux_smoke.py` exists with 5 test functions
    - `test_get_runtime_stats_returns_healthy_struct` calls `classic_shared.get_runtime_stats()` (NOT `RuntimeStats()`)
    - All tests pass after rebuild of classic_shared and classic_file_io wheels
    - The wheels exist at `ClassicLib-rs/python-bindings/.venv/Lib/site-packages/classic_shared*` and `classic_file_io*`
  </acceptance_criteria>
  <done>Both smoke test files created and passing; classic_shared wheel verified buildable and importable.</done>
</task>

<task type="auto">
  <name>Task 4: Update registry, refresh baseline, run D-10 4-step wiring chain + 5-step verification chain</name>
  <files>
    ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    docs/implementation/python_api_parity/baseline/parity_contract.json
    docs/implementation/python_api_parity/baseline/parity_contract.md
    docs/implementation/python_api_parity/baseline/parity_diff_report.json
    docs/implementation/python_api_parity/baseline/parity_diff_report.md
    docs/implementation/python_api_parity/baseline/rust_api_surface.json
    docs/implementation/python_api_parity/baseline/python_api_surface.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    docs/implementation/python_api_parity/baseline/tier1_gate_report.md
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (find `python-tier2-aux-cache-runtime` to delete — this is the ONLY aux entry in the registry; `python-deferred-aux-297` is NOT here, it's in `deferred_runtime_backlog.json` and is owned by Phase 6)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"D-10" (4-step wiring chain)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 5" (full chain commands)
  </read_first>
  <action>
    Step 1: Update `runtime_coverage_registry.json`:
    - ADD a new selector entry `python-tier1-shared`:
      ```json
      {
        "coverageId": "python-tier1-shared",
        "classification": "runtime_verified",
        "ownerModule": "shared",
        "tier": "tier1",
        "contractSelector": {"ownerModule": "shared", "tier": "tier1"},
        "contractCount": 6,
        "contractIdsHash": "<recomputed by generate_baseline.py>",
        "verificationMode": "workflow_smoke",
        "testSuite": "ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py",
        "testCaseId": "classic_shared_smoke_suite"
      }
      ```
    - ADD a new selector entry `python-tier1-file_io`:
      ```json
      {
        "coverageId": "python-tier1-file_io",
        "classification": "runtime_verified",
        "ownerModule": "file_io",
        "tier": "tier1",
        "contractSelector": {"ownerModule": "file_io", "tier": "tier1"},
        "contractCount": 5,
        "contractIdsHash": "<recomputed by generate_baseline.py>",
        "verificationMode": "workflow_smoke",
        "testSuite": "ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py",
        "testCaseId": "file_io_aux_smoke_suite"
      }
      ```
    - DELETE existing aux Tier-2 entries from runtime_coverage_registry.json (R2 CORRECTION — `python-deferred-aux-297` is NOT in runtime_coverage_registry.json; it lives in docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json:3702. Phase 6 owns that file via DOC-02/DOC-04. Plan 08 DOES NOT delete it.):
      - DELETE `python-tier2-aux-cache-runtime` (coverageId, VERIFIED present in runtime_coverage_registry.json) — covered 3 bindings: `classic_file_io.FileHasher.cache_stats`, `classic_file_io.FileHasher.reset_cache_stats`, `classic_file_io.FileHasher.clear_cache`. Safe to delete because all 3 bindings are now promoted via Task 1.
      - DO NOT delete `python-deferred-aux-297` — it is in a DIFFERENT file (deferred_runtime_backlog.json), governed by Phase 6.

    R12 PRE-STEP: Before Task 4 commits, verify whether `generate_baseline.py --write-baseline` auto-recomputes selector `contractIdsHash` values. Run:
    ```powershell
    Select-String -Path tools/python_api_parity/generate_baseline.py,tools/binding_parity_runtime_coverage.py -Pattern 'contractIdsHash|_stable_id_hash' -SimpleMatch
    ```
    If `generate_baseline.py` does NOT recompute selector hashes (likely — the current implementation does not touch runtime_coverage_registry.json), compute the hash directly in Task 4 before writing the registry:
    ```python
    import hashlib
    import json
    contract = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read())
    shared_ids = sorted([m['id'] for m in contract['tier1Mappings'] if m.get('ownerModule') == 'shared'])
    file_io_ids = sorted([m['id'] for m in contract['tier1Mappings'] if m.get('ownerModule') == 'file_io'])
    shared_hash = hashlib.sha256(','.join(shared_ids).encode()).hexdigest()[:16]
    file_io_hash = hashlib.sha256(','.join(file_io_ids).encode()).hexdigest()[:16]
    print(f"shared hash: {shared_hash}")
    print(f"file_io hash: {file_io_hash}")
    ```
    Use these computed values in the registry entries — NO placeholder strings. Verify shape matches existing `_stable_id_hash` function; if it uses a different digest length or format (e.g., full 64 chars), adapt.

    R12 acceptance: After Task 4 commits, `runtime_coverage_registry.json` MUST NOT contain the literal string `<recomputed by generate_baseline.py>` or `<computed>` — every `contractIdsHash` must be a valid hex string.

    Step 2: Refresh baseline per D-03:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 3: D-10 4-step wiring chain (exact commands from RESEARCH Q5):

    **D-10 Step 1: Python parity gate exits 0 with classic_shared enrolled:**
    ```powershell
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    ```
    Expected: exit 0. Verify with `jq` that contract_results contains 6 rows where pythonModule=='classic_shared' all with status=='matched'.

    **D-10 Step 2: rebuild_rust.ps1 builds classic_shared wheel:**
    ```powershell
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared
    ```
    Expected: exit 0; wheel at `ClassicLib-rs/foundation/classic-shared-py/dist/classic_shared*.whl`; installed in `.venv`.

    **D-10 Step 3: pytest smoke imports classic_shared and calls get_runtime_stats():**
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py -x -q
    ```
    Expected: exit 0; all 6 tests pass.

    **D-10 Step 4: mypy --strict on classic_shared.pyi:**
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi
    ```
    Expected: `Success: no issues found in 1 source file`.

    R2 Additional verification: After Task 4 Step 2 refreshes the baseline, verify that `runtime_coverage_summary.json::summary.deferred_total` no longer counts `python-deferred-aux-297` (because it is now covered by a Tier-1 contract row authored in Task 1). The deferred_total should drop by at least 1 from its pre-Plan-08 value.

    ```powershell
    $before = (Get-Content '.planning/phases/03-python-tier-collapse/03-07-SUMMARY.md' -Raw | Select-String -Pattern 'deferred_total: (\d+)').Matches.Groups[1].Value
    $after = ((Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json).summary.deferred_total)
    if ($after -ge [int]$before) {
        Write-Error "R2 check: deferred_total did not decrease after Plan 08 — python-deferred-aux-297 may still be deferred"
        exit 1
    }
    Write-Host "R2 check passed: deferred_total $before -> $after"
    ```

    R2 note: The deferred_runtime_backlog.json file itself is NOT edited by Plan 08 — Phase 6 DOC-02/DOC-04 owns that file. Plan 08 only verifies the outcome (the deferred_total metric drops because the ID is now in tier1Mappings).

    Step 4: Run the full 5-step plan-close verification chain (gate, validate_stubs, rebuild_rust, full pytest, mypy on all updated stubs).

    If any D-10 step fails, fix INSIDE this plan (per CONTEXT D-10 — discovered gaps are not deferred).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; pwsh -File rebuild_rust.ps1 -Target python classic_shared classic_file_io; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 358`
    - 6 rows with `ownerModule == 'shared'`; 5+ rows with `ownerModule == 'file_io'`
    - `runtime_coverage_registry.json` contains new `python-tier1-shared` (contractCount=6) and `python-tier1-file_io` (contractCount=5) selector entries
    - `python-tier2-aux-cache-runtime` entry DELETED from runtime_coverage_registry.json (R2: `python-deferred-aux-297` lives in `deferred_runtime_backlog.json`, NOT the registry — it is NOT deleted by Plan 08; Phase 6 DOC-02/DOC-04 owns that file)
    - `runtime_coverage_summary.json::summary.deferred_total` drops by at least 1 after Plan 08 baseline refresh (verifies `python-deferred-aux-297` is now covered by a Tier-1 contract row)
    - D-10 4-step wiring chain exits 0:
      - Step 1: gate exits 0 with classic_shared 6 rows matched
      - Step 2: classic_shared.whl built and installed in .venv
      - Step 3: test_classic_shared_smoke.py passes (HARM-03 satisfied)
      - Step 4: mypy --strict classic_shared.pyi exits 0 (HARM-04 satisfied)
    - 5-step plan-close verification chain exits 0
    - No tier1_missing_runtime_total errors (the 2 new selectors cover the 11 new rows)
  </acceptance_criteria>
  <done>classic_shared wired as gate-enforced binding (HARM-03/04 complete); file_io aux promoted; D-10 chain green.</done>
</task>

</tasks>

<verification>
D-10 4-step wiring chain (1: gate, 2: rebuild_rust, 3: pytest, 4: mypy) plus standard 5-step plan-close chain.
</verification>

<success_criteria>
- 11 new contract rows (6 classic_shared + 5 file_io); tier1Mappings 347 → 358 (R9 propagation)
- HARM-03 satisfied: rebuild_rust.ps1 builds classic_shared wheel, classic_shared.get_runtime_stats() returns healthy stats
- HARM-04 satisfied: classic_shared enrolled in tier1Mappings (6 rows), mypy --strict clean
- A2 honored: aux entry placed in classic_file_io plan, NOT classic_shared
- A8 honored: classic_shared.pyi NOT edited (already complete); RuntimeStats constructed via factory
- 5-step verification chain exits 0
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-08-SUMMARY.md` with files modified, tier1Mappings.length (358), D-10 wiring chain results, HARM-03/HARM-04 satisfaction evidence.
</output>

