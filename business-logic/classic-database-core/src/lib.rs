//! CLASSIC Database Core - Pure Rust database operations
//!
//! This crate provides the core database operations for CLASSIC without any PyO3 dependencies.
//! It can be used directly by Rust applications (CLI/TUI) or through the Python bindings
//! in classic-database-py.
//!
//! ## Features
//! - TRUE ASYNC connection pooling with sqlx
//! - WAL mode for concurrent reads
//! - TTL-based smart caching
//! - Batch query optimization
//! - FormID-specific operations
//! - Multiple database file support

mod formid_value_lookup;
mod pool_sqlx;

pub use formid_value_lookup::{
    FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupError,
    FormIdValueLookupInMemoryReply, FormIdValueLookupOutcome,
};
pub use pool_sqlx::{
    BATCH_CACHE_TTL_SECS, CacheEntry, CacheKey, DEFAULT_CACHE_CLEANUP_INTERVAL_SECS,
    DEFAULT_CACHE_CLEANUP_OP_THRESHOLD, DEFAULT_CACHE_TTL_SECS, DEFAULT_QUERY_CACHE_CAPACITY,
    DatabaseError, DatabasePool, MAX_CACHE_CLEANUP_INTERVAL_SECS, MAX_CACHE_CLEANUP_OP_THRESHOLD,
    MAX_CACHE_TTL_SECS, MAX_QUERY_CACHE_CAPACITY, MIN_CACHE_CLEANUP_INTERVAL_SECS,
    MIN_CACHE_CLEANUP_OP_THRESHOLD, MIN_QUERY_CACHE_CAPACITY, PoolStatistics,
};
