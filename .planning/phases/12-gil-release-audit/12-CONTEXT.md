# Phase 12: GIL Release Audit - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Audit all Rust FFI operations to ensure proper GIL release during long-running computations. Measure FFI overhead separately from Rust compute time. Establish permanent benchmarks and verification tests.

</domain>

<decisions>
## Implementation Decisions

### Audit Scope
- Audit ALL Rust FFI operations, not just hot paths — comprehensive review
- Document only GIL-relevant operations (those needing or having GIL release)
- Include TUI review for async/blocking pattern consistency (not GIL, but related)
- Create persistent audit document (markdown) listing all audited operations

### Measurement Output
- Use Criterion benchmark suite — permanent, feeds into Phase 13 infrastructure
- Summary statistics only (mean, median, p95, p99) — standard Criterion output
- Local baselines only — CI runners have different specs, so committed baselines won't be comparable
- Measure timing for ALL operations (complete data), even if only GIL-relevant ops are documented

### Verification Approach
- Integration tests with concurrent Python threads alongside Rust operations — proves GIL released
- Tests in regular test suite (tests/rust_integration/) — runs with every pytest invocation
- Hard test failures for missing GIL releases — blocks merge
- Debug assertions in production code (`debug_assert!`) to detect missing GIL releases at runtime

### Threshold Handling
- 1ms threshold as guideline with documented exceptions — not a hard rule
- Runtime-configurable threshold (environment variable or config) — useful for profiling
- Borderline operations: measure first, then decide — data-driven approach
- Document timing for all operations even if below threshold — complete reference

### Claude's Discretion
- Specific Criterion benchmark structure and organization
- Debug assertion placement and messaging
- Exception documentation format in audit doc
- TUI review scope and depth

</decisions>

<specifics>
## Specific Ideas

- CI runners have vastly different specs than development machine — local baselines won't translate to CI regression detection
- Permanent benchmarks created here will feed directly into Phase 13 Benchmark Infrastructure
- Tests should prove GIL release works at runtime, not just verify code presence

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-gil-release-audit*
*Context gathered: 2026-02-04*
