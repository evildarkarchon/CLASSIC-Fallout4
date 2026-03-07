## Why

Batch SQL generation currently varies heavily with batch length, reducing prepared-statement reuse and increasing query construction overhead. Stabilizing query shapes should improve repeatability and throughput for batched lookup workloads.

## What Changes

- Introduce stable batch query shape strategy (fixed size buckets or equivalent) for Rust batch lookups.
- Ensure binding and execution behavior remains correct for partial/final batches.
- Add observability for selected query bucket/shape and batch execution characteristics.
- Validate behavior parity and measure statement/cache reuse improvements.

## Capabilities

### New Capabilities
- `rust-db-stable-batch-query-shapes`: Execute Rust batch lookups using stable query shapes to improve statement reuse and reduce query-shape churn.

### Modified Capabilities
- (none)

## Impact

- Affected code:
  - `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
  - Batch lookup tests/benchmarks
- Runtime impact:
  - Improved consistency for large and repeated batch workloads
  - Potential lower CPU overhead during query construction
- No intended change to caller-facing batch lookup contract.
