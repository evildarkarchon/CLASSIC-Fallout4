# Phase 13: Benchmark Infrastructure - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish Criterion benchmark infrastructure that produces statistical output and stores historical baselines for comparison across commits. This phase sets up the tooling and initial benchmarks; actual optimization based on benchmark data is Phase 16, and CI integration is Phase 17.

</domain>

<decisions>
## Implementation Decisions

### Benchmark Scope
- Benchmark all `-core` crates (yaml-core, scanlog-core, file-io-core, etc.)
- Include both public API functions AND internal hot paths
- Measure FFI overhead separately from pure Rust compute time (Python→Rust→Python round-trip benchmarks)
- Use both realistic fixtures (actual crash logs, real YAML configs) and synthetic data (for size scaling tests)

### Output & Reporting
- Include percentile statistics (p95/p99) in addition to standard min/mean/median/stddev
- Configurable verbosity: summary by default, --verbose flag for full details
- Export format: JSON (machine-readable for tooling)
- Display performance changes as percentage relative to baseline (+15%, -8%)

### Baseline Storage
- Baselines are gitignored (local only, not version controlled)
- Store in Criterion's default location: `target/criterion/`
- Name baselines by date (timestamp-based naming)
- Auto-cleanup: keep 10 most recent baselines, delete older ones

### Run Configuration
- Two modes: quick (fewer samples, for dev iteration) and thorough (full samples, for baselines)
- Mode selection via environment variable: `BENCH_MODE=quick` or `BENCH_MODE=thorough`
- Default to quick mode when no env var set
- Use Criterion's default warmup (auto-calibration)

### Claude's Discretion
- Specific iteration counts for quick vs thorough modes
- Benchmark grouping and organization within crates
- Statistical significance thresholds for reporting changes
- Fixture file selection and synthetic data generation approach

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard Criterion patterns and best practices.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-benchmark-infrastructure*
*Context gathered: 2026-02-04*
