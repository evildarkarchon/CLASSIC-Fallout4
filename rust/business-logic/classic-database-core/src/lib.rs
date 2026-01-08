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

mod pool_sqlx;

pub use pool_sqlx::{
    BATCH_CACHE_TTL_SECS, CacheEntry, CacheKey, DEFAULT_CACHE_TTL_SECS, DatabaseError,
    DatabasePool, MAX_CACHE_TTL_SECS, PoolStatistics,
};
