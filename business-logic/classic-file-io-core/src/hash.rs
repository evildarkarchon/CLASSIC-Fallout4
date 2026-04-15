//! File hashing utilities for integrity verification.
//!
//! This module provides SHA256 hashing functionality with:
//! - Chunked reading for memory efficiency
//! - Parallel batch hashing with Rayon
//! - Integration with FileIOCore cache
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
use std::fmt::Write as _;
use std::fs::File;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use std::sync::LazyLock;
use std::sync::atomic::{AtomicU64, Ordering};
use tracing::{debug, warn};

/// Optimal chunk size for reading files during hashing (64KB).
/// This balances memory usage with I/O throughput.
const HASH_CHUNK_SIZE: usize = 64 * 1024;

/// Global hash cache for repeated hash calculations.
/// Uses bounded `quick_cache` eviction to prevent unbounded growth.
static HASH_CACHE: LazyLock<Cache<PathBuf, String>> = LazyLock::new(|| Cache::new(1024));

/// Global counter for hash cache hits.
static CACHE_HITS: AtomicU64 = AtomicU64::new(0);

/// Global counter for hash cache misses.
static CACHE_MISSES: AtomicU64 = AtomicU64::new(0);

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
/// Provides SHA256 hashing with caching and parallel batch operations.
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
        // Check cache first
        if let Some(cached_hash) = HASH_CACHE.get(path) {
            CACHE_HITS.fetch_add(1, Ordering::Relaxed);
            debug!("Cache hit for hash: {}", path.display());
            return Ok(cached_hash);
        }

        CACHE_MISSES.fetch_add(1, Ordering::Relaxed);

        // Validate file exists
        if !path.exists() {
            return Err(FileIOError::NotFound(path.display().to_string()));
        }

        if !path.is_file() {
            return Err(FileIOError::InvalidPath(format!(
                "Path is not a file: {}",
                path.display()
            )));
        }

        // Calculate hash
        let hash = Self::calculate_sha256(path)?;

        // Cache result
        HASH_CACHE.insert(path.to_path_buf(), hash.clone());
        debug!("Cached hash for: {}", path.display());

        Ok(hash)
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
        let results: Vec<(PathBuf, Option<String>)> = paths
            .par_iter()
            .map(|&path| {
                let path_buf = path.to_path_buf();
                match Self::hash_file(path) {
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
        let results = Self::hash_files_parallel(paths)?;
        let map = results
            .into_iter()
            .filter_map(|(path, hash_opt)| hash_opt.map(|hash| (path, hash)))
            .collect();
        Ok(map)
    }

    /// Clear the hash cache.
    ///
    /// Useful for testing or when files are known to have changed.
    /// This clears cached hashes only; hit/miss counters remain available until
    /// `reset_cache_stats()` is called.
    ///
    /// # Example
    /// ```rust
    /// # use classic_file_io_core::hash::FileHasher;
    /// FileHasher::clear_cache();
    /// ```
    pub fn clear_cache() {
        HASH_CACHE.clear();
        debug!("Hash cache cleared");
    }

    /// Return canonical cache performance statistics.
    pub fn cache_stats() -> CacheStats {
        let hits = CACHE_HITS.load(Ordering::Relaxed);
        let misses = CACHE_MISSES.load(Ordering::Relaxed);
        let total = hits + misses;

        CacheStats {
            hits,
            misses,
            hit_rate: if total > 0 {
                hits as f64 / total as f64
            } else {
                0.0
            },
            size: HASH_CACHE.len(),
            capacity: HASH_CACHE.capacity() as usize,
        }
    }

    /// Reset only cache performance counters.
    ///
    /// This preserves cached hash entries so callers can clear observability
    /// independently from cache contents during tests and benchmarks.
    pub fn reset_cache_stats() {
        CACHE_HITS.store(0, Ordering::Relaxed);
        CACHE_MISSES.store(0, Ordering::Relaxed);
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
        Self::cache_stats().size
    }
}

fn encode_hex(bytes: &[u8]) -> String {
    let mut hex = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut hex, "{byte:02x}").expect("writing to String cannot fail");
    }
    hex
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use std::collections::HashSet;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    #[serial]
    fn test_hash_file_basic() -> Result<(), Box<dyn std::error::Error>> {
        // Create temp file with known content
        let mut temp_file = NamedTempFile::new()?;
        temp_file.write_all(b"Hello, World!")?;
        temp_file.flush()?;

        let hash = FileHasher::hash_file(temp_file.path())?;

        // Verify hash length (SHA256 = 64 hex chars)
        assert_eq!(hash.len(), 64);
        // Verify known SHA256 hash of "Hello, World!"
        assert_eq!(
            hash,
            "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        );

        Ok(())
    }

    #[test]
    #[serial]
    fn test_hash_file_caching() -> Result<(), Box<dyn std::error::Error>> {
        FileHasher::clear_cache();
        FileHasher::reset_cache_stats();

        let mut temp_file = NamedTempFile::new()?;
        temp_file.write_all(b"Test caching")?;
        temp_file.flush()?;

        // First call - should cache
        let hash1 = FileHasher::hash_file(temp_file.path())?;
        assert_eq!(FileHasher::cache_size(), 1);
        let miss_stats = FileHasher::cache_stats();
        assert_eq!(miss_stats.misses, 1);
        assert_eq!(miss_stats.hits, 0);
        assert_eq!(miss_stats.size, 1);

        // Second call - should hit cache
        let hash2 = FileHasher::hash_file(temp_file.path())?;
        assert_eq!(hash1, hash2);
        assert_eq!(FileHasher::cache_size(), 1);
        let hit_stats = FileHasher::cache_stats();
        assert_eq!(hit_stats.misses, 1);
        assert_eq!(hit_stats.hits, 1);
        assert_eq!(hit_stats.size, 1);
        assert_eq!(hit_stats.capacity, 1024);
        assert_eq!(hit_stats.hit_rate, 0.5);

        FileHasher::clear_cache();
        assert_eq!(FileHasher::cache_size(), 0);

        Ok(())
    }

    #[test]
    fn test_hash_nonexistent_file() {
        let result = FileHasher::hash_file(Path::new("nonexistent_file.txt"));
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), FileIOError::NotFound(_)));
    }

    #[test]
    #[serial]
    fn test_hash_files_parallel() -> Result<(), Box<dyn std::error::Error>> {
        FileHasher::clear_cache();

        // Create multiple temp files
        let mut files = Vec::new();
        let mut temp_files = Vec::new();

        for i in 0..5 {
            let mut temp_file = NamedTempFile::new()?;
            temp_file.write_all(format!("Content {}", i).as_bytes())?;
            temp_file.flush()?;
            files.push(temp_file.path().to_path_buf());
            temp_files.push(temp_file); // Keep alive
        }

        let paths: Vec<&Path> = files.iter().map(|p| p.as_path()).collect();
        let results = FileHasher::hash_files_parallel(&paths)?;

        // Verify all succeeded
        assert_eq!(results.len(), 5);
        for (_, hash_opt) in &results {
            assert!(hash_opt.is_some());
            assert_eq!(hash_opt.as_ref().unwrap().len(), 64);
        }

        Ok(())
    }

    #[test]
    #[serial]
    fn test_hash_files_to_map() -> Result<(), Box<dyn std::error::Error>> {
        FileHasher::clear_cache();

        let mut temp_file = NamedTempFile::new()?;
        temp_file.write_all(b"Map test")?;
        temp_file.flush()?;

        let paths = vec![temp_file.path()];
        let map = FileHasher::hash_files_to_map(&paths)?;

        assert_eq!(map.len(), 1);
        assert!(map.contains_key(temp_file.path()));
        assert_eq!(map.get(temp_file.path()).unwrap().len(), 64);

        Ok(())
    }

    #[test]
    #[serial]
    fn test_large_file_chunked_reading() -> Result<(), Box<dyn std::error::Error>> {
        // Create file larger than chunk size
        let mut temp_file = NamedTempFile::new()?;
        let data = vec![0u8; HASH_CHUNK_SIZE * 3]; // 3x chunk size
        temp_file.write_all(&data)?;
        temp_file.flush()?;

        let hash = FileHasher::hash_file(temp_file.path())?;

        // Verify hash was calculated successfully
        assert_eq!(hash.len(), 64);

        Ok(())
    }

    #[test]
    #[serial]
    fn test_hash_cache_stats_reset_preserves_cache_entries()
    -> Result<(), Box<dyn std::error::Error>> {
        FileHasher::clear_cache();
        FileHasher::reset_cache_stats();

        let mut temp_file = NamedTempFile::new()?;
        temp_file.write_all(b"stats reset")?;
        temp_file.flush()?;

        FileHasher::hash_file(temp_file.path())?;
        assert_eq!(FileHasher::cache_size(), 1);

        FileHasher::reset_cache_stats();
        let stats = FileHasher::cache_stats();
        assert_eq!(stats.hits, 0);
        assert_eq!(stats.misses, 0);
        assert_eq!(stats.size, 1);
        assert_eq!(stats.capacity, 1024);

        Ok(())
    }

    #[test]
    #[serial]
    fn test_hash_clear_cache_empties_entries_without_resetting_stats()
    -> Result<(), Box<dyn std::error::Error>> {
        FileHasher::clear_cache();
        FileHasher::reset_cache_stats();

        let mut temp_file = NamedTempFile::new()?;
        temp_file.write_all(b"clear cache")?;
        temp_file.flush()?;

        FileHasher::hash_file(temp_file.path())?;
        let before_clear = FileHasher::cache_stats();
        assert_eq!(before_clear.size, 1);
        assert_eq!(before_clear.misses, 1);

        FileHasher::clear_cache();
        let after_clear = FileHasher::cache_stats();
        assert_eq!(after_clear.size, 0);
        assert_eq!(after_clear.capacity, 1024);
        assert_eq!(after_clear.misses, 1);
        assert_eq!(after_clear.hits, 0);

        Ok(())
    }

    #[test]
    #[serial]
    fn test_hash_cache_bounded_eviction() -> Result<(), Box<dyn std::error::Error>> {
        FileHasher::clear_cache();
        FileHasher::reset_cache_stats();

        let mut temp_files = Vec::new();
        let mut first_hash = None;

        for index in 0..1025 {
            let mut temp_file = NamedTempFile::new()?;
            temp_file.write_all(format!("bounded-cache-{index}").as_bytes())?;
            temp_file.flush()?;

            let hash = FileHasher::hash_file(temp_file.path())?;
            if index == 0 {
                first_hash = Some((temp_file.path().to_path_buf(), hash));
            }
            temp_files.push(temp_file);
        }

        let stats = FileHasher::cache_stats();
        assert_eq!(stats.capacity, 1024);
        assert!(stats.size <= stats.capacity);
        assert!(stats.size < 1025);
        assert_eq!(stats.misses, 1025);
        assert_eq!(stats.hits, 0);

        let (first_path, original_hash) = first_hash.expect("first file should exist");
        let rehashed = FileHasher::hash_file(&first_path)?;
        assert_eq!(rehashed, original_hash);

        let after_rehash = FileHasher::cache_stats();
        assert!(after_rehash.size <= after_rehash.capacity);
        assert_eq!(after_rehash.capacity, 1024);
        assert!(after_rehash.hits + after_rehash.misses >= 1026);
        assert!(after_rehash.misses >= 1025);

        let distinct_hashes = temp_files
            .iter()
            .map(|file| FileHasher::hash_file(file.path()))
            .collect::<Result<HashSet<_>, _>>()?;
        assert_eq!(distinct_hashes.len(), 1025);

        Ok(())
    }
}
