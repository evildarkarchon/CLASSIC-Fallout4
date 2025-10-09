//! CLASSIC Database Core - Pure Rust database operations
//!
//! This crate provides the core database operations for CLASSIC without any PyO3 dependencies.
//! It can be used directly by Rust applications (CLI/TUI) or through the Python bindings
//! in classic-database-py.
//!
//! ## Features
//! - Connection pooling with rusqlite
//! - TTL-based smart caching
//! - Batch query optimization
//! - FormID-specific operations
//! - Multiple database file support

mod pool;

pub use pool::{DatabasePool, CacheEntry, PoolStatistics, DatabaseError};
