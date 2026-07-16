# `classic-database-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-database-core/`](../../business-logic/classic-database-core).

Crate metadata:

- Crate: `classic-database-core`
- Description: `Pure Rust database operations for CLASSIC (no PyO3)`

This crate is the Rust-side FormID database access layer for CLASSIC. It manages SQLite connection pools, cached lookup results, and multi-database query flow for consumers that need entry text for `(formid, plugin)` pairs.

It is a pure Rust business-logic crate. It does not own a UI surface, binding layer, or Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- open one or more SQLite FormID databases for read-heavy lookup workloads
- look up a single `(formid, plugin)` pair or batch many pairs efficiently
- cache lookup results with TTL and bounded-capacity eviction
- tune connection-budget, cache, and cleanup behavior for scan workloads
- attach a shared database pool to downstream crates such as [`classic-scanlog-core`](../../business-logic/classic-scanlog-core)

Do not use this crate for:

- creating or owning a Tokio runtime
- general-purpose SQL write workflows
- schema migration tooling
- binding-specific wrapper APIs
- crash-log analysis itself

Those concerns live in related crates such as [`classic-scanlog-core`](../../business-logic/classic-scanlog-core), [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge), [`classic-node`](../../node-bindings/classic-node), and [`classic-database-py`](../../python-bindings/classic-database-py).

---

## API Map

This crate does not expose modules directly. `lib.rs` re-exports the public surface from the internal `pool_sqlx` module.

## Core pool API

- `DatabasePool` - main async lookup and pool-management type
- `DatabaseError` - typed error enum for pool open/query failures
- `PoolStatistics` - observability snapshot for cache, cleanup, and connection-budget state

## Cache helpers and tuning constants

- `CacheEntry` - cached value plus timestamps
- `CacheKey` - normalized cache key for `(table, formid, plugin)`
- `DEFAULT_CACHE_TTL_SECS`, `BATCH_CACHE_TTL_SECS`, `MAX_CACHE_TTL_SECS`
- `DEFAULT_QUERY_CACHE_CAPACITY`, `MIN_QUERY_CACHE_CAPACITY`, `MAX_QUERY_CACHE_CAPACITY`
- `DEFAULT_CACHE_CLEANUP_OP_THRESHOLD`, `MIN_CACHE_CLEANUP_OP_THRESHOLD`, `MAX_CACHE_CLEANUP_OP_THRESHOLD`
- `DEFAULT_CACHE_CLEANUP_INTERVAL_SECS`, `MIN_CACHE_CLEANUP_INTERVAL_SECS`, `MAX_CACHE_CLEANUP_INTERVAL_SECS`

---

## Public API Surface

## `DatabasePool`

`DatabasePool` is the main contributor-facing integration point.

Important lifecycle methods:

- `DatabasePool::new(max_connections, cache_ttl, game_table)`
- `initialize(db_paths) -> Result<(), DatabaseError>`
- `close() -> Result<(), DatabaseError>`
- `optimize() -> Result<(), DatabaseError>`

Lookup methods:

- `get_entry(formid, plugin, table) -> Result<Option<String>, DatabaseError>`
- `get_entries_batch(formid_plugin_pairs, table, batch_size) -> Result<HashMap<String, String>, DatabaseError>`

Configuration and introspection methods:

- `set_game_table()` / `get_game_table()`
- `set_cache_ttl()` / `get_cache_ttl()`
- `set_cache_capacity()` / `get_cache_capacity()`
- `set_cache_cleanup_threshold()` / `get_cache_cleanup_threshold()`
- `set_cache_cleanup_interval()` / `get_cache_cleanup_interval()`
- `set_max_connections()` / `get_max_connections()` / `recalculate_max_connections()`
- `rebalance_connections() -> Result<(), DatabaseError>`
- `clear_cache(expired_only) -> usize`
- `cache_size() -> usize`
- `is_available() -> bool`
- `get_stats() -> Result<PoolStatistics, DatabaseError>`

Behavior worth knowing from the source:

- `new(None, ...)` computes a default global connection budget as `num_cpus * 4`, clamped to `8..=64`
- `initialize()` filters out nonexistent database paths with a warning instead of returning `NotFound`
- pools are opened read-only with SQLite pragmas tuned for read-heavy access (`synchronous=NORMAL`, `temp_store=MEMORY`, `mmap_size`, and `cache_size`)
- `initialize()` and `rebalance_connections()` rebuild active pools and clear the query cache
- `set_max_connections()` and `recalculate_max_connections()` are config-only until the next `initialize()` or `rebalance_connections()` call
- `close()` clears pools and caches, but preserves cumulative query counters for later inspection
- `DatabasePool` derives `Clone`; clones share the same underlying pools, cache, and statistics via `Arc`

## `DatabaseError`

Public error enum for pool and query operations.

Variants:

- `OpenError(String)`
- `QueryError(String)`
- `NotFound(String)`
- `IoError(std::io::Error)`
- `SqlxError(sqlx::Error)`
- `InvalidTableIdentifier(String)` - resolved table name failed SQL-identifier validation and was rejected to prevent SQL injection (see [Table identifier validation](#table-identifier-validation))

Contributor notes:

- `DatabasePool` production code mainly surfaces `OpenError` and `SqlxError`
- `QueryError` exists publicly, but in current source it is mostly constructed in test helpers rather than the main pool implementation
- `InvalidTableIdentifier` is returned by `get_entry()` and `get_entries_batch()` when the resolved table name is not a safe unquoted SQLite identifier; it is the only variant that is a deliberate injection-prevention rejection rather than an I/O or driver failure
- missing database files during `initialize()` do not currently raise `NotFound`; they are skipped

## `PoolStatistics`

`PoolStatistics` is a read-only snapshot returned by `get_stats()`.

Field groups include:

- query counters: `total_queries`, `cache_hits`, `cache_misses`
- lifecycle counters: `total_connections`, `active_connections`
- cache maintenance: `cache_evictions`, `cleanup_runs`, `cleanup_removed`
- timing metrics: cleanup and eviction total/max nanoseconds
- connection-budget observability: `configured_connection_budget`, `effective_connection_budget`, `active_pool_count`, `min_pool_allocation`, `max_pool_allocation`, `allocation_spread`
- batch-shape counters: `stable_shape_selections`, `stable_shape_padding_pairs`, and per-bucket counters for `8` through `1024`

This struct is useful when tuning scan-time profiles or verifying that cache and batch optimizations behave as expected.

## `CacheKey` and `CacheEntry`

These types are public, but most consumers do not need to construct them directly.

- `CacheEntry::new(value, ttl)` stores a cached value plus `created_at` and `expires_at`
- `CacheEntry::is_expired()` checks TTL expiration
- `CacheKey::new(game_table, formid, plugin)` normalizes plugin names to lowercase for cache matching
- `CacheKey::from_normalized_plugin(...)` avoids repeating normalization work when the caller already has a normalized plugin string
- `CacheKey::normalize_plugin(plugin)` exposes the cache's normalization rule

These helpers matter mainly for tests, wrappers, and contributors extending cache-related behavior.

---

## Connection, Pool, And Query Flow

The source-visible lifecycle is:

1. Construct `DatabasePool::new(...)` with a global connection budget, cache TTL, and default table name.
2. Optionally tune cache capacity, cleanup threshold/interval, or connection budget before initialization.
3. Call `initialize(db_paths)` with one or more SQLite files.
4. The crate removes missing paths, sorts/deduplicates the remaining set for allocation planning, and divides the global connection budget across active database files.
5. Each database file gets its own `sqlx::SqlitePool` opened in read-only mode.
6. Call `get_entry()` or `get_entries_batch()` for lookup work.
7. Optionally inspect `get_stats()`, clear cache state, rebalance connections, or run `optimize()`.
8. Call `close()` explicitly when the shared pool is no longer needed.

### Connection-budget model

`max_connections` is a global budget for the whole `DatabasePool`, not a per-database limit.

- if there are `N` active database files, the crate distributes the configured budget across those `N` pools
- the effective budget is clamped upward to at least `N`, so each active pool gets at least one connection
- allocations are deterministic for the sorted unique path set used during rebuild
- changing the configured budget does nothing to already-open pools until `rebalance_connections()` or `initialize()` runs

### Single lookup flow

`get_entry()` currently does this:

1. maybe run proactive cache cleanup
2. resolve the effective table name from `table` or the pool's current `game_table`
3. validate the resolved table name as a safe unquoted SQLite identifier, returning `InvalidTableIdentifier` otherwise
4. check the in-memory cache using a case-normalized plugin key
5. on cache miss, query each open database file with exact plugin case first
6. if exact-case queries miss everywhere, retry with `COLLATE nocase`
7. cache the first found value and return `Ok(Some(entry))`
8. if no database returns a row, return `Ok(None)`

### Batch lookup flow

`get_entries_batch()` adds more optimization on top of the same lookup semantics:

1. resolve the effective table name from `table` or the pool's current `game_table`, then validate it as a safe unquoted SQLite identifier, returning `InvalidTableIdentifier` otherwise
2. pre-check the cache for every requested pair
3. group remaining uncached pairs into caller-sized chunks, clamped to `1..=1024`
4. round each chunk up to a stable bucket shape (`8`, `16`, `32`, `64`, `128`, `256`, `512`, `1024`) by padding with duplicate pairs
5. build or reuse cached `UNION ALL` query templates for that bucket size
6. query all active database pools in parallel with `join_all`
7. run an exact-case pass first, then a `COLLATE nocase` pass only for unresolved keys
8. merge results into a `HashMap<String, String>` keyed as `"{formid}:{plugin}"`
9. cache found values and update stable-shape statistics

Contributor-relevant detail: stable-shape padding is an internal optimization for query-template reuse. Callers still see results only for the real requested pairs.

### Table identifier validation

SQLite does not support binding identifiers (table or column names) as query parameters, so the resolved game table name is interpolated directly into the SQL strings built by `get_entry()` and `get_entries_batch()`. All `(formid, plugin)` lookup values are still bound with `.bind(...)`, but the table name itself cannot be.

To keep that interpolation safe, both lookup methods validate the resolved table name with `DatabasePool::validate_table_identifier` before any SQL is constructed. A name is accepted only if it matches the unquoted SQLite identifier grammar `[A-Za-z_][A-Za-z0-9_]*` (non-empty, ASCII letters/underscore/digits only, and not starting with a digit). Anything else — including empty strings, spaces, punctuation, quotes, semicolons, or substrings like `x; DROP TABLE y--` — is rejected with `DatabaseError::InvalidTableIdentifier` rather than forwarded to sqlx.

This guard matters because the foreign-language `set_game_table` bindings (`classic-database-py`, `classic-node`) can otherwise supply an arbitrary string from outside Rust. Internally set game names such as `Fallout4`, `Skyrim`, and `FalloutNewVegas` always pass validation.

### Expected SQLite shape

The public API does not expose a schema builder, but the source and tests make the expected table shape clear.

Lookup queries assume a table with at least these columns:

- `formid TEXT`
- `plugin TEXT`
- `entry TEXT`

Tests use a composite primary key on `(formid, plugin)`, which matches the query pattern the crate is optimized around.

---

## Error Handling Model

Most APIs use `Result<_, DatabaseError>`, but the crate is intentionally fail-soft in several places.

## Hard errors

These cases can return an actual error:

- invalid SQLite connection options or pool creation failures during `initialize()` / `rebalance_connections()`
- `sqlx` row extraction failures when a query succeeds but result decoding fails
- explicit I/O errors surfaced while creating or opening database files in tests or wrappers
- an unsafe table name passed to `get_entry()` or `get_entries_batch()`, rejected up front as `InvalidTableIdentifier` (see [Table identifier validation](#table-identifier-validation))

## Fail-soft behavior

These behaviors are visible in production source today:

- `initialize()` skips missing database files instead of failing
- `get_entry()` on an uninitialized or fully closed pool returns `Ok(None)`
- per-database query errors inside `get_entry()` are logged and the search continues in other pools
- per-database batch query errors inside `get_entries_batch()` are logged and that database contributes no rows, but the overall batch call still returns `Ok(results)`
- `optimize()` logs `ANALYZE` failures per database and continues

That model is useful for scan workflows, but contributors should be careful not to assume that `Ok(...)` means every configured database was healthy.

---

## Async, Runtime, And Concurrency Notes

This crate exposes async APIs but does not create its own runtime.

- async entry points include `initialize()`, `get_entry()`, `get_entries_batch()`, `rebalance_connections()`, `close()`, and `optimize()`
- production code uses `sqlx` async pools and queries directly; it does not call `spawn_blocking()` for database work
- runtime ownership is expected to stay in higher layers, consistent with the shared-runtime rule in [`AGENTS.md`](../../AGENTS.md)

Concurrency and performance notes visible in source:

- `DatabasePool` is cloneable and designed for shared use across async tasks
- caches and pool maps use concurrent/shared primitives (`DashMap`, atomics, `Arc`, `RwLock`)
- batch queries run across database files in parallel with `futures::join_all`
- single-entry lookups do not parallelize across database files; they iterate pool-by-pool
- cache maintenance is hybrid: expired entries can be removed lazily on access, proactively by operation count plus time interval, and aggressively when capacity is exceeded

Contributor rule: if you extend this crate, keep new async work compatible with the shared Tokio runtime model used elsewhere in CLASSIC.

---

## Related Crates And Integration Points

- [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) - downstream consumer; the final scan-run engine attaches a `DatabasePool` internally for richer FormID report text
- [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - configures scan-time DB cache profiles and logs `PoolStatistics`
- [`classic-node`](../../node-bindings/classic-node) - JavaScript/TypeScript wrapper over this crate's pool API
- [`classic-database-py`](../../python-bindings/classic-database-py) - PyO3 adapter that delegates business logic to this crate
- [`classic-shared-core`](../../foundation/classic-shared-core) - shared runtime policy used by higher-level callers and benchmarks

This crate sits upstream of the optional FormID-enrichment path in [`classic-scanlog-core`](../../business-logic/classic-scanlog-core). Scanlog analysis can run without it, but richer entry descriptions depend on it.

---

## Usage Example

This example follows the real public API used by tests and downstream crates.

```rust
use classic_database_core::{DEFAULT_CACHE_TTL_SECS, DatabasePool};
use std::path::PathBuf;
use std::time::Duration;

# async fn example() -> Result<(), classic_database_core::DatabaseError> {
let pool = DatabasePool::new(
    Some(8),
    Duration::from_secs(DEFAULT_CACHE_TTL_SECS),
    "Fallout4".to_string(),
);

pool.initialize(vec![
    PathBuf::from("C:/CLASSIC/CLASSIC Data/databases/Fallout4 FormIDs Main.db"),
    PathBuf::from("C:/CLASSIC/CLASSIC Data/databases/Fallout4 FormIDs Local.db"),
])
.await?;

if let Some(entry) = pool.get_entry("0000003C", "Fallout4.esm", None).await? {
    println!("Found entry: {entry}");
}

let results = pool
    .get_entries_batch(
        vec![
            ("0000003C".to_string(), "Fallout4.esm".to_string()),
            ("02000800".to_string(), "SomeMod.esp".to_string()),
        ],
        None,
        100,
    )
    .await?;

println!("Resolved {} entries", results.len());
println!("Cache size: {}", pool.cache_size());
println!("Stats: {:?}", pool.get_stats()?);

pool.close().await?;
# Ok(())
# }
```

If you want to query a different table than the pool's default game table, pass `Some("OtherTable")` as the `table` argument to `get_entry()` or `get_entries_batch()`.

---

## Contributor Notes And Known Limits

- The public API is entirely re-export based; changing `src/lib.rs` changes the crate surface.
- The internal module name is `pool_sqlx`, but consumers should treat `lib.rs` re-exports as the supported surface.
- Table names are interpolated directly into SQL strings (SQLite cannot bind identifiers as parameters), but `get_entry()` and `get_entries_batch()` validate the resolved name as a safe unquoted SQLite identifier first and reject unsafe values with `DatabaseError::InvalidTableIdentifier`; see [Table identifier validation](#table-identifier-validation). `set_game_table()` itself does not validate, so the lookup-time guard is the enforcement point.
- Cross-database duplicate resolution is not documented as a stable priority contract. The current implementation returns the first match it encounters, and contributors should not assume a documented precedence rule between database files.
- `initialize()` silently ignores nonexistent database files, so `is_available()` is the practical check for whether any usable pools exist.
- `DatabaseError::NotFound` is public, but the normal initialization path does not currently use it for missing files.
- `optimize()` currently runs `ANALYZE`; source comments note that `VACUUM` is not attempted because pools are opened read-only.
- The crate depends on `tokio`, but runtime construction belongs in higher layers, not here.

If you extend this crate, update this document when you change:

- re-exports in `src/lib.rs`
- connection-budget allocation behavior
- cache TTL, cleanup, or eviction semantics
- single or batch lookup ordering/priority rules
- expected SQLite table shape
- integration assumptions used by [`classic-scanlog-core`](../../business-logic/classic-scanlog-core)
