---
phase: 14-hot-path-profiling
plan: 02
subsystem: cache-instrumentation
tags: [dhat, cache-stats, atomicu64, dashmap, tracing]
dependency-graph:
  requires: [14-01-profiling-infrastructure]
  provides: [dhat-heap-profiling, cache-hit-miss-tracking, cache-stats-api]
  affects: [16-performance-optimization, future-cache-tuning]
tech-stack:
  added: [dhat]
  patterns: [atomicu64-counters, serde-serializable-stats, trace-instrumentation]
key-files:
  created:
    - scripts/profile/run_dhat.ps1
    - scripts/profile/dump_cache_stats.ps1
  modified:
    - rust/business-logic/classic-yaml-core/Cargo.toml
    - rust/business-logic/classic-yaml-core/src/lib.rs
    - rust/business-logic/classic-settings-core/Cargo.toml
    - rust/business-logic/classic-settings-core/src/cache.rs
    - rust/business-logic/classic-settings-core/src/lib.rs
decisions:
  - id: CACHE-01
    summary: "AtomicU64 with Ordering::Relaxed for cache counters"
    context: "Hit/miss tracking needs thread safety but not strict ordering"
    alternatives: ["Mutex-protected counters", "Thread-local counters"]
    rationale: "Relaxed ordering sufficient for statistics; lock-free for performance"
  - id: CACHE-02
    summary: "CacheStats struct with Serialize derive for JSON export"
    context: "Need to export stats to Python and external tools"
    alternatives: ["HashMap return", "Custom serialization"]
    rationale: "Structured type with serde enables both Rust and Python consumption"
metrics:
  duration: "~8m"
  completed: "2026-02-05"
---

# Phase 14 Plan 02: Cache Instrumentation Summary

**One-liner:** AtomicU64 hit/miss counters with CacheStats struct and dhat feature flag for heap profiling.

## What Was Done

### Task 1: classic-yaml-core Cache Instrumentation
- Added `dhat-heap` feature flag with optional dhat dependency
- Added `serde` and `tracing` dependencies
- Added static `CACHE_HITS` and `CACHE_MISSES` AtomicU64 counters
- Added `CacheStats` struct with Serialize derive
- Added `cache_stats()` function returning hit rate and size
- Added `reset_cache_stats()` function for testing
- Updated `load_yaml_file()` to track hits/misses with TRACE-level tracing

### Task 2: classic-settings-core Cache Instrumentation
- Added `dhat-heap` feature flag with optional dhat dependency
- Added `tracing` dependency
- Added static `CACHE_HITS` and `CACHE_MISSES` AtomicU64 counters
- Added `CacheStats` struct with Serialize derive (includes keys list)
- Added `cache_stats()` and `reset_cache_stats()` functions
- Updated `get_cached()` to track hits/misses with TRACE-level tracing
- Exported new cache stats API from lib.rs

### Task 3: PowerShell Profiling Scripts
- Created `run_dhat.ps1` (184 lines) for dhat heap profiling
  - Supports `-Test`, `-Bench`, `-TestFilter` parameters
  - Generates timestamped output files
  - Provides link to online dhat viewer
- Created `dump_cache_stats.ps1` (215 lines) for cache stats extraction
  - Supports `console`, `json`, `both` output formats
  - Shows hit rate as percentage
  - Provides summary across all caches

## Commits

| Commit | Description |
|--------|-------------|
| 81dd63c7 | feat(14-02): add dhat feature and cache instrumentation to classic-yaml-core |
| dc4b6fc0 | feat(14-02): add cache instrumentation to classic-settings-core |
| 2ab0a9e5 | feat(14-02): create dhat and cache stats PowerShell scripts |

## Files Changed

**Created:**
- `scripts/profile/run_dhat.ps1` - dhat heap profiling runner
- `scripts/profile/dump_cache_stats.ps1` - cache stats extraction

**Modified:**
- `rust/business-logic/classic-yaml-core/Cargo.toml` - dhat-heap feature, serde/tracing deps
- `rust/business-logic/classic-yaml-core/src/lib.rs` - CacheStats, counters, tracing
- `rust/business-logic/classic-settings-core/Cargo.toml` - dhat-heap feature, tracing dep
- `rust/business-logic/classic-settings-core/src/cache.rs` - CacheStats, counters, tracing
- `rust/business-logic/classic-settings-core/src/lib.rs` - export cache_stats API

## Verification Results

1. Both crates compile with dhat feature:
   - `cargo check -p classic-yaml-core --features dhat-heap` - OK
   - `cargo check -p classic-settings-core --features dhat-heap` - OK

2. All profile scripts exist:
   - `run_flamegraph.ps1` (from 14-01)
   - `run_pyspy.ps1` (from 14-01)
   - `run_dhat.ps1` (this plan)
   - `dump_cache_stats.ps1` (this plan)

3. Scripts have comprehensive help text via Get-Help

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Met

- [x] classic-yaml-core has dhat-heap feature flag and compiles with it
- [x] classic-settings-core has dhat-heap feature flag and compiles with it
- [x] Both caches track hits/misses via AtomicU64 counters
- [x] cache_stats() function exported from both crates
- [x] CacheStats struct serializable to JSON
- [x] scripts/profile/run_dhat.ps1 exists with test/bench support
- [x] scripts/profile/dump_cache_stats.ps1 exists with console/JSON output
- [x] TRACE-level tracing events for per-key cache access detail

## Next Phase Readiness

Phase 14 (Hot Path Profiling) is now complete. The profiling infrastructure is ready:
- Flamegraph generation for CPU profiling
- py-spy for combined Python+Rust stack analysis
- dhat for heap allocation profiling
- Cache hit/miss statistics for cache effectiveness analysis

Next: Phase 15 (GIL Audit & Release) - analyze and optimize GIL handling
