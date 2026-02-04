# Requirements: CLASSIC v8.3.0 Performance & Polish

**Defined:** 2026-02-04
**Core Value:** Python is the UI, Rust is the engine — every piece of business logic lives in Rust `-core` crates, Python only handles presentation and user interaction.

## v8.3.0 Requirements

Requirements for the Performance & Polish milestone. Establish baselines, optimize hot paths, fix pre-existing bugs.

### Benchmarking Infrastructure

- [ ] **BENCH-01**: Benchmarks execute in release mode only (debug builds rejected)
- [ ] **BENCH-02**: Benchmark results include statistical aggregation (min/mean/median/stddev/p95/p99)
- [ ] **BENCH-03**: Benchmark results export to JSON format for historical tracking
- [ ] **BENCH-04**: Benchmarks run multiple iterations with configurable warmup
- [ ] **BENCH-05**: CI pipeline detects performance regressions (>10% threshold)
- [ ] **BENCH-06**: Historical baselines stored for comparison across commits

### GIL & FFI Optimization

- [ ] **GIL-01**: Rust operations >1ms release Python GIL via `py.allow_threads()`
- [ ] **GIL-02**: FFI type conversion overhead measured separately from Rust compute time
- [ ] **GIL-03**: DashMap cache hit rates instrumented and reportable

### Profiling

- [ ] **PROF-01**: Flamegraph generation available for hot path identification
- [ ] **PROF-02**: py-spy integration captures Python+Rust combined stack traces
- [ ] **PROF-03**: Memory allocation profiling available via dhat

### Bug Fixes

- [ ] **BUG-01**: `test_clear_cache` in classic-yaml-core passes reliably (fix parallel test pollution)
- [ ] **BUG-02**: `classic_settings()` resolves file paths correctly regardless of CWD

## Future Requirements

Deferred to later milestones. Not in current roadmap.

### Extended Benchmarking

- **BENCH-07**: HTML report generation for benchmark results
- **BENCH-08**: Benchmark comparison between Git branches
- **BENCH-09**: Automated benchmark suite for all 16+ Rust -core crates

### Extended Profiling

- **PROF-04**: Continuous profiling in production builds
- **PROF-05**: Allocation hotspot visualization

## Out of Scope

Explicitly excluded from v8.3.0.

| Feature | Reason |
|---------|--------|
| New user-facing features | Performance milestone only |
| GUI framework changes | Keep PySide6/Qt, optimize existing |
| Rust async refactoring | Only add GIL release, don't restructure |
| Micro-benchmarking every function | Focus on hot paths identified by profiling |
| Custom benchmark framework | Use Criterion (Rust) and pytest-benchmark (Python) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GIL-01 | Phase 12 | Pending |
| GIL-02 | Phase 12 | Pending |
| BENCH-01 | Phase 13 | Pending |
| BENCH-02 | Phase 13 | Pending |
| BENCH-03 | Phase 13 | Pending |
| BENCH-04 | Phase 13 | Pending |
| BENCH-06 | Phase 13 | Pending |
| PROF-01 | Phase 14 | Pending |
| PROF-02 | Phase 14 | Pending |
| PROF-03 | Phase 14 | Pending |
| GIL-03 | Phase 14 | Pending |
| BUG-01 | Phase 15 | Pending |
| BUG-02 | Phase 15 | Pending |
| BENCH-05 | Phase 17 | Pending |

**Coverage:**
- v8.3.0 requirements: 14 total
- Mapped to phases: 14/14 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after roadmap revision (Phase 12 split)*
