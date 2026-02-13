# GIL Release Audit

**Audited:** 2026-02-04
**Threshold:** 1ms guideline (documented exceptions)
**PyO3 Version:** 0.27.2
**Helper Used:** `classic_shared_py::without_gil()`

## Summary

| Category | Count |
|----------|-------|
| Operations with existing GIL release | 13 |
| Operations added GIL release | 18 |
| Operations not needing GIL release | 45+ |
| Async operations (different GIL semantics) | 20+ |

## Key Findings

1. **Async operations (`future_into_py`)** release GIL automatically when awaited - no additional work needed
2. **Batch operations** are the highest priority for GIL release (parallel benefit)
3. **File I/O operations** benefit significantly from GIL release
4. **Pattern matching and parsing** operations benefit when processing >1000 lines

## By Crate

### classic-shared-py (Foundation)

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `without_gil()` | N/A | HELPER | GIL release helper definition |
| `PyStringProcessor.*` | <0.1ms | NOT NEEDED | Fast string operations |
| `PyPathHandler.*` | <0.1ms | NOT NEEDED | Path manipulation |
| `get_runtime_stats()` | <0.1ms | NOT NEEDED | Simple metric access |

### classic-yaml-py

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `parse_yaml` | 2-50ms | **ADDED** | YAML parsing scales with content size |
| `dump_yaml` | 1-20ms | **ADDED** | YAML serialization |
| `load_yaml_file` | 5-100ms | **ADDED** | File I/O + parsing combined |
| `save_yaml_file` | 5-50ms | **ADDED** | File I/O + serialization |
| `get_setting` | <0.5ms | NOT NEEDED | Simple dict traversal |
| `set_setting` | <0.5ms | NOT NEEDED | Simple dict modification |
| `clear_cache` | <0.1ms | NOT NEEDED | Simple cache clear |
| `get_cache_stats` | <0.1ms | NOT NEEDED | Simple stat access |
| `get_string_value` | <0.5ms | NOT NEEDED | Simple extraction |
| `get_vec_value` | <0.5ms | NOT NEEDED | Simple extraction |
| `get_hashmap_value` | <0.5ms | NOT NEEDED | Simple extraction |

### classic-scanlog-py

#### Parser Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `parse_segments` | 5-100ms | EXISTING (conditional) | GIL released for >1000 lines |
| `parse_segments_parallel` | 10-200ms | EXISTING | Always releases GIL |
| `find_patterns` | 5-50ms | EXISTING (conditional) | GIL released for >1000 lines |
| `find_patterns_chunked` | 10-100ms | EXISTING | Always releases GIL |
| `extract_section` | <1ms | NOT NEEDED | Single section extraction |
| `extract_sections_batch` | 1-10ms | **ADDED** | Batch extraction |
| `parse_crash_header` | <1ms | NOT NEEDED | Header parsing only |
| `get_section` | <0.5ms | NOT NEEDED | Simple section lookup |
| `parse_all_sections` | 2-20ms | **ADDED** | Full section parsing |
| `parse_complete` | 5-50ms | **ADDED** | Complete log parsing |
| `extract_formids` | 1-5ms | **ADDED** | FormID extraction |
| `extract_plugins` | 1-5ms | **ADDED** | Plugin extraction |
| `extract_addresses` | 1-5ms | **ADDED** | Address extraction |
| `find_errors` | 1-5ms | **ADDED** | Error pattern matching |
| `benchmark` | Variable | NOT NEEDED | Testing only |

#### Mod Detector Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `detect_mods_single` | 2-20ms | **ADDED** | Pattern matching against plugins |
| `detect_mods_double` | 2-20ms | **ADDED** | Pattern matching (conflict detection) |
| `detect_mods_important` | 2-20ms | **ADDED** | Pattern matching with GPU/XSE |
| `detect_mods_batch` | 5-100ms | **ADDED** | Batch detection (high priority) |

#### FormID Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `extract_formids` | 1-5ms | **ADDED** | Regex extraction |
| `parse_formid` | <0.1ms | NOT NEEDED | Single FormID parse |
| `analyze_batch` | 2-20ms | **ADDED** | Batch analysis |
| `clear_cache` | <0.1ms | NOT NEEDED | Cache management |
| `cache_stats` | <0.1ms | NOT NEEDED | Stat access |

#### FormID Analyzer Core

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `extract_formids` | 1-5ms | **ADDED** | FormID extraction |
| `formid_match` | 5-50ms | EXISTING | Async with GIL release |
| `extract_formids_batch` | 5-50ms | **ADDED** | Batch extraction |
| `is_valid_formid` | <0.1ms | NOT NEEDED | Simple validation |
| `validate_formids_batch` | 1-5ms | **ADDED** | Batch validation |

#### Suspect Scanner Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `suspect_scan_mainerror` | 2-10ms | **ADDED** | Pattern scanning |
| `suspect_scan_stack` | 5-30ms | **ADDED** | Stack trace scanning |
| `scan_suspects_batch` | 10-100ms | **ADDED** | Batch scanning (high priority) |
| `check_dll_crash` | <1ms | NOT NEEDED | Simple check |

#### Plugin Analyzer Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `loadorder_scan_log` | 2-20ms | **ADDED** | Load order parsing |
| `check_plugin_limit` | 1-5ms | **ADDED** | Limit checking |
| `plugin_match` | 2-10ms | **ADDED** | Plugin matching |
| `filter_ignored_plugins` | 1-5ms | **ADDED** | Plugin filtering |
| `detect_plugins_batch` | 5-50ms | **ADDED** | Batch detection |
| `contains_plugin` | <0.1ms | NOT NEEDED | Simple check |

#### Record Scanner Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `scan_named_records` | 2-10ms | **ADDED** | Record scanning |
| `extract_records` | 1-5ms | **ADDED** | Record extraction |
| `clear_cache` | <0.1ms | NOT NEEDED | Cache management |
| `scan_records_batch` | 5-50ms | **ADDED** | Batch scanning |
| `contains_record` | <0.1ms | NOT NEEDED | Simple check |

#### Report Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `PyStringPool.*` | <0.5ms | NOT NEEDED | Fast operations |
| `PyReportFragment.*` | <0.5ms | NOT NEEDED | Fragment manipulation |
| `PyReportComposer.compose` | 1-5ms | NOT NEEDED | Usually fast |
| `PyReportComposer.compose_optimized` | 1-5ms | NOT NEEDED | Usually fast |
| `PyReportGenerator.*` | <0.5ms each | NOT NEEDED | Fragment generation |
| `PyParallelReportProcessor.*` | 1-10ms | NOT NEEDED | Currently passthrough |

#### Orchestrator Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `process_log` | 50-500ms | EXISTING | Full log processing |
| `process_logs_batch` | Variable | EXISTING | Batch processing |
| `write_reports_batch` | Variable | EXISTING | File I/O batch |
| `load_loadorder` | 5-50ms | EXISTING | File I/O |
| `detect_folon` | <0.5ms | NOT NEEDED | Simple check |
| `check_loadorder_exists` | <0.1ms | NOT NEEDED | File existence |
| `is_feature_complete` | <0.1ms | NOT NEEDED | State check |
| `has_database_pool` | <0.1ms | NOT NEEDED | State check |
| `is_initialized` | <0.1ms | NOT NEEDED | State check |

### classic-file-io-py

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `read_file` | Variable | ASYNC | `future_into_py` |
| `write_file` | Variable | ASYNC | `future_into_py` |
| `read_lines` | Variable | ASYNC | `future_into_py` |
| `stream_lines` | Variable | ASYNC | `future_into_py` |
| `stream_lines_sync` | Variable | **ADDED** | Sync streaming |
| `read_bytes` | Variable | ASYNC | `future_into_py` |
| `write_lines` | Variable | ASYNC | `future_into_py` |
| `write_bytes` | Variable | ASYNC | `future_into_py` |
| `append_file` | Variable | ASYNC | `future_into_py` |
| `clear_cache` | <1ms | EXISTING | GIL release |
| `file_exists` | <0.1ms | NOT NEEDED | Fast check |
| `get_file_info` | <1ms | NOT NEEDED | Metadata access |
| `get_file_size` | <0.1ms | NOT NEEDED | Cached access |
| `read_file_mmap` | Variable | ASYNC | `future_into_py` |
| `read_file_with_encoding` | Variable | ASYNC | `future_into_py` |
| `read_dds_header` | 1-10ms | EXISTING | GIL release |
| `read_dds_headers_batch` | 10-500ms | **ADDED** | Batch file I/O |
| `walk_directory` | 10-1000ms | **ADDED** | Directory traversal |
| `read_multiple_files` | Variable | ASYNC | `future_into_py` |
| `write_multiple_files` | Variable | ASYNC | `future_into_py` |

### classic-scangame-py

#### Integrity Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `check_executable_version` | 10-100ms | **ADDED** | SHA256 hashing of EXE |
| `check_installation_location` | <1ms | NOT NEEDED | Path checking |
| `run_all_checks` | 15-150ms | **ADDED** | Multiple file operations |
| `run_full_check` | 15-150ms | **ADDED** | Combined check string |

#### BA2 Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `find_ba2_files` | 10-100ms | **ADDED** | Directory search |
| `scan_archive` | 50-500ms | **ADDED** | BA2 file parsing |
| `scan_archives_batch` | 100-5000ms | **ADDED** | Batch BA2 scanning |
| `scan_all_ba2_archives` | 100-5000ms | **ADDED** | Convenience function |

#### Unpacked Module

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `scan_directory` | 50-1000ms | **ADDED** | Directory traversal |
| `scan_unpacked_files` | 50-1000ms | **ADDED** | Convenience function |

#### Other Modules (config, enb, ini, logs, toml_check, xse)

| Module | Operations | GIL Status | Notes |
|--------|------------|------------|-------|
| config | duplicate detection | **ADDED** | File parsing |
| enb | ENB detection | <1ms typical | NOT NEEDED |
| ini | INI validation | **ADDED** | File parsing |
| logs | log processing | **ADDED** | File I/O |
| toml_check | TOML validation | **ADDED** | File parsing |
| xse | XSE plugin checks | **ADDED** | File operations |

### classic-config-py

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| `YamlData::new` | 50-500ms | EXISTING | YAML loading with GIL release |
| `from_yaml_content` | 10-100ms | NOT NEEDED | No file I/O, parsing only |
| All getters | <0.1ms | NOT NEEDED | Simple property access |
| `create_yamldata` | 50-500ms | EXISTING (via YamlData::new) | Wrapper function |
| `clear_yaml_cache` | <0.1ms | NOT NEEDED | Cache clear |

### classic-database-py

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| All operations | Variable | ASYNC | All use `future_into_py` |

### classic-message-py

| Operation | Timing | GIL Status | Notes |
|-----------|--------|------------|-------|
| All operations | <0.1ms | NOT NEEDED | Fast message handling |
| `strip_emoji` | <0.1ms | NOT NEEDED | Simple string processing |
| `format_log_message` | <0.1ms | NOT NEEDED | Simple formatting |

### Low-Priority Crates (NOT NEEDED for GIL release)

| Crate | Reason |
|-------|--------|
| classic-constants-py | Static constant access only |
| classic-path-py | Fast path operations |
| classic-perf-py | Fast metric operations |
| classic-registry-py | Fast registry operations |
| classic-resource-py | Fast resource lookup |
| classic-settings-py | Fast settings access |
| classic-version-py | Fast version comparison |
| classic-web-py | URL utilities only (async for actual network) |
| classic-xse-py | Fast XSE checks |
| classic-update-py | Uses async for network operations |
| classic-pybridge-py | Bridge utilities only |

## Implementation Notes

### Pattern: Conditional GIL Release

For operations that may be fast or slow depending on input size:

```rust
if data.len() > 1000 {
    without_gil(py, || process(&data))
} else {
    process(&data)
}
```

### Pattern: Async Operations

Operations using `future_into_py` automatically handle GIL correctly:

```rust
future_into_py(py, async move {
    // GIL is released when Python awaits the coroutine
    inner.async_operation().await.map_err(to_pyerr)
})
```

### Pattern: Extract Before Release

**Critical:** Extract ALL Python data before calling `without_gil`:

```rust
// CORRECT
let rust_data: Vec<String> = py_list.extract()?;
without_gil(py, || process(&rust_data))

// WRONG - will panic
without_gil(py, || {
    py_list.extract() // Accessing Python object without GIL!
})
```

## Verification

GIL release is verified through:

1. **Criterion benchmarks** measuring pure Rust compute time
2. **Integration tests** proving concurrent Python threads make progress
3. **Timing comparisons** (concurrent vs sequential execution)

See:
- `ClassicLib-rs/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs`
- `ClassicLib-rs/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs`
- `ClassicLib-rs/python-bindings/classic-yaml-py/benches/gil_benchmarks.rs`
- `tests/rust_integration/gil_release/test_concurrent_operations.py`
