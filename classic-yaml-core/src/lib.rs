//! CLASSIC YAML Core - Pure Rust YAML business logic
//!
//! This crate provides the core YAML operations for CLASSIC without any PyO3 dependencies.
//! It can be used directly by Rust applications (CLI/TUI) or through the Python bindings
//! in classic-yaml-py.
//!
//! ## Architecture
//! - Pure Rust - no PyO3, usable by CLI/TUI directly
//! - Based on yaml-rust2 (YAML 1.2 compliant)
//! - Thread-safe caching with DashMap
//! - Atomic file writes for safety

use dashmap::DashMap;
use once_cell::sync::Lazy;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::SystemTime;
use thiserror::Error;
use yaml_rust2::{Yaml, YamlEmitter, YamlLoader};

/// Global YAML cache for frequently accessed files
///
/// NOTE: This is lazily initialized on first use to avoid deadlocks during module import.
/// The cache is thread-safe and uses DashMap for concurrent access.
static YAML_CACHE: Lazy<DashMap<PathBuf, CachedYaml>> = Lazy::new(DashMap::new);

/// YAML operation errors
#[derive(Debug, Error)]
pub enum YamlError {
    #[error("Failed to parse YAML: {0}")]
    ParseError(String),

    #[error("Failed to serialize YAML: {0}")]
    SerializeError(String),

    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Empty YAML document")]
    EmptyDocument,

    #[error("Invalid value: {0}")]
    InvalidValue(String),

    #[error("Unresolved YAML alias")]
    UnresolvedAlias,

    #[error("Invalid key path: {0}")]
    InvalidKeyPath(String),

    #[error("Type conversion error: {0}")]
    TypeConversionError(String),
}

/// Format configuration matching ruamel.yaml defaults
#[derive(Debug, Clone)]
pub struct YamlFormatConfig {
    pub preserve_quotes: bool,
    pub width: usize,
    pub indent_mapping: usize,
    pub indent_sequence: usize,
    pub indent_offset: usize,
}

impl Default for YamlFormatConfig {
    fn default() -> Self {
        Self {
            preserve_quotes: true,
            width: 120,
            indent_mapping: 2,
            indent_sequence: 4,
            indent_offset: 2,
        }
    }
}

/// Cached YAML document with metadata
#[derive(Clone)]
struct CachedYaml {
    data: Arc<Yaml>,
    modified: SystemTime,
    raw_content: Option<String>,
}

/// Main YAML operations handler (Pure Rust)
pub struct YamlOperations {
    #[allow(dead_code)] // Reserved for future format preservation features
    format_config: YamlFormatConfig,
    cache_enabled: bool,
}

impl YamlOperations {
    /// Create a new YamlOperations instance
    pub fn new() -> Self {
        Self {
            format_config: YamlFormatConfig::default(),
            cache_enabled: true,
        }
    }

    /// Create with custom format configuration
    pub fn with_config(format_config: YamlFormatConfig) -> Self {
        Self {
            format_config,
            cache_enabled: true,
        }
    }

    /// Parse YAML content from a string
    pub fn parse_yaml(&self, content: &str) -> Result<Yaml, YamlError> {
        let docs =
            YamlLoader::load_from_str(content).map_err(|e| YamlError::ParseError(e.to_string()))?;

        docs.first().cloned().ok_or(YamlError::EmptyDocument)
    }

    /// Convert YAML to string
    pub fn dump_yaml(&self, yaml: &Yaml) -> Result<String, YamlError> {
        let mut out_str = String::new();
        let mut emitter = YamlEmitter::new(&mut out_str);

        emitter
            .dump(yaml)
            .map_err(|e| YamlError::SerializeError(e.to_string()))?;

        Ok(out_str)
    }

    /// Load YAML file with caching
    pub fn load_yaml_file(&self, path: &Path) -> Result<Yaml, YamlError> {
        let file_path = path.to_path_buf();

        // Check cache first
        if self.cache_enabled {
            if let Some(cached) = YAML_CACHE.get(&file_path) {
                // Check if file has been modified
                if let Ok(metadata) = std::fs::metadata(&file_path) {
                    if let Ok(modified) = metadata.modified() {
                        if modified <= cached.modified {
                            // Cache is still valid
                            return Ok((*cached.data).clone());
                        }
                    }
                }
            }
        }

        // Read and parse file
        let content = std::fs::read_to_string(&file_path)?;

        let docs = YamlLoader::load_from_str(&content)
            .map_err(|e| YamlError::ParseError(e.to_string()))?;

        let yaml = docs.first().cloned().ok_or(YamlError::EmptyDocument)?;

        // Update cache
        if self.cache_enabled {
            if let Ok(metadata) = std::fs::metadata(&file_path) {
                if let Ok(modified) = metadata.modified() {
                    YAML_CACHE.insert(
                        file_path.clone(),
                        CachedYaml {
                            data: Arc::new(yaml.clone()),
                            modified,
                            raw_content: Some(content),
                        },
                    );
                }
            }
        }

        Ok(yaml)
    }

    /// Save YAML to file with atomic write
    pub fn save_yaml_file(&self, path: &Path, yaml: &Yaml) -> Result<(), YamlError> {
        // Serialize
        let yaml_str = self.dump_yaml(yaml)?;

        let file_path = path.to_path_buf();
        let temp_path = file_path.with_extension("yaml.tmp");

        // Write to temp file first (atomic write pattern)
        std::fs::write(&temp_path, yaml_str.as_bytes())?;

        // Rename temp file to target (atomic on most filesystems)
        std::fs::rename(&temp_path, &file_path)?;

        // Invalidate cache
        if self.cache_enabled {
            YAML_CACHE.remove(&file_path);
        }

        Ok(())
    }

    /// Get a setting value by key path (dot notation)
    pub fn get_setting(&self, yaml: &Yaml, key_path: &str) -> Option<Yaml> {
        // Navigate through the key path
        let keys: Vec<&str> = key_path.split('.').collect();
        let mut current = yaml;

        for key in keys {
            match current {
                Yaml::Hash(hash) => {
                    // Try to find by string key
                    let key_yaml = Yaml::String(key.to_string());
                    current = hash.get(&key_yaml)?;
                }
                _ => return None,
            }
        }

        Some(current.clone())
    }

    /// Set a setting value by key path (dot notation)
    pub fn set_setting(&self, yaml: &Yaml, key_path: &str, value: Yaml) -> Result<Yaml, YamlError> {
        // Check for empty key path
        if key_path.trim().is_empty() {
            return Err(YamlError::InvalidKeyPath("Empty key path".to_string()));
        }

        let mut root_yaml = yaml.clone();

        // Navigate and create path if necessary
        let keys: Vec<&str> = key_path.split('.').collect();
        let last_key = keys
            .last()
            .ok_or_else(|| YamlError::InvalidKeyPath("Empty key path".to_string()))?;

        // Helper function to ensure we have a mutable hash
        fn ensure_hash(yaml: &mut Yaml) -> &mut yaml_rust2::yaml::Hash {
            if !matches!(yaml, Yaml::Hash(_)) {
                *yaml = Yaml::Hash(yaml_rust2::yaml::Hash::new());
            }
            match yaml {
                Yaml::Hash(h) => h,
                _ => unreachable!(),
            }
        }

        // Navigate to parent of last key
        let mut current = &mut root_yaml;
        for key in &keys[..keys.len() - 1] {
            let key_yaml = Yaml::String(key.to_string());
            let hash = ensure_hash(current);
            current = hash
                .entry(key_yaml)
                .or_insert(Yaml::Hash(yaml_rust2::yaml::Hash::new()));
        }

        // Set the final value
        let hash = ensure_hash(current);
        hash.insert(Yaml::String(last_key.to_string()), value);

        Ok(root_yaml)
    }

    /// Clear the YAML cache
    pub fn clear_cache(&self) {
        YAML_CACHE.clear();
    }

    /// Get cache statistics
    pub fn get_cache_stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();
        stats.insert("cached_files".to_string(), YAML_CACHE.len());

        let total_size: usize = YAML_CACHE
            .iter()
            .filter_map(|entry| entry.raw_content.as_ref().map(|s| s.len()))
            .sum();

        stats.insert("total_bytes".to_string(), total_size);
        stats
    }

    /// Enable or disable caching
    pub fn set_cache_enabled(&mut self, enabled: bool) {
        self.cache_enabled = enabled;
    }

    /// Check if caching is enabled
    pub fn is_cache_enabled(&self) -> bool {
        self.cache_enabled
    }
}

impl Default for YamlOperations {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_yaml() {
        let ops = YamlOperations::new();
        let yaml_str = r#"
            name: test
            value: 123
        "#;

        let result = ops.parse_yaml(yaml_str);
        assert!(result.is_ok());
    }

    #[test]
    fn test_dump_yaml() {
        let ops = YamlOperations::new();
        let mut hash = yaml_rust2::yaml::Hash::new();
        hash.insert(
            Yaml::String("name".to_string()),
            Yaml::String("test".to_string()),
        );
        hash.insert(Yaml::String("value".to_string()), Yaml::Integer(123));

        let yaml = Yaml::Hash(hash);
        let result = ops.dump_yaml(&yaml);
        assert!(result.is_ok());
        let yaml_str = result.unwrap();
        assert!(yaml_str.contains("name"));
        assert!(yaml_str.contains("test"));
    }

    #[test]
    fn test_get_setting() {
        let ops = YamlOperations::new();
        let yaml_str = r#"
            settings:
              debug: true
              level: 5
        "#;

        let yaml = ops.parse_yaml(yaml_str).unwrap();
        let value = ops.get_setting(&yaml, "settings.debug");
        assert!(value.is_some());
        assert_eq!(value.unwrap(), Yaml::Boolean(true));
    }

    #[test]
    fn test_set_setting() {
        let ops = YamlOperations::new();
        let yaml_str = r#"
            settings:
              debug: false
        "#;

        let yaml = ops.parse_yaml(yaml_str).unwrap();
        let new_yaml = ops
            .set_setting(&yaml, "settings.debug", Yaml::Boolean(true))
            .unwrap();
        let value = ops.get_setting(&new_yaml, "settings.debug");
        assert_eq!(value.unwrap(), Yaml::Boolean(true));
    }
}
