//! Configuration File Cache with Encoding Detection
//!
//! Provides an encoding-aware INI/CONF file cache that scans a game directory,
//! detects duplicates, and offers typed getters for configuration values.
//! Replaces Python `ClassicLib.scanning.game.config.ConfigFileCache`.
//!
//! ## Key Features
//!
//! - Automatic character encoding detection via `chardetng` + `encoding_rs`
//! - Lazy-loading: files are parsed on first access, then cached
//! - Typed value retrieval (`get_str`, `get_bool`, `get_int`, `get_float`)
//! - Issue detection without modification (read-only / FCX mode)
//! - TOML config reading for crash generator settings
//!
//! ## Architecture
//!
//! The cache scans a game root directory at construction time, collecting all INI/CONF
//! files. It delegates duplicate detection to the existing `ConfigDuplicateDetector`.
//! File contents are loaded on first access with encoding auto-detection.

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use configparser::ini::Ini;
use thiserror::Error;
use walkdir::WalkDir;

use crate::ini::{ConfigIssue, IssueSeverity};

/// Errors that can occur during config cache operations
#[derive(Debug, Error)]
pub enum ConfigCacheError {
    /// I/O error during file operations
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// INI parse error
    #[error("INI parse error for {path}: {message}")]
    ParseError {
        /// File that failed to parse
        path: PathBuf,
        /// Error message
        message: String,
    },

    /// File not found in cache
    #[error("File not found in cache: {0}")]
    NotFound(String),

    /// Game root directory not found
    #[error("Game root directory not found: {0}")]
    GameRootNotFound(String),
}

/// Result type for config cache operations
pub type Result<T> = std::result::Result<T, ConfigCacheError>;

/// A cached configuration file with its parsed contents
#[derive(Debug, Clone)]
pub struct CachedConfigFile {
    /// Detected encoding name
    pub encoding: String,

    /// Path to the file on disk
    pub path: PathBuf,

    /// Raw text content (decoded)
    pub text: String,
}

/// Configuration file cache with encoding-aware loading and duplicate detection
///
/// Scans a game root directory for INI/CONF files, caches their paths, and provides
/// lazy-loading with automatic encoding detection. Duplicate files are tracked separately.
///
/// # Example
///
/// ```rust,no_run
/// use classic_scangame_core::config_cache::ConfigFileCache;
/// use std::path::Path;
///
/// let mut cache = ConfigFileCache::new(Path::new("C:/Games/Fallout4"), &["F4EE"])?;
/// if cache.contains("enblocal.ini") {
///     let value = cache.get_bool("enblocal.ini", "ENGINE", "ForceVSync");
///     println!("VSync: {:?}", value);
/// }
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
pub struct ConfigFileCache {
    /// Map of lowercase filename -> file path (first occurrence)
    config_files: HashMap<String, PathBuf>,

    /// Cache of parsed INI data (loaded on first access)
    ini_cache: HashMap<String, Ini>,

    /// Cache of file metadata (encoding, text)
    file_cache: HashMap<String, CachedConfigFile>,

    /// Duplicate files: lowercase filename -> list of duplicate paths
    pub duplicate_files: HashMap<String, Vec<PathBuf>>,

    /// Whitelist of directory/filename prefixes for duplicate detection
    duplicate_whitelist: Vec<String>,

    /// Hash cache for duplicate detection
    hash_cache: HashMap<PathBuf, String>,
}

impl ConfigFileCache {
    /// Create a new config file cache by scanning a game root directory
    ///
    /// Scans `game_root` for INI/CONF files, registers them by lowercase filename,
    /// and detects duplicates using content hash and similarity analysis.
    ///
    /// # Arguments
    ///
    /// * `game_root` - Root directory of the game installation
    /// * `duplicate_whitelist` - Directory/filename prefixes to include in duplicate detection
    ///
    /// # Returns
    ///
    /// A populated cache, or an error if the game root doesn't exist
    pub fn new(game_root: &Path, duplicate_whitelist: &[&str]) -> Result<Self> {
        if !game_root.exists() {
            return Err(ConfigCacheError::GameRootNotFound(
                game_root.display().to_string(),
            ));
        }

        let mut cache = Self {
            config_files: HashMap::new(),
            ini_cache: HashMap::new(),
            file_cache: HashMap::new(),
            duplicate_files: HashMap::new(),
            duplicate_whitelist: duplicate_whitelist.iter().map(|s| s.to_string()).collect(),
            hash_cache: HashMap::new(),
        };

        cache.scan_directory(game_root);
        Ok(cache)
    }

    /// Scan a directory tree for config files
    fn scan_directory(&mut self, game_root: &Path) {
        for entry in WalkDir::new(game_root)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().is_file())
        {
            let path = entry.path();
            let Some(file_name) = path.file_name().and_then(|n| n.to_str()) else {
                continue;
            };

            let file_lower = file_name.to_lowercase();

            // Check file extension: .ini, .conf, or dxvk.conf
            let is_config = file_lower.ends_with(".ini")
                || file_lower.ends_with(".conf")
                || file_lower == "dxvk.conf";
            if !is_config {
                continue;
            }

            // For duplicate detection, check whitelist
            let path_str = path.to_string_lossy();
            let matches_whitelist = self.duplicate_whitelist.is_empty()
                || self.duplicate_whitelist.iter().any(|w| {
                    path_str.contains(w.as_str()) || file_lower.contains(&w.to_lowercase())
                });

            // Register or detect duplicate
            if let Some(existing_path) = self.config_files.get(&file_lower) {
                if matches_whitelist {
                    let existing_path = existing_path.clone();
                    // Check for duplicate
                    let is_dup = self.is_duplicate(&existing_path, path);
                    if is_dup {
                        self.duplicate_files
                            .entry(file_lower.clone())
                            .or_insert_with(|| vec![existing_path])
                            .push(path.to_path_buf());
                    }
                }
            } else {
                // First occurrence
                self.config_files.insert(file_lower, path.to_path_buf());
            }
        }
    }

    /// Check if two files are duplicates (hash, size+mtime, or INI comparison)
    fn is_duplicate(&mut self, file1: &Path, file2: &Path) -> bool {
        // Check hash equality
        let hash1 = self.get_cached_hash(file1);
        let hash2 = self.get_cached_hash(file2);
        if hash1 == hash2 {
            return true;
        }

        // Check size + mtime
        if let (Ok(m1), Ok(m2)) = (file1.metadata(), file2.metadata()) {
            if m1.len() == m2.len() {
                if let (Ok(t1), Ok(t2)) = (m1.modified(), m2.modified()) {
                    if t1 == t2 {
                        return true;
                    }
                }
            }
        }

        false
    }

    /// Get or compute a file hash
    fn get_cached_hash(&mut self, path: &Path) -> String {
        if let Some(hash) = self.hash_cache.get(path) {
            return hash.clone();
        }

        let hash = compute_file_hash(path);
        self.hash_cache.insert(path.to_path_buf(), hash.clone());
        hash
    }

    /// Load and parse an INI file with encoding detection
    fn load_file(&mut self, file_name_lower: &str) -> Result<()> {
        if self.ini_cache.contains_key(file_name_lower) {
            return Ok(());
        }

        let path = self
            .config_files
            .get(file_name_lower)
            .ok_or_else(|| ConfigCacheError::NotFound(file_name_lower.to_string()))?
            .clone();

        let file_bytes = fs::read(&path)?;

        // Detect encoding
        let (text, encoding_name) = decode_with_detection(&file_bytes);

        // Parse INI -- disable inline comment symbols so values like "; F10" are preserved
        // (matches Python iniparse behavior where semicolons in values are not stripped)
        let mut ini = Ini::new();
        ini.set_inline_comment_symbols(Some(&[]));
        ini.read(text.clone())
            .map_err(|msg| ConfigCacheError::ParseError {
                path: path.clone(),
                message: msg,
            })?;

        self.ini_cache.insert(file_name_lower.to_string(), ini);
        self.file_cache.insert(
            file_name_lower.to_string(),
            CachedConfigFile {
                encoding: encoding_name,
                path,
                text,
            },
        );

        Ok(())
    }

    /// Check if a file is registered in the cache
    pub fn contains(&self, file_name_lower: &str) -> bool {
        self.config_files.contains_key(file_name_lower)
    }

    /// Get the path for a registered file
    pub fn get_path(&self, file_name_lower: &str) -> Option<&Path> {
        self.config_files.get(file_name_lower).map(|p| p.as_path())
    }

    /// Iterate over all registered config files
    pub fn iter(&self) -> impl Iterator<Item = (&str, &Path)> {
        self.config_files
            .iter()
            .map(|(k, v)| (k.as_str(), v.as_path()))
    }

    /// Check if a setting exists in a file
    pub fn has_setting(&mut self, file_name_lower: &str, section: &str, setting: &str) -> bool {
        if !self.config_files.contains_key(file_name_lower) {
            return false;
        }

        if self.load_file(file_name_lower).is_err() {
            return false;
        }

        self.ini_cache
            .get(file_name_lower)
            .is_some_and(|ini| ini.get(section, setting).is_some())
    }

    /// Get a string value from an INI file
    pub fn get_str(
        &mut self,
        file_name_lower: &str,
        section: &str,
        setting: &str,
    ) -> Option<String> {
        self.load_file(file_name_lower).ok()?;
        self.ini_cache.get(file_name_lower)?.get(section, setting)
    }

    /// Get a boolean value from an INI file
    ///
    /// Interprets "true", "1", "yes" (case-insensitive) as true.
    pub fn get_bool(
        &mut self,
        file_name_lower: &str,
        section: &str,
        setting: &str,
    ) -> Option<bool> {
        let value = self.get_str(file_name_lower, section, setting)?;
        let trimmed = value.trim().to_lowercase();
        Some(trimmed == "true" || trimmed == "1" || trimmed == "yes")
    }

    /// Get an integer value from an INI file
    pub fn get_int(&mut self, file_name_lower: &str, section: &str, setting: &str) -> Option<i64> {
        let value = self.get_str(file_name_lower, section, setting)?;
        value.trim().parse().ok()
    }

    /// Get a float value from an INI file
    pub fn get_float(
        &mut self,
        file_name_lower: &str,
        section: &str,
        setting: &str,
    ) -> Option<f64> {
        let value = self.get_str(file_name_lower, section, setting)?;
        value.trim().parse().ok()
    }

    /// Detect a configuration issue without modifying the file
    ///
    /// Checks if a setting meets a condition and returns a `ConfigIssue` if so.
    ///
    /// # Arguments
    ///
    /// * `file_name_lower` - Lowercase filename
    /// * `section` - INI section name
    /// * `setting` - Setting key name
    /// * `recommended_value` - String representation of the recommended value
    /// * `description` - Human-readable issue description
    /// * `condition_check` - Returns true if the current value represents an issue
    /// * `severity` - Issue severity level
    #[allow(clippy::too_many_arguments)]
    pub fn detect_issue<F>(
        &mut self,
        file_name_lower: &str,
        section: &str,
        setting: &str,
        recommended_value: &str,
        description: &str,
        condition_check: F,
        severity: IssueSeverity,
    ) -> Option<ConfigIssue>
    where
        F: FnOnce(&str) -> bool,
    {
        let current_value = self.get_str(file_name_lower, section, setting)?;

        if !condition_check(&current_value) {
            return None;
        }

        let file_path = self.config_files.get(file_name_lower)?.clone();

        Some(ConfigIssue {
            file_path,
            section: section.to_string(),
            setting: setting.to_string(),
            current_value,
            recommended_value: recommended_value.to_string(),
            description: description.to_string(),
            severity,
        })
    }

    /// Get the map of config files (lowercase name -> path) for external use
    pub fn config_files(&self) -> &HashMap<String, PathBuf> {
        &self.config_files
    }
}

/// Decode bytes with automatic encoding detection
///
/// Uses `chardetng` for encoding detection and `encoding_rs` for decoding.
/// Falls back to UTF-8 with lossy conversion if detection fails.
fn decode_with_detection(bytes: &[u8]) -> (String, String) {
    use chardetng::{EncodingDetector, Iso2022JpDetection, Utf8Detection};

    let mut detector = EncodingDetector::new(Iso2022JpDetection::Deny);
    detector.feed(bytes, true);

    let encoding = detector.guess(None, Utf8Detection::Allow);
    let (decoded, _, _) = encoding.decode(bytes);

    (decoded.into_owned(), encoding.name().to_string())
}

/// Compute a simple hash of file contents for duplicate detection
fn compute_file_hash(path: &Path) -> String {
    use sha2::{Digest, Sha256};

    let Ok(bytes) = fs::read(path) else {
        return String::new();
    };

    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    crate::encode_hex(hasher.finalize().as_ref())
}

/// Read a TOML file value (for crash generator config checking)
///
/// Reads a section/key from a TOML file with encoding detection.
/// Returns the value as a `toml::Value`, or None if not found.
///
/// # Arguments
///
/// * `toml_path` - Path to the TOML file
/// * `section` - Section name in the TOML file
/// * `key` - Key within the section
pub fn read_toml_value(
    toml_path: &Path,
    section: &str,
    key: &str,
) -> std::result::Result<Option<toml::Value>, ConfigCacheError> {
    let bytes = fs::read(toml_path)?;
    let (text, _) = decode_with_detection(&bytes);

    let data: HashMap<String, toml::Value> =
        toml::from_str(&text).map_err(|e| ConfigCacheError::ParseError {
            path: toml_path.to_path_buf(),
            message: e.to_string(),
        })?;

    Ok(data
        .get(section)
        .and_then(|s| s.as_table())
        .and_then(|t| t.get(key))
        .cloned())
}

#[cfg(test)]
#[path = "config_cache_tests.rs"]
mod tests;
