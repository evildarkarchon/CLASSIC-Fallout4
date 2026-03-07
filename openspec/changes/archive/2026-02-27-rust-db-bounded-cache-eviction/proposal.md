## Why

The Rust database query cache is currently unbounded in practice, which can cause memory growth during long scans or repeated batch workloads. We need explicit cache capacity and eviction behavior to keep performance predictable.

## What Changes

- Add bounded cache policy for Rust database query caching with deterministic eviction behavior.
- Add periodic cleanup behavior for expired entries so stale keys do not accumulate.
- Add configuration and observability hooks for cache capacity, eviction counts, and cleanup activity.
- Preserve existing lookup semantics and cache-hit behavior from a caller perspective.

## Capabilities

### New Capabilities
- `rust-db-bounded-cache-eviction`: Provide bounded, observable cache lifecycle management for Rust database lookups.

### Modified Capabilities
- (none)

## Impact

- Affected code:
  - `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
  - Related tests in `classic-database-core`
- Operational impact:
  - Lower risk of unbounded memory growth
  - More predictable long-running scan behavior
- No intended public API break for existing binding consumers.
