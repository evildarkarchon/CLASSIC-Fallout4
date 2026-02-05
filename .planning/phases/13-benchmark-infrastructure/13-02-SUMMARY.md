---
phase: 13-benchmark-infrastructure
plan: 02
subsystem: testing
tags: [criterion, benchmarks, yaml, scanlog, file-io, performance]

# Dependency graph
requires:
  - phase: 13-01
    provides: Shared benchmark configuration module (BENCH_MODE, configure_criterion)
provides:
  - yaml-core Criterion benchmarks (parsing, serialization, traversal, modification)
  - scanlog-core Criterion benchmarks with real crash log fixtures
  - file-io-core Criterion benchmarks (encoding detection, path filtering)
affects: [13-03-baseline-establishment, future-performance-regression-testing]

# Tech tracking
tech-stack:
  added:
    - criterion 0.6.0 (in each -core crate)
  patterns:
    - "#[path] attribute for shared benchmark module imports"
    - "include_str! for embedding real crash logs at compile time"
    - "Synthetic data generation for controlled measurements"
    - "Throughput measurements (bytes/sec) for data processing benchmarks"

key-files:
  created:
    - rust/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs
    - rust/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs
    - rust/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs
  modified:
    - rust/business-logic/classic-yaml-core/Cargo.toml
    - rust/business-logic/classic-scanlog-core/Cargo.toml
    - rust/business-logic/classic-file-io-core/Cargo.toml
    - rust/benches/common/config.rs (added allow attributes)
    - rust/benches/common/fixtures.rs (added allow attributes)

key-decisions:
  - "Use #[path = '../../../benches/common/mod.rs'] for shared config import"
  - "Embed real crash logs via include_str! for realistic scanlog benchmarks"
  - "Use synthetic data for file-io-core (controlled, reproducible measurements)"
  - "Each crate has 5-7 benchmark groups covering major operations"

patterns-established:
  - "Benchmark file location: rust/business-logic/{crate}/benches/{name}_benchmarks.rs"
  - "Cargo.toml [[bench]] section with harness = false"
  - "criterion_group! macro with config = common::config::configure_criterion()"
  - "Throughput::Bytes for all data processing benchmarks"

# Metrics
duration: 12min
completed: 2026-02-05
---

# Phase 13 Plan 02: Business Logic Crate Benchmarks Summary

**Comprehensive Criterion benchmarks for yaml-core, scanlog-core, and file-io-core using shared configuration and realistic fixtures**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-02-05T00:01:12Z
- **Completed:** 2026-02-05T00:13:XX
- **Tasks:** 3
- **Files created:** 3 benchmark files
- **Files modified:** 3 Cargo.toml + 2 shared module files

## Accomplishments

- Created yaml-core benchmarks covering YAML parsing, serialization, traversal, and modification
- Created scanlog-core benchmarks using real crash log fixtures (15KB, 37KB, 61KB)
- Created file-io-core benchmarks for encoding detection, path filtering, and file operations
- All benchmarks use shared `configure_criterion()` from rust/benches/common/config.rs
- No duplicated BENCH_MODE logic - centralized in shared config module

## Task Commits

Each task was committed atomically:

1. **Task 1: yaml-core benchmarks** - `2771f13a` (feat)
2. **Task 2: scanlog-core benchmarks** - `acfc3e3f` (feat)
3. **Task 3: file-io-core benchmarks** - `360a1b18` (feat)

## Benchmark Coverage

### yaml-core (5 groups, 19 benchmarks)
- **yaml_parsing**: Parse YAML of varying sizes (100, 1000, 5000 lines)
- **yaml_serialization**: Dump YAML structures to strings
- **yaml_traversal**: Navigate nested structures (shallow, nested, deep 10-level)
- **yaml_modification**: Update/create values in YAML documents
- **yaml_config_variants**: Compare default vs custom config performance

### scanlog-core (7 groups, 32 benchmarks)
- **segment_parsing**: Parse crash logs into segments (cached and uncached)
- **formid_extraction**: Extract FormIDs from callstack lines
- **pattern_matching**: Aho-Corasick multi-pattern matching (15 patterns)
- **plugin_detection**: Line-by-line and batch plugin detection
- **record_scanning**: Named record detection
- **full_pipeline**: Complete crash log analysis workflow
- **parser_creation**: Component initialization overhead

### file-io-core (5 groups, 26 benchmarks)
- **encoding_detection**: UTF-8, UTF-8+BOM, Windows-1252 detection
- **path_filtering**: Extension filtering, prefix matching, unique counts
- **file_io_core**: FileIOCore creation, cached file reads
- **log_patterns**: Crash log filename pattern matching
- **dds_parsing**: DDS magic validation and dimension extraction

## Decisions Made

1. **Shared config via #[path]**: All benchmark files import `common::config::configure_criterion()` using Rust's `#[path]` attribute rather than workspace dependency. This keeps benchmark-specific code out of library crates.

2. **Real crash logs for scanlog**: scanlog-core uses `include_str!` to embed actual crash logs (crash-0DB9300.log, crash-12624.log, crash-2022-06-05-12-58-02.log) for realistic performance measurements.

3. **Synthetic data for file-io**: file-io-core uses generated data (UTF-8/Windows-1252 content, path lists) for controlled, reproducible measurements independent of filesystem.

4. **Throughput metrics**: All data processing benchmarks include `Throughput::Bytes()` for bytes/second measurements.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added allow attributes to shared benchmark modules**

- **Found during:** Task 1 verification
- **Issue:** Strict linting rules in workspace caused errors for unused items when shared module is imported
- **Fix:** Added `#![allow(dead_code)]` and `#![allow(unused_imports)]` to config.rs and fixtures.rs
- **Files modified:** rust/benches/common/config.rs, rust/benches/common/fixtures.rs
- **Commit:** Included in 2771f13a

**2. [Rule 1 - Bug] Fixed #[path] attribute paths**

- **Found during:** Task 1 verification
- **Issue:** Initial path `../../../../benches/common/mod.rs` was incorrect for business-logic crate layout
- **Fix:** Corrected to `../../../benches/common/mod.rs` (3 levels up from benches/ to rust/)
- **Files modified:** All benchmark files
- **Commit:** Included in 2771f13a

**3. [Rule 2 - API Usage] Simplified scanlog benchmarks for available APIs**

- **Found during:** Task 2 compilation
- **Issue:** PluginAnalyzer doesn't have scan_plugins method as assumed in plan
- **Fix:** Used detect_plugins_batch() function for full log plugin detection instead
- **Files modified:** rust/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs
- **Commit:** Included in acfc3e3f

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three business logic crates have comprehensive Criterion benchmarks
- Ready for Plan 13-03 (Baseline Establishment) to run benchmarks and save baselines
- PowerShell runner from Plan 13-01 can now benchmark all crates:
  ```powershell
  ./scripts/bench/run_benchmarks.ps1 -Mode quick
  ./scripts/bench/run_benchmarks.ps1 -Mode thorough -SaveBaseline
  ```

---
*Phase: 13-benchmark-infrastructure*
*Completed: 2026-02-05*
