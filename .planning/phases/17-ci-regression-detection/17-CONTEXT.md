# Phase 17: CI Regression Detection - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Automated performance regression detection in CI pipeline. Benchmarks run on PRs, compare against baselines, block merges on significant regressions, and update baselines on main branch merges. Uses the Criterion benchmark infrastructure established in Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Threshold Behavior
- Tiered thresholds: 5% regression = warning annotation, 10% = build failure
- Per-benchmark evaluation (each benchmark checked individually, not aggregated)
- Allow per-benchmark custom thresholds via config (for inherently noisy benchmarks)
- Label bypass: PR label `perf-regression-accepted` allows merge with documented justification

### Baseline Management
- Baselines update automatically on main branch merge only
- Store baselines in GitHub Actions cache (not committed to repo)
- Missing baseline scenario: skip comparison, pass with warning annotation
- Cache eviction recovery: next main branch run re-establishes baseline, PRs warn until then

### Reporting Format
- PR comment with table posted by bot
- Compact summary: only regressions and improvements shown, unchanged benchmarks hidden
- Update existing comment on each push, collapse previous results under details tag
- Failure messages: actionable summary listing failing benchmarks with % regression and link to detailed report

### Benchmark Scope
- Run all benchmarks (full suite, not subset)
- Same quick mode (50 samples) for both PRs and main branch
- Trigger: only when PR is marked ready for review (not on draft PRs)
- Required check: benchmark check must pass before merge is allowed

### Claude's Discretion
- Exact GitHub Actions workflow structure and job organization
- Cache key naming strategy
- PR comment markdown formatting and styling
- How to detect "ready for review" state change

</decisions>

<specifics>
## Specific Ideas

- Consistent with Phase 13's quick/thorough benchmark modes (BENCH_MODE env var)
- 10% threshold aligns with ROADMAP.md success criteria
- Label bypass provides escape hatch for intentional trade-offs (e.g., accepting slower code for better correctness)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-ci-regression-detection*
*Context gathered: 2026-02-04*
