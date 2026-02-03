# Phase 6: Foundation & Settings - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate settings cache operations entirely to Rust (classic-settings-core) and establish golden file infrastructure for parity testing. Python becomes a thin wrapper delegating all cache operations to Rust's DashMap-based cache. Golden files capture Python output for 15-20 crash logs to validate Rust parity in later phases.

Note: Python fallbacks were removed in v1.0 cleanup milestone — Rust is the only code path.

</domain>

<decisions>
## Implementation Decisions

### Cache Failover Behavior
- Hard error on Rust cache failure — surface problems immediately during migration
- No dual-run validation mode — trust Rust once wired, rely on pre-migration tests
- Targeted cache invalidation — only invalidate specific settings that changed, not entire cache
- Error messages include developer detail — Rust error specifics, setting name, file path for debugging

### Golden File Selection
- Include common cases AND edge cases (unusual crashes, empty logs, corrupt data, huge logs)
- Target 15-20 representative crash logs for meaningful coverage
- Source logs from `sample_logs/` and/or `Crash Logs/` directories in project root
- Capture intermediate outputs (parsed segments, analysis results) AND final report — debugging at each stage

### Parity Strictness
- Character-exact matching — byte-for-byte identical output
- Mask dynamic data before comparison — replace timestamps and paths with placeholders
- Full diff on failure — complete side-by-side diff for debugging
- Parity tests in pytest with marker — skippable in fast runs, included in full CI

### Migration Visibility
- DEBUG-level logging for code paths used
- DEBUG-level performance metrics for settings cache (hit rate, load times)
- Expose cache.debug_info() method for runtime state inspection

### Claude's Discretion
- Specific placeholder format for masking timestamps/paths
- Exact pytest marker name for parity tests
- Debug log format and verbosity level

</decisions>

<specifics>
## Specific Ideas

- Python fallbacks already removed in v1.0 — no need for force-Python toggle
- Intermediate output capture enables pinpointing which processing stage diverges

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-foundation-settings*
*Context gathered: 2026-02-02*
