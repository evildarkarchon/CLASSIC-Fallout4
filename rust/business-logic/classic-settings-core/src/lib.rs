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

// Re-export public API
pub use cache::{
    cache_keys, cache_size, clear_cache, get_cached, invalidate, is_cached, load_batch_async,
    load_batch_sync, load_settings_async, load_settings_sync,
};
pub use error::{Result, SettingsError};
pub use loader::{load_yaml_async, load_yaml_batch_async, load_yaml_batch_sync, load_yaml_sync};

// Re-export yaml_rust2 types for convenience
pub use yaml_rust2::Yaml;

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn create_test_yaml(content: &str) -> NamedTempFile {
        let mut file = NamedTempFile::new().unwrap();
        file.write_all(content.as_bytes()).unwrap();
        file.flush().unwrap();
        file
    }

    #[test]
    #[serial]
    fn test_full_workflow_sync() {
        clear_cache();

        let yaml_content = "game: Fallout4\nversion: 1.0\n";
        let file = create_test_yaml(yaml_content);

        // Load
        let result = load_settings_sync("game_settings", file.path());
        assert!(result.is_ok());

        // Check cached
        assert!(is_cached("game_settings"));
        assert_eq!(cache_size(), 1);

        // Get cached
        let cached = get_cached("game_settings");
        assert!(cached.is_some());

        // Get keys
        let keys = cache_keys();
        assert_eq!(keys.len(), 1);

        // Invalidate
        assert!(invalidate("game_settings"));
        assert!(!is_cached("game_settings"));
    }

    #[tokio::test]
    #[serial]
    async fn test_full_workflow_async() {
        clear_cache();

        let yaml_content = "game: Skyrim\nversion: 2.0\n";
        let file = create_test_yaml(yaml_content);

        // Load async
        let result = load_settings_async("game_settings_async", file.path()).await;
        assert!(result.is_ok());

        // Check cached (sync operation)
        assert!(is_cached("game_settings_async"));
        assert_eq!(cache_size(), 1);

        // Clear
        clear_cache();
        assert_eq!(cache_size(), 0);
    }

    #[test]
    #[serial]
    fn test_yaml_parsing() {
        clear_cache();

        let yaml_content = "key: value\nnumber: 42\nlist:\n  - item1\n  - item2\n";
        let file = create_test_yaml(yaml_content);

        let docs = load_settings_sync("test_parse", file.path()).unwrap();
        assert_eq!(docs.len(), 1);

        let doc = &docs[0];
        assert!(doc.is_badvalue() == false);
    }
}
