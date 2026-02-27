## Why

Rust scan-time FormID value resolution currently performs per-entry database lookups in a hot loop. This creates avoidable query overhead and limits throughput on large crash logs with many FormIDs.

## What Changes

- Integrate batch database lookups into `classic-scanlog-core` FormID analysis instead of issuing one query per FormID.
- Aggregate FormID/plugin lookup pairs, perform batched resolution via `DatabasePool::get_entries_batch`, and map results back to existing report formatting.
- Preserve current user-visible behavior (same matching semantics, same report ordering/format expectations, same fallback when values are missing).
- Add focused tests for correctness parity (case-insensitive plugin handling, missing values, duplicate FormIDs, mixed plugin-prefix scenarios).

## Capabilities

### New Capabilities
- `formid-batch-lookup-integration`: Support batch FormID value resolution in the Rust scan pipeline while preserving existing report behavior.

### Modified Capabilities
- (none)

## Impact

- Affected code:
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/formid_analyzer.rs`
  - `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` (if wiring adjustments are required)
  - Potential supporting tests in `classic-scanlog-core` and integration test suites
- Performance impact:
  - Reduced query round-trips for logs with many FormIDs
  - Better utilization of existing `classic-database-core` batch query path
- API compatibility:
  - No intended public API break for existing Rust/Python/C++/Node orchestrator consumers.
