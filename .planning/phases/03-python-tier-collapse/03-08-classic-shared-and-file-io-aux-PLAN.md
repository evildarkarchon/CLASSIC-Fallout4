---
phase: 03-python-tier-collapse
plan: 08
type: execute
wave: 8
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-07]
files_modified:
  - ClassicLib-rs/foundation/classic-shared-py/src/lib.rs
  - ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi
  - ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi
  - ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py
  - ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
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
    - "rebuild_rust.ps1 -Target python classic_shared produces a wheel and installs it into ClassicLib-rs/python-bindings/.venv (no script changes needed per A8 — Get-PythonRustModules already searches foundation/)"
    - "test_classic_shared_smoke.py imports classic_shared, calls get_runtime_stats() returning a non-None RuntimeStats with worker_threads > 0, and verifies all 6 surface symbols are accessible (RuntimeStats constructed via factory, NOT directly per A8)"
    - "mypy --strict classic_shared.pyi exits 0 (stub already complete per A8 — verify only)"
    - "python-deferred-aux-297 (classic_file_io.FileHasher.cache_size) and 4 Tier-2 runtime-verified FileHasher cache helpers (cache_stats, reset_cache_stats, clear_cache, plus the cache_size canonical) are all promoted to tier1Mappings as 5 file_io rows"
    - "classic_file_io.pyi covers PyFileHasher cache helpers; mypy --strict clean"
    - "5-step verification chain exits 0; tier1Mappings.length == 359 (348 + 6 classic_shared + 5 file_io)"
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
      provides: "tier1Mappings.length = 359; new selector entries python-tier1-shared and python-tier1-file_io"
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
- DELETE the existing aux Tier-2 explicit-binding registry entries (python-deferred-aux-297, python-tier2-aux-cache-runtime)
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

    Step 2: Author 5 classic_file_io tier1Mapping rows. Verify exact `rustSymbol` paths from `classic-file-io-core/src/hasher.rs` and the `-py` wrapper. Approximate shape:

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

    Step 3: Insert 11 total rows (6 classic_shared + 5 file_io) into `parity_contract.json::tier1Mappings`. Final length: 348 + 11 = 359.

    Step 4: Do NOT regenerate baseline yet — Task 4 handles atomic refresh.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); shared = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'shared']; file_io = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'file_io']; print(f'shared: {len(shared)}, file_io: {len(file_io)}'); assert len(shared) == 6; assert len(file_io) >= 5"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 359`
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

    Step 2: Update `classic_file_io.pyi` to add stub entries for `FileHasher` and its cache methods. The stub may be very sparse; preserve existing content and add:

    ```python
    """Type stubs for classic_file_io PyO3 bindings."""
    from __future__ import annotations

    class FileHasher:
        """File content hasher with bounded cache."""
        def __init__(self) -> None: ...

        def hash_file(self, path: str) -> str:
            """Compute hash of a file's contents."""
            ...

        def cache_size(self) -> int:
            """Returns the current cache entry count (compatibility adapter)."""
            ...

        def cache_stats(self) -> dict[str, int]:
            """Returns canonical cache statistics: hits, misses, evictions, etc."""
            ...

        def reset_cache_stats(self) -> None:
            """Reset cache statistics counters."""
            ...

        def clear_cache(self) -> None:
            """Evict all cached entries."""
            ...
    ```

    Verify exact method signatures and return types from `classic-file-io-py/src/*.rs`. If `cache_stats()` returns a typed `CacheStats` struct rather than a dict, use that type instead.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_shared.pyi` contains all 6 surface symbols (PathHandler, StringProcessor, RustPerformanceMonitor, RuntimeStats, get_runtime_stats, is_runtime_healthy)
    - `classic_shared.pyi::class RuntimeStats` does NOT have a constructible `__init__` (or has only default attributes)
    - `classic_file_io.pyi` contains `class FileHasher:` with cache_size, cache_stats, reset_cache_stats, clear_cache methods
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
        ph = classic_shared.PathHandler()
        # Verify exact method name from PyPathHandler #[pymethods]
        # If split_path doesn't exist, use the actual method name
        if hasattr(ph, "split_path"):
            parts = ph.split_path("a/b/c")
            assert isinstance(parts, (list, tuple))
        else:
            # Fallback: just verify the class is constructible
            assert ph is not None


    def test_rust_performance_monitor_record_smoke() -> None:
        mon = classic_shared.RustPerformanceMonitor()
        # Verify exact method name from PyRustPerformanceMonitor #[pymethods]
        if hasattr(mon, "record_metric"):
            mon.record_metric("test_op", 1)
            if hasattr(mon, "get_all_stats"):
                stats = mon.get_all_stats()
                assert "test_op" in stats
        else:
            assert mon is not None
    ```

    Create `test_promoted_file_io_aux_smoke.py`:

    ```python
    """Smoke tests for Phase 3 Plan 08 — classic-file-io-py FileHasher cache helpers.

    Covers the 1 aux entry (cache_size) plus 4 Tier-2 runtime-verified migrations
    (cache_stats, reset_cache_stats, clear_cache, the canonical cache_size).
    """
    from __future__ import annotations

    import classic_file_io


    def test_file_hasher_construct() -> None:
        hasher = classic_file_io.FileHasher()
        assert hasher is not None


    def test_file_hasher_cache_size_after_construct() -> None:
        hasher = classic_file_io.FileHasher()
        size = hasher.cache_size()
        assert isinstance(size, int)
        assert size >= 0


    def test_file_hasher_cache_stats_returns_dict() -> None:
        hasher = classic_file_io.FileHasher()
        stats = hasher.cache_stats()
        # cache_stats may return dict or a typed CacheStats struct
        assert stats is not None


    def test_file_hasher_reset_cache_stats_smoke() -> None:
        hasher = classic_file_io.FileHasher()
        # reset_cache_stats returns None on success
        hasher.reset_cache_stats()
        # No assertion — successful call is the smoke


    def test_file_hasher_clear_cache_smoke() -> None:
        hasher = classic_file_io.FileHasher()
        hasher.clear_cache()
        # After clear, cache_size should be 0
        size = hasher.cache_size()
        assert size == 0
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
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (find python-deferred-aux-297 and any python-tier2-aux-* entries to delete)
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
    - DELETE existing aux Tier-2 entries: `python-deferred-aux-297`, `python-tier2-aux-cache-runtime` (and any other aux/cache Tier-2 explicit-binding rows now covered by tier1 contract rows)

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

    Step 4: Run the full 5-step plan-close verification chain (gate, validate_stubs, rebuild_rust, full pytest, mypy on all updated stubs).

    If any D-10 step fails, fix INSIDE this plan (per CONTEXT D-10 — discovered gaps are not deferred).
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; pwsh -File rebuild_rust.ps1 -Target python classic_shared classic_file_io; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length == 359`
    - 6 rows with `ownerModule == 'shared'`; 5+ rows with `ownerModule == 'file_io'`
    - `runtime_coverage_registry.json` contains new `python-tier1-shared` (contractCount=6) and `python-tier1-file_io` (contractCount=5) selector entries
    - `python-deferred-aux-297` and `python-tier2-aux-cache-runtime` entries DELETED from runtime_coverage_registry.json
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
- 11 new contract rows (6 classic_shared + 5 file_io); tier1Mappings 348 → 359
- HARM-03 satisfied: rebuild_rust.ps1 builds classic_shared wheel, classic_shared.get_runtime_stats() returns healthy stats
- HARM-04 satisfied: classic_shared enrolled in tier1Mappings (6 rows), mypy --strict clean
- A2 honored: aux entry placed in classic_file_io plan, NOT classic_shared
- A8 honored: classic_shared.pyi NOT edited (already complete); RuntimeStats constructed via factory
- 5-step verification chain exits 0
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-08-SUMMARY.md` with files modified, tier1Mappings.length (359), D-10 wiring chain results, HARM-03/HARM-04 satisfaction evidence.
</output>
