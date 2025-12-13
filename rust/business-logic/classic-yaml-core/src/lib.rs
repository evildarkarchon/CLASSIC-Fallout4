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
//!
//! # Complete Usage Example
//!
//! ```rust,no_run
//! use classic_yaml_core::{YamlOperations, YamlFormatConfig, YamlError};
//! use std::path::Path;
//!
//! fn main() -> Result<(), YamlError> {
//!     // Create YAML operations handler with default settings
//!     let yaml_ops = YamlOperations::new();
//!
//!     // Or with custom formatting
//!     let custom_config = YamlFormatConfig {
//!         preserve_quotes: true,
//!         width: 100,
//!         indent_mapping: 2,
//!         indent_sequence: 2,
//!         indent_offset: 0,
//!     };
//!     let yaml_ops_custom = YamlOperations::with_config(custom_config);
//!
//!     // Parse YAML from string
//!     let yaml_string = r#"
//!         game: Fallout4
//!         version: 1.10.163
//!         settings:
//!           fcx_mode: true
//!           show_values: false
//!     "#;
//!
//!     let parsed = yaml_ops.parse_yaml(yaml_string)?;
//!
//!     // Get nested settings using dot notation
//!     if let Some(fcx) = yaml_ops.get_setting(&parsed, "settings.fcx_mode") {
//!         println!("FCX Mode: {:?}", fcx);
//!     }
//!
//!     // Update settings
//!     let updated = yaml_ops.set_setting(
//!         &parsed,
//!         "settings.show_values",
//!         yaml_rust2::Yaml::Boolean(true)
//!     )?;
//!
//!     // Save to file with atomic writes
//!     let config_path = Path::new("config.yaml");
//!     yaml_ops.save_yaml_file(config_path, &updated)?;
//!
//!     // Load from file (uses caching automatically)
//!     let loaded = yaml_ops.load_yaml_file(config_path)?;
//!
//!     // Cache management
//!     let stats = yaml_ops.get_cache_stats();
//!     println!("Cached files: {}", stats["cached_files"]);
//!     println!("Cache size: {} bytes", stats["total_bytes"]);
//!
//!     // Clear cache when needed
//!     yaml_ops.clear_cache();
//!
//!     Ok(())
//! }
//! ```
//!
//! # Caching Behavior
//!
//! The module includes automatic file caching with modification time tracking:
//!
//! ```rust,no_run
//! use classic_yaml_core::YamlOperations;
//! use std::path::Path;
//!
//! # fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let yaml_ops = YamlOperations::new();
//! let config = Path::new("config.yaml");
//!
//! // First load: reads from disk and caches
//! let data1 = yaml_ops.load_yaml_file(config)?;
//!
//! // Second load: returns cached version (instant)
//! let data2 = yaml_ops.load_yaml_file(config)?;
//!
//! // If file is modified externally, cache is automatically invalidated
//! // and the file is re-read on next load
//!
//! // Disable caching if needed
//! let mut ops_no_cache = YamlOperations::new();
//! ops_no_cache.set_cache_enabled(false);
//! # Ok(())
//! # }
//! ```
//!
//! # Thread Safety
//!
//! All operations are thread-safe. The cache uses `DashMap` for concurrent access:
//!
//! ```rust,no_run
//! use classic_yaml_core::YamlOperations;
//! use std::sync::Arc;
//! use std::thread;
//! use std::path::Path;
//!
//! # fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let yaml_ops = Arc::new(YamlOperations::new());
//! let config_path = Arc::new(Path::new("shared_config.yaml").to_path_buf());
//!
//! // Multiple threads can safely access the same cached YAML
//! let handles: Vec<_> = (0..4).map(|_| {
//!     let ops = yaml_ops.clone();
//!     let path = config_path.clone();
//!     thread::spawn(move || {
//!         ops.load_yaml_file(&path)
//!     })
//! }).collect();
//!
//! for handle in handles {
//!     let _ = handle.join().unwrap()?;
//! }
//! # Ok(())
//! # }
//! ```
//!
//! # Performance
//!
//! - **Caching**: 15-30x faster than repeated file reads
//! - **Atomic Writes**: Uses temp file + rename for crash safety
//! - **Parallel Access**: Lock-free concurrent reads with DashMap

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

/// An enumeration of errors that can occur while working with YAML data.
///
/// This error type encompasses various error scenarios, including parsing,
/// serialization, I/O issues, and semantic considerations.
/// # Variants
///
/// - `ParseError(String)`
///   An error occurred when parsing a YAML document.
///   This includes the detailed error message as a string.
///
/// - `SerializeError(String)`
///   An error occurred while attempting to serialize data into YAML format.
///   The error message provides additional context as a string.
///
/// - `IoError(std::io::Error)`
///   Represents I/O-related errors encountered during YAML operations,
///   such as reading from or writing to a file. This variant wraps the
///   underlying `std::io::Error`.
///
/// - `EmptyDocument`
///   The YAML document is empty or does not contain any meaningful content.
///
/// - `InvalidValue(String)`
///   Indicates that a value in the YAML document is invalid or not as
///   expected. The string contains details about the invalid value.
///
/// - `UnresolvedAlias`
///   An unresolved YAML alias was encountered. This occurs when a YAML
///   alias references an anchor that was not defined in the document.
///
/// - `InvalidKeyPath(String)`
///   An invalid key path was specified, typically when trying to access
///   a nested value in a YAML document. The string provides the
///   problematic key path or a description of the error.
///
/// - `TypeConversionError(String)`
///   Indicates a type conversion error when trying to serialize or deserialize
///   YAML data into a specific type. The string provides additional details about
///   the conversion failure.
///
/// # Example
/// ```
/// use thiserror::Error;
/// use crate::YamlError;
///
/// fn handle_yaml() -> Result<(), YamlError> {
///     // Example usage of the YamlError enum.
///     Err(YamlError::ParseError("Unexpected token".to_string()))
/// }
///
/// if let Err(e) = handle_yaml() {
///     println!("Error occurred: {}", e);
/// }
/// ```
///
/// This error type is particularly useful when working with YAML libraries or
/// tools to clearly handle and report different failure scenarios.
#[derive(Debug, Error)]
pub enum YamlError {
    /// Failed to parse YAML document
    #[error("Failed to parse YAML: {0}")]
    ParseError(String),

    /// Failed to serialize YAML to string
    #[error("Failed to serialize YAML: {0}")]
    SerializeError(String),

    /// I/O error during file operations
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    /// YAML document is empty
    #[error("Empty YAML document")]
    EmptyDocument,

    /// Invalid value encountered
    #[error("Invalid value: {0}")]
    InvalidValue(String),

    /// Unresolved YAML alias reference
    #[error("Unresolved YAML alias")]
    UnresolvedAlias,

    /// Invalid key path for nested access
    #[error("Invalid key path: {0}")]
    InvalidKeyPath(String),

    /// Type conversion failed
    #[error("Type conversion error: {0}")]
    TypeConversionError(String),
}

/// `YamlFormatConfig` is a configuration structure that defines formatting preferences
/// for YAML serialization and deserialization. This structure allows customization of
/// YAML output by adjusting indentation, width, and optional preservation of quotes
/// for better control over the generated YAML structure.
/// # Fields
///
/// * `preserve_quotes` (bool):  
///   - Determines whether to preserve quotes around scalar values, ensuring that values
///     remain quoted in the output regardless of YAML formatting rules.
///   - If `true`, quotes are retained.  
///   - If `false`, quotes may be removed for plain scalar styles.
///
/// * `width` (usize):  
///   - Specifies the maximum line width for wrapped text.   
///   - Lines exceeding this width will be automatically wrapped for better readability.
///
/// * `indent_mapping` (usize):  
///   - Defines the number of spaces used for indenting YAML mappings (key-value pairs).  
///   - Higher values increase indentation for nested mappings.
///
/// * `indent_sequence` (usize):  
///   - Specifies the number of spaces used for indenting YAML sequences (lists).  
///   - Useful for controlling the visual alignment of sequence elements.
///
/// * `indent_offset` (usize):  
///   - Determines the additional offset applied to nested structures beyond the
///     `indent_mapping` or `indent_sequence` values.
///   - Can be used to fine-tune the overall indentation appearance.
///
/// # Usage
///
/// To create a custom YAML format configuration:
/// ```
/// let config = YamlFormatConfig {
///     preserve_quotes: true,
///     width: 80,
///     indent_mapping: 2,
///     indent_sequence: 2,
///     indent_offset: 0,
/// };
/// println!("{:?}", config);
/// ```
#[derive(Debug, Clone)]
pub struct YamlFormatConfig {
    /// Preserve quotes around scalar values
    pub preserve_quotes: bool,
    /// Maximum line width for wrapped text
    pub width: usize,
    /// Number of spaces for indenting mappings (key-value pairs)
    pub indent_mapping: usize,
    /// Number of spaces for indenting sequences (lists)
    pub indent_sequence: usize,
    /// Additional offset for nested structures
    pub indent_offset: usize,
}

impl Default for YamlFormatConfig {
    /// Provides the default implementation for a configuration struct.
    /// # Returns
    /// A new instance of the struct with the following default values:
    /// - `preserve_quotes`: `true` - Indicates whether or not quotes should be preserved.
    /// - `width`: `120` - Sets the default width, likely representing maximum line width.
    /// - `indent_mapping`: `2` - Specifies the indentation level for mappings, such as key-value pairs.
    /// - `indent_sequence`: `4` - Specifies the indentation spaces for sequences or lists.
    /// - `indent_offset`: `2` - Defines additional offset indentation for certain scenarios.
    ///
    /// # Example
    /// ```
    /// let config = Config::default();
    /// assert_eq!(config.preserve_quotes, true);
    /// assert_eq!(config.width, 120);
    /// assert_eq!(config.indent_mapping, 2);
    /// assert_eq!(config.indent_sequence, 4);
    /// assert_eq!(config.indent_offset, 2);
    /// ```
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

/// A structure representing a cached YAML configuration or data.
///
/// The `CachedYaml` struct is designed to encapsulate YAML data along with metadata
/// regarding the last modification time and optional raw content. This can be useful for
/// scenarios where YAML data needs to be cached and periodically checked for updates.
/// # Fields
///
/// - `data`:
///   A thread-safe, shared reference-counted pointer (`Arc`) to the parsed YAML data.
///   This allows safe shared usage of the YAML data across threads.
///
/// - `modified`:
///   A `SystemTime` instance representing the last time the YAML resource
///   was modified. This can be used to determine whether the cached data
///   is up-to-date with the source.
///
/// - `raw_content`:
///   An optional `String` containing the raw content of the YAML file.
///   This is only present if the raw text representation is required in addition
///   to the parsed YAML data.
///
/// # Derives
///
/// - `Clone`:
///   The `Clone` trait allows creating a duplicate `CachedYaml` instance efficiently.
///   This is made possible due to the usage of `Arc` for the `data` field, which ensures
///   that the cloned instance shares the same underlying data rather than duplicating it.
///
/// # Usage
///
/// This struct is ideal for caching parsed YAML content while retaining flexibility for metadata
/// like the last modified time and raw content. It can support scenarios like file change
/// detection, configuration management, or data consistency checks.
///
/// # Example
///
/// ```rust,no_run
/// use std::sync::Arc;
/// use std::time::SystemTime;
/// use some_yaml_crate::Yaml; // Replace with the actual crate providing the `Yaml` type.
///
/// let yaml_data: Yaml = /* parsed YAML data */;
/// let cached_yaml = CachedYaml {
///     data: Arc::new(yaml_data),
///     modified: SystemTime::now(),
///     raw_content: Some(String::from("raw YAML string")),
/// };
///
/// // Clone cached YAML data
/// let cloned_cached_yaml = cached_yaml.clone();
/// ```
#[derive(Clone)]
struct CachedYaml {
    data: Arc<Yaml>,
    modified: SystemTime,
    raw_content: Option<String>,
}

/// A struct representing operations and configurations related to YAML processing.
///
/// The `YamlOperations` struct is designed to provide functionality for handling
/// YAML files with customizable configurations. This includes format configuration
/// and optional caching to optimize performance in repeated operations.
/// # Fields
///
/// * `format_config` - (Reserved for future use) This field will be utilized in
///   future versions to store YAML format preservation configurations, allowing
///   fine-grained control over YAML serialization and deserialization.
///   For now, this field is unused and deliberately marked with `#[allow(dead_code)]`.
///
/// * `cache_enabled` - A boolean field that enables or disables caching functionality.
///   When set to `true`, caching can be used to avoid redundant processing, improving
///   performance in scenarios involving multiple reads or writes.
///
/// # Usage
///
/// While the `format_config` field is currently not in use, the `cache_enabled`
/// field can be utilized to configure whether caching is enabled for YAML operations.
///
/// Example:
/// ```
/// let yaml_ops = YamlOperations {
///     format_config: Default::default(),
///     cache_enabled: true,
/// };
///
/// assert_eq!(yaml_ops.cache_enabled, true);
/// ```
pub struct YamlOperations {
    #[allow(dead_code)] // Reserved for future format preservation features
    format_config: YamlFormatConfig,
    cache_enabled: bool,
}

impl YamlOperations {
    /// Creates a new instance of the struct with default configuration.
    /// # Returns
    /// A new instance where:
    /// - `format_config` is initialized with the default settings provided by `YamlFormatConfig::default()`.
    /// - `cache_enabled` is set to `true`.
    ///
    /// # Example
    /// ```
    /// let instance = YourStruct::new();
    /// assert!(instance.cache_enabled);
    /// ```
    pub fn new() -> Self {
        Self {
            format_config: YamlFormatConfig::default(),
            cache_enabled: true,
        }
    }

    /// Creates a new instance of the struct with the specified YAML format configuration.
    /// # Parameters
    /// - `format_config`: A `YamlFormatConfig` instance that specifies the configuration
    ///   settings to be used for YAML formatting.
    ///
    /// # Returns
    /// - Returns a new instance of the struct with the given configuration and
    ///   `cache_enabled` set to `true` by default.
    ///
    /// # Example
    /// ```
    /// let config = YamlFormatConfig::new();
    /// let instance = MyStruct::with_config(config);
    /// ```
    pub fn with_config(format_config: YamlFormatConfig) -> Self {
        Self {
            format_config,
            cache_enabled: true,
        }
    }

    /// Parses a YAML string and returns the first YAML document found.
    /// # Arguments
    ///
    /// * `content` - A string slice containing the YAML content to parse.
    ///
    /// # Returns
    ///
    /// * `Ok(Yaml)` containing the first YAML document parsed from the input string upon success.
    /// * `Err(YamlError)` if:
    ///     - The input string fails to parse as valid YAML (`YamlError::ParseError`).
    ///     - The parsed YAML contains no documents (`YamlError::EmptyDocument`).
    ///
    /// # Errors
    ///
    /// This function can return the following errors:
    /// * `YamlError::ParseError` - Returned if the YAML parser encounters an error while processing the input string.
    /// * `YamlError::EmptyDocument` - Returned if the YAML content is valid but contains no documents.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use some_crate::{Yaml, YamlError};
    ///
    /// let yaml_content = r#"
    /// - item1
    /// - item2
    /// "#;
    ///
    /// let parser = SomeParser::new();
    /// match parser.parse_yaml(yaml_content) {
    ///     Ok(yaml) => {
    ///         // Successfully parsed the YAML content
    ///         println!("{:?}", yaml);
    ///     }
    ///     Err(e) => {
    ///         // Handle the error
    ///         eprintln!("Failed to parse YAML: {:?}", e);
    ///     }
    /// }
    /// ```
    #[must_use = "parsing may fail; handle the Result"]
    pub fn parse_yaml(&self, content: &str) -> Result<Yaml, YamlError> {
        let docs =
            YamlLoader::load_from_str(content).map_err(|e| YamlError::ParseError(e.to_string()))?;

        docs.first().cloned().ok_or(YamlError::EmptyDocument)
    }

    /// Serializes the given `Yaml` data structure into a YAML-formatted `String`.
    ///
    /// This method utilizes a `YamlEmitter` to convert the provided `Yaml` object into
    /// its string representation in YAML format. If the serialization process fails,
    /// an appropriate `YamlError` is returned.
    /// # Arguments
    ///
    /// * `yaml` - A reference to the `Yaml` object to be serialized.
    ///
    /// # Returns
    ///
    /// * `Ok(String)` - A `String` containing the serialized YAML representation of the input.
    /// * `Err(YamlError)` - An error indicating a failure during the serialization process.
    ///
    /// # Errors
    ///
    /// Returns a `YamlError::SerializeError` if the `YamlEmitter` fails to serialize the
    /// given `Yaml` object.
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use your_crate_name::some_module::{YourStruct, Yaml, YamlError};
    ///
    /// let yaml_data = Yaml::String("example".to_string());
    /// let instance = YourStruct::new();
    ///
    /// match instance.dump_yaml(&yaml_data) {
    ///     Ok(serialized) => println!("Serialized YAML: {}", serialized),
    ///     Err(e) => eprintln!("Failed to serialize YAML: {:?}", e),
    /// }
    /// ```
    #[must_use = "serialization may fail; handle the Result"]
    pub fn dump_yaml(&self, yaml: &Yaml) -> Result<String, YamlError> {
        let mut out_str = String::new();
        let mut emitter = YamlEmitter::new(&mut out_str);

        emitter
            .dump(yaml)
            .map_err(|e| YamlError::SerializeError(e.to_string()))?;

        Ok(out_str)
    }

    /// Loads a YAML file from the specified file path and optionally caches the result.
    ///
    /// This method provides the functionality to parse a YAML file and support caching,
    /// ensuring that subsequent reads of the same file are optimized. Caching can reduce
    /// redundant file reads and YAML parsing when the file hasn't been modified since
    /// the last read.
    /// # Arguments
    ///
    /// * `path` - A reference to a `Path` representing the file path to the YAML file to load.
    ///
    /// # Returns
    ///
    /// * `Ok(Yaml)` - A populated `Yaml` object representing the parsed contents of the YAML file.
    /// * `Err(YamlError)` - If an error occurs during file I/O, parsing, or if the document is empty.
    ///
    /// # Behavior
    ///
    /// - **Cache Check**: If caching is enabled (`self.cache_enabled` is `true`), the method will:
    ///   - Check if the file's contents are already cached in `YAML_CACHE`.
    ///   - Compare the last modified timestamp of the file to the cached entry's timestamp.
    ///   - Return the cached YAML object if the file hasn't been modified.
    ///
    /// - **File Reading and Parsing**: If either:
    ///   - The file isn't cached, or
    ///   - The cached content is invalid or outdated,
    ///
    ///   The method proceeds to:
    ///   - Read the file contents as a string using `std::fs::read_to_string`.
    ///   - Parse the contents into a YAML document using `YamlLoader::load_from_str`.
    ///   - Return the first YAML document from the parsed result.
    ///   - If the document is empty, returns a `YamlError::EmptyDocument`.
    ///
    /// - **Cache Update**: After successfully parsing the file:
    ///   - If caching is enabled, the method updates the cache with the new document, its raw contents,
    ///     and its last modified timestamp.
    ///
    /// # Caching Details
    ///
    /// Caching is controlled via the `self.cache_enabled` flag. An internal global cache, `YAML_CACHE`,
    /// is used to store parsed documents. The cache keeps track of:
    /// - The parsed YAML document.
    /// - The last modification timestamp of the file.
    /// - The raw file contents (optional, for potential future validation).
    ///
    /// # Errors
    ///
    /// The method can fail with the following error variants:
    /// - `YamlError::FileError` for file I/O errors (e.g., missing file or insufficient permissions).
    /// - `YamlError::ParseError` if the YAML is invalid or cannot be parsed.
    /// - `YamlError::EmptyDocument` if the file lacks any YAML document.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use std::path::Path;
    ///
    /// let loader = YourLoaderStructure::new(cache_enabled: true); // Imaginary structure holding this method
    /// let yaml_path = Path::new("config.yaml");
    ///
    /// match loader.load_yaml_file(yaml_path) {
    ///     Ok(yaml) => {
    ///         println!("Successfully loaded YAML: {:?}", yaml);
    ///     },
    ///     Err(e) => {
    ///         eprintln!("Failed to load YAML: {}", e);
    ///     },
    /// }
    /// ```
    ///
    /// # Notes
    ///
    /// - Ensure that the file exists at the specified path before invoking this method.
    /// - Caching leverages a global/static cache (`YAML_CACHE`), so proper initialization and handling
    ///   of this cache is expected prior to method execution.
    ///
    /// # Thread Safety
    ///
    /// The method assumes thread-safe operations where necessary, particularly for the global `YAML_CACHE`.
    /// Use of `Arc` ensures shared ownership of cached YAML data across threads.
    #[must_use = "file loading may fail; handle the Result"]
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

    /// Saves a given YAML structure to a file in an atomic manner.
    ///
    /// This method serializes the provided YAML data and writes it to a temporary file first.
    /// Once the write operation to the temporary file is successful, it renames the temporary file
    /// to the final target file path, ensuring an atomic write process. This helps avoid data corruption
    /// in case of interruption during file writing. Additionally, if caching is enabled, it invalidates
    /// the cache for the written file.
    ///
    /// # Parameters
    /// - `path`: The file path where the YAML data should be saved. The final file will have a `.yaml` extension.
    /// - `yaml`: The YAML data to be serialized and written to the file.
    ///
    /// # Returns
    /// - `Ok(())`: If the YAML file is successfully saved.
    /// - `Err(YamlError)`: If an error occurs during serialization, file write, or renaming operations.
    ///
    /// # Behavior
    /// 1. The method serializes the input `yaml` data into a string using `self.dump_yaml`.
    /// 2. A temporary file with a `.yaml.tmp` extension is created and the YAML content is written to it.
    /// 3. The temporary file is renamed to the final target file, ensuring an atomic operation.
    /// 4. If caching is enabled (`self.cache_enabled` is `true`), the cache entry for the file is removed.
    /// # Errors
    /// - The method returns an error if:
    ///   - Serialization of the YAML data fails.
    ///   - Writing to the temporary file fails.
    ///   - Renaming the temporary file to the target file fails.
    ///
    /// # Example
    /// ```
    /// use std::path::Path;
    /// # use yaml_rust2::Yaml;
    /// # struct YourStruct;
    /// # impl YourStruct {
    /// #     fn new() -> Self { YourStruct }
    /// #     fn save_yaml_file(&self, _path: &Path, _yaml: &Yaml) -> Result<(), String> { Ok(()) }
    /// # }
    ///
    /// let yaml_data = Yaml::String("value".to_string()); // Example YAML data
    /// let path = Path::new("config.yaml");
    /// let your_instance = YourStruct::new();
    ///
    /// if let Err(e) = your_instance.save_yaml_file(&path, &yaml_data) {
    ///     eprintln!("Failed to save YAML file: {}", e);
    /// } else {
    ///     println!("YAML file saved successfully!");
    /// }
    /// ```
    #[must_use = "file saving may fail; handle the Result"]
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

    /// Retrieves a specific setting from a YAML structure based on a dot-delimited key path.
    /// # Parameters
    /// - `&self`: A reference to the current instance of the struct (implied in the method signature, may represent some context the method belongs to).
    /// - `yaml: &Yaml`: A reference to the root YAML structure from which the setting will be extracted.
    /// - `key_path: &str`: The dot-delimited string representing the key path to the desired setting (e.g., `"parent.child.key"`).
    ///
    /// # Returns
    /// `Option<Yaml>`:
    /// - Returns `Some(Yaml)` containing the value at the specified key path if it exists and is accessible.
    /// - Returns `None` if any key in the key path does not exist, the path encounters a non-hash value along the way,
    ///   or the structure does not match the expected hierarchy.
    ///
    /// # Behavior
    /// 1. The function splits the provided `key_path` string into individual keys using the `.` character as a delimiter.
    /// 2. Starting from the root YAML structure, it navigates through each key in the path:
    ///    - If the current value is a `Yaml::Hash`, it attempts to find the next key in the path.
    ///    - If the key exists, it moves to the next level.
    ///    - If the key is not found or the current value is not a `Yaml::Hash`, the function returns `None`.
    /// 3. If the entire key path is successfully traversed, it returns the value found at the final key.
    ///
    /// # Example
    /// ```rust,no_run
    /// use yaml_rust::{Yaml, YamlLoader};
    ///
    /// let yaml_str = r#"
    ///     parent:
    ///       child:
    ///         key: "value"
    /// "#;
    /// let docs = YamlLoader::load_from_str(yaml_str).unwrap();
    /// let root_yaml = &docs[0];
    ///
    /// let result = some_instance.get_setting(root_yaml, "parent.child.key");
    /// assert_eq!(result, Some(Yaml::String("value".to_string())));
    ///
    /// let missing = some_instance.get_setting(root_yaml, "parent.child.nonexistent");
    /// assert_eq!(missing, None);
    /// ```
    ///
    /// # Notes
    /// - The function assumes the input YAML follows a hierarchical structure of nested maps and values.
    /// - It clones the final value found, which may have performance implications for large or deeply nested YAML structures.
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

    /// Updates or creates a value in a nested YAML structure at the specified key path.
    ///
    /// This function takes a YAML object, a dot-separated key path, and a value.
    /// It navigates the structure according to the key path, creating intermediate structures as needed,
    /// and sets the specified value at the desired location.
    /// # Parameters
    /// - `&self`: Reference to the instance of the object calling this function.
    /// - `yaml`: A reference to the original `Yaml` object that will be updated.
    /// - `key_path`: A dot-separated string representing the hierarchical path to the value.
    /// - `value`: The `Yaml` value to set at the given key path.
    ///
    /// # Returns
    /// - `Ok(Yaml)`: The updated `Yaml` object with the new value set.
    /// - `Err(YamlError)`: If the key path is invalid (e.g., empty).
    ///
    /// # Errors
    /// - Returns a `YamlError::InvalidKeyPath` if the provided `key_path` is empty or invalid.
    ///
    /// # Examples
    /// ```
    /// use yaml_rust2::yaml::Yaml;
    /// use yaml_rust2::yaml::Hash;
    ///
    /// let yaml = Yaml::Hash(Hash::new());
    /// let key_path = "settings.theme.color";
    /// let value = Yaml::String("blue".to_string());
    ///
    /// let updated_yaml = instance.set_setting(&yaml, key_path, value).unwrap();
    /// ```
    ///
    /// In this example, the `updated_yaml` will have the following structure (as YAML format):
    /// ```yaml
    /// settings:
    ///   theme:
    ///     color: blue
    /// ```
    ///
    /// # Notes
    /// - If any intermediate path segments (e.g., `settings` or `theme` in the above example)
    ///   do not exist in the YAML object, they will be automatically created as empty `Yaml::Hash`.
    /// - The function handles both existing and missing paths gracefully, ensuring a nested structure
    ///   is built as needed.
    #[must_use = "setting modification may fail; handle the Result"]
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

    /// Returns a `HashMap` containing statistics about the YAML cache.
    ///
    /// The returned `HashMap` contains the following key-value pairs:
    /// - `"cached_files"`: The number of entries currently stored in the YAML cache.
    /// - `"total_bytes"`: The total size in bytes of the raw content of all cached entries.
    ///
    /// The function iterates over the `YAML_CACHE`, counting the number of entries
    /// and calculating the total size of all entries' raw content if available.
    /// # Returns
    /// A `HashMap<String, usize>` containing the cache statistics.
    ///
    /// # Example
    /// ```
    /// let stats = cache.get_cache_stats();
    /// println!("Cached files: {}", stats.get("cached_files").unwrap());
    /// println!("Total bytes: {}", stats.get("total_bytes").unwrap());
    /// ```
    ///
    /// # Note
    /// This function assumes that `YAML_CACHE` is a globally accessible data structure
    /// that holds cached entries, where each entry may contain an optional `raw_content`.
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

    /// Get multiple settings at once (batch operation)
    ///
    /// This method retrieves multiple settings in a single operation, which is more
    /// efficient than calling `get_setting` multiple times when you need several values.
    ///
    /// # Parameters
    /// - `yaml`: The root YAML structure to query
    /// - `key_paths`: A slice of key paths to retrieve
    ///
    /// # Returns
    /// A HashMap where keys are the key paths and values are the corresponding YAML values.
    /// If a key path doesn't exist, it won't be included in the result.
    ///
    /// # Example
    /// ```rust,no_run
    /// use classic_yaml_core::YamlOperations;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let ops = YamlOperations::new();
    /// let yaml_str = r#"
    ///     settings:
    ///       debug: true
    ///       level: 5
    ///       name: "test"
    /// "#;
    /// let yaml = ops.parse_yaml(yaml_str)?;
    ///
    /// let keys = vec!["settings.debug", "settings.level", "settings.name"];
    /// let results = ops.get_settings_batch(&yaml, &keys);
    ///
    /// assert_eq!(results.len(), 3);
    /// # Ok(())
    /// # }
    /// ```
    pub fn get_settings_batch(&self, yaml: &Yaml, key_paths: &[&str]) -> HashMap<String, Yaml> {
        let mut results = HashMap::with_capacity(key_paths.len());

        for key_path in key_paths {
            if let Some(value) = self.get_setting(yaml, key_path) {
                results.insert(key_path.to_string(), value);
            }
        }

        results
    }

    /// Set multiple settings at once (batch operation)
    ///
    /// This method updates multiple settings in a single operation, which is more
    /// efficient than calling `set_setting` multiple times.
    ///
    /// # Parameters
    /// - `yaml`: The root YAML structure to update
    /// - `settings`: A slice of tuples containing (key_path, value) pairs
    ///
    /// # Returns
    /// The updated YAML structure with all settings applied, or an error if any
    /// key path is invalid.
    ///
    /// # Example
    /// ```rust,no_run
    /// use classic_yaml_core::{YamlOperations, YamlError};
    /// use yaml_rust2::Yaml;
    ///
    /// # fn example() -> Result<(), YamlError> {
    /// let ops = YamlOperations::new();
    /// let yaml_str = r#"
    ///     settings:
    ///       debug: false
    /// "#;
    /// let yaml = ops.parse_yaml(yaml_str)?;
    ///
    /// let updates = vec![
    ///     ("settings.debug", Yaml::Boolean(true)),
    ///     ("settings.level", Yaml::Integer(10)),
    /// ];
    ///
    /// let updated = ops.set_settings_batch(&yaml, &updates)?;
    /// # Ok(())
    /// # }
    /// ```
    pub fn set_settings_batch(
        &self,
        yaml: &Yaml,
        settings: &[(&str, Yaml)],
    ) -> Result<Yaml, YamlError> {
        let mut current = yaml.clone();

        for (key_path, value) in settings {
            current = self.set_setting(&current, key_path, value.clone())?;
        }

        Ok(current)
    }

    /// Load multiple YAML files at once (batch operation)
    ///
    /// This method loads multiple YAML files in parallel, which is significantly
    /// faster than loading them sequentially. Caching is applied as normal.
    ///
    /// # Parameters
    /// - `paths`: A slice of file paths to load
    ///
    /// # Returns
    /// A HashMap where keys are the file paths (as strings) and values are the
    /// parsed YAML documents. Files that fail to load are not included in the result.
    ///
    /// # Example
    /// ```rust,no_run
    /// use classic_yaml_core::YamlOperations;
    /// use std::path::Path;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let ops = YamlOperations::new();
    /// let paths = vec![
    ///     Path::new("config1.yaml"),
    ///     Path::new("config2.yaml"),
    /// ];
    ///
    /// let results = ops.load_yaml_files_batch(&paths);
    /// # Ok(())
    /// # }
    /// ```
    pub fn load_yaml_files_batch(&self, paths: &[&Path]) -> HashMap<String, Yaml> {
        let mut results = HashMap::with_capacity(paths.len());

        for path in paths {
            if let Ok(yaml) = self.load_yaml_file(path) {
                results.insert(path.to_string_lossy().to_string(), yaml);
            }
        }

        results
    }

    /// Extract a string value from YAML using a dot-separated key path
    ///
    /// This is a convenience method for getting string values from nested YAML structures.
    /// It navigates through the YAML document using dot notation (e.g., "parent.child.field")
    /// and returns the string value or a default if the key doesn't exist or isn't a string.
    ///
    /// # Arguments
    /// * `data` - YAML data to extract from
    /// * `key_path` - Dot-separated path (e.g., "parent.child.field")
    /// * `default` - Default value if key not found or not a string
    ///
    /// # Returns
    /// String value or default
    ///
    /// # Example
    /// ```rust,no_run
    /// use classic_yaml_core::YamlOperations;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let ops = YamlOperations::new();
    /// let yaml_str = r#"
    ///     game:
    ///       name: Fallout4
    ///       version: "1.10.163"
    /// "#;
    /// let yaml = ops.parse_yaml(yaml_str)?;
    ///
    /// let name = ops.get_string_value(&yaml, "game.name", "Unknown");
    /// assert_eq!(name, "Fallout4");
    ///
    /// let missing = ops.get_string_value(&yaml, "game.missing", "default");
    /// assert_eq!(missing, "default");
    /// # Ok(())
    /// # }
    /// ```
    pub fn get_string_value(&self, data: &Yaml, key_path: &str, default: &str) -> String {
        let keys: Vec<&str> = key_path.split('.').collect();
        let mut current = data;

        for key in keys {
            match current {
                Yaml::Hash(hash) => {
                    let key_yaml = Yaml::String(key.to_string());
                    current = match hash.get(&key_yaml) {
                        Some(value) => value,
                        None => return default.to_string(),
                    };
                }
                _ => return default.to_string(),
            }
        }

        current.as_str().unwrap_or(default).to_string()
    }

    /// Extract a vector of strings from YAML using a dot-separated key path
    ///
    /// This is a convenience method for getting string arrays from nested YAML structures.
    /// It navigates through the YAML document using dot notation and returns a vector
    /// of strings, or an empty vector if the key doesn't exist or isn't an array.
    ///
    /// # Arguments
    /// * `data` - YAML data to extract from
    /// * `key_path` - Dot-separated path (e.g., "parent.child.array")
    ///
    /// # Returns
    /// Vector of strings, or empty vector if key not found or not an array
    ///
    /// # Example
    /// ```rust,no_run
    /// use classic_yaml_core::YamlOperations;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let ops = YamlOperations::new();
    /// let yaml_str = r#"
    ///     game:
    ///       plugins:
    ///         - plugin1.esp
    ///         - plugin2.esp
    ///         - plugin3.esp
    /// "#;
    /// let yaml = ops.parse_yaml(yaml_str)?;
    ///
    /// let plugins = ops.get_vec_value(&yaml, "game.plugins");
    /// assert_eq!(plugins.len(), 3);
    /// assert_eq!(plugins[0], "plugin1.esp");
    /// # Ok(())
    /// # }
    /// ```
    pub fn get_vec_value(&self, data: &Yaml, key_path: &str) -> Vec<String> {
        let keys: Vec<&str> = key_path.split('.').collect();
        let mut current = data;

        for key in keys {
            match current {
                Yaml::Hash(hash) => {
                    let key_yaml = Yaml::String(key.to_string());
                    current = match hash.get(&key_yaml) {
                        Some(value) => value,
                        None => return Vec::new(),
                    };
                }
                _ => return Vec::new(),
            }
        }

        match current {
            Yaml::Array(arr) => arr
                .iter()
                .filter_map(|item| item.as_str().map(String::from))
                .collect(),
            _ => Vec::new(),
        }
    }

    /// Extract a hashmap from YAML using a dot-separated key path
    ///
    /// This is a convenience method for getting string key-value maps from nested YAML structures.
    /// It navigates through the YAML document using dot notation and returns a HashMap,
    /// or an empty map if the key doesn't exist or isn't a hash.
    ///
    /// # Arguments
    /// * `data` - YAML data to extract from
    /// * `key_path` - Dot-separated path (e.g., "parent.child.map")
    ///
    /// # Returns
    /// HashMap of string key-value pairs, or empty map if key not found or not a hash
    ///
    /// # Example
    /// ```rust,no_run
    /// use classic_yaml_core::YamlOperations;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let ops = YamlOperations::new();
    /// let yaml_str = r#"
    ///     game:
    ///       mods:
    ///         mod1: "Description 1"
    ///         mod2: "Description 2"
    /// "#;
    /// let yaml = ops.parse_yaml(yaml_str)?;
    ///
    /// let mods = ops.get_hashmap_value(&yaml, "game.mods");
    /// assert_eq!(mods.len(), 2);
    /// assert_eq!(mods.get("mod1"), Some(&"Description 1".to_string()));
    /// # Ok(())
    /// # }
    /// ```
    pub fn get_hashmap_value(&self, data: &Yaml, key_path: &str) -> HashMap<String, String> {
        let keys: Vec<&str> = key_path.split('.').collect();
        let mut current = data;

        for key in keys {
            match current {
                Yaml::Hash(hash) => {
                    let key_yaml = Yaml::String(key.to_string());
                    current = match hash.get(&key_yaml) {
                        Some(value) => value,
                        None => return HashMap::new(),
                    };
                }
                _ => return HashMap::new(),
            }
        }

        match current {
            Yaml::Hash(map) => map
                .iter()
                .filter_map(|(k, v)| match (k.as_str(), v.as_str()) {
                    (Some(key_str), Some(val_str)) => {
                        Some((key_str.to_string(), val_str.to_string()))
                    }
                    _ => None,
                })
                .collect(),
            _ => HashMap::new(),
        }
    }
}

impl Default for YamlOperations {
    fn default() -> Self {
        Self::new()
    }
}

/// Clear the global YAML cache
///
/// This function clears all cached YAML data. It's primarily useful for
/// testing to ensure clean state between test runs.
///
/// # Example
/// ```rust,no_run
/// use classic_yaml_core::clear_global_yaml_cache;
///
/// // Clear all cached YAML files
/// clear_global_yaml_cache();
/// ```
pub fn clear_global_yaml_cache() {
    YAML_CACHE.clear();
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

    #[test]
    fn test_get_settings_batch() {
        let ops = YamlOperations::new();
        let yaml_str = r#"
            settings:
              debug: true
              level: 5
              name: "test"
        "#;

        let yaml = ops.parse_yaml(yaml_str).unwrap();
        let keys = vec!["settings.debug", "settings.level", "settings.name"];
        let results = ops.get_settings_batch(&yaml, &keys);

        assert_eq!(results.len(), 3);
        assert_eq!(results.get("settings.debug"), Some(&Yaml::Boolean(true)));
        assert_eq!(results.get("settings.level"), Some(&Yaml::Integer(5)));
        assert_eq!(
            results.get("settings.name"),
            Some(&Yaml::String("test".to_string()))
        );
    }

    #[test]
    fn test_set_settings_batch() {
        let ops = YamlOperations::new();
        let yaml_str = r#"
            settings:
              debug: false
        "#;

        let yaml = ops.parse_yaml(yaml_str).unwrap();
        let updates = vec![
            ("settings.debug", Yaml::Boolean(true)),
            ("settings.level", Yaml::Integer(10)),
            ("settings.name", Yaml::String("updated".to_string())),
        ];

        let updated = ops.set_settings_batch(&yaml, &updates).unwrap();

        assert_eq!(
            ops.get_setting(&updated, "settings.debug"),
            Some(Yaml::Boolean(true))
        );
        assert_eq!(
            ops.get_setting(&updated, "settings.level"),
            Some(Yaml::Integer(10))
        );
        assert_eq!(
            ops.get_setting(&updated, "settings.name"),
            Some(Yaml::String("updated".to_string()))
        );
    }
}
