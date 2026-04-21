//! Core YAML settings cache with dual sync/async API.
//!
//! This crate provides a high-performance, thread-safe cache for YAML settings files.
//! It offers both synchronous and asynchronous APIs for maximum flexibility:
//!
//! - Sync API for backwards compatibility and simple use cases
//! - Async API for non-blocking I/O in async contexts
//! - Batch loading support for efficient multi-file operations
//! - Lock-free concurrent access using DashMap
//!
//! # Architecture
//!
//! The cache uses a three-layer design:
//! - **Loader Layer**: Handles YAML file reading (sync/async)
//! - **Cache Layer**: Manages thread-safe storage and retrieval
//! - **Error Layer**: Provides rich error types with context
//!
//! # ONE RUNTIME RULE
//!
//! This crate integrates with `classic-shared-core` to ensure all async
//! operations use the shared global Tokio runtime.
//!
//! # Performance
//!
//! - Lock-free concurrent reads/writes via DashMap
//! - Zero-copy Arc-based value sharing
//! - Async batch loading for parallel file I/O
//! - Efficient memory usage with shared YAML documents
//!
//! # Examples
//!
//! ## Synchronous API
//!
//! ```rust
//! use classic_settings_core::{load_settings_sync, get_cached};
//! use std::path::Path;
//!
//! # fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Load and cache a YAML file
//! let docs = load_settings_sync("game_config", Path::new("config.yaml"))?;
//!
//! // Retrieve from cache
//! let cached = get_cached("game_config");
//! assert!(cached.is_some());
//! # Ok(())
//! # }
//! ```
//!
//! ## Asynchronous API
//!
//! ```rust
//! use classic_settings_core::{load_settings_async, get_cached};
//! use std::path::Path;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Load and cache a YAML file asynchronously
//! let docs = load_settings_async("game_config", Path::new("config.yaml")).await?;
//!
//! // Retrieve from cache (sync operation)
//! let cached = get_cached("game_config");
//! assert!(cached.is_some());
//! # Ok(())
//! # }
//! ```
//!
//! ## Batch Loading
//!
//! ```rust
//! use classic_settings_core::load_batch_async;
//! use std::path::Path;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Load multiple files concurrently
//! let paths = vec![
//!     Path::new("config1.yaml"),
//!     Path::new("config2.yaml"),
//!     Path::new("config3.yaml"),
//! ];
//! let count = load_batch_async(&paths).await?;
//! println!("Loaded {} files", count);
//! # Ok(())
//! # }
//! ```

mod cache;
mod error;
mod loader;
mod schema_version;
pub mod validators;
mod yaml_file;

// YAML operations (absorbed from classic-yaml-core per D-01)
mod yaml_merge;
mod yaml_ops;

// Re-export public API
pub use cache::{
    CacheStats, cache_keys, cache_size, cache_stats, clear_cache, get_cached, invalidate,
    is_cached, load_batch_async, load_batch_sync, load_settings_async, load_settings_sync,
    reset_cache_stats,
};
pub use error::{Result, SettingsError, SettingsSource};
pub use loader::{
    load_yaml_async, load_yaml_batch_async, load_yaml_batch_sync, load_yaml_merged_async,
    load_yaml_merged_sync, load_yaml_sync, merge_yaml_documents, parse_yaml_content,
};
pub use schema_version::{
    Compatibility, SCHEMA_VERSION_KEY, SchemaCompat, SchemaParseError, SchemaVersion,
    YamlSchemaError, extract_schema_version, schema_compat_check,
};
pub use yaml_file::*;

// YAML operations re-exports (D-04 flat re-exports)
pub use yaml_merge::merge_keys;
pub use yaml_ops::{
    YamlCacheStats, YamlError, YamlOperations, clear_global_yaml_cache, reset_yaml_cache_stats,
    yaml_cache_stats,
};

// Re-export yaml_rust2 types for convenience
pub use yaml_rust2::Yaml;

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
