//! File hashing utilities for integrity verification.
//!
//! This module provides SHA256 hashing functionality with:
//! - Chunked reading for memory efficiency
//! - Parallel batch hashing with Rayon
//! - Bounded result caching, with independent [`FileHashScope`] stores for
//!   callers that must not share entries or statistics
//! - Comprehensive error handling
//!
//! ## Performance
//! - 3-5x faster than Python hashlib implementation
//! - Parallel batch operations scale linearly with CPU cores
//! - Optimized 64KB chunk size for I/O throughput
//!
//! ## Example
//! ```rust,no_run
//! use classic_file_io_core::hash::FileHasher;
//! use std::path::Path;
//!
//! # fn main() -> Result<(), Box<dyn std::error::Error>> {
//! // Single file hash
//! let hash = FileHasher::hash_file(Path::new("game.exe"))?;
//! println!("SHA256: {}", hash);
//!
//! // Batch parallel hashing
//! let files = vec![
//!     Path::new("file1.bin"),
//!     Path::new("file2.bin"),
//!     Path::new("file3.bin"),
//! ];
//! let hashes = FileHasher::hash_files_parallel(&files)?;
//! # Ok(())
//! # }
//! ```

use crate::error::FileIOError;
use quick_cache::sync::Cache;
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use std::fmt;
use std::fmt::Write as _;
use std::fs::File;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock};
use tracing::{debug, warn};

/// Optimal chunk size for reading files during hashing (64KB).
/// This balances memory usage with I/O throughput.
const HASH_CHUNK_SIZE: usize = 64 * 1024;

/// Maximum number of cached hashes per scope.
const HASH_CACHE_CAPACITY: usize = 1024;

/// One hash-cache store: bounded entries plus its own hit/miss counters.
struct FileHashStore {
    /// Cached hashes keyed by the path the caller passed.
    /// Uses bounded `quick_cache` eviction to prevent unbounded growth.
    entries: Cache<PathBuf, String>,
    /// Hash cache hits since this store's last counter reset.
    hits: AtomicU64,
    /// Hash cache misses since this store's last counter reset.
    misses: AtomicU64,
}

impl FileHashStore {
    fn new() -> Self {
        Self {
            entries: Cache::new(HASH_CACHE_CAPACITY),
            hits: AtomicU64::new(0),
            misses: AtomicU64::new(0),
        }
    }
}

/// Process default hash-cache scope used by the unscoped [`FileHasher`]
/// functions.
static DEFAULT_SCOPE: LazyLock<FileHashScope> = LazyLock::new(FileHashScope::new_isolated);

/// Opaque handle to one file-hash cache store and its statistics.
///
/// Cloning a handle shares the same store; two handles compare equal exactly
/// when they name the same store. [`FileHashScope::default_scope`] is the
/// store behind the unscoped [`FileHasher`] functions.
/// [`FileHashScope::new_isolated`] creates a fresh, empty store with the same
/// capacity, eviction, counter, and clear rules that shares no entries or
/// counters with any other scope. Each method behaves exactly like the
/// [`FileHasher`] function of the same name, applied to this scope's store.
///
/// Handles are `Send + Sync + 'static`, so an adapter can move one into
/// parallel or async work and the work keeps naming the same store.
///
/// # Example
///
/// ```rust
/// use classic_file_io_core::hash::{FileHashScope, FileHasher};
///
/// let scope = FileHashScope::new_isolated();
/// assert_ne!(scope, FileHashScope::default_scope());
/// assert_eq!(scope.cache_stats().size, 0);
/// assert_eq!(scope.cache_stats().capacity, FileHasher::cache_stats().capacity);
/// ```
#[derive(Clone)]
pub struct FileHashScope {
    store: Arc<FileHashStore>,
}

impl FileHashScope {
    /// Return a handle to the process default scope used by the unscoped
    /// [`FileHasher`] functions.
    #[must_use]
    pub fn default_scope() -> Self {
        DEFAULT_SCOPE.clone()
    }

    /// Create a new, empty scope that shares no entries or counters with any
    /// other scope, including the default one.
    #[must_use]
    pub fn new_isolated() -> Self {
        Self {
            store: Arc::new(FileHashStore::new()),
        }
    }

    /// Calculate the SHA256 hash of a file through this scope's cache.
    ///
    /// A cached path counts as a hit; anything else, including a failed hash,
    /// counts as a miss. Only successful hashes are cached. See
    /// [`FileHasher::hash_file`].
    ///
    /// # Errors
    /// Returns [`FileIOError`] when the path does not exist, is not a file, or
    /// cannot be read.
    pub fn hash_file(&self, path: &Path) -> Result<String, FileIOError> {
        // Check cache first
        if let Some(cached_hash) = self.store.entries.get(path) {
            self.store.hits.fetch_add(1, Ordering::Relaxed);
            debug!("Cache hit for hash: {}", path.display());
            return Ok(cached_hash);
        }

        self.store.misses.fetch_add(1, Ordering::Relaxed);

        let hash = FileHasher::hash_file_uncached(path)?;

        // Cache result
        self.store.entries.insert(path.to_path_buf(), hash.clone());
        debug!("Cached hash for: {}", path.display());

        Ok(hash)
    }

    /// Hash several files in parallel through this scope's cache, keeping a
    /// `None` for each file that fails. See [`FileHasher::hash_files_parallel`].
    ///
    /// # Errors
    /// Currently infallible; per-file failures are reported as `None`.
    pub fn hash_files_parallel(
        &self,
        paths: &[&Path],
    ) -> Result<Vec<(PathBuf, Option<String>)>, FileIOError> {
        let results: Vec<(PathBuf, Option<String>)> = paths
            .par_iter()
            .map(|&path| {
                let path_buf = path.to_path_buf();
                match self.hash_file(path) {
                    Ok(hash) => (path_buf, Some(hash)),
                    Err(e) => {
                        warn!("Failed to hash {}: {}", path.display(), e);
                        (path_buf, None)
                    }
                }
            })
            .collect();

        Ok(results)
    }

    /// Hash several files through this scope's cache and return only the
    /// successful results. See [`FileHasher::hash_files_to_map`].
    ///
    /// # Errors
    /// Currently infallible; failed files are omitted from the map.
    pub fn hash_files_to_map(
        &self,
        paths: &[&Path],
    ) -> Result<std::collections::HashMap<PathBuf, String>, FileIOError> {
        let results = self.hash_files_parallel(paths)?;
        let map = results
            .into_iter()
            .filter_map(|(path, hash_opt)| hash_opt.map(|hash| (path, hash)))
            .collect();
        Ok(map)
    }

    /// Evict every cached hash in this scope without resetting its counters.
    /// Other scopes are unaffected. See [`FileHasher::clear_cache`].
    pub fn clear_cache(&self) {
        self.store.entries.clear();
        debug!("Hash cache cleared");
    }

    /// Return this scope's hit/miss counters, entry count, and capacity.
    /// See [`FileHasher::cache_stats`].
    #[must_use]
    pub fn cache_stats(&self) -> CacheStats {
        let hits = self.store.hits.load(Ordering::Relaxed);
        let misses = self.store.misses.load(Ordering::Relaxed);
        let total = hits + misses;

        CacheStats {
            hits,
            misses,
            hit_rate: if total > 0 {
                hits as f64 / total as f64
            } else {
                0.0
            },
            size: self.store.entries.len(),
            capacity: self.store.entries.capacity() as usize,
        }
    }

    /// Reset this scope's hit and miss counters without evicting entries.
    /// See [`FileHasher::reset_cache_stats`].
    pub fn reset_cache_stats(&self) {
        self.store.hits.store(0, Ordering::Relaxed);
        self.store.misses.store(0, Ordering::Relaxed);
    }

    /// Return the number of hashes currently cached in this scope.
    /// See [`FileHasher::cache_size`].
    #[must_use]
    pub fn cache_size(&self) -> usize {
        self.store.entries.len()
    }
}

impl PartialEq for FileHashScope {
    /// Two handles are equal when they name the same store.
    fn eq(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.store, &other.store)
    }
}

impl Eq for FileHashScope {}

impl fmt::Debug for FileHashScope {
    // Report identity and occupancy only; dumping every cached path would be
    // noisy in logs.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("FileHashScope")
            .field("is_default", &(*self == *DEFAULT_SCOPE))
            .field("size", &self.store.entries.len())
            .finish()
    }
}

/// Hash cache performance statistics.
#[derive(Debug, Clone)]
pub struct CacheStats {
    /// Number of cache hits since the last reset.
    pub hits: u64,
    /// Number of cache misses since the last reset.
    pub misses: u64,
    /// Hit rate as a fraction from 0.0 to 1.0.
    pub hit_rate: f64,
    /// Current number of cached entries.
    pub size: usize,
    /// Maximum configured cache capacity.
    pub capacity: usize,
}

/// File hashing utility for integrity verification.
///
/// Provides SHA256 hashing with caching and parallel batch operations. Every
/// associated function uses the process default [`FileHashScope`]; callers
/// that need their own cache contents and statistics hold a scope from
/// [`FileHashScope::new_isolated`] and call its same-named methods instead.
pub struct FileHasher;

impl FileHasher {
    /// Calculate SHA256 hash of a file with caching.
    ///
    /// This function reads the file in 64KB chunks for memory efficiency
    /// and caches results for repeated calculations.
    ///
    /// # Arguments
    /// * `path` - Path to the file to hash
    ///
    /// # Returns
    /// Lowercase hexadecimal SHA256 hash string (64 characters)
    ///
    /// # Errors
    /// Returns `FileIOError` if:
    /// - File does not exist
    /// - File cannot be read (permissions)
    /// - I/O error during reading
    ///
    /// # Example
    /// ```rust,no_run
    /// # use classic_file_io_core::hash::FileHasher;
    /// # use std::path::Path;
    /// let hash = FileHasher::hash_file(Path::new("data.bin"))?;
    /// assert_eq!(hash.len(), 64); // SHA256 is 256 bits = 64 hex chars
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn hash_file(path: &Path) -> Result<String, FileIOError> {
        DEFAULT_SCOPE.hash_file(path)
    }

    /// Calculate SHA256 for a file without mutating any scope's cache or stats.
    pub(crate) fn hash_file_uncached(path: &Path) -> Result<String, FileIOError> {
        Self::validate_hash_target(path)?;
        Self::calculate_sha256(path)
    }

    fn validate_hash_target(path: &Path) -> Result<(), FileIOError> {
        if !path.exists() {
            return Err(FileIOError::NotFound(path.display().to_string()));
        }

        if !path.is_file() {
            return Err(FileIOError::InvalidPath(format!(
                "Path is not a file: {}",
                path.display()
            )));
        }

        Ok(())
    }

    /// Calculate SHA256 hash without caching (internal implementation).
    ///
    /// Reads file in chunks to handle large files efficiently.
    fn calculate_sha256(path: &Path) -> Result<String, FileIOError> {
        // File::open and read errors automatically convert to IoError via #[from]
        let file = File::open(path)?;

        let mut reader = BufReader::with_capacity(HASH_CHUNK_SIZE, file);
        let mut hasher = Sha256::new();
        let mut buffer = vec![0u8; HASH_CHUNK_SIZE];

        loop {
            let bytes_read = reader.read(&mut buffer)?;

            if bytes_read == 0 {
                break;
            }

            hasher.update(&buffer[..bytes_read]);
        }

        let result = hasher.finalize();
        Ok(encode_hex(result.as_ref()))
    }

    /// Calculate SHA256 hashes for multiple files in parallel.
    ///
    /// Uses Rayon to parallelize hash calculations across available CPU cores.
    /// Files that fail to hash will log warnings but won't fail the entire batch.
    ///
    /// # Arguments
    /// * `paths` - Slice of file paths to hash
    ///
    /// # Returns
    /// Vector of `(PathBuf, Option<String>)` tuples where:
    /// - `PathBuf` is the input path
    /// - `Some(hash)` for successful calculations
    /// - `None` for files that failed to hash
    ///
    /// # Example
    /// ```rust,no_run
    /// # use classic_file_io_core::hash::FileHasher;
    /// # use std::path::Path;
    /// let files = vec![
    ///     Path::new("file1.bin"),
    ///     Path::new("file2.bin"),
    /// ];
    /// let results = FileHasher::hash_files_parallel(&files)?;
    ///
    /// for (path, hash_opt) in results {
    ///     match hash_opt {
    ///         Some(hash) => println!("{}: {}", path.display(), hash),
    ///         None => eprintln!("Failed to hash: {}", path.display()),
    ///     }
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn hash_files_parallel(
        paths: &[&Path],
    ) -> Result<Vec<(PathBuf, Option<String>)>, FileIOError> {
        DEFAULT_SCOPE.hash_files_parallel(paths)
    }

    /// Calculate hashes and return only successful results.
    ///
    /// This is a convenience wrapper around `hash_files_parallel` that
    /// filters out failures and returns a HashMap of successful hashes.
    ///
    /// # Arguments
    /// * `paths` - Slice of file paths to hash
    ///
    /// # Returns
    /// HashMap mapping file paths to their SHA256 hashes.
    /// Files that failed to hash are excluded.
    ///
    /// # Example
    /// ```rust,no_run
    /// # use classic_file_io_core::hash::FileHasher;
    /// # use std::path::Path;
    /// let files = vec![
    ///     Path::new("file1.bin"),
    ///     Path::new("file2.bin"),
    /// ];
    /// let hashes = FileHasher::hash_files_to_map(&files)?;
    ///
    /// for (path, hash) in hashes {
    ///     println!("{}: {}", path.display(), hash);
    /// }
    /// # Ok::<(), Box<dyn std::error::Error>>(())
    /// ```
    pub fn hash_files_to_map(
        paths: &[&Path],
    ) -> Result<std::collections::HashMap<PathBuf, String>, FileIOError> {
        DEFAULT_SCOPE.hash_files_to_map(paths)
    }

    /// Clear the default scope's hash cache.
    ///
    /// Useful for testing or when files are known to have changed.
    /// This clears cached hashes only; hit/miss counters remain available until
    /// `reset_cache_stats()` is called. Isolated scopes are unaffected.
    ///
    /// # Example
    /// ```rust
    /// # use classic_file_io_core::hash::FileHasher;
    /// FileHasher::clear_cache();
    /// ```
    pub fn clear_cache() {
        DEFAULT_SCOPE.clear_cache();
    }

    /// Return the default scope's canonical cache performance statistics.
    pub fn cache_stats() -> CacheStats {
        DEFAULT_SCOPE.cache_stats()
    }

    /// Reset only cache performance counters.
    ///
    /// This preserves cached hash entries so callers can clear observability
    /// independently from cache contents during tests and benchmarks.
    pub fn reset_cache_stats() {
        DEFAULT_SCOPE.reset_cache_stats();
    }

    /// Get the number of cached hashes.
    ///
    /// # Returns
    /// Number of hashes currently in cache
    ///
    /// # Example
    /// ```rust
    /// # use classic_file_io_core::hash::FileHasher;
    /// let count = FileHasher::cache_size();
    /// println!("Cached hashes: {}", count);
    /// ```
    pub fn cache_size() -> usize {
        DEFAULT_SCOPE.cache_size()
    }
}

fn encode_hex(bytes: &[u8]) -> String {
    let mut hex = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = write!(&mut hex, "{byte:02x}");
    }
    hex
}

#[cfg(test)]
#[path = "hash_tests.rs"]
mod tests;
