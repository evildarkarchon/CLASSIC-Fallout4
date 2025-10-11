//! High-performance path handling utilities with caching
//!
//! This module provides path operations optimized for the CLASSIC application.
//! It caches path lookups and provides efficient path validation without hardcoding
//! any game paths. All game paths are discovered at runtime through Python.

use dashmap::DashMap;
use pyo3::exceptions::PyIOError;
use pyo3::prelude::*;
use rayon::prelude::*;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};

/// A structure representing an entry in a path cache.
///
/// This struct is used to store information about a specific entry in a cache, including the
/// cached path, the time it was added or last updated, and how many times it has been accessed.
/// # Fields
///
/// * `value` (`PathBuf`) -
///   The file system path associated with this cache entry.
///
/// * `timestamp` (`Instant`) -
///   The time when this cache entry was created or last updated. Used to track the age
///   or relevance of the cache entry.
///
/// * `hit_count` (`u32`) -
///   The number of times this cache entry has been accessed. Useful for determining
///   the frequency of access and prioritizing or evicting cache entries.
#[derive(Clone, Debug)]
struct PathCacheEntry {
    value: PathBuf,
    timestamp: Instant,
    hit_count: u32,
}

/// A structure to handle and manage paths with caching for resolved paths and validation results.
///
/// This struct provides functionality to cache resolved paths and their validation results
/// for a specified Time-To-Live (TTL) duration. It helps in optimizing path resolutions
/// and validations by reducing repetitive computations.
/// # Fields
/// * `path_cache` - A thread-safe, concurrent cache (using `DashMap`) for storing resolved paths
///   with their respective TTL. The cache improves performance by avoiding repetitive path resolutions 
///   when paths are accessed multiple times within their TTL.
/// * `validation_cache` - A thread-safe, concurrent cache (using `DashMap`) for storing the results
///   of path validations. Each entry contains:
///   - A boolean indicating whether the validation was successful.
///   - A string providing additional information about the validation result.
///   - An `Instant` representing the time when the validation was stored.
///   The cache is used to reduce the need for re-validating paths multiple times in a short span.
/// * `cache_ttl` - A `Duration` specifying the maximum time-to-live for cached entries
///   in both the `path_cache` and the `validation_cache`. Entries exceeding this duration
///   are considered expired and should be resolved/validated again.
#[pyclass]
pub struct PathHandler {
    /// Cache for resolved paths with TTL
    path_cache: Arc<DashMap<String, PathCacheEntry>>,
    /// Cache for validation results
    validation_cache: Arc<DashMap<PathBuf, (bool, String, Instant)>>,
    /// Cache TTL in seconds
    cache_ttl: Duration,
}

#[pymethods]
impl PathHandler {
    /// Creates a new instance of the struct with optional cache TTL (time-to-live) configuration.
    /// # Parameters
    /// - `cache_ttl_seconds` (u64): The duration (in seconds) for which cached items remain in the cache. 
    ///   Defaults to 300 seconds (5 minutes) if not explicitly specified.
    ///
    /// # Returns
    /// A new instance of the struct with initialized caches (`path_cache` and `validation_cache`) 
    /// and the specified or default cache TTL.
    ///
    /// # Attributes
    /// - `#[new]`: Marks this method as the constructor when exposed to Python using PyO3.
    /// - `#[pyo3(signature = (cache_ttl_seconds=300))]`: Specifies the default argument for 
    ///   `cache_ttl_seconds` when invoked from Python.
    ///
    /// # Example (in Python)
    /// ```python
    /// instance = YourClassName(cache_ttl_seconds=600)  # Sets cache TTL to 600 seconds
    /// default_instance = YourClassName()  # Defaults to 300 seconds for cache TTL
    /// ```
    #[new]
    #[pyo3(signature = (cache_ttl_seconds=300))]
    pub fn new(cache_ttl_seconds: u64) -> Self {
        Self {
            path_cache: Arc::new(DashMap::new()),
            validation_cache: Arc::new(DashMap::new()),
            cache_ttl: Duration::from_secs(cache_ttl_seconds),
        }
    }

    /// Normalizes a file path, resolving symbolic links and cleaning up any redundant components.
    ///
    /// This function checks for a cached result of a previously normalized path to improve efficiency.
    /// If the path is cached and the entry is still valid (based on cache time-to-live),
    /// it retrieves the cached value, updates the cache hit count, and returns it immediately.
    /// Otherwise, it performs normalization using `canonicalize` to resolve the path to an absolute path.
    /// If `canonicalize` fails, it falls back to a custom cleanup process for the path.
    /// The normalized result is then added to the cache for future use.
    /// # Arguments
    /// * `path` - A `String` representing the file path to normalize.
    ///
    /// # Returns
    /// * `PyResult<String>` - A Python-compatible result containing the normalized path.
    /// The normalized path is returned as a `String`.
    ///
    /// # Errors
    /// Returns an error if normalization (including path cleanup) fails during processing.
    ///
    /// # Behavior
    /// 1. **Check Cache**: If the input path exists in the cache and is still valid, the cached result is returned.
    /// 2. **Normalize Path**:
    ///    - Uses `canonicalize` to resolve the path to an absolute and normalized form.
    ///    - If `canonicalize` fails, it falls back to `self.clean_path` to clean up the path.
    /// 3. **Cache Update**: The normalized result is stored in the cache for subsequent lookups. If the cache is accessed,
    ///    the cache hit count for the entry is incremented.
    /// 4. Returns the normalized path as a `String`.
    ///
    /// # Example
    /// ```
    /// let normalized_path = instance.normalize_path("/some/../path/here".to_string());
    /// match normalized_path {
    ///     Ok(result) => println!("Normalized path: {}", result),
    ///     Err(err) => eprintln!("Failed to normalize path: {:?}", err),
    /// }
    /// ```
    ///
    /// # Cache Details
    /// - Cached entries include the normalized path, a timestamp of when it was cached, and a hit count.
    /// - When a cache hit occurs, the timestamp remains unchanged but the hit count is incremented.
    /// - Expired cache entries (older than the `cache_ttl`) are not used and will be overwritten.
    ///
    /// # Note
    /// - This function relies on the `PathBuf::canonicalize` method, which may fail for non-existent or inaccessible paths.
    /// - The `clean_path` method is used as a fallback for cases where canonicalization fails.
    pub fn normalize_path(&self, path: String) -> PyResult<String> {
        // Check cache first
        if let Some(entry) = self.path_cache.get(&path) {
            if entry.timestamp.elapsed() < self.cache_ttl {
                // Clone the value we need before dropping the guard
                let result = entry.value.to_string_lossy().to_string();
                let mut updated_entry = entry.clone();
                updated_entry.hit_count += 1;
                // Drop the guard before inserting
                drop(entry);
                // Update hit count
                self.path_cache.insert(path.clone(), updated_entry);
                return Ok(result);
            }
        }

        // Normalize the path
        let path_buf = PathBuf::from(&path);
        let normalized = match path_buf.canonicalize() {
            Ok(p) => p,
            Err(_) => {
                // If canonicalize fails, just clean up the path
                let cleaned = self.clean_path(&path_buf)?;
                cleaned
            }
        };

        // Cache the result
        let entry = PathCacheEntry {
            value: normalized.clone(),
            timestamp: Instant::now(),
            hit_count: 1,
        };
        self.path_cache.insert(path, entry);

        Ok(normalized.to_string_lossy().to_string())
    }

    /// Clear all caches
    pub fn clear_cache(&self) {
        self.path_cache.clear();
        self.validation_cache.clear();
    }

    /// Returns the current statistics of the internal caches.
    ///
    /// This method provides information about the number of entries
    /// in the `path_cache` and `validation_cache` of the object.
    /// # Returns
    /// A tuple containing two `usize` values:
    /// - The first element represents the number of entries in the `path_cache`.
    /// - The second element represents the number of entries in the `validation_cache`.
    ///
    /// # Example
    /// ```
    /// let stats = instance.cache_stats();
    /// println!("Path cache size: {}", stats.0);
    /// println!("Validation cache size: {}", stats.1);
    /// ```
    pub fn cache_stats(&self) -> (usize, usize) {
        (self.path_cache.len(), self.validation_cache.len())
    }

    /// Cleans up expired items from the `path_cache` and `validation_cache` based on the configured cache TTL.
    ///
    /// This method iterates through the respective caches (`path_cache` and `validation_cache`)
    /// and removes any entries that have existed longer than the predefined time-to-live (TTL).
    /// # Process:
    /// 1. The current time is captured using `Instant::now()`.
    /// 2. For the `path_cache`, each entry's timestamp is checked and any entry older than the
    ///    cache TTL is removed.
    /// 3. For the `validation_cache`, each entry's timestamp is similarly checked and older
    ///    entries are removed based on the same TTL criteria.
    ///
    /// # Example Behavior:
    /// If an entry in either cache was added 10 minutes ago, and the cache TTL is set to 5 minutes,
    /// the entry will be removed when this method is called.
    ///
    /// # Notes:
    /// - The `cache_ttl` duration is assumed to be configured and represents the maximum time
    ///   an entry is valid in the cache.
    /// - The method assumes `path_cache` and `validation_cache` expose a `retain` method to filter
    ///   entries based on the provided condition.
    ///
    /// # Implementation Details:
    /// - `path_cache` is cleaned based on each entry's `timestamp` attribute.
    /// - `validation_cache` is cleaned based on a tuple containing a `timestamp` at the end.
    ///
    /// # Dependencies:
    /// - Uses `std::time::Instant` for time tracking.
    pub fn cleanup_cache(&self) {
        let now = Instant::now();

        // Clean path cache
        self.path_cache
            .retain(|_, entry| now.duration_since(entry.timestamp) < self.cache_ttl);

        // Clean validation cache
        self.validation_cache
            .retain(|_, (_, _, timestamp)| now.duration_since(*timestamp) < self.cache_ttl);
    }
}

// Internal helper methods (not exposed to Python)
impl PathHandler {
    /// Cleans a given file path by resolving and removing redundant components.
    ///
    /// This function takes care of simplifying file paths by handling redundant
    /// components such as `.` (current directory) and `..` (parent directory). It effectively
    /// cleans up the path without performing any filesystem operations or validations.
    /// # Parameters
    /// - `path`: A reference to the `PathBuf` containing the path to be cleaned.
    ///
    /// # Returns
    /// - `PyResult<PathBuf>`: A `PathBuf` containing the cleaned path inside a `PyResult`,
    ///   which represents the result of the operation. The cleaned path has all redundant
    ///   components removed.
    ///
    /// # Behavior
    /// - `..` (parent directory) components are resolved by removing the last valid component
    ///   if available.
    /// - `.` (current directory) components are skipped.
    /// - All other components are retained in their original order.
    ///
    /// # Example
    /// ```rust
    /// let path_to_clean = PathBuf::from("a/./b/c/../d");
    /// let cleaned_path = clean_path(&path_to_clean)?;
    /// assert_eq!(cleaned_path, PathBuf::from("a/b/d"));
    /// ```
    ///
    /// # Notes
    /// - This function does not interact with the filesystem, so it doesn't validate
    ///   whether the path exists or check for symlinks.
    /// - It operates purely on the logical structure of the path.
    ///
    /// # Errors
    /// - This function returns a `PyResult` because it is intended to be part of a 
    ///   Python binding using PyO3. However, in its current implementation, it does not
    ///   fail under normal circumstances.
    fn clean_path(&self, path: &PathBuf) -> PyResult<PathBuf> {
        let mut components = vec![];
        for component in path.components() {
            match component {
                std::path::Component::ParentDir => {
                    components.pop();
                }
                std::path::Component::CurDir => {
                    // Skip
                }
                c => components.push(c),
            }
        }

        let mut result = PathBuf::new();
        for component in components {
            result.push(component);
        }
        Ok(result)
    }

    /// Validates a batch of file paths for validity and caches the results for quicker subsequent validations.
    ///
    /// # Parameters
    /// - `paths` (`Vec<String>`): A vector of file paths (as strings) to validate.
    ///
    /// # Returns
    /// - `Vec<(String, bool, String)>`: A vector of tuples where each tuple contains:
    ///   - `String`: The original file path as provided.
    ///   - `bool`: A boolean indicating whether the path is valid (`true`) or invalid (`false`).
    ///   - `String`: A message providing details about the validation result.
    ///
    /// # Behavior
    /// - Validates the provided file paths concurrently using a parallel iterator for improved performance.
    /// - Before performing validation, checks the `validation_cache` for any cached results.
    ///   - If a cached entry for a path exists and the time-to-live (`cache_ttl`) has not elapsed, 
    ///     the cached result is returned without re-validating.
    ///   - If no valid cached entry exists or the cache has expired, the path is validated using 
    ///     the `validate_single_path` method.
    /// - Updates the `validation_cache` with the validation result and the current timestamp.
    ///
    /// # Caching
    /// - The method uses a cache (`validation_cache`) to store the validation results of paths along with a timestamp. 
    /// - Cached results are only used if they are still within the specified `cache_ttl` period.
    ///
    /// # Parallelism
    /// - This function takes advantage of parallelism using `par_iter()` to validate paths concurrently, 
    ///   which can significantly improve performance when working with a large number of paths.
    ///
    /// # Notes
    /// - The `validation_cache` and `cache_ttl` are assumed to be part of the struct implementing this method (`self`).
    /// - The `validate_single_path` method, which performs the actual path validation, is also part of the struct
    ///   and is called for paths that do not have valid cached results.
    pub fn validate_paths_batch(&self, paths: Vec<String>) -> Vec<(String, bool, String)> {
        paths
            .par_iter()
            .map(|path| {
                let path_buf = PathBuf::from(path);

                // Check validation cache
                if let Some(cached) = self.validation_cache.get(&path_buf) {
                    let (is_valid, msg, timestamp) = cached.clone();
                    if timestamp.elapsed() < self.cache_ttl {
                        return (path.clone(), is_valid, msg);
                    }
                }

                // Perform validation
                let (is_valid, msg) = self.validate_single_path(&path_buf);

                // Cache result
                self.validation_cache
                    .insert(path_buf.clone(), (is_valid, msg.clone(), Instant::now()));

                (path.clone(), is_valid, msg)
            })
            .collect()
    }

    /// Validates a single file system path.
    ///
    /// This method checks if the provided path exists and if it is readable by attempting
    /// to fetch its metadata. If the path does not exist or is not readable, an appropriate
    /// error message is returned.
    /// # Arguments
    ///
    /// * `path` - A `PathBuf` reference representing the file system path to validate.
    ///
    /// # Returns
    ///
    /// A tuple consisting of:
    /// * `bool` - A boolean value indicating whether the path is valid (true) or not (false).
    /// * `String` - An error message if the path is invalid. Returns an empty string if the path is valid.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use std::path::PathBuf;
    ///
    /// let path = PathBuf::from("/some/path");
    /// let (is_valid, message) = validate_single_path(&path);
    ///
    /// if is_valid {
    ///     println!("Path is valid!");
    /// } else {
    ///     println!("Path is invalid: {}", message);
    /// }
    /// ```
    fn validate_single_path(&self, path: &PathBuf) -> (bool, String) {
        if !path.exists() {
            return (false, format!("Path does not exist: {}", path.display()));
        }

        // Check if readable
        if let Err(e) = std::fs::metadata(path) {
            return (false, format!("Cannot read metadata: {}", e));
        }

        (true, String::new())
    }

    /// Joins a base path with a series of path components to construct a new combined path.
    /// # Arguments
    ///
    /// * `base` - A `String` representing the base path. This will serve as the starting point for the path construction.
    /// * `components` - A `Vec<String>` containing additional path components to be appended to the base path.
    ///
    /// # Returns
    ///
    /// A `String` representing the combined path created by appending the `components` to the `base`.
    ///
    /// The returned path is converted to a lossless UTF-8 string using `to_string_lossy()`.
    ///
    /// # Example
    ///
    /// ```
    /// use std::path::PathBuf;
    ///
    /// let base = String::from("/home/user");
    /// let components = vec![String::from("documents"), String::from("file.txt")];
    ///
    /// let combined_path = your_struct.join_paths(base, components);
    /// assert_eq!(combined_path, "/home/user/documents/file.txt");
    /// ```
    pub fn join_paths(&self, base: String, components: Vec<String>) -> String {
        let mut path = PathBuf::from(base);
        for component in components {
            path.push(component);
        }
        path.to_string_lossy().to_string()
    }

    /// Splits the given file system path into its individual components.
    ///
    /// This method takes a `String` representation of a file system path and
    /// splits it into a `Vec<String>` where each element represents a component
    /// (e.g., directory, file name) of the path. The components are converted to
    /// `String` using a lossless string conversion to ensure non-UTF-8 compatible
    /// sequences are handled gracefully.
    /// # Arguments
    ///
    /// * `path` - A `String` representing the file system path to be split.
    ///
    /// # Returns
    ///
    /// A `Vec<String>` containing the individual components of the provided path.
    ///
    /// # Example
    ///
    /// ```
    /// let splitter = YourStruct {}; // Replace `YourStruct` with the structure that implements this function.
    /// let components = splitter.split_path(String::from("/home/user/documents"));
    /// assert_eq!(components, vec!["/", "home", "user", "documents"]);
    /// ```
    pub fn split_path(&self, path: String) -> Vec<String> {
        let path_buf = PathBuf::from(path);
        path_buf
            .components()
            .map(|c| c.as_os_str().to_string_lossy().to_string())
            .collect()
    }

    /// Retrieves the filename from a given file path.
    ///
    /// This function converts the provided path into a `PathBuf`,
    /// extracts the file name if available, and returns it as a `String`.
    /// If the file path does not contain a filename (e.g., if it is a directory),
    /// it returns `None`.
    /// # Arguments
    ///
    /// * `path` - A `String` representing the file path.
    ///
    /// # Returns
    ///
    /// This function returns a `PyResult<Option<String>>`:
    /// - `Ok(Some(String))` if a file name is successfully extracted.
    /// - `Ok(None)` if the given path does not include a file name.
    /// - Any failure in input processing is propagated as an error within the `PyResult`.
    ///
    /// # Examples
    ///
    /// ```rust
    /// # use your_module::YourStruct;
    /// # use pyo3::prelude::*;
    /// let struct_instance = YourStruct::new();
    /// let filename = struct_instance.get_filename("/some/directory/file.txt".to_string()).unwrap();
    /// assert_eq!(filename, Some("file.txt".to_string()));
    ///
    /// let no_filename = struct_instance.get_filename("/some/directory/".to_string()).unwrap();
    /// assert_eq!(no_filename, None);
    /// ```
    ///
    /// # Notes
    ///
    /// - This function treats the input `path` as a UTF-8 string. Any invalid Unicode characters
    ///   in the file name will be converted into the Unicode replacement character (`�`) during the
    ///   conversion to a `String`.
    pub fn get_filename(&self, path: String) -> PyResult<Option<String>> {
        let path_buf = PathBuf::from(path);
        Ok(path_buf
            .file_name()
            .map(|name| name.to_string_lossy().to_string()))
    }

    /// Retrieves the file extension from a given file path.
    ///
    /// This function takes a file path as input, converts it into a `PathBuf`,
    /// and attempts to extract the file's extension. If the file has an extension,
    /// it is returned as a `String`. If there is no extension, the function returns `None`.
    /// # Arguments
    ///
    /// * `path` - A `String` representing the file path to extract the extension from.
    ///
    /// # Returns
    ///
    /// Returns a `PyResult<Option<String>>`:
    /// - `Ok(Some(String))`: The file has an extension, and it is returned as a `String`.
    /// - `Ok(None)`: The file does not have an extension.
    /// - `Err(PyErr)`: If an error occurs during the operation.
    ///
    /// # Example
    ///
    /// ```rust
    /// let path = "example.txt".to_string();
    /// let extension = instance.get_extension(path).unwrap();
    /// assert_eq!(extension, Some("txt".to_string()));
    ///
    /// let path_without_extension = "example".to_string();
    /// let no_extension = instance.get_extension(path_without_extension).unwrap();
    /// assert_eq!(no_extension, None);
    /// ```
    ///
    /// # Notes
    ///
    /// The function uses `to_string_lossy` to safely handle non-UTF-8 file extensions, converting
    /// them into a `String` representation. This ensures compatibility with both valid UTF-8
    /// and non-UTF-8 extensions.
    pub fn get_extension(&self, path: String) -> PyResult<Option<String>> {
        let path_buf = PathBuf::from(path);
        Ok(path_buf
            .extension()
            .map(|ext| ext.to_string_lossy().to_string()))
    }

    /// Retrieves the parent directory of a given file or directory path.
    /// # Arguments
    ///
    /// * `path` - A `String` representing the file or directory path.
    ///
    /// # Returns
    ///
    /// * `PyResult<Option<String>>`:
    ///   - If the given path has a parent directory, it returns `Ok(Some(String))` containing the parent path as a `String`.
    ///   - If the given path has no parent directory (e.g., it's a root directory), it returns `Ok(None)`.
    ///   - If there are any issues with the input, it may return a Python error result.
    ///
    /// The function internally converts the provided path into a `PathBuf` and then determines its parent directory. The parent directory path is safely converted to a `String` using a lossy conversion to handle invalid UTF-8 sequences.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use your_module::YourStruct;
    /// use pyo3::PyResult;
    ///
    /// let path = "/some/directory/file.txt".to_string();
    /// let parent = YourStruct.get_parent(path);
    ///
    /// match parent {
    ///     Ok(Some(parent_path)) => println!("Parent directory: {}", parent_path),
    ///     Ok(None) => println!("No parent exists (root directory)"),
    ///     Err(e) => eprintln!("Error: {}", e),
    /// }
    /// ```
    pub fn get_parent(&self, path: String) -> PyResult<Option<String>> {
        let path_buf = PathBuf::from(path);
        Ok(path_buf.parent().map(|p| p.to_string_lossy().to_string()))
    }

    /// Checks if a given file path is an absolute path.
    /// # Arguments
    ///
    /// * `path` - A `String` representing the file path to be checked.
    ///
    /// # Returns
    ///
    /// * `bool` - Returns `true` if the given path is an absolute path,
    ///   otherwise returns `false`.
    ///
    /// # Example
    ///
    /// ```
    /// use std::path::PathBuf;
    ///
    /// let path_check = YourStruct {};
    /// assert!(path_check.is_absolute("/absolute/path".to_string()));
    /// assert!(!path_check.is_absolute("relative/path".to_string()));
    /// ```
    pub fn is_absolute(&self, path: String) -> bool {
        PathBuf::from(path).is_absolute()
    }

    /// Converts a given file path to an absolute path.
    /// # Parameters
    /// - `path`: A `String` representing the file path to be converted.
    /// - `base`: An optional `String` representing the base directory to resolve the path.
    ///   - If provided, `path` will be joined with `base` if `path` is not already absolute.
    ///   - If not provided, the current working directory will be used as the base.
    ///
    /// # Returns
    /// - `PyResult<String>`: The absolute path as a `String`, or an error if the current directory cannot be retrieved.
    ///
    /// # Behavior
    /// - If `path` is already absolute, it will be returned as-is.
    /// - If `path` is not absolute:
    ///   - If a `base` is provided, `path` will be resolved relative to the `base`.
    ///   - If no `base` is provided, the current working directory (`std::env::current_dir`) will be used as the base to resolve `path`.
    /// - The resulting absolute path will be converted to a UTF-8 string using `to_string_lossy` to ensure compatibility with non-UTF-8 paths.
    ///
    /// # Errors
    /// - Returns a `PyIOError` if there is an issue obtaining the current working directory (when `base` is `None`).
    ///
    /// # Examples
    /// ```
    /// let path = "some/relative/path".to_string();
    /// let base = Some("/base/directory".to_string());
    ///
    /// let absolute_path = to_absolute(path, base).unwrap();
    /// assert_eq!(absolute_path, "/base/directory/some/relative/path");
    ///
    /// let path = "/already/absolute/path".to_string();
    /// let absolute_path = to_absolute(path, None).unwrap();
    /// assert_eq!(absolute_path, "/already/absolute/path");
    /// ```
    pub fn to_absolute(&self, path: String, base: Option<String>) -> PyResult<String> {
        let path_buf = PathBuf::from(&path);

        let absolute = if path_buf.is_absolute() {
            path_buf
        } else {
            match base {
                Some(b) => PathBuf::from(b).join(path_buf),
                None => std::env::current_dir()
                    .map_err(|e| PyIOError::new_err(e.to_string()))?
                    .join(path_buf),
            }
        };

        Ok(absolute.to_string_lossy().to_string())
    }

    /// Finds the common prefix of a list of file system paths.
    ///
    /// This method takes a vector of strings representing file paths and determines
    /// their longest common prefix. If the input vector is empty or there are no
    /// common components in the paths, it returns `None`. Otherwise, it returns
    /// the common prefix as a `String`.
    ///
    /// # Arguments
    ///  
    ///  - `paths`: A vector of strings representing the file system paths to compare.
    ///  
    ///  # Returns
    ///  
    ///  - `Some(String)`: The common prefix path as a string, if found.
    ///  - `None`: If the input vector is empty or there is no common prefix.
    ///  
    ///  # Examples
    ///  
    ///  ```
    ///  use std::path::PathBuf;
    ///  
    ///  let paths = vec![
    ///      "/home/user/docs".to_string(),
    ///      "/home/user/downloads".to_string(),
    ///      "/home/user/pictures".to_string(),
    ///  ];
    ///   
    ///  let common = some_instance.common_prefix(paths);
    ///  assert_eq!(common, Some("/home/user".to_string()));
    ///      
    ///  let no_common = some_instance.common_prefix(vec![
    ///      "/var/log".to_string(),
    ///      "/home/user".to_string(),
    ///  ]);
    ///  assert_eq!(no_common, None);
    ///  ```
    ///
    /// # Note
    ///
    /// This function internally uses `PathBuf` and `Path` to parse, manage, and compare
    /// path components in a platform-agnostic way, and ensures proper handling of path
    /// separators and other conventions.
    pub fn common_prefix(&self, paths: Vec<String>) -> Option<String> {
        if paths.is_empty() {
            return None;
        }

        let path_bufs: Vec<PathBuf> = paths.iter().map(|p| PathBuf::from(p)).collect();
        let first_components: Vec<_> = path_bufs[0].components().collect();

        let mut common_len = 0;
        for i in 0..first_components.len() {
            if path_bufs
                .iter()
                .all(|p| p.components().nth(i) == Some(first_components[i]))
            {
                common_len = i + 1;
            } else {
                break;
            }
        }

        if common_len == 0 {
            return None;
        }

        let mut result = PathBuf::new();
        for component in first_components.iter().take(common_len) {
            result.push(component);
        }

        Some(result.to_string_lossy().to_string())
    }
}
