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
    cache_keys, cache_size, cache_stats, clear_cache, get_cached, invalidate, is_cached,
    load_batch_async, load_batch_sync, load_settings_async, load_settings_sync, reset_cache_stats,
    CacheStats,
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
    use std::sync::Arc;
    use std::thread;
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
        assert!(!doc.is_badvalue());
    }

    // ========================================================================
    // Additional Tests for Improved Coverage
    // ========================================================================

    #[test]
    #[serial]
    fn test_cache_replacement_on_reload() {
        clear_cache();

        // Load first file
        let yaml1 = create_test_yaml("original: value1\n");
        let result1 = load_settings_sync("replace_key", yaml1.path());
        assert!(result1.is_ok());
        let docs1 = result1.unwrap();
        assert_eq!(docs1[0]["original"].as_str(), Some("value1"));

        // Load different content with same key - should replace
        let yaml2 = create_test_yaml("replaced: value2\n");
        let result2 = load_settings_sync("replace_key", yaml2.path());
        assert!(result2.is_ok());
        let docs2 = result2.unwrap();
        assert_eq!(docs2[0]["replaced"].as_str(), Some("value2"));

        // Cache should still have only one entry
        assert_eq!(cache_size(), 1);

        // Cached value should be the new one
        let cached = get_cached("replace_key").unwrap();
        assert_eq!(cached[0]["replaced"].as_str(), Some("value2"));
        assert!(cached[0]["original"].is_badvalue());
    }

    #[tokio::test]
    #[serial]
    async fn test_async_cache_replacement_on_reload() {
        clear_cache();

        // Load first file
        let yaml1 = create_test_yaml("original: async_value1\n");
        let result1 = load_settings_async("async_replace", yaml1.path()).await;
        assert!(result1.is_ok());

        // Load different content with same key - should replace
        let yaml2 = create_test_yaml("replaced: async_value2\n");
        let result2 = load_settings_async("async_replace", yaml2.path()).await;
        assert!(result2.is_ok());

        // Cached value should be the new one
        let cached = get_cached("async_replace").unwrap();
        assert_eq!(cached[0]["replaced"].as_str(), Some("async_value2"));
    }

    #[test]
    #[serial]
    fn test_file_not_found_error() {
        clear_cache();

        let result = load_settings_sync("missing", std::path::Path::new("/nonexistent/file.yaml"));
        assert!(result.is_err());

        let err = result.unwrap_err();
        match err {
            SettingsError::IoError { path, .. } => {
                assert!(path.to_string_lossy().contains("nonexistent"));
            }
            _ => panic!("Expected IoError, got {:?}", err),
        }
    }

    #[tokio::test]
    #[serial]
    async fn test_async_file_not_found_error() {
        clear_cache();

        let result = load_settings_async(
            "missing_async",
            std::path::Path::new("/nonexistent/async.yaml"),
        )
        .await;
        assert!(result.is_err());

        let err = result.unwrap_err();
        assert!(matches!(err, SettingsError::IoError { .. }));
    }

    #[test]
    #[serial]
    fn test_invalid_yaml_error() {
        clear_cache();

        // Create YAML with invalid syntax (tabs in indentation)
        let yaml_content = "key: value\n\tinvalid: tabs";
        let file = create_test_yaml(yaml_content);

        let result = load_settings_sync("invalid_yaml", file.path());
        assert!(result.is_err());

        let err = result.unwrap_err();
        assert!(matches!(err, SettingsError::YamlParseError { .. }));
    }

    #[test]
    #[serial]
    fn test_multi_document_yaml() {
        clear_cache();

        // YAML with multiple documents separated by ---
        let yaml_content = "doc1: value1\n---\ndoc2: value2\n";
        let file = create_test_yaml(yaml_content);

        let docs = load_settings_sync("multi_doc", file.path()).unwrap();
        assert_eq!(docs.len(), 2);
        assert_eq!(docs[0]["doc1"].as_str(), Some("value1"));
        assert_eq!(docs[1]["doc2"].as_str(), Some("value2"));
    }

    #[test]
    #[serial]
    fn test_empty_yaml_file() {
        clear_cache();

        let file = create_test_yaml("");
        let docs = load_settings_sync("empty_yaml", file.path()).unwrap();
        // Empty YAML should return empty documents list or a BadValue doc
        assert!(docs.is_empty() || docs[0].is_badvalue());
    }

    #[test]
    #[serial]
    fn test_invalidate_nonexistent_key() {
        clear_cache();

        // Invalidating a key that doesn't exist should return false
        let removed = invalidate("never_existed");
        assert!(!removed);
    }

    #[test]
    #[serial]
    fn test_get_cached_nonexistent_key() {
        clear_cache();

        let cached = get_cached("nonexistent_key");
        assert!(cached.is_none());
    }

    #[test]
    #[serial]
    fn test_concurrent_cache_reads() {
        clear_cache();

        // Pre-populate cache
        let yaml_content = "key: concurrent_value\n";
        let file = create_test_yaml(yaml_content);
        load_settings_sync("concurrent", file.path()).unwrap();

        // Spawn multiple threads to read concurrently
        let handles: Vec<_> = (0..10)
            .map(|_| {
                thread::spawn(|| {
                    let cached = get_cached("concurrent");
                    assert!(cached.is_some());
                    let docs = cached.unwrap();
                    assert_eq!(docs[0]["key"].as_str(), Some("concurrent_value"));
                })
            })
            .collect();

        for handle in handles {
            handle.join().expect("Thread panicked");
        }
    }

    #[test]
    #[serial]
    fn test_concurrent_cache_writes_different_keys() {
        clear_cache();

        // Create test files
        let files: Vec<_> = (0..5)
            .map(|i| {
                let content = format!("key{}: value{}\n", i, i);
                create_test_yaml(&content)
            })
            .collect();

        // Keep file paths accessible
        let paths: Vec<_> = files.iter().map(|f| f.path().to_path_buf()).collect();

        // Spawn threads to write to different keys concurrently
        let handles: Vec<_> = paths
            .iter()
            .enumerate()
            .map(|(i, path)| {
                let path = path.clone();
                let key = format!("concurrent_write_{}", i);
                thread::spawn(move || {
                    let result = load_settings_sync(&key, &path);
                    assert!(result.is_ok());
                })
            })
            .collect();

        for handle in handles {
            handle.join().expect("Thread panicked");
        }

        // Verify all entries exist
        assert_eq!(cache_size(), 5);
        for i in 0..5 {
            let key = format!("concurrent_write_{}", i);
            assert!(is_cached(&key));
        }
    }

    #[test]
    #[serial]
    fn test_arc_sharing_across_gets() {
        clear_cache();

        let yaml_content = "shared: data\n";
        let file = create_test_yaml(yaml_content);

        load_settings_sync("arc_test", file.path()).unwrap();

        // Get the cached value twice
        let cached1 = get_cached("arc_test").unwrap();
        let cached2 = get_cached("arc_test").unwrap();

        // Both should point to the same Arc
        assert!(Arc::ptr_eq(&cached1, &cached2));
    }

    #[tokio::test]
    #[serial]
    async fn test_async_batch_with_one_invalid_file() {
        clear_cache();

        let yaml1 = create_test_yaml("valid: file\n");
        let paths = vec![yaml1.path(), std::path::Path::new("/nonexistent.yaml")];

        // Batch loading should fail if any file fails
        let result = load_batch_async(&paths).await;
        assert!(result.is_err());
    }

    #[test]
    #[serial]
    fn test_sync_batch_with_one_invalid_file() {
        clear_cache();

        let yaml1 = create_test_yaml("valid: file\n");
        let paths = vec![yaml1.path(), std::path::Path::new("/nonexistent.yaml")];

        // Batch loading should fail if any file fails
        let result = load_batch_sync(&paths);
        assert!(result.is_err());
    }

    #[test]
    #[serial]
    fn test_complex_yaml_structures() {
        clear_cache();

        let yaml_content = r#"
root:
  nested:
    deep: value
  list:
    - item1
    - item2
    - nested_item:
        key: nested_value
  number: 42
  float: 3.14
  boolean: true
"#;
        let file = create_test_yaml(yaml_content);

        let docs = load_settings_sync("complex", file.path()).unwrap();
        assert_eq!(docs.len(), 1);

        let root = &docs[0]["root"];
        assert_eq!(root["nested"]["deep"].as_str(), Some("value"));
        assert_eq!(root["number"].as_i64(), Some(42));
        assert!(root["list"][0].as_str().is_some());
    }

    #[test]
    #[serial]
    fn test_cache_keys_ordering() {
        clear_cache();

        // Insert in specific order
        let yaml = create_test_yaml("key: value\n");
        for key in ["alpha", "beta", "gamma", "delta"] {
            load_settings_sync(key, yaml.path()).unwrap();
        }

        let keys = cache_keys();
        assert_eq!(keys.len(), 4);
        // All keys should be present (order may vary due to DashMap)
        assert!(keys.contains(&"alpha".to_string()));
        assert!(keys.contains(&"beta".to_string()));
        assert!(keys.contains(&"gamma".to_string()));
        assert!(keys.contains(&"delta".to_string()));
    }

    #[tokio::test]
    #[serial]
    async fn test_async_concurrent_loads() {
        clear_cache();

        // Create test files
        let files: Vec<_> = (0..5)
            .map(|i| {
                let content = format!("async_key{}: async_value{}\n", i, i);
                create_test_yaml(&content)
            })
            .collect();

        // Load all files concurrently using async
        let mut handles = Vec::new();
        for (i, file) in files.iter().enumerate() {
            let path = file.path().to_path_buf();
            let key = format!("async_concurrent_{}", i);
            handles.push(tokio::spawn(async move {
                load_settings_async(&key, &path).await
            }));
        }

        // Wait for all to complete
        for handle in handles {
            let result = handle.await.unwrap();
            assert!(result.is_ok());
        }

        // Verify all are cached
        assert_eq!(cache_size(), 5);
    }
}
