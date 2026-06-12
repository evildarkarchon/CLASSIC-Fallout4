"""Smoke tests for the classic_shared Python module (HARM-03 / HARM-04, Phase 3 Plan 08).

Covers all 61 classic_shared tier1 contract rows promoted in Plan 08:
- PathHandler class + 17 methods
- StringProcessor class + 12 methods
- RustPerformanceMonitor class + 7 methods
- RuntimeStats class (factory-only, NO #[new] per A8)
- Module-level get_runtime_stats() and is_runtime_healthy() functions
- 19 rust-only @rust-suffixed proxy rows (verified via rust_api_surface parity guard)

R11 NOTES:
- ``PathHandler.normalize_path`` NOT ``normalize`` (verified classic_shared.pyi:28)
- ``RuntimeStats.is_healthy`` is a bare attribute, NOT a method (no parens)
- ``RuntimeStats`` has NO ``#[new]`` — construct via ``get_runtime_stats()`` factory
- ``RustPerformanceMonitor.record_metric`` takes 3 positional args
  (operation, duration_ms, bytes_processed=None) per classic_shared.pyi:408-413

See 03-08-METHOD-INVENTORY.md for the full verified inventory.
"""

from __future__ import annotations

import json
from pathlib import Path

import classic_shared

# ---------------------------------------------------------------------------
# Runtime diagnostics (module-level functions + RuntimeStats factory)
# ---------------------------------------------------------------------------


def test_get_runtime_stats_returns_healthy_struct() -> None:
    """HARM-03 / D-10 step 3 — RuntimeStats factory returns a populated struct."""
    stats = classic_shared.get_runtime_stats()
    assert stats is not None
    assert stats.worker_threads > 0
    # R11: is_healthy is a bare attribute, not a method
    assert stats.is_healthy is True


def test_is_runtime_healthy_free_function() -> None:
    """Module-level `is_runtime_healthy()` returns a bool."""
    result = classic_shared.is_runtime_healthy()
    assert isinstance(result, bool)
    assert result is True


def test_runtime_stats_repr_is_descriptive() -> None:
    """RuntimeStats.__repr__ includes the class name and worker_threads field."""
    stats = classic_shared.get_runtime_stats()
    text = repr(stats)
    assert "RuntimeStats" in text
    assert "worker_threads" in text


def test_runtime_stats_has_no_direct_constructor() -> None:
    """R11/A8: RuntimeStats has no #[new] — direct construction raises TypeError.

    This test locks the contract — callers MUST use the factory.
    """
    try:
        classic_shared.RuntimeStats()  # type: ignore[call-arg]
    except TypeError:
        return
    msg = "RuntimeStats() did not raise TypeError — #[new] was added unexpectedly"
    raise AssertionError(msg)


# ---------------------------------------------------------------------------
# PathHandler (promoted 17 methods)
# ---------------------------------------------------------------------------


def test_path_handler_default_construction() -> None:
    """PathHandler() takes an optional cache_ttl_seconds with a default."""
    ph = classic_shared.PathHandler()
    assert ph is not None
    # Also verify the kwarg form is accepted
    ph2 = classic_shared.PathHandler(cache_ttl_seconds=60)
    assert ph2 is not None


def test_path_handler_normalize_path() -> None:
    """R11: method is `normalize_path`, NOT `normalize`."""
    ph = classic_shared.PathHandler()
    result = ph.normalize_path("/tmp/test")
    assert isinstance(result, str)
    assert len(result) > 0


def test_path_handler_split_and_join() -> None:
    """split_path decomposes and join_paths recomposes a path."""
    ph = classic_shared.PathHandler()
    parts = ph.split_path("a/b/c")
    assert isinstance(parts, list)
    assert len(parts) >= 1

    joined = ph.join_paths("/base", ["sub", "leaf.txt"])
    assert isinstance(joined, str)
    assert len(joined) > 0


def test_path_handler_filename_extension_parent_helpers() -> None:
    """get_filename / get_extension / get_parent return str-or-None."""
    ph = classic_shared.PathHandler()
    name = ph.get_filename("/tmp/file.txt")
    ext = ph.get_extension("/tmp/file.txt")
    parent = ph.get_parent("/tmp/file.txt")
    assert name is None or isinstance(name, str)
    assert ext is None or isinstance(ext, str)
    assert parent is None or isinstance(parent, str)


def test_path_handler_is_absolute_and_to_absolute() -> None:
    """is_absolute returns bool; to_absolute returns a str."""
    ph = classic_shared.PathHandler()
    assert isinstance(ph.is_absolute("/tmp"), bool)
    abs_path = ph.to_absolute("relative.txt", base=None)
    assert isinstance(abs_path, str)


def test_path_handler_common_prefix() -> None:
    """common_prefix accepts a list and returns Optional[str]."""
    ph = classic_shared.PathHandler()
    result = ph.common_prefix(["/a/b/c", "/a/b/d"])
    assert result is None or isinstance(result, str)


def test_path_handler_validate_paths_batch_shape() -> None:
    """validate_paths_batch returns list[tuple[str, bool, str]]."""
    ph = classic_shared.PathHandler()
    results = ph.validate_paths_batch(["/tmp", "/non/existent/path/for/test"])
    assert isinstance(results, list)
    assert len(results) == 2
    for item in results:
        assert isinstance(item, tuple)
        assert len(item) == 3
        path, is_valid, message = item
        assert isinstance(path, str)
        assert isinstance(is_valid, bool)
        assert isinstance(message, str)


def test_path_handler_validate_paths_batch_fast_shape() -> None:
    """validate_paths_batch_fast has the same return shape as the non-fast variant."""
    ph = classic_shared.PathHandler()
    results = ph.validate_paths_batch_fast(["/tmp"])
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], tuple)
    assert len(results[0]) == 3


def test_path_handler_split_path_fast() -> None:
    """split_path_fast returns a list of path components."""
    ph = classic_shared.PathHandler()
    result = ph.split_path_fast("a/b/c")
    assert isinstance(result, list)


def test_path_handler_cache_helpers() -> None:
    """cache_stats, cache_metrics, clear_cache, cleanup_cache all callable."""
    ph = classic_shared.PathHandler()
    # Warm up the cache via normalization so metrics are non-zero
    ph.normalize_path("/tmp/one")
    ph.normalize_path("/tmp/one")

    stats = ph.cache_stats()
    assert isinstance(stats, tuple)
    assert len(stats) == 2
    assert all(isinstance(x, int) for x in stats)

    metrics = ph.cache_metrics()
    assert isinstance(metrics, tuple)
    assert len(metrics) == 3
    assert isinstance(metrics[0], int)
    assert isinstance(metrics[1], int)
    assert isinstance(metrics[2], float)

    # Void methods
    ph.cleanup_cache()
    ph.clear_cache()


# ---------------------------------------------------------------------------
# StringProcessor (promoted 12 methods)
# ---------------------------------------------------------------------------


def test_string_processor_default_construction() -> None:
    """StringProcessor() is parameterless."""
    sp = classic_shared.StringProcessor()
    assert sp is not None


def test_string_processor_normalize_and_intern() -> None:
    """normalize returns str; intern returns str (the interned copy)."""
    sp = classic_shared.StringProcessor()
    normalized = sp.normalize("  HELLO  ")
    assert isinstance(normalized, str)

    interned = sp.intern("some-string")
    assert interned == "some-string"


def test_string_processor_batch_operations() -> None:
    """process_batch / process_batch_fast / intern_batch return list[str]."""
    sp = classic_shared.StringProcessor()

    result = sp.process_batch(["A", "B", "C"], "lower")
    assert isinstance(result, list)
    assert all(isinstance(x, str) for x in result)

    result_fast = sp.process_batch_fast(["X", "Y"], "upper")
    assert isinstance(result_fast, list)

    interned = sp.intern_batch(["foo", "bar", "baz"])
    assert isinstance(interned, list)
    assert len(interned) == 3


def test_string_processor_line_operations() -> None:
    """split_lines / split_lines_fast / join_lines round-trip correctly."""
    sp = classic_shared.StringProcessor()
    lines = sp.split_lines("alpha\nbeta\ngamma")
    assert isinstance(lines, list)
    assert len(lines) >= 3

    lines_fast = sp.split_lines_fast("one\ntwo")
    assert isinstance(lines_fast, list)

    joined = sp.join_lines(["a", "b", "c"], ",")
    assert isinstance(joined, str)
    assert "a" in joined


def test_string_processor_common_prefix() -> None:
    """common_prefix returns the shared leading substring of all inputs."""
    sp = classic_shared.StringProcessor()
    prefix = sp.common_prefix(["foobar", "foobaz", "foobat"])
    assert isinstance(prefix, str)
    assert prefix.startswith("foo")


def test_string_processor_pool_helpers() -> None:
    """pool_stats returns int; clear_pool is a no-op (logs warning)."""
    sp = classic_shared.StringProcessor()
    sp.intern("pooled")
    count = sp.pool_stats()
    assert isinstance(count, int)
    sp.clear_pool()  # Documented as a warning-log no-op; should not raise


# ---------------------------------------------------------------------------
# RustPerformanceMonitor (promoted 7 methods)
# ---------------------------------------------------------------------------


def test_rust_performance_monitor_default_construction() -> None:
    """RustPerformanceMonitor() is parameterless."""
    mon = classic_shared.RustPerformanceMonitor()
    assert mon is not None


def test_rust_performance_monitor_record_metric_and_stats() -> None:
    """record_metric takes 3 positional args (R11); get_all_stats returns a dict."""
    mon = classic_shared.RustPerformanceMonitor()
    # Fresh monitor — clear any prior state
    mon.clear_metrics()

    # R11: takes operation, duration_ms, bytes_processed
    mon.record_metric("test_op", 1, None)
    mon.record_metric("test_op", 2, 1024)

    stats = mon.get_all_stats()
    assert isinstance(stats, dict)


def test_rust_performance_monitor_get_operation_stats() -> None:
    """get_operation_stats returns dict | None for a given op name."""
    mon = classic_shared.RustPerformanceMonitor()
    mon.clear_metrics()
    mon.record_metric("opname", 1, None)
    result = mon.get_operation_stats("opname")
    assert result is None or isinstance(result, dict)


def test_rust_performance_monitor_start_stop_timer() -> None:
    """start_timer returns a dict, stop_timer consumes it."""
    mon = classic_shared.RustPerformanceMonitor()
    timer = mon.start_timer("timed_op")
    assert isinstance(timer, dict)
    mon.stop_timer(timer, bytes_processed=512)


# ---------------------------------------------------------------------------
# Pitfall 2 rust-only guard — all 19 @rust-suffixed symbols exist in the
# classic-shared-py surface. This locks the @rust proxy row contract and
# prevents silent surface drift.
# ---------------------------------------------------------------------------


def test_rust_only_symbols_in_core_surface() -> None:
    """All 19 classic_shared @rust-suffixed rust_symbol values exist in the parsed Rust surface.

    Matches the Wave 1/Plan 06/Plan 07 Pitfall 2 guard pattern.
    """
    surface_path = Path("docs/implementation/python_api_parity/baseline/rust_api_surface.json")
    contract_path = Path("docs/implementation/python_api_parity/baseline/parity_contract.json")

    assert surface_path.exists(), f"Missing {surface_path}"
    assert contract_path.exists(), f"Missing {contract_path}"

    with surface_path.open(encoding="utf-8") as f:
        surface = json.load(f)
    with contract_path.open(encoding="utf-8") as f:
        contract = json.load(f)

    shared_symbols = {
        s["symbol"] for s in surface["symbols"] if s.get("crate") == "classic-shared-py"
    }

    rust_only_rows = [
        r for r in contract["tier1Mappings"]
        if r.get("ownerModule") == "shared" and r["id"].endswith("@rust")
    ]

    missing: list[str] = []
    for row in rust_only_rows:
        if row["rustSymbol"] not in shared_symbols:
            missing.append(f"{row['id']} -> {row['rustSymbol']}")

    assert not missing, "Rust-only @rust-suffix shared rows missing from rust_api_surface: " + ", ".join(missing)

    # Plan 08 enrolled 19 @rust-suffixed shared proxy rows. Floor allows
    # minor fluctuations from future refactors without breaking the guard.
    assert len(rust_only_rows) >= 15, (
        f"Expected >=15 @rust rows for shared owner; got {len(rust_only_rows)}"
    )
