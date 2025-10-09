//! Core file I/O implementation with async support (Pure Rust)
//!
//! This module provides high-performance file I/O operations with:
//! - Async file operations with Tokio
//! - Memory-mapped file support for large files
//! - Parallel directory traversal
//! - DDS header parsing
//! - Multi-level caching
//! - Encoding detection

use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::num::NonZeroUsize;
use tokio::fs;
use tokio::sync::{RwLock, Semaphore};
use tokio::io::AsyncWriteExt;
use lru::LruCache;
use dashmap::DashMap;
use memmap2::Mmap;
use rayon::prelude::*;
use walkdir::WalkDir;
use std::fs::File;
use std::io::Read;

use super::encoding::EncodingDetector;
use super::dds::DDSHeader;
use super::error::FileIOError;

/// File metadata cache entry
#[derive(Clone, Debug)]
struct FileMetadata {
    size: u64,
    is_file: bool,
    is_dir: bool,
}

/// High-performance file I/O core with caching and encoding detection
pub struct FileIOCore {
    encoding_detector: Arc<EncodingDetector>,
    // Multi-level caching
    read_cache: Arc<RwLock<LruCache<PathBuf, String>>>,
    path_cache: Arc<DashMap<String, PathBuf>>,
    metadata_cache: Arc<DashMap<PathBuf, FileMetadata>>,
    dds_cache: Arc<RwLock<LruCache<PathBuf, DDSHeader>>>,
    // Concurrency control
    io_semaphore: Arc<Semaphore>,
    // Configuration
    default_encoding: String,
    default_errors: String,
}

impl FileIOCore {
    /// Create a new FileIOCore instance
    pub fn new(
        encoding: &str,
        errors: &str,
        cache_size: usize,
        max_concurrent_io: usize
    ) -> Self {
        let cache_size = NonZeroUsize::new(cache_size.max(1)).unwrap();
        let dds_cache_size = NonZeroUsize::new(1000).unwrap();

        Self {
            encoding_detector: Arc::new(EncodingDetector::new()),
            read_cache: Arc::new(RwLock::new(LruCache::new(cache_size))),
            path_cache: Arc::new(DashMap::new()),
            metadata_cache: Arc::new(DashMap::new()),
            dds_cache: Arc::new(RwLock::new(LruCache::new(dds_cache_size))),
            io_semaphore: Arc::new(Semaphore::new(max_concurrent_io)),
            default_encoding: encoding.to_string(),
            default_errors: errors.to_string(),
        }
    }

    /// Read a file with encoding detection
    pub async fn read_file(&self, path: &Path) -> Result<String, FileIOError> {
        // Check cache first
        {
            let mut cache_guard = self.read_cache.write().await;
            if let Some(cached) = cache_guard.get(path) {
                return Ok(cached.clone());
            }
        }

        // Read file with encoding detection
        let content = self.read_file_with_encoding(path).await?;

        // Update cache
        {
            let mut cache_guard = self.read_cache.write().await;
            cache_guard.put(path.to_path_buf(), content.clone());
        }

        Ok(content)
    }

    /// Write a file
    pub async fn write_file(&self, path: &Path, content: &str) -> Result<(), FileIOError> {
        fs::write(path, content.as_bytes()).await?;
        Ok(())
    }

    /// Read file lines
    pub async fn read_lines(&self, path: &Path) -> Result<Vec<String>, FileIOError> {
        let content = self.read_file(path).await?;
        Ok(content.lines().map(|s| s.to_string()).collect())
    }

    /// Read file as bytes
    pub async fn read_bytes(&self, path: &Path) -> Result<Vec<u8>, FileIOError> {
        let bytes = fs::read(path).await?;
        Ok(bytes)
    }

    /// Write lines to file
    pub async fn write_lines(&self, path: &Path, lines: Vec<String>) -> Result<(), FileIOError> {
        let mut content = lines.join("\n");
        if !content.ends_with('\n') {
            content.push('\n');
        }
        self.write_file(path, &content).await
    }

    /// Write bytes to file
    pub async fn write_bytes(&self, path: &Path, content: Vec<u8>) -> Result<(), FileIOError> {
        // Ensure parent directory exists
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).await?;
        }
        fs::write(path, content).await?;
        Ok(())
    }

    /// Append content to file
    pub async fn append_file(&self, path: &Path, content: &str) -> Result<(), FileIOError> {
        // Ensure parent directory exists
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).await?;
        }

        let mut file = tokio::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .await?;

        file.write_all(content.as_bytes()).await?;
        Ok(())
    }

    /// Clear all caches
    pub async fn clear_cache(&self) {
        let mut read_guard = self.read_cache.write().await;
        read_guard.clear();
        let mut dds_guard = self.dds_cache.write().await;
        dds_guard.clear();
        self.path_cache.clear();
        self.metadata_cache.clear();
    }

    /// Check if file exists
    pub fn file_exists(&self, path: &Path) -> bool {
        path.exists()
    }

    /// Get file size in bytes
    pub fn get_file_size(&self, path: &Path) -> Option<u64> {
        std::fs::metadata(path).ok().map(|m| m.len())
    }

    /// Read DDS header
    pub async fn read_dds_header(&self, path: &Path) -> Result<Option<DDSHeader>, FileIOError> {
        // Check cache first
        {
            let mut cache_guard = self.dds_cache.write().await;
            if let Some(cached) = cache_guard.get(path) {
                return Ok(Some(cached.clone()));
            }
        }

        // Read first 2KB for header analysis
        let mut file = File::open(path)?;
        let mut buffer = vec![0u8; 2048];
        let bytes_read = file.read(&mut buffer)?;
        buffer.truncate(bytes_read);

        let header = DDSHeader::from_bytes(&buffer)
            .map_err(|e| FileIOError::DDSError(e.to_string()))?;

        // Cache result if found
        if let Some(ref h) = header {
            let mut cache_guard = self.dds_cache.write().await;
            cache_guard.put(path.to_path_buf(), h.clone());
        }

        Ok(header)
    }

    /// Batch DDS header reading with parallel processing
    pub fn read_dds_headers_batch(&self, paths: Vec<PathBuf>) -> Vec<(PathBuf, Option<DDSHeader>)> {
        paths
            .into_par_iter()
            .map(|path| {
                let header = self.read_dds_header_sync(&path).ok().flatten();
                (path, header)
            })
            .collect()
    }

    /// Read file with memory mapping for large files
    pub async fn read_file_mmap(&self, path: &Path, encoding: Option<&str>) -> Result<String, FileIOError> {
        let file = File::open(path)?;
        let mmap = unsafe { Mmap::map(&file)? };

        let encoding_detector = self.encoding_detector.clone();
        let detected_encoding = encoding_detector.detect(&mmap);
        let encoding_name = encoding.unwrap_or(detected_encoding.name());

        let (decoded, _, had_errors) = if encoding_name == "UTF-8" || encoding_name == "utf-8" {
            encoding_rs::UTF_8.decode(&mmap)
        } else {
            encoding_rs::WINDOWS_1252.decode(&mmap)
        };

        if had_errors && self.default_errors != "ignore" {
            return Err(FileIOError::EncodingError(
                format!("Encoding errors in file: {}", path.display())
            ));
        }

        Ok(decoded.to_string())
    }

    /// Walk directory and return matching files
    pub fn walk_directory(&self, path: &Path, pattern: Option<&str>, max_depth: Option<usize>) -> Result<Vec<PathBuf>, FileIOError> {
        let walker = if let Some(depth) = max_depth {
            WalkDir::new(path).max_depth(depth)
        } else {
            WalkDir::new(path)
        };

        // Compile regex pattern if provided
        let regex_pattern = if let Some(pat) = pattern {
            Some(regex::Regex::new(pat).map_err(|e| FileIOError::InvalidPath(format!("Invalid regex pattern: {}", e)))?)
        } else {
            None
        };

        let files: Vec<PathBuf> = walker
            .into_iter()
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().is_file())
            .filter(|e| {
                if let Some(ref regex) = regex_pattern {
                    e.path()
                        .file_name()
                        .and_then(|n| n.to_str())
                        .map(|n| regex.is_match(n))
                        .unwrap_or(false)
                } else {
                    true
                }
            })
            .map(|e| e.path().to_path_buf())
            .collect();

        Ok(files)
    }

    /// Ensure path is converted to PathBuf with caching
    pub fn ensure_path(&self, path: impl AsRef<str>) -> PathBuf {
        let path_str = path.as_ref();
        if let Some(cached) = self.path_cache.get(path_str) {
            return cached.clone();
        }
        let path_buf = PathBuf::from(path_str);
        self.path_cache.insert(path_str.to_string(), path_buf.clone());
        path_buf
    }

    /// Read multiple files in parallel with concurrency control
    pub async fn read_multiple_files(&self, paths: Vec<PathBuf>) -> Vec<(PathBuf, Result<String, FileIOError>)> {
        use futures::stream::{self, StreamExt};

        let semaphore = self.io_semaphore.clone();
        let results: Vec<_> = stream::iter(paths)
            .map(|path| {
                let semaphore = semaphore.clone();
                let self_clone = self.clone_refs();
                async move {
                    let _permit = semaphore.acquire().await.expect("semaphore closed");
                    let result = self_clone.read_file(&path).await;
                    (path, result)
                }
            })
            .buffer_unordered(10)
            .collect()
            .await;

        results
    }

    /// Write multiple files in parallel with concurrency control
    pub async fn write_multiple_files(&self, files: Vec<(PathBuf, String)>) -> Vec<(PathBuf, Result<(), FileIOError>)> {
        use futures::stream::{self, StreamExt};

        let semaphore = self.io_semaphore.clone();
        let results: Vec<_> = stream::iter(files)
            .map(|(path, content)| {
                let semaphore = semaphore.clone();
                async move {
                    let _permit = semaphore.acquire().await.expect("semaphore closed");

                    // Ensure parent directory exists
                    if let Some(parent) = path.parent() {
                        if let Err(e) = fs::create_dir_all(parent).await {
                            return (path, Err(e.into()));
                        }
                    }

                    let result = fs::write(&path, content.as_bytes()).await.map_err(|e| e.into());
                    (path, result)
                }
            })
            .buffer_unordered(10)
            .collect()
            .await;

        results
    }

    /// Helper to clone internal references for async operations
    fn clone_refs(&self) -> Self {
        Self {
            encoding_detector: self.encoding_detector.clone(),
            read_cache: self.read_cache.clone(),
            path_cache: self.path_cache.clone(),
            metadata_cache: self.metadata_cache.clone(),
            dds_cache: self.dds_cache.clone(),
            io_semaphore: self.io_semaphore.clone(),
            default_encoding: self.default_encoding.clone(),
            default_errors: self.default_errors.clone(),
        }
    }

    // Helper methods

    async fn read_file_with_encoding(&self, path: &Path) -> Result<String, FileIOError> {
        let bytes = fs::read(path).await?;
        let detected = self.encoding_detector.detect(&bytes);
        let (decoded, _, had_errors) = detected.decode(&bytes);

        if had_errors && self.default_errors != "ignore" {
            return Err(FileIOError::EncodingError(
                format!("Encoding errors in file: {}", path.display())
            ));
        }

        Ok(decoded.to_string())
    }

    fn read_dds_header_sync(&self, path: &Path) -> Result<Option<DDSHeader>, FileIOError> {
        let mut file = File::open(path)?;
        let mut buffer = vec![0u8; 2048];
        let bytes_read = file.read(&mut buffer)?;
        buffer.truncate(bytes_read);

        DDSHeader::from_bytes(&buffer)
            .map_err(|e| FileIOError::DDSError(e.to_string()))
    }
}

impl Default for FileIOCore {
    fn default() -> Self {
        Self::new("utf-8", "ignore", 100, 50)
    }
}
