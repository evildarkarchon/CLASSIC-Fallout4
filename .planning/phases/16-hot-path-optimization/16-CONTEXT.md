# Phase 16: Hot Path Optimization (Data-Driven) - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize hot paths based on profiling data from Phase 14. Measure improvements against Phase 13 benchmark baselines. Top 3+ hot paths should show measurable improvement (20%+ median), with no regressions (within ±5% noise) in non-optimized paths. This phase uses existing profiling infrastructure to identify targets, then applies optimizations — it does not create new profiling tools.

</domain>

<decisions>
## Implementation Decisions

### Profiling scope
- Profile full app lifecycle (CLI scan workflow), let data reveal hot paths
- Use realistic data (actual crash logs and YAML configs from real users)
- Use combined Python+Rust stacks via py-spy --native for comprehensive visibility
- Run 5+ profiling iterations with statistical analysis before selecting optimization targets

### Target prioritization
- Rank hot paths by time spent (CPU cycles) — pure data-driven selection
- Minimum 3 targets; expand if optimizing one path easily fixes related nearby paths
- If profiling reveals significant Python hot paths, migrate them to Rust as part of optimization
- For third-party library hot paths (PyO3, yaml-rust2): cache/batch to amortize costs rather than work around

### Improvement thresholds
- 20% improvement (median) minimum to consider a hot path "optimized"
- Measure against median (most stable, less affected by outliers)
- Regression defined as >±5% change (anything within ±5% is noise margin)
- Best-effort completion: document any hot paths that resist optimization and why

### Trade-off preferences
- Balanced memory vs speed: moderate caching acceptable, but not 2x memory usage
- Moderate code complexity acceptable for gains (SIMD, custom allocators, unsafe blocks)
- Minor API evolution OK: add new faster APIs alongside existing ones, deprecate old paths
- Stop optimizing a path at diminishing returns (squeeze out easy wins, then move on)

### Claude's Discretion
- Specific optimization techniques per hot path (algorithmic, caching, batching, parallelism)
- Order of attacking hot paths within priority ranking
- Exact threshold for "diminishing returns"
- Whether unsafe code is warranted for specific optimizations

</decisions>

<specifics>
## Specific Ideas

- Phase 14 infrastructure is ready but `target/profiling/` is empty — first task is collecting actual profiling data
- Benchmark baselines exist in `target/criterion/` from Phase 13 — compare against these
- Match the quick/thorough pattern: thorough profiling runs before selecting targets, quick runs during optimization iteration

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-hot-path-optimization*
*Context gathered: 2026-02-04*
