//! Domain-neutral YAML rules shared by every CLASSIC owner.
//!
//! This module is the single owner of CLASSIC's generic YAML behavior:
//!
//! - **Parsing and loading**: [`parse_yaml_content`] plus sync/async single-file,
//!   merged, and batch loaders ([`load_yaml_sync`], [`load_yaml_async`],
//!   [`load_yaml_merged_sync`], [`load_yaml_merged_async`],
//!   [`load_yaml_batch_sync`], [`load_yaml_batch_async`]).
//! - **Merging**: multi-document stream merging ([`merge_yaml_documents`]) and
//!   YAML 1.1 merge-key (`<<`) resolution ([`merge_keys`]).
//! - **Scalar validation**: the [`validators`] submodule's typed validation and
//!   coercion of string setting values.
//! - **Schema compatibility**: `schema_version` header extraction and
//!   `MAJOR.MINOR` compatibility checks ([`extract_schema_version`],
//!   [`schema_compat_check`]).
//! - **Logical-key cache**: a bounded, process-wide cache of parsed YAML
//!   documents keyed by caller-chosen logical names ([`load_settings_sync`],
//!   [`get_cached`], [`cache_stats`], ...). It holds 64 entries, never checks
//!   file freshness (a key is only refreshed when it is loaded again), counts
//!   hits and misses only on [`get_cached`], and keeps entry eviction
//!   ([`clear_cache`], [`invalidate`]) separate from counter resets
//!   ([`reset_cache_stats`]).
//!
//! CLASSIC-specific file identity (which YAML files exist and where they
//! live) is deliberately *not* here; it belongs to the domain owners that
//! consume these rules.
//!
//! # Errors
//!
//! Loading, parsing, and document merging report [`SettingsError`], whose
//! [`SettingsSource`] names either the failing path or a logical label.
//! Merge-key resolution reports [`YamlError`]. Schema-header extraction
//! reports [`YamlSchemaError`].
//!
//! # Runtime
//!
//! The async loaders run on whatever Tokio runtime polls them; batch loading
//! spawns one task per file onto that runtime. CLASSIC callers reach these
//! through the shared runtime from [`crate::get_runtime`].
//!
//! # Example
//!
//! ```rust
//! use classic_shared_core::yaml::{merge_yaml_documents, parse_yaml_content};
//!
//! let docs = parse_yaml_content("inline", "a: 1\n---\nb: 2\n").unwrap();
//! let merged = merge_yaml_documents("inline", &docs).unwrap();
//! assert_eq!(merged["a"].as_i64(), Some(1));
//! assert_eq!(merged["b"].as_i64(), Some(2));
//! ```

mod error;
mod loader;
mod logical_key_cache;
mod merge;
mod operation_error;
mod schema_version;
pub mod validators;

pub use error::{Result, SettingsError, SettingsSource};
pub use loader::{
    load_yaml_async, load_yaml_batch_async, load_yaml_batch_sync, load_yaml_merged_async,
    load_yaml_merged_sync, load_yaml_sync, parse_yaml_content,
};
pub use logical_key_cache::{
    CacheStats, cache_keys, cache_size, cache_stats, clear_cache, get_cached, invalidate,
    is_cached, load_batch_async, load_batch_sync, load_settings_async, load_settings_sync,
    reset_cache_stats,
};
pub use merge::{merge_keys, merge_yaml_documents};
pub use operation_error::YamlError;
pub use schema_version::{
    Compatibility, SCHEMA_VERSION_KEY, SchemaCompat, SchemaParseError, SchemaVersion,
    YamlSchemaError, extract_schema_version, schema_compat_check,
};

// Re-export the parsed YAML value type so callers can name results without
// taking their own yaml-rust2 dependency.
pub use yaml_rust2::Yaml;
