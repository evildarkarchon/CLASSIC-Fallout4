"""Smoke tests for Phase 3 Plan 08 classic_file_io promotion (105 contract rows).

Plan 08 owns ALL classic_file_io gaps surfaced by the parity parser per R3.
This smoke suite provides at-least-one-test-per-class coverage for the 95
tier1 rows Plan 08 enrolls for classic_file_io:

- FileIOCore class + async/sync method coverage
- FileHasher class (static-only, R13 — NO #[new]) + cache helpers
- DDSHeader class (factory via from_bytes)
- EncodingDetector class
- FileGenerator / FileGeneratorConfig classes
- PyLogCollector / PyLineStreamer / PySyncLineStreamer classes
- RustFileIOError / RustFileIOIOError / RustFileIOParseError exceptions
- Module-level generate_ignore_file_async / generate_local_yaml_async functions
- 25 rust-only @rust-suffixed proxy rows (verified via rust_api_surface parity guard)

R13 CRITICAL: ``PyFileHasher`` has NO ``#[new]`` — all methods are
``#[staticmethod]``. Tests MUST call ``classic_file_io.FileHasher.method()``
NOT ``classic_file_io.FileHasher().method()``. Calling ``FileHasher()`` will
raise TypeError.

R13 cache_size semantics: ``cache_size()`` returns ``HASH_CACHE.len()``
(entry count), NOT bytes. After ``clear_cache()``, ``cache_size() == 0``
is the correct assertion.

Verified from:
  - classic-file-io-py/src/hash.rs (PyFileHasher, all #[staticmethod])
  - classic-file-io-core/src/hash.rs:308 (cache_size returns stats.size / len)
  - classic-file-io-py/src/log_collector.rs (sync block_on methods)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
from pathlib import Path

import classic_file_io
import pytest


# ---------------------------------------------------------------------------
# FileHasher (R13 — static-only, no constructor)
# ---------------------------------------------------------------------------


def test_file_hasher_has_no_constructor() -> None:
    """R13: PyFileHasher has NO #[new] — instance construction raises TypeError.

    Verified from classic-file-io-py/src/hash.rs:30-34:
        #[pyclass(name = "FileHasher", module = "classic_file_io")]
        pub struct PyFileHasher;  // Empty unit struct
    """
    assert classic_file_io.FileHasher is not None
    try:
        classic_file_io.FileHasher()  # type: ignore[call-arg]
    except TypeError:
        return
    msg = "FileHasher() should raise TypeError — no #[new] constructor exists"
    raise AssertionError(msg)


def test_file_hasher_cache_size_static_call() -> None:
    """R13: cache_size() is #[staticmethod] — call via class, not instance.

    Returns HASH_CACHE.len() — an entry COUNT, not a byte size.
    """
    size = classic_file_io.FileHasher.cache_size()
    assert isinstance(size, int)
    assert size >= 0


def test_file_hasher_cache_stats_returns_dict() -> None:
    """cache_stats() static method returns a dict with the canonical 5 keys."""
    stats = classic_file_io.FileHasher.cache_stats()
    assert isinstance(stats, dict)
    assert "hits" in stats
    assert "misses" in stats
    assert "hit_rate" in stats
    assert "size" in stats
    assert "capacity" in stats
    assert isinstance(stats["hits"], int)
    assert isinstance(stats["misses"], int)
    assert isinstance(stats["size"], int)
    assert isinstance(stats["capacity"], int)


def test_file_hasher_reset_cache_stats_zeros_counters() -> None:
    """reset_cache_stats() zeros hits and misses while preserving entries."""
    classic_file_io.FileHasher.reset_cache_stats()
    stats = classic_file_io.FileHasher.cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


def test_file_hasher_clear_cache_resets_entries_to_zero() -> None:
    """R13: clear_cache() removes all entries; cache_size() == 0 after.

    Verified from classic-file-io-core/src/hash.rs:308:
        pub fn cache_size() -> usize { Self::cache_stats().size }
    where ``stats.size`` is ``HASH_CACHE.len()`` — entry count, NOT bytes.
    """
    classic_file_io.FileHasher.clear_cache()
    assert classic_file_io.FileHasher.cache_size() == 0, (
        "cache_size() after clear_cache() must be 0 (entry count, not bytes)."
    )


def test_file_hasher_hash_file_sha256_roundtrip(tmp_path: Path) -> None:
    """hash_file returns the lowercase hex SHA256 of the file contents."""
    content = b"plan 08 smoke test payload"
    target = tmp_path / "payload.bin"
    target.write_bytes(content)

    classic_file_io.FileHasher.clear_cache()
    result = classic_file_io.FileHasher.hash_file(str(target))

    expected = hashlib.sha256(content).hexdigest()
    assert isinstance(result, str)
    assert len(result) == 64  # SHA256 is 256 bits == 64 hex chars
    assert result == expected


def test_file_hasher_hash_files_parallel_returns_dict(tmp_path: Path) -> None:
    """hash_files_parallel returns a dict mapping paths to hashes-or-None."""
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"alpha")
    b.write_bytes(b"beta")

    results = classic_file_io.FileHasher.hash_files_parallel([str(a), str(b)])
    assert isinstance(results, dict)
    assert len(results) == 2
    for value in results.values():
        assert value is None or isinstance(value, str)


def test_file_hasher_hash_files_to_map(tmp_path: Path) -> None:
    """hash_files_to_map filters out failures and returns a dict."""
    a = tmp_path / "map_a.bin"
    a.write_bytes(b"gamma")
    result = classic_file_io.FileHasher.hash_files_to_map([str(a)])
    assert isinstance(result, dict)
    assert len(result) >= 1  # Successful entry for a.bin


# ---------------------------------------------------------------------------
# FileIOCore (class + constructor + sync helpers)
# ---------------------------------------------------------------------------


def test_file_io_core_default_construction() -> None:
    """FileIOCore() takes optional encoding/errors/cache_size/max_concurrent_io kwargs."""
    core = classic_file_io.FileIOCore()
    assert core is not None


def test_file_io_core_file_exists_and_size(tmp_path: Path) -> None:
    """file_exists / get_file_size / get_file_info are synchronous helpers."""
    target = tmp_path / "sync_test.txt"
    target.write_text("hello world", encoding="utf-8")

    core = classic_file_io.FileIOCore()
    assert core.file_exists(str(target)) is True
    assert core.file_exists(str(tmp_path / "nonexistent.txt")) is False

    size = core.get_file_size(str(target))
    assert isinstance(size, int)
    assert size == len("hello world")

    info = core.get_file_info(str(target))
    assert isinstance(info, dict)


def test_file_io_core_read_file_async(tmp_path: Path) -> None:
    """read_file returns a coroutine; await yields the file contents."""
    target = tmp_path / "async_test.txt"
    target.write_text("async payload", encoding="utf-8")

    core = classic_file_io.FileIOCore()

    async def runner() -> str:
        return await core.read_file(str(target))

    result = asyncio.run(runner())
    assert isinstance(result, str)
    assert "async payload" in result


def test_file_io_core_walk_directory_sync(tmp_path: Path) -> None:
    """py_walk_directory is synchronous; returns a list of file paths.

    R1 NOTE: Despite the stub signature showing ``pattern`` and ``max_depth``
    as Optional, the PyO3 runtime requires both positional arguments. Pass
    ``None`` explicitly to get the "no filter / unlimited depth" behavior.
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file1.txt").write_text("one", encoding="utf-8")
    (tmp_path / "file2.log").write_text("two", encoding="utf-8")

    core = classic_file_io.FileIOCore()
    results = core.py_walk_directory(str(tmp_path), None, None)
    assert isinstance(results, list)
    assert all(isinstance(p, str) for p in results)


def test_file_io_core_clear_cache_sync() -> None:
    """clear_cache is synchronous and returns None."""
    core = classic_file_io.FileIOCore()
    core.clear_cache()  # must not raise


# ---------------------------------------------------------------------------
# DDSHeader (factory-only via from_bytes)
# ---------------------------------------------------------------------------


def test_dds_header_from_bytes_none_on_invalid() -> None:
    """DDSHeader.from_bytes returns None for empty/invalid bytes."""
    result = classic_file_io.DDSHeader.from_bytes(b"")
    assert result is None


def test_dds_header_from_bytes_none_on_short_bytes() -> None:
    """Fewer than 128 bytes is not a valid DDS header."""
    assert classic_file_io.DDSHeader.from_bytes(b"too short") is None


# ---------------------------------------------------------------------------
# EncodingDetector
# ---------------------------------------------------------------------------


def test_encoding_detector_default_construction_and_detect() -> None:
    """EncodingDetector() is parameterless; detect_encoding returns str."""
    detector = classic_file_io.EncodingDetector()
    result = detector.detect_encoding(b"Hello, world!")
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# FileGenerator + FileGeneratorConfig
# ---------------------------------------------------------------------------


def test_file_generator_config_construction_and_fields() -> None:
    """FileGeneratorConfig holds three strings and exposes them as attributes."""
    cfg = classic_file_io.FileGeneratorConfig(
        ignore_file_content="# Ignore patterns\n*.tmp",
        local_yaml_content="# Local config",
        game_name="Fallout4",
    )
    assert cfg.ignore_file_content.startswith("# Ignore")
    assert cfg.local_yaml_content.startswith("# Local")
    assert cfg.game_name == "Fallout4"


def test_file_generator_paths_and_config_accessor() -> None:
    """FileGenerator exposes ignore/local paths (as os.PathLike) and its config.

    R1 NOTE: The runtime returns ``pathlib.Path`` (``WindowsPath`` on Windows)
    rather than the ``str`` type the stub declares. Cast to str for the
    contract check and verify with ``os.fspath`` which accepts both forms.
    """
    import os

    cfg = classic_file_io.FileGeneratorConfig("a", "b", "Fallout4")
    gen = classic_file_io.FileGenerator(cfg)

    ignore_path = gen.ignore_file_path()
    local_path = gen.local_yaml_path()
    assert isinstance(os.fspath(ignore_path), str)
    assert isinstance(os.fspath(local_path), str)
    assert len(str(ignore_path)) > 0
    assert len(str(local_path)) > 0

    config = gen.config()
    assert config.game_name == "Fallout4"


# ---------------------------------------------------------------------------
# Log collection family (PyLogCollector, PyLineStreamer, PySyncLineStreamer)
# ---------------------------------------------------------------------------


def test_py_log_collector_construct_and_dir_accessors(tmp_path: Path) -> None:
    """PyLogCollector exposes sync path accessors."""
    collector = classic_file_io.PyLogCollector(
        base_folder=str(tmp_path),
        xse_folder=None,
        custom_folder=None,
    )
    crash_dir = collector.crash_logs_dir()
    pastebin_dir = collector.pastebin_dir()
    assert isinstance(crash_dir, str)
    assert isinstance(pastebin_dir, str)


def test_py_sync_line_streamer_iteration(tmp_path: Path) -> None:
    """PySyncLineStreamer is a real Python iterator obtained via FileIOCore.

    Exercises PySyncLineStreamer.__iter__ / __next__ (2 promoted rows).
    """
    target = tmp_path / "lines.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    core = classic_file_io.FileIOCore()
    streamer = core.stream_lines_sync(str(target))
    assert isinstance(streamer, classic_file_io.PySyncLineStreamer)

    collected = list(streamer)
    assert collected == ["alpha", "beta", "gamma"]


def test_py_line_streamer_async_iteration(tmp_path: Path) -> None:
    """PyLineStreamer is an async iterator — exercises __aiter__ / __anext__."""
    target = tmp_path / "async_lines.txt"
    target.write_text("one\ntwo\n", encoding="utf-8")

    core = classic_file_io.FileIOCore()

    async def runner() -> list[str]:
        streamer = await core.stream_lines(str(target))
        assert isinstance(streamer, classic_file_io.PyLineStreamer)
        out: list[str] = []
        async for line in streamer:
            out.append(line)
        return out

    lines = asyncio.run(runner())
    assert lines == ["one", "two"]


# ---------------------------------------------------------------------------
# Module-level generator free functions + Exception classes
# ---------------------------------------------------------------------------


def test_generate_ignore_file_async_and_local_yaml_async(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generate_ignore_file_async and generate_local_yaml_async are callable.

    Both are module-level free functions that return coroutines (the stub declares
    them as ``async def``). Run them in a temporary working directory so they do
    not pollute the repo.
    """
    monkeypatch.chdir(tmp_path)

    async def runner() -> tuple[bool, bool]:
        # generate_ignore_file_async(content)
        ignore = await classic_file_io.generate_ignore_file_async("# ignore patterns\n*.tmp")
        # generate_local_yaml_async(content, game_name)
        local = await classic_file_io.generate_local_yaml_async("# local config\n", "Fallout4")
        return ignore, local

    ignore_created, local_created = asyncio.run(runner())
    assert isinstance(ignore_created, bool)
    assert isinstance(local_created, bool)
    # Creation should have occurred at least once
    assert (tmp_path / "CLASSIC Ignore.yaml").exists()


def test_rust_file_io_error_is_exception_hierarchy() -> None:
    """The 3 RustFileIO* exception classes form a standard inheritance tree."""
    assert issubclass(classic_file_io.RustFileIOError, Exception)
    assert issubclass(
        classic_file_io.RustFileIOIOError, classic_file_io.RustFileIOError
    )
    assert issubclass(
        classic_file_io.RustFileIOParseError, classic_file_io.RustFileIOError
    )


# ---------------------------------------------------------------------------
# Pitfall 2 rust-only guard — all 25 file_io @rust-suffixed symbols exist in
# the classic-file-io-core surface (locks the proxy row contract)
# ---------------------------------------------------------------------------


def test_rust_only_symbols_in_core_surface() -> None:
    """All 25 classic_file_io @rust-suffixed rows resolve against rust_api_surface."""
    surface_path = Path("docs/implementation/python_api_parity/baseline/rust_api_surface.json")
    contract_path = Path("docs/implementation/python_api_parity/baseline/parity_contract.json")

    assert surface_path.exists(), f"Missing {surface_path}"
    assert contract_path.exists(), f"Missing {contract_path}"

    with surface_path.open(encoding="utf-8") as f:
        surface = json.load(f)
    with contract_path.open(encoding="utf-8") as f:
        contract = json.load(f)

    file_io_symbols = {
        s["symbol"] for s in surface["symbols"] if s.get("crate") == "classic-file-io-core"
    }

    rust_only_rows = [
        r for r in contract["tier1Mappings"]
        if r.get("ownerModule") == "file_io" and r["id"].endswith("@rust")
    ]

    missing: list[str] = []
    for row in rust_only_rows:
        if row["rustSymbol"] not in file_io_symbols:
            missing.append(f"{row['id']} -> {row['rustSymbol']}")

    assert not missing, (
        "Rust-only file_io @rust-suffix rows missing from rust_api_surface: "
        + ", ".join(missing)
    )

    assert len(rust_only_rows) >= 25, (
        f"Expected >=25 @rust rows for file_io owner; got {len(rust_only_rows)}"
    )
