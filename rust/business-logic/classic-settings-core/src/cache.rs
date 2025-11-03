//! Thread-safe YAML settings cache with dual sync/async API.

use crate::error::Result;
use crate::loader::{load_yaml_async, load_yaml_batch_async, load_yaml_batch_sync, load_yaml_sync};
use dashmap::DashMap;
use once_cell::sync::Lazy;
use std::path::Path;
use std::sync::Arc;
use yaml_rust2::Yaml;

/// Global settings cache storage.
///
/// Uses DashMap for lock-free concurrent access to cached YAML settings.
/// Each cache entry stores the parsed YAML documents for a file.
static SETTINGS_CACHE: Lazy<DashMap<String, Arc<Vec<Yaml>>>> = Lazy::new(DashMap::new);

/// Load and cache YAML settings synchronously.
///
/// Loads a YAML file, caches it with the given key, and returns the parsed documents.
/// If the key already exists in the cache, it will be replaced.
///
/// # Arguments
///
/// * `key` - Cache key (typically the file path or a logical name)
/// * `path` - Path to the YAML file
///
/// # Returns
///
/// The parsed YAML documents.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_settings_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_settings_sync("game_config", Path::new("config.yaml"))?;
/// # Ok(())
/// # }
/// ```
pub fn load_settings_sync(key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
    let docs = load_yaml_sync(path)?;
    let arc_docs = Arc::new(docs);
    SETTINGS_CACHE.insert(key.to_string(), arc_docs.clone());
    Ok(arc_docs)
}

/// Load and cache YAML settings asynchronously.
///
/// Loads a YAML file asynchronously, caches it with the given key, and returns the parsed documents.
/// If the key already exists in the cache, it will be replaced.
///
/// # Arguments
///
/// * `key` - Cache key (typically the file path or a logical name)
/// * `path` - Path to the YAML file
///
/// # Returns
///
/// The parsed YAML documents.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_settings_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let docs = load_settings_async("game_config", Path::new("config.yaml")).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_settings_async(key: &str, path: &Path) -> Result<Arc<Vec<Yaml>>> {
    let docs = load_yaml_async(path).await?;
    let arc_docs = Arc::new(docs);
    SETTINGS_CACHE.insert(key.to_string(), arc_docs.clone());
    Ok(arc_docs)
}

/// Load multiple YAML settings in batch (synchronous).
///
/// Loads multiple YAML files and caches them. Each path becomes its own cache key.
///
/// # Arguments
///
/// * `paths` - Slice of paths to load
///
/// # Returns
///
/// Number of files successfully loaded and cached.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_batch_sync;
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let count = load_batch_sync(&paths)?;
/// # Ok(())
/// # }
/// ```
pub fn load_batch_sync(paths: &[&Path]) -> Result<usize> {
    let results = load_yaml_batch_sync(paths)?;

    for (path_str, docs) in results {
        SETTINGS_CACHE.insert(path_str, Arc::new(docs));
    }

    Ok(paths.len())
}

/// Load multiple YAML settings in batch (asynchronous).
///
/// Loads multiple YAML files concurrently and caches them. Each path becomes its own cache key.
///
/// # Arguments
///
/// * `paths` - Slice of paths to load
///
/// # Returns
///
/// Number of files successfully loaded and cached.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::load_batch_async;
/// use std::path::Path;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let paths = vec![Path::new("config1.yaml"), Path::new("config2.yaml")];
/// let count = load_batch_async(&paths).await?;
/// # Ok(())
/// # }
/// ```
pub async fn load_batch_async(paths: &[&Path]) -> Result<usize> {
    let results = load_yaml_batch_async(paths).await?;

    for (path_str, docs) in results {
        SETTINGS_CACHE.insert(path_str, Arc::new(docs));
    }

    Ok(paths.len())
}

/// Get cached settings by key.
///
/// Retrieves cached YAML documents by key. Returns None if the key is not in the cache.
///
/// # Arguments
///
/// * `key` - Cache key to look up
///
/// # Returns
///
/// The cached YAML documents, or None if not found.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{get_cached, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// let docs = get_cached("game_config");
/// assert!(docs.is_some());
/// # Ok(())
/// # }
/// ```
pub fn get_cached(key: &str) -> Option<Arc<Vec<Yaml>>> {
    SETTINGS_CACHE.get(key).map(|entry| entry.value().clone())
}

/// Check if a key exists in the cache.
///
/// # Arguments
///
/// * `key` - Cache key to check
///
/// # Returns
///
/// `true` if the key exists, `false` otherwise.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{is_cached, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// assert!(is_cached("game_config"));
/// # Ok(())
/// # }
/// ```
pub fn is_cached(key: &str) -> bool {
    SETTINGS_CACHE.contains_key(key)
}

/// Invalidate (remove) a cached entry.
///
/// Removes a key from the cache. Returns `true` if the key existed and was removed.
///
/// # Arguments
///
/// * `key` - Cache key to invalidate
///
/// # Returns
///
/// `true` if the key was removed, `false` if it didn't exist.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{invalidate, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// let removed = invalidate("game_config");
/// assert!(removed);
/// # Ok(())
/// # }
/// ```
pub fn invalidate(key: &str) -> bool {
    SETTINGS_CACHE.remove(key).is_some()
}

/// Clear all cached settings.
///
/// Removes all entries from the cache.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::clear_cache;
///
/// clear_cache();
/// ```
pub fn clear_cache() {
    SETTINGS_CACHE.clear();
}

/// Get the number of cached entries.
///
/// # Returns
///
/// The number of entries currently in the cache.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{cache_size, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("game_config", Path::new("config.yaml"))?;
/// assert_eq!(cache_size(), 1);
/// # Ok(())
/// # }
/// ```
pub fn cache_size() -> usize {
    SETTINGS_CACHE.len()
}

/// Get all cache keys.
///
/// Returns a vector of all keys currently in the cache.
///
/// # Returns
///
/// Vector of cache keys.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::{cache_keys, load_settings_sync};
/// use std::path::Path;
///
/// # fn example() -> Result<(), Box<dyn std::error::Error>> {
/// load_settings_sync("config1", Path::new("config1.yaml"))?;
/// load_settings_sync("config2", Path::new("config2.yaml"))?;
/// let keys = cache_keys();
/// assert_eq!(keys.len(), 2);
/// # Ok(())
/// # }
/// ```
pub fn cache_keys() -> Vec<String> {
    SETTINGS_CACHE
        .iter()
        .map(|entry| entry.key().clone())
        .collect()
}

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
    fn test_load_settings_sync() {
        clear_cache();

        let yaml_content = "key: value\nnumber: 42\n";
        let file = create_test_yaml(yaml_content);

        let result = load_settings_sync("test", file.path());
        assert!(result.is_ok());

        let cached = get_cached("test");
        assert!(cached.is_some());
    }

    #[tokio::test]
    #[serial]
    async fn test_load_settings_async() {
        clear_cache();

        let yaml_content = "key: value\nnumber: 42\n";
        let file = create_test_yaml(yaml_content);

        let result = load_settings_async("test_async", file.path()).await;
        assert!(result.is_ok());

        let cached = get_cached("test_async");
        assert!(cached.is_some());
    }

    #[test]
    #[serial]
    fn test_load_batch_sync() {
        clear_cache();

        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let result = load_batch_sync(&paths);

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 2);
        assert_eq!(cache_size(), 2);
    }

    #[tokio::test]
    #[serial]
    async fn test_load_batch_async() {
        clear_cache();

        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        let paths = vec![yaml1.path(), yaml2.path()];
        let result = load_batch_async(&paths).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 2);
        assert_eq!(cache_size(), 2);
    }

    #[test]
    #[serial]
    fn test_cache_operations() {
        clear_cache();

        let yaml_content = "key: value\n";
        let file = create_test_yaml(yaml_content);

        // Load and check
        load_settings_sync("test_key", file.path()).unwrap();
        assert!(is_cached("test_key"));
        assert_eq!(cache_size(), 1);

        // Get keys
        let keys = cache_keys();
        assert_eq!(keys.len(), 1);
        assert!(keys.contains(&"test_key".to_string()));

        // Invalidate
        let removed = invalidate("test_key");
        assert!(removed);
        assert!(!is_cached("test_key"));
        assert_eq!(cache_size(), 0);
    }

    #[test]
    #[serial]
    fn test_clear_cache() {
        clear_cache();

        let yaml1 = create_test_yaml("key1: value1\n");
        let yaml2 = create_test_yaml("key2: value2\n");

        load_settings_sync("key1", yaml1.path()).unwrap();
        load_settings_sync("key2", yaml2.path()).unwrap();

        assert_eq!(cache_size(), 2);

        clear_cache();
        assert_eq!(cache_size(), 0);
    }
}
