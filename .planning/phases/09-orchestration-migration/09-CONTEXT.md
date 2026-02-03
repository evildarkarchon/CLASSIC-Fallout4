# Phase 9: Orchestration Migration - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Route all crash log scanning through Rust OrchestratorCore. Single-log processing, batch parallelism with unbounded default concurrency, VR auto-detection per-log, and all analyzers (Plugin, FormID, Suspect, Mod, Record, Settings) called from Rust. Python becomes a pure caller — no business logic remains.

</domain>

<decisions>
## Implementation Decisions

### Error Handling
- Continue scanning when a log fails — skip failed logs, continue with others
- Tiered verbosity: brief error info by default, detailed (stack trace, line numbers) in verbose/debug mode
- Isolate analyzer failures: each analyzer runs independently — one failing doesn't affect others on the same log
- Write accumulated errors to a separate error log file (not inline in results, not summary section)

### Progress Reporting
- Use callback functions: Python passes a callback to Rust, Rust calls it with progress updates
- Per-log granularity: callback fires when each log completes (coarse, low overhead)
- Callback data: (current, total) count + current log filename being processed
- Support cancellation: Rust checks a cancellation flag between logs to allow mid-batch abort

### Batch Result Ordering
- Preserve input order: results returned in same order as input (may require buffering)
- Placeholder entries for failed logs: keeps position in results, shows error info
- Configurable concurrency limit: default unbounded, but allow setting max concurrency
- Trust Tokio for resource management: no explicit backpressure mechanism needed

### Fallback Behavior
- RuntimeError if Rust unavailable: consistent with Phase 7-8 patterns, no Python fallback
- Remove Python OrchestratorCore entirely: callers import Rust directly (not thin wrapper, not deprecate-first)
- Technical error message: "Rust orchestrator module not available" (developer-focused)
- Fail on use: no pre-check health function, just fail when actually called

### Claude's Discretion
- Exact callback signature and data structure
- Cancellation token implementation (CancellationToken vs AtomicBool)
- Buffering strategy for preserving input order
- Error log file naming and location

</decisions>

<specifics>
## Specific Ideas

- Error handling follows the "continue scanning" pattern — batch operations should be resilient to individual failures
- Progress callbacks should be lightweight (per-log, not per-analyzer) to minimize overhead
- Cancellation support is important for responsive UI during long batch operations

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-orchestration-migration*
*Context gathered: 2026-02-03*
