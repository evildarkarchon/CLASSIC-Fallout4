## Why

Rust database caching currently relies on frequently constructed string keys in hot lookup paths, creating avoidable allocation and normalization overhead. A cache-key refactor can reduce per-query cost while preserving behavior.

## What Changes

- Refactor Rust database cache keys from formatted string composition toward a typed normalized key path.
- Centralize key normalization (especially plugin case normalization) to avoid repeated conversions in hot loops.
- Preserve existing case-insensitive semantics and cache hit/miss behavior.
- Add focused tests for key equivalence and collision-sensitive behavior.

## Capabilities

### New Capabilities
- `rust-db-cache-key-refactor`: Provide typed, normalized cache key handling for Rust database lookups with behavior parity.

### Modified Capabilities
- (none)

## Impact

- Affected code:
  - `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
  - Related cache/stat tests
- Performance impact:
  - Lower allocation pressure in single and batch lookup hot paths
  - Improved cache key consistency
- No intended change to public lookup API shape.
