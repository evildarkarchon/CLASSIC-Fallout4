## 1. Replace RwLock<PoolStatistics> with AtomicU64 fields

- [x] 1.1 Add `use std::sync::atomic::{AtomicU64, Ordering};` to `pool_sqlx.rs` imports
- [x] 1.2 Add five `Arc<AtomicU64>` fields to the `DatabasePool` struct: `stat_total_queries`, `stat_cache_hits`, `stat_cache_misses`, `stat_total_connections`, `stat_active_connections`
- [x] 1.3 Initialize all five atomics to `Arc::new(AtomicU64::new(0))` in `DatabasePool::new()`
- [x] 1.4 Remove the `stats: Arc<RwLock<PoolStatistics>>` field and its initialization from `DatabasePool`
- [x] 1.5 Replace every `if let Ok(mut s) = self.stats.write() { s.cache_hits += 1; ... }` block with `self.stat_cache_hits.fetch_add(1, Ordering::Relaxed);` (and equivalent for other counter fields)
- [x] 1.6 Implement (or update) `get_stats()` to return `PoolStatistics` by loading all atomics: `PoolStatistics { total_queries: self.stat_total_queries.load(Ordering::Relaxed), ... }`
- [x] 1.7 Remove all remaining references to `self.stats` and confirm no compilation errors

## 2. Remove dead CacheKey allocation

- [x] 2.1 In `get_entries_batch()`, delete the `let cache_key = CacheKey::new(&game_table, formid, plugin);` line from the per-FormID-pair loop
- [x] 2.2 Delete the corresponding `let _ = cache_key;` suppressor line
- [x] 2.3 Confirm `CacheKey` type definition itself is retained (it is not removed)

## 3. Build and test

- [x] 3.1 Run `cargo build -p classic-database-core --manifest-path ClassicLib-rs/Cargo.toml` and confirm clean compilation
- [x] 3.2 Run `cargo test -p classic-database-core --manifest-path ClassicLib-rs/Cargo.toml` and confirm all tests pass
- [x] 3.3 Run `cargo clippy -p classic-database-core --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` and resolve any new warnings
