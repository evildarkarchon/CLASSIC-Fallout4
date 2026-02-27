## 1. Integration Design and Data Flow Prep

- [x] 1.1 Identify and document the exact per-entry lookup path in `formid_analyzer.rs` that will be replaced by batch lookup integration.
- [x] 1.2 Define the mapping strategy from extracted FormID/plugin candidates to batch lookup keys while preserving report generation order.
- [x] 1.3 Define chunking behavior and default batch size usage for large candidate sets.

## 2. Batch Lookup Implementation

- [x] 2.1 Implement batched FormID value resolution via `DatabasePool::get_entries_batch` in the Rust scan pipeline.
- [x] 2.2 Implement result remapping from batch response keys back to caller-visible report entries, including normalized duplicate handling.
- [x] 2.3 Preserve existing fallback behavior for unresolved values and query failures without changing report structure.

## 3. Correctness and Parity Testing

- [x] 3.1 Add tests for case-insensitive plugin matching and mixed-case input compatibility.
- [x] 3.2 Add tests for duplicate normalized keys and first-match-wins behavior.
- [x] 3.3 Add tests for partial misses and large lookup candidate sets to confirm parity with current report behavior.

## 4. Performance Validation and Rollout Safety

- [x] 4.1 Run targeted Rust tests (`classic-scanlog-core` and affected integration tests) to verify no behavior regressions.
- [x] 4.2 Run benchmark comparison against baseline and record per-scenario deltas for FormID resolution paths.
- [x] 4.3 Document tuning notes (batch size, observed trade-offs) for follow-up optimization changes.
