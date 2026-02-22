## Context

`DatabasePool` in `pool_sqlx.rs` tracks query statistics (hits, misses, total queries, connections) in a `PoolStatistics` struct behind `Arc<RwLock<PoolStatistics>>`. Every `get_entry` and `get_entries_batch` call acquires a write lock to update counters. In `get_entries_batch`, this happens once per FormID pair in a loop — O(n) exclusive write acquisitions with no payload, on a code path that is otherwise async and concurrent.

Additionally, `get_entries_batch` constructs a `CacheKey` struct (three String fields) per FormID pair and immediately discards it (`let _ = cache_key;`). This is dead code left from an incomplete migration. The struct pre-computes a hash but was never wired into the actual cache lookup, which still uses a `legacy_key: String`.

## Goals / Non-Goals

**Goals:**
- Replace `RwLock<PoolStatistics>` with per-field `AtomicU64` counters (lock-free)
- Remove the dead `CacheKey::new()` call from the `get_entries_batch` loop
- Preserve the `get_stats() -> PoolStatistics` public API (returning a snapshot by reading atomics)

**Non-Goals:**
- Completing the `CacheKey`-based cache migration (the `String`-based key works; that's a separate optimization)
- Changing `DatabasePool::new()`, `get_entry()`, or `get_entries_batch()` signatures
- Removing the `CacheKey` type itself (it may be used in future)

## Decisions

### 1. Use `AtomicU64` directly on `DatabasePool`, not a wrapper struct

Replace:
```rust
stats: Arc<RwLock<PoolStatistics>>,
```
With individual fields:
```rust
stat_total_queries:    Arc<AtomicU64>,
stat_cache_hits:       Arc<AtomicU64>,
stat_cache_misses:     Arc<AtomicU64>,
stat_total_connections: Arc<AtomicU64>,
stat_active_connections: Arc<AtomicU64>,
```

`get_stats()` constructs and returns a `PoolStatistics` snapshot by loading all atomics with `Relaxed` ordering (stats are diagnostic; strict ordering is unnecessary).

**Why not keep `PoolStatistics` as the storage struct?** `PoolStatistics` has non-atomic fields — wrapping it in a struct requires locking or making each field atomic individually. Individual atomics on the parent struct is simpler.

**Why `Relaxed` ordering?** These are performance counters read for monitoring. Stale reads by a few operations are acceptable; we do not use these values for coordination.

### 2. Remove `CacheKey::new()` call only — leave the type

The `CacheKey` type and its `Hash`/`PartialEq` impls are a sensible future optimization for switching the cache from `DashMap<String, ...>` to `DashMap<CacheKey, ...>`. Deleting just the dead `let cache_key = CacheKey::new(...); let _ = cache_key;` lines is the minimal safe change.

## Risks / Trade-offs

- **Stats snapshot non-atomic**: The `get_stats()` snapshot reads five atomics separately; a concurrent update between reads means the snapshot may be slightly inconsistent (e.g., `cache_hits + cache_misses != total_queries` momentarily). This is acceptable for diagnostic counters.
- **No behaviour change**: All logic paths remain identical; only the storage mechanism for counters changes.

## Migration Plan

1. Add five `Arc<AtomicU64>` fields to `DatabasePool`
2. Initialize them in `DatabasePool::new()` with `Arc::new(AtomicU64::new(0))`
3. Replace all `if let Ok(mut s) = self.stats.write() { s.X += 1; }` with `self.stat_X.fetch_add(1, Ordering::Relaxed);`
4. Implement `get_stats()` to return `PoolStatistics` from atomic loads
5. Remove `stats: Arc<RwLock<PoolStatistics>>` field and its initialization
6. Remove the three dead `CacheKey` lines from `get_entries_batch`

## Open Questions

*(none)*
