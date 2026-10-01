//! CLASSIC YAML settings facade.
//!
//! The generic YAML rules this crate used to own (parsing, document and
//! merge-key merging, sync/async loaders, scalar validators, schema-version
//! compatibility, and the logical-key settings cache) now live in
//! [`classic_shared_core::yaml`]. Every such item below is a `pub use` of that
//! owner, so loading through this facade or through `classic_shared_core::yaml`
//! reads and clears the same logical-key cache, with the same capacity,
//! freshness, counters, and errors.
//!
//! This crate still owns two things until their own migrations land:
//!
//! - [`YamlFile`], CLASSIC's domain-specific YAML file identity, until config
//!   takes ownership of file policy.
//! - [`YamlOperations`] and its path/mtime-aware YAML-file cache
//!   ([`yaml_cache_stats`], [`clear_global_yaml_cache`], ...), which stays
//!   distinct from the logical-key cache.
//!
//! The crate identity is scheduled for retirement once its remaining callers
//! import the accepted owners directly.
//!
//! # ONE RUNTIME RULE
//!
//! The async loaders re-exported here run on the shared global Tokio runtime
//! from `classic-shared-core`.
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

mod yaml_file;

// YAML operations (absorbed from classic-yaml-core per D-01)
mod yaml_ops;

// Generic YAML rules re-exported from their shared-core owner.
pub use classic_shared_core::yaml::validators;
pub use classic_shared_core::yaml::{
    CacheStats, Compatibility, Result, SCHEMA_VERSION_KEY, SchemaCompat, SchemaParseError,
    SchemaVersion, SettingsError, SettingsSource, Yaml, YamlSchemaError, cache_keys, cache_size,
    cache_stats, clear_cache, extract_schema_version, get_cached, invalidate, is_cached,
    load_batch_async, load_batch_sync, load_settings_async, load_settings_sync, load_yaml_async,
    load_yaml_batch_async, load_yaml_batch_sync, load_yaml_merged_async, load_yaml_merged_sync,
    load_yaml_sync, merge_keys, merge_yaml_documents, parse_yaml_content, reset_cache_stats,
    schema_compat_check,
};
pub use yaml_file::*;

// YAML operations re-exports (D-04 flat re-exports)
pub use yaml_ops::{
    YamlCacheStats, YamlError, YamlOperations, clear_global_yaml_cache, reset_yaml_cache_stats,
    yaml_cache_stats,
};

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
