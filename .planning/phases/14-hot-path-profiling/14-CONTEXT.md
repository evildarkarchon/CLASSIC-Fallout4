# Phase 14: Hot Path Profiling & Cache Instrumentation - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Developer tooling for performance analysis. Enables flamegraph generation for Rust hot paths, combined Python+Rust stack traces via py-spy, memory allocation profiling via dhat, and DashMap cache hit/miss observability. This phase produces profiling infrastructure — actual optimization happens in Phase 16 based on data gathered here.

</domain>

<decisions>
## Implementation Decisions

### Output location & format
- Store all profiling output under `target/profiling/`
- Flamegraphs in interactive SVG format (zoomable, searchable in browser)
- Timestamped filenames (e.g., `flamegraph-2026-02-05-143022.svg`) to preserve history
- Cache statistics: both JSON file for programmatic analysis and console summary for quick review

### Invocation method
- Primary invocation via PowerShell scripts (consistent with `rebuild_rust.ps1` pattern)
- Cargo aliases in `.cargo/config.toml` for quick command-line access
- Profiling scripts separate from benchmark scripts (benchmarks measure, profilers diagnose)
- py-spy: both wrapper for real app entry points and dedicated test harness for targeted profiling

### Cache logging granularity
- Configurable detail levels: aggregate stats by default, per-key tracking opt-in
- Use `tracing` crate log levels: TRACE for per-key detail, DEBUG for aggregate
- Instrument hot path caches only (yaml-core, scanlog-core, file-io-core)
- Report on demand only — developer explicitly calls function/script to dump stats

### Profile scope controls
- Support both whole-application profiling and per-crate isolation
- Duration control: time-bounded, manual start/stop, or operation-count bounded
- Pre-capture filtering: specify function prefixes to include/exclude
- Quick/thorough modes (matching Phase 13 benchmark pattern) for sampling rate

### Claude's Discretion
- dhat integration approach (feature flag vs build profile)
- Exact script naming and parameter design
- tracing subscriber configuration details
- Flamegraph generation toolchain choice (inferno, flamegraph-rs, etc.)

</decisions>

<specifics>
## Specific Ideas

- Match the quick/thorough pattern from Phase 13 benchmarks for consistency across tooling
- Keep profiling completely separate from benchmarking — they serve different purposes
- Cache stats should be easily comparable across runs (JSON format enables this)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-hot-path-profiling*
*Context gathered: 2026-02-04*
