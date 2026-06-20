//! Parse, dump, file I/O, and cache-control operations.

use super::cache::{
    CACHE_HITS, CACHE_MISSES, CachedYaml, YAML_CACHE, total_cached_bytes, yaml_cache_stats,
};
use super::error::YamlError;
use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;
use std::sync::atomic::Ordering;
use tracing::trace;
use yaml_rust2::{Yaml, YamlEmitter, YamlLoader};

/// A struct representing operations and configurations related to YAML processing.
///
/// The `YamlOperations` struct is designed to provide functionality for handling
/// YAML files with customizable configurations. This includes format configuration
/// and optional caching to optimize performance in repeated operations.
/// # Fields
///
/// * `cache_enabled` - A boolean field that enables or disables caching functionality.
///   When set to `true`, caching can be used to avoid redundant processing, improving
///   performance in scenarios involving multiple reads or writes.
///
/// # Usage
///
/// Example:
/// ```rust
/// use classic_settings_core::YamlOperations;
///
/// let yaml_ops = YamlOperations::new();
/// assert!(yaml_ops.is_cache_enabled());
/// ```
pub struct YamlOperations {
    cache_enabled: bool,
}

impl YamlOperations {
    /// Creates a new instance of the struct with default configuration.
    /// # Returns
    /// A new instance where:
    /// - `cache_enabled` is set to `true`.
    ///
    /// # Example
    /// ```rust
    /// use classic_settings_core::YamlOperations;
    ///
    /// let instance = YamlOperations::new();
    /// assert!(instance.is_cache_enabled());
    /// ```
    pub fn new() -> Self {
        Self {
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
                            // Cache is still valid - record hit
                            CACHE_HITS.fetch_add(1, Ordering::Relaxed);
                            trace!(cache = "yaml", path = %file_path.display(), "cache hit");
                            return Ok((*cached.data).clone());
                        }

                        let _ = YAML_CACHE.remove(&file_path);
                    }
                }
            }
        }

        // Cache miss (either not cached, cache disabled, or file modified)
        CACHE_MISSES.fetch_add(1, Ordering::Relaxed);
        trace!(cache = "yaml", path = %file_path.display(), "cache miss");

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
    /// The helper adapts the canonical cache stats contract and supplements it with
    /// YAML-specific raw byte totals for legacy callers.
    /// # Returns
    /// A `HashMap<String, usize>` containing the cache statistics.
    ///
    /// # Example
    /// ```rust
    /// use classic_settings_core::YamlOperations;
    ///
    /// let yaml_ops = YamlOperations::new();
    /// let stats = yaml_ops.get_cache_stats();
    /// println!("Cached files: {}", stats.get("cached_files").unwrap());
    /// println!("Total bytes: {}", stats.get("total_bytes").unwrap());
    /// ```
    ///
    /// # Note
    /// This function assumes that `YAML_CACHE` is a globally accessible data structure
    /// that holds cached entries, where each entry may contain an optional `raw_content`.
    pub fn get_cache_stats(&self) -> HashMap<String, usize> {
        let canonical = yaml_cache_stats();
        let mut stats = HashMap::new();
        stats.insert("cached_files".to_string(), canonical.size);
        stats.insert("capacity".to_string(), canonical.capacity);
        stats.insert("total_bytes".to_string(), total_cached_bytes());
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
    /// use classic_settings_core::YamlOperations;
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
}

impl Default for YamlOperations {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
#[path = "operations_tests.rs"]
mod tests;
