## Why

Two performance issues in `classic-database-core/src/pool_sqlx.rs` create unnecessary overhead on every FormID lookup:

1. `PoolStatistics` fields are updated via `std::sync::RwLock::write()` on every cache hit, cache miss, and total query — meaning O(n) exclusive write-lock acquisitions per `get_entries_batch` call across all FormIDs in a batch.
2. In `get_entries_batch`, a `CacheKey` struct (allocating three `String` fields) is constructed per FormID pair then immediately discarded with `let _ = cache_key;` — the migration to use it was never completed, leaving 3×n dead allocations per batch call.

## What Changes

- **Replace** `PoolStatistics` counter fields (`total_queries`, `cache_hits`, `cache_misses`, `total_connections`, `active_connections`) with `AtomicU64` fields; remove the wrapping `Arc<RwLock<PoolStatistics>>`
- **Remove** the dead `CacheKey::new()` call (and `let _ = cache_key;` suppressor) from `get_entries_batch`'s cache-check loop
- **Retain** `CacheKey` type and its `get_stats()` public API (`PoolStatistics` as a snapshot type returned from a method) for external callers — only the internal storage changes

## Capabilities

### New Capabilities

- `db-pool-atomic-stats`: Database pool statistics use `AtomicU64` counters for lock-free concurrent updates

### Modified Capabilities

*(none — external API of `DatabasePool` is unchanged; `get_stats()` still returns a `PoolStatistics` snapshot)*

## Impact

- **Modified**: `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
- **Performance**: Eliminates O(n) write-lock acquisitions per batch; eliminates 3n String allocations per batch
- **No API change**: `DatabasePool::new()`, `get_entry()`, `get_entries_batch()` signatures unchanged
