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

use crate::runtime::spawn_result;
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
        spawn_result(
            async move { inner.read_file(Path::new(&path)).await },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Write string content to a file.
    ///
    /// Overwrites the file if it exists. Invalidates any cached content for this path.
    #[napi]
    pub async fn write_file(&self, path: String, content: String) -> Result<()> {
        let inner = self.inner.clone();
        spawn_result(
            async move { inner.write_file(Path::new(&path), &content).await },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Read a file and return its lines as an array of strings.
    #[napi]
    pub async fn read_lines(&self, path: String) -> Result<Vec<String>> {
        let inner = self.inner.clone();
        spawn_result(
            async move { inner.read_lines(Path::new(&path)).await },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Write an array of strings as lines to a file.
    ///
    /// Lines are joined with newline characters and a trailing newline is appended.
    #[napi]
    pub async fn write_lines(&self, path: String, lines: Vec<String>) -> Result<()> {
        let inner = self.inner.clone();
        spawn_result(
            async move { inner.write_lines(Path::new(&path), lines).await },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Read a file as raw bytes (Buffer).
    ///
    /// Useful for binary files -- no encoding detection is performed.
    #[napi]
    pub async fn read_bytes(&self, path: String) -> Result<Vec<u8>> {
        let inner = self.inner.clone();
        spawn_result(
            async move { inner.read_bytes(Path::new(&path)).await },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Write raw bytes to a file.
    ///
    /// Parent directories are created automatically if they don't exist.
    #[napi]
    pub async fn write_bytes(&self, path: String, content: Vec<u8>) -> Result<()> {
        let inner = self.inner.clone();
        spawn_result(
            async move { inner.write_bytes(Path::new(&path), content).await },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Append string content to a file.
    ///
    /// Creates the file (and parent directories) if they don't exist.
    #[napi]
    pub async fn append_file(&self, path: String, content: String) -> Result<()> {
        let inner = self.inner.clone();
        spawn_result(
            async move { inner.append_file(Path::new(&path), &content).await },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Clear all internal caches (read cache, metadata cache, path cache, DDS cache).
    #[napi]
    pub async fn clear_cache(&self) -> Result<()> {
        let inner = self.inner.clone();
        spawn_result(
            async move {
                inner.clear_cache().await;
                Ok::<(), classic_file_io_core::FileIOError>(())
            },
            to_napi_err,
            to_napi_err,
        )
        .await
    }

    /// Read multiple files concurrently with controlled parallelism.
    ///
    /// Returns a Record mapping each path to its content string.
    /// Files that fail to read are mapped to empty strings (errors are logged).
    #[napi]
    pub async fn read_multiple_files(&self, paths: Vec<String>) -> Result<HashMap<String, String>> {
        let inner = self.inner.clone();
        let path_bufs: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        spawn_result(
            async move {
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
            },
            to_napi_err,
            to_napi_err,
        )
        .await
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
        spawn_result(
            async move {
                let results = inner.write_multiple_files(file_pairs).await;
                for (_path, result) in results {
                    result?;
                }
                Ok::<(), classic_file_io_core::FileIOError>(())
            },
            to_napi_err,
            to_napi_err,
        )
        .await
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

/// Canonical hash cache performance statistics.
#[napi(object)]
pub struct HashCacheStats {
    /// Number of cache hits since last reset.
    pub hits: i64,
    /// Number of cache misses since last reset.
    pub misses: i64,
    /// Hit rate as a fraction (0.0 to 1.0).
    #[napi(js_name = "hit_rate")]
    pub hit_rate: f64,
    /// Current number of cached entries.
    pub size: u32,
    /// Maximum bounded cache capacity.
    pub capacity: u32,
}

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

/// Return canonical hash cache statistics.
#[napi]
pub fn get_hash_cache_stats() -> HashCacheStats {
    let stats = FileHasher::cache_stats();
    HashCacheStats {
        hits: stats.hits as i64,
        misses: stats.misses as i64,
        hit_rate: stats.hit_rate,
        size: stats.size as u32,
        capacity: stats.capacity as u32,
    }
}

/// Reset hash cache hit/miss counters without clearing cached entries.
#[napi]
pub fn reset_hash_cache_stats() {
    FileHasher::reset_cache_stats();
}

/// Clear all cached file hashes without resetting hit/miss counters.
#[napi]
pub fn clear_hash_cache() {
    FileHasher::clear_cache();
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
        spawn_result(
            async move {
                let manager = BackupManager::new(PathBuf::from(&game_root), None);
                let info = manager.create_backup(bt).await.map_err(to_napi_err)?;
                Ok(JsBackupInfo {
                    backup_type: info.backup_type.display_name().to_string(),
                    backup_dir: info.backup_dir.to_string_lossy().to_string(),
                    file_count: info.file_count as u32,
                    exists: info.exists,
                })
            },
            to_napi_err,
            |error| error,
        )
        .await
    }

    /// Restore a backup of the specified type.
    ///
    /// @param backupType - One of: "xse", "reshade", "vulkan", "enb"
    /// @returns Number of files restored
    #[napi]
    pub async fn restore_backup(&self, backup_type: String) -> Result<u32> {
        let bt = parse_backup_type(&backup_type)?;
        let game_root = self.game_root.clone();
        spawn_result(
            async move {
                let manager = BackupManager::new(PathBuf::from(&game_root), None);
                let count = manager.restore_backup(bt).await.map_err(to_napi_err)?;
                Ok(count as u32)
            },
            to_napi_err,
            |error| error,
        )
        .await
    }

    /// Check if a backup of the specified type exists.
    ///
    /// @param backupType - One of: "xse", "reshade", "vulkan", "enb"
    #[napi]
    pub async fn backup_exists(&self, backup_type: String) -> Result<bool> {
        let bt = parse_backup_type(&backup_type)?;
        let game_root = self.game_root.clone();
        spawn_result(
            async move {
                let manager = BackupManager::new(PathBuf::from(&game_root), None);
                manager.backup_exists(bt).await.map_err(to_napi_err)
            },
            to_napi_err,
            |error| error,
        )
        .await
    }
}

// ============================================================================
// 4. DDS Texture Analysis
// ============================================================================

/// Parse a game target string to the core enum.
fn parse_game_target(s: &str) -> Result<classic_file_io_core::dds::GameTarget> {
    match s {
        "Fallout4" => Ok(classic_file_io_core::dds::GameTarget::Fallout4),
        "SkyrimSE" | "SkyrimSe" => Ok(classic_file_io_core::dds::GameTarget::SkyrimSE),
        _ => Err(napi::Error::from_reason(format!(
            "Unknown game target: {s}. Valid: Fallout4, SkyrimSE"
        ))),
    }
}

/// A single validation issue found in a DDS texture file.
#[napi(object)]
pub struct JsDDSIssue {
    /// Human-readable description of the issue.
    pub message: String,
}

/// DDS texture analyzer with game-specific validation rules.
///
/// Validates DDS texture files against game-specific requirements
/// (dimension limits, BC compression compatibility, mipmap recommendations).
#[napi]
pub struct JsDDSAnalyzer {
    inner: classic_file_io_core::dds::DDSAnalyzer,
}

#[napi]
impl JsDDSAnalyzer {
    /// Create a new DDS analyzer targeting a specific game.
    ///
    /// @param gameTarget - One of: "Fallout4", "SkyrimSE"
    #[napi(constructor)]
    pub fn new(game_target: String) -> Result<Self> {
        let target = parse_game_target(&game_target)?;
        Ok(Self {
            inner: classic_file_io_core::dds::DDSAnalyzer::new(target),
        })
    }

    /// Validate a single DDS file and return any issues found.
    ///
    /// An empty array means the file is valid. If the file cannot be read
    /// or parsed, returns a single "Unable to read DDS header" issue.
    ///
    /// @param path - Absolute path to the DDS file.
    /// @returns Array of validation issues.
    #[napi]
    pub fn validate_file(&self, path: String) -> Vec<JsDDSIssue> {
        self.inner
            .validate_file(Path::new(&path))
            .into_iter()
            .map(|issue| JsDDSIssue {
                message: issue.message,
            })
            .collect()
    }

    /// Validate multiple DDS files in parallel using Rayon.
    ///
    /// Returns an array of `[path, issues[]]` pairs for files that had issues.
    /// Files with no issues are omitted from the result.
    ///
    /// @param paths - Array of absolute paths to DDS files.
    /// @returns Array of `{ path, issues }` objects for files with issues.
    #[napi]
    pub fn validate_batch(&self, paths: Vec<String>) -> Vec<JsDdsBatchResult> {
        let path_bufs: Vec<PathBuf> = paths.into_iter().map(PathBuf::from).collect();
        self.inner
            .validate_batch(&path_bufs)
            .into_iter()
            .map(|(path, issues)| JsDdsBatchResult {
                path: path.to_string_lossy().to_string(),
                issues: issues
                    .into_iter()
                    .map(|i| JsDDSIssue { message: i.message })
                    .collect(),
            })
            .collect()
    }

    /// Validate DDS dimensions from width/height only (fallback for non-parseable files).
    ///
    /// Checks for even dimensions and reasonable size limits.
    ///
    /// @param width - Texture width in pixels.
    /// @param height - Texture height in pixels.
    /// @returns Array of validation issues.
    #[napi]
    pub fn validate_dimensions(width: u32, height: u32) -> Vec<JsDDSIssue> {
        classic_file_io_core::dds::DDSAnalyzer::validate_dimensions(width, height)
            .into_iter()
            .map(|issue| JsDDSIssue {
                message: issue.message,
            })
            .collect()
    }
}

/// Result from batch DDS validation for a single file.
#[napi(object)]
pub struct JsDdsBatchResult {
    /// Path to the DDS file that had issues.
    pub path: String,
    /// Validation issues found.
    pub issues: Vec<JsDDSIssue>,
}

// ============================================================================
// 5. File Similarity
// ============================================================================

/// Calculate the similarity ratio between two files.
///
/// Reads both files, splits into lines, and computes an LCS-based similarity ratio.
/// Returns a number between 0.0 (completely different) and 1.0 (identical).
///
/// @param path1 - Absolute path to the first file.
/// @param path2 - Absolute path to the second file.
/// @returns Similarity ratio (0.0 to 1.0).
#[napi]
pub fn calculate_file_similarity(path1: String, path2: String) -> Result<f64> {
    classic_file_io_core::similarity::calculate_similarity(Path::new(&path1), Path::new(&path2))
        .map_err(to_napi_err)
}

/// Calculate the similarity ratio between two text strings.
///
/// Computes an LCS-based similarity ratio between two in-memory strings.
/// Returns a number between 0.0 (completely different) and 1.0 (identical).
///
/// @param text1 - First text content.
/// @param text2 - Second text content.
/// @returns Similarity ratio (0.0 to 1.0).
#[napi]
pub fn calculate_text_similarity(text1: String, text2: String) -> f64 {
    classic_file_io_core::similarity::similarity_ratio(&text1, &text2)
}

// ============================================================================
// 6. Log Collection (path info only)
// ============================================================================

/// File pattern for standard crash log files.
#[napi]
pub const CRASH_LOG_PATTERN: &str = classic_file_io_core::CRASH_LOG_PATTERN;

/// File pattern for AUTOSCAN report files generated during crash analysis.
#[napi]
pub const CRASH_AUTOSCAN_PATTERN: &str = classic_file_io_core::CRASH_AUTOSCAN_PATTERN;

/// Log collector for organizing crash logs from multiple sources.
///
/// Provides path information for the crash logs directory structure.
/// For actual log collection (file moves/copies), use the async collect methods.
#[napi]
pub struct JsLogCollector {
    inner: classic_file_io_core::LogCollector,
    base_folder: String,
    xse_folder: Option<String>,
    custom_folder: Option<String>,
}

#[napi]
impl JsLogCollector {
    /// Create a new log collector with the specified base folder.
    ///
    /// @param baseFolder - Working directory where the "Crash Logs" folder will be created.
    /// @param xseFolder - Optional path to the game's XSE folder (e.g., My Games/Fallout4/F4SE).
    /// @param customFolder - Optional path to a custom scan directory.
    #[napi(constructor)]
    pub fn new(
        base_folder: String,
        xse_folder: Option<String>,
        custom_folder: Option<String>,
    ) -> Self {
        let base_path = PathBuf::from(&base_folder);
        let xse_path = xse_folder.clone().map(PathBuf::from);
        let custom_path = custom_folder.clone().map(PathBuf::from);

        Self {
            inner: classic_file_io_core::LogCollector::new(base_path, xse_path, custom_path),
            base_folder,
            xse_folder,
            custom_folder,
        }
    }

    /// Get the path to the Crash Logs directory.
    #[napi]
    pub fn crash_logs_dir(&self) -> String {
        self.inner.crash_logs_dir().to_string_lossy().to_string()
    }

    /// Get the path to the Pastebin subdirectory.
    #[napi]
    pub fn pastebin_dir(&self) -> String {
        self.inner.pastebin_dir().to_string_lossy().to_string()
    }

    /// Execute the full log collection workflow and return discovered crash log paths.
    #[napi]
    pub async fn collect_all(&self) -> Result<Vec<String>> {
        let collector = classic_file_io_core::LogCollector::new(
            PathBuf::from(&self.base_folder),
            self.xse_folder.clone().map(PathBuf::from),
            self.custom_folder.clone().map(PathBuf::from),
        );
        let handle = classic_shared_core::get_runtime().handle().clone();
        handle
            .spawn(async move {
                collector
                    .collect_all()
                    .await
                    .map(|paths| {
                        paths
                            .into_iter()
                            .map(|path| path.to_string_lossy().to_string())
                            .collect()
                    })
                    .map_err(to_napi_err)
            })
            .await
            .map_err(to_napi_err)?
    }
}

// ============================================================================
// 7. File Generation
// ============================================================================

/// File generator for CLASSIC configuration files (ignore file and local YAML).
#[napi]
pub struct JsFileGenerator {
    inner: classic_file_io_core::FileGenerator,
}

#[napi]
impl JsFileGenerator {
    /// Create a new file generator.
    ///
    /// @param ignoreFileContent - Default content for CLASSIC Ignore.yaml.
    /// @param localYamlContent - Default content for the local YAML file.
    /// @param gameName - Game name for local YAML path (e.g., "Fallout4").
    #[napi(constructor)]
    pub fn new(ignore_file_content: String, local_yaml_content: String, game_name: String) -> Self {
        Self {
            inner: classic_file_io_core::FileGenerator::new(
                classic_file_io_core::FileGeneratorConfig::new(
                    ignore_file_content,
                    local_yaml_content,
                    game_name,
                ),
            ),
        }
    }

    /// Get the path where the ignore file would be created.
    #[napi]
    pub fn ignore_file_path(&self) -> String {
        self.inner.ignore_file_path().to_string_lossy().to_string()
    }

    /// Get the path where the local YAML file would be created.
    #[napi]
    pub fn local_yaml_path(&self) -> String {
        self.inner.local_yaml_path().to_string_lossy().to_string()
    }
}

/// Generate a CLASSIC Ignore.yaml file if it does not already exist.
///
/// @param content - Default content to write.
/// @returns `true` if the file was generated, `false` if it already existed.
#[napi]
pub async fn generate_ignore_file(content: String) -> Result<bool> {
    let handle = classic_shared_core::get_runtime().handle().clone();
    handle
        .spawn(async move {
            classic_file_io_core::generate_ignore_file(content)
                .await
                .map_err(to_napi_err)
        })
        .await
        .map_err(to_napi_err)?
}

/// Generate a CLASSIC local YAML file if it does not already exist.
///
/// @param content - Default content to write.
/// @param gameName - Game name for the file path (e.g., "Fallout4").
/// @returns `true` if the file was generated, `false` if it already existed.
#[napi]
pub async fn generate_local_yaml(content: String, game_name: String) -> Result<bool> {
    let handle = classic_shared_core::get_runtime().handle().clone();
    handle
        .spawn(async move {
            classic_file_io_core::generate_local_yaml(content, game_name)
                .await
                .map_err(to_napi_err)
        })
        .await
        .map_err(to_napi_err)?
}

// ============================================================================
// 8. Game Files Manager
// ============================================================================

/// Result of a game file operation (backup, restore, or remove).
#[napi(object)]
pub struct JsFileOperationResult {
    /// The operation performed: "BACKUP", "RESTORE", or "REMOVE".
    pub operation: String,
    /// Label identifying the file group that was targeted.
    pub label: String,
    /// Number of files/directories successfully affected.
    pub files_affected: u32,
    /// Error messages for any failures encountered (non-fatal).
    pub errors: Vec<String>,
}

/// Game file manager for backup, restore, and remove operations.
///
/// Operates on a game root directory and a backup root directory, matching
/// files using case-insensitive substring patterns.
#[napi]
pub struct JsGameFilesManager {
    game_root: String,
    backup_root: String,
}

#[napi]
impl JsGameFilesManager {
    /// Create a new game files manager.
    ///
    /// @param gameRoot - Path to the game installation directory.
    /// @param backupRoot - Path to the backup root directory.
    #[napi(constructor)]
    pub fn new(game_root: String, backup_root: String) -> Self {
        Self {
            game_root,
            backup_root,
        }
    }

    /// Back up matching files from the game directory to a labeled backup subdirectory.
    ///
    /// @param label - A label for this backup group (used as subdirectory name).
    /// @param patterns - Case-insensitive substring patterns to match filenames.
    /// @returns Operation result with file count and any errors.
    #[napi]
    pub async fn backup(
        &self,
        label: String,
        patterns: Vec<String>,
    ) -> Result<JsFileOperationResult> {
        let game_root = self.game_root.clone();
        let backup_root = self.backup_root.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let manager = classic_file_io_core::GameFilesManager::new(
                    PathBuf::from(&game_root),
                    PathBuf::from(&backup_root),
                );
                let result = manager
                    .backup(&label, &patterns)
                    .await
                    .map_err(to_napi_err)?;
                Ok(JsFileOperationResult {
                    operation: result.operation.to_string(),
                    label: result.label,
                    files_affected: result.files_affected as u32,
                    errors: result.errors,
                })
            })
            .await
            .map_err(to_napi_err)?
    }

    /// Restore matching files from a labeled backup subdirectory back to the game directory.
    ///
    /// @param label - The backup group label (subdirectory name under backupRoot).
    /// @param patterns - Case-insensitive substring patterns to match filenames.
    /// @returns Operation result with file count and any errors.
    #[napi]
    pub async fn restore(
        &self,
        label: String,
        patterns: Vec<String>,
    ) -> Result<JsFileOperationResult> {
        let game_root = self.game_root.clone();
        let backup_root = self.backup_root.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let manager = classic_file_io_core::GameFilesManager::new(
                    PathBuf::from(&game_root),
                    PathBuf::from(&backup_root),
                );
                let result = manager
                    .restore(&label, &patterns)
                    .await
                    .map_err(to_napi_err)?;
                Ok(JsFileOperationResult {
                    operation: result.operation.to_string(),
                    label: result.label,
                    files_affected: result.files_affected as u32,
                    errors: result.errors,
                })
            })
            .await
            .map_err(to_napi_err)?
    }

    /// Remove matching files/directories from the game directory.
    ///
    /// @param label - A label identifying the file group (for result tracking).
    /// @param patterns - Case-insensitive substring patterns to match filenames.
    /// @returns Operation result with file count and any errors.
    #[napi]
    pub async fn remove(
        &self,
        label: String,
        patterns: Vec<String>,
    ) -> Result<JsFileOperationResult> {
        let game_root = self.game_root.clone();
        let backup_root = self.backup_root.clone();
        let handle = classic_shared_core::get_runtime().handle().clone();

        handle
            .spawn(async move {
                let manager = classic_file_io_core::GameFilesManager::new(
                    PathBuf::from(&game_root),
                    PathBuf::from(&backup_root),
                );
                let result = manager
                    .remove(&label, &patterns)
                    .await
                    .map_err(to_napi_err)?;
                Ok(JsFileOperationResult {
                    operation: result.operation.to_string(),
                    label: result.label,
                    files_affected: result.files_affected as u32,
                    errors: result.errors,
                })
            })
            .await
            .map_err(to_napi_err)?
    }
}
