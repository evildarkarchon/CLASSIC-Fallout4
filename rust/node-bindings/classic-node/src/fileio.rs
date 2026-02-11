//! File I/O bindings (classic-file-io-core)
//!
//! Exposes file reading, writing, hashing, encoding detection, and backup management
//! to JavaScript/TypeScript. All business logic is delegated to `classic-file-io-core`.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer:
//! - Delegates all business logic to `classic-file-io-core`
//! - Only handles JavaScript <-> Rust type conversions
//! - Respects the ONE RUNTIME RULE via `classic_shared_core::get_runtime()`

use classic_file_io_core::FileIOCore;
use classic_file_io_core::backup::{BackupManager, BackupType};
use classic_file_io_core::encoding::EncodingDetector;
use classic_file_io_core::hash::FileHasher;
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Convert any Display error to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

// ============================================================================
// 1. JsFileIO class — wraps FileIOCore
// ============================================================================

/// High-performance file I/O manager with caching and encoding detection.
///
/// Wraps `classic-file-io-core::FileIOCore` with multi-level caching,
/// memory-mapped large-file reading, and automatic encoding detection.
#[napi(js_name = "JsFileIO")]
pub struct JsFileIO {
    inner: FileIOCore,
}

/// Optional configuration for JsFileIO constructor.
#[napi(object)]
pub struct FileIOConfig {
    /// Default text encoding (default: "utf-8")
    pub encoding: Option<String>,
    /// Cache size for read operations (default: 100)
    pub cache_size: Option<u32>,
    /// Maximum concurrent I/O operations (default: 50)
    pub max_concurrent_io: Option<u32>,
}

#[napi]
impl JsFileIO {
    /// Create a new JsFileIO instance.
    ///
    /// Accepts an optional configuration object. Unspecified fields use sensible defaults.
    ///
    /// ```ts
    /// const io = new JsFileIO();
    /// const io2 = new JsFileIO({ cacheSize: 200, maxConcurrentIo: 100 });
    /// ```
    #[napi(constructor)]
    pub fn new(config: Option<FileIOConfig>) -> Self {
        let (encoding, cache_size, max_concurrent_io) = match config {
            Some(cfg) => (
                cfg.encoding.unwrap_or_else(|| "utf-8".to_string()),
                cfg.cache_size.unwrap_or(100) as usize,
                cfg.max_concurrent_io.unwrap_or(50) as usize,
            ),
            None => ("utf-8".to_string(), 100, 50),
        };

        Self {
            inner: FileIOCore::new(&encoding, "ignore", cache_size, max_concurrent_io),
        }
    }

    // ---- Async file operations ----

    /// Read a file with automatic encoding detection.
    ///
    /// Returns the file contents as a string. Uses caching for repeated reads.
    #[napi]
    pub async fn read_file(&self, path: String) -> Result<String> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.read_file(Path::new(&path)).await })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Write string content to a file.
    ///
    /// Overwrites the file if it exists. Invalidates any cached content for this path.
    #[napi]
    pub async fn write_file(&self, path: String, content: String) -> Result<()> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.write_file(Path::new(&path), &content).await })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Read a file and return its lines as an array of strings.
    #[napi]
    pub async fn read_lines(&self, path: String) -> Result<Vec<String>> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.read_lines(Path::new(&path)).await })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Write an array of strings as lines to a file.
    ///
    /// Lines are joined with newline characters and a trailing newline is appended.
    #[napi]
    pub async fn write_lines(&self, path: String, lines: Vec<String>) -> Result<()> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.write_lines(Path::new(&path), lines).await })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Read a file as raw bytes (Buffer).
    ///
    /// Useful for binary files -- no encoding detection is performed.
    #[napi]
    pub async fn read_bytes(&self, path: String) -> Result<Vec<u8>> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.read_bytes(Path::new(&path)).await })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Write raw bytes to a file.
    ///
    /// Parent directories are created automatically if they don't exist.
    #[napi]
    pub async fn write_bytes(&self, path: String, content: Vec<u8>) -> Result<()> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.write_bytes(Path::new(&path), content).await })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Append string content to a file.
    ///
    /// Creates the file (and parent directories) if they don't exist.
    #[napi]
    pub async fn append_file(&self, path: String, content: String) -> Result<()> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move { inner.append_file(Path::new(&path), &content).await })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Clear all internal caches (read cache, metadata cache, path cache, DDS cache).
    #[napi]
    pub async fn clear_cache(&self) -> Result<()> {
        let inner = self.inner.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move {
                inner.clear_cache().await;
                Ok::<(), classic_file_io_core::FileIOError>(())
            })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Read multiple files concurrently with controlled parallelism.
    ///
    /// Returns a Record mapping each path to its content string.
    /// Files that fail to read are mapped to empty strings (errors are logged).
    #[napi]
    pub async fn read_multiple_files(&self, paths: Vec<String>) -> Result<HashMap<String, String>> {
        let inner = self.inner.clone();
        let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let results = inner.read_multiple_files(path_bufs).await;
                let mut map = HashMap::new();
                for (path, result) in results {
                    let path_str = path.to_string_lossy().to_string();
                    match result {
                        Ok(content) => {
                            map.insert(path_str, content);
                        }
                        Err(_e) => {
                            map.insert(path_str, String::new());
                        }
                    }
                }
                Ok::<HashMap<String, String>, classic_file_io_core::FileIOError>(map)
            })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    /// Write multiple files concurrently with controlled parallelism.
    ///
    /// Accepts a Record mapping paths to content strings. Parent directories
    /// are created automatically.
    #[napi]
    pub async fn write_multiple_files(&self, files: HashMap<String, String>) -> Result<()> {
        let inner = self.inner.clone();
        let file_pairs: Vec<(PathBuf, String)> = files
            .into_iter()
            .map(|(path, content)| (PathBuf::from(path), content))
            .collect();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let results = inner.write_multiple_files(file_pairs).await;
                for (_path, result) in results {
                    result?;
                }
                Ok::<(), classic_file_io_core::FileIOError>(())
            })
            .await
            .map_err(to_napi_err)?
            .map_err(to_napi_err)
    }

    // ---- Sync file operations ----

    /// Check if a file or directory exists at the given path.
    ///
    /// Uses a metadata cache for fast repeated lookups.
    #[napi]
    pub fn file_exists(&self, path: String) -> bool {
        self.inner.file_exists(Path::new(&path))
    }

    /// Get the size of a file in bytes.
    ///
    /// Returns `undefined` if the path is a directory or does not exist.
    #[napi]
    pub fn get_file_size(&self, path: String) -> Option<f64> {
        // Return as f64 because NAPI BigInt handling is complex and file sizes
        // up to 2^53 are safely representable as f64.
        self.inner.get_file_size(Path::new(&path)).map(|s| s as f64)
    }

    /// Check if a path points to a directory.
    #[napi]
    pub fn is_directory(&self, path: String) -> bool {
        self.inner.is_directory(Path::new(&path))
    }

    /// Recursively walk a directory and return paths matching an optional regex pattern.
    ///
    /// @param root - Directory to walk
    /// @param pattern - Optional regex pattern to match file names (not full paths)
    /// @param maxDepth - Optional maximum recursion depth (undefined = unlimited)
    /// @returns Array of matching file path strings
    #[napi]
    pub fn walk_directory(
        &self,
        root: String,
        pattern: Option<String>,
        max_depth: Option<u32>,
    ) -> Result<Vec<String>> {
        let files = self
            .inner
            .walk_directory(
                Path::new(&root),
                pattern.as_deref(),
                max_depth.map(|d| d as usize),
            )
            .map_err(to_napi_err)?;

        Ok(files
            .into_iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect())
    }
}

// ============================================================================
// 2. Free functions — hashing, encoding detection
// ============================================================================

/// Calculate the SHA256 hash of a file.
///
/// Returns a lowercase hex string (64 characters). Results are cached.
#[napi]
pub fn hash_file(path: String) -> Result<String> {
    FileHasher::hash_file(Path::new(&path)).map_err(to_napi_err)
}

/// Calculate SHA256 hashes for multiple files in parallel.
///
/// Returns a Record mapping each path to its hash string.
/// Files that fail to hash are mapped to empty strings.
#[napi]
pub fn hash_files_parallel(paths: Vec<String>) -> Result<HashMap<String, String>> {
    let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
    let path_refs: Vec<&Path> = path_bufs.iter().map(|p| p.as_path()).collect();

    let results = FileHasher::hash_files_parallel(&path_refs).map_err(to_napi_err)?;

    let mut map = HashMap::new();
    for (path_buf, hash_opt) in results {
        let key = path_buf.to_string_lossy().to_string();
        map.insert(key, hash_opt.unwrap_or_default());
    }
    Ok(map)
}

/// Detect the encoding of a file by reading its content.
///
/// Returns the encoding name (e.g. "UTF-8", "windows-1252").
#[napi]
pub fn detect_encoding(path: String) -> Result<String> {
    let bytes = std::fs::read(Path::new(&path)).map_err(to_napi_err)?;
    let detector = EncodingDetector::new();
    Ok(detector.detect_name(&bytes))
}

// ============================================================================
// 3. JsBackupManager class — wraps BackupManager
// ============================================================================

/// Convert a backup type string to the enum.
fn parse_backup_type(s: &str) -> Result<BackupType> {
    match s.to_ascii_lowercase().as_str() {
        "xse" => Ok(BackupType::XSE),
        "reshade" => Ok(BackupType::ReShade),
        "vulkan" => Ok(BackupType::Vulkan),
        "enb" => Ok(BackupType::ENB),
        _ => Err(napi::Error::from_reason(format!(
            "Unknown backup type: {s}. Valid types: xse, reshade, vulkan, enb"
        ))),
    }
}

/// Backup information returned from backup operations.
#[napi(object)]
pub struct JsBackupInfo {
    /// Backup type name
    pub backup_type: String,
    /// Backup directory path
    pub backup_dir: String,
    /// Number of files in the backup
    pub file_count: u32,
    /// Whether the backup exists on disk
    pub exists: bool,
}

/// Backup manager for game mod files (XSE, ReShade, Vulkan, ENB).
///
/// Creates and restores backups of game modification files.
#[napi]
pub struct JsBackupManager {
    /// Store the game root path separately since BackupManager.game_root is private.
    game_root: String,
}

#[napi]
impl JsBackupManager {
    /// Create a new backup manager for the specified game root directory.
    ///
    /// Backups are stored in `<gameRoot>/CLASSIC_Backups/` by default.
    #[napi(constructor)]
    pub fn new(game_root: String) -> Self {
        Self { game_root }
    }

    /// Create a backup of the specified type.
    ///
    /// @param backupType - One of: "xse", "reshade", "vulkan", "enb"
    /// @returns Backup information including file count
    #[napi]
    pub async fn create_backup(&self, backup_type: String) -> Result<JsBackupInfo> {
        let bt = parse_backup_type(&backup_type)?;
        let game_root = self.game_root.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let manager = BackupManager::new(PathBuf::from(&game_root), None);
                let info = manager.create_backup(bt).await.map_err(to_napi_err)?;
                Ok(JsBackupInfo {
                    backup_type: info.backup_type.display_name().to_string(),
                    backup_dir: info.backup_dir.to_string_lossy().to_string(),
                    file_count: info.file_count as u32,
                    exists: info.exists,
                })
            })
            .await
            .map_err(to_napi_err)?
    }

    /// Restore a backup of the specified type.
    ///
    /// @param backupType - One of: "xse", "reshade", "vulkan", "enb"
    /// @returns Number of files restored
    #[napi]
    pub async fn restore_backup(&self, backup_type: String) -> Result<u32> {
        let bt = parse_backup_type(&backup_type)?;
        let game_root = self.game_root.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let manager = BackupManager::new(PathBuf::from(&game_root), None);
                let count = manager.restore_backup(bt).await.map_err(to_napi_err)?;
                Ok(count as u32)
            })
            .await
            .map_err(to_napi_err)?
    }

    /// Check if a backup of the specified type exists.
    ///
    /// @param backupType - One of: "xse", "reshade", "vulkan", "enb"
    #[napi]
    pub async fn backup_exists(&self, backup_type: String) -> Result<bool> {
        let bt = parse_backup_type(&backup_type)?;
        let game_root = self.game_root.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let manager = BackupManager::new(PathBuf::from(&game_root), None);
                manager.backup_exists(bt).await.map_err(to_napi_err)
            })
            .await
            .map_err(to_napi_err)?
    }
}
