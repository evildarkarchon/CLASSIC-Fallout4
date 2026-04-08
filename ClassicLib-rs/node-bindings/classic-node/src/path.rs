//! Path detection and validation bindings (classic-path-core)
//!
//! Exposes game path detection, validation, and document path utilities
//! to JavaScript/TypeScript. Windows registry access gated behind cfg.

use napi::bindgen_prelude::*;
use std::path::PathBuf;

/// Convert any Display error to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

// ============================================================================
// 1. GamePathFinder class
// ============================================================================

/// Multi-strategy game path finder.
///
/// Attempts to locate a game installation by checking:
/// 1. A cached path (if provided and valid)
/// 2. Windows registry (Windows only)
/// 3. XSE (script extender) log parsing
///
/// Construct with `new GamePathFinder(gameExe, xseLoader, gameName, isVr)`.
#[napi]
pub struct GamePathFinder {
    inner: classic_path_core::GamePathFinder,
}

#[napi]
impl GamePathFinder {
    /// Create a new GamePathFinder.
    ///
    /// @param gameExe - Game executable name (e.g., "Fallout4.exe").
    /// @param xseLoader - Optional XSE loader name (e.g., "f4se_loader.exe"), or null.
    /// @param gameName - Game name for registry queries (e.g., "Fallout4").
    /// @param isVr - Whether this is a VR version of the game.
    #[napi(constructor)]
    pub fn new(
        game_exe: String,
        xse_loader: Option<String>,
        game_name: String,
        is_vr: bool,
    ) -> Self {
        Self {
            inner: classic_path_core::GamePathFinder::new(game_exe, xse_loader, game_name, is_vr),
        }
    }

    /// Find the game installation path using multiple strategies.
    ///
    /// Tries cached path, Windows registry, and XSE log in order.
    /// Returns the first valid path found, or null if all strategies fail.
    ///
    /// @param cachedPath - Optional cached path from settings, or null.
    /// @param xseLogPath - Optional path to XSE log file, or null.
    /// @returns The game installation path as a string, or null if not found.
    #[napi]
    pub fn find_game_path(
        &self,
        cached_path: Option<String>,
        xse_log_path: Option<String>,
    ) -> Option<String> {
        let cached = cached_path.as_ref().map(PathBuf::from);
        let xse_log = xse_log_path.as_ref().map(PathBuf::from);

        self.inner
            .find_game_path(cached.as_deref(), xse_log.as_deref())
            .ok()
            .map(|p| p.to_string_lossy().to_string())
    }

    /// Validate that a path is a valid game installation directory.
    ///
    /// Checks that the directory exists and contains the game executable
    /// (and XSE loader if configured).
    ///
    /// @param path - The path to validate.
    /// @throws if validation fails.
    #[napi]
    pub fn validate_game_path(&self, path: String) -> Result<()> {
        self.inner
            .validate_game_path(&PathBuf::from(path))
            .map_err(to_napi_err)
    }

    /// Get the game executable name.
    #[napi(getter)]
    pub fn game_exe(&self) -> String {
        self.inner.game_exe().to_string()
    }

    /// Get the XSE loader executable name, or null if not configured.
    #[napi(getter)]
    pub fn xse_loader(&self) -> Option<String> {
        self.inner.xse_loader().map(|s| s.to_string())
    }

    /// Whether this finder targets a VR version.
    #[napi(getter)]
    pub fn is_vr(&self) -> bool {
        self.inner.is_vr()
    }
}

/// Parse an XSE log file to extract the game installation path.
///
/// Looks for the "plugin directory = ..." line and navigates up to the game root.
///
/// @param logPath - Path to the XSE log file (e.g., "f4se.log").
/// @returns The game installation path, or null if parsing fails.
#[napi]
pub fn parse_xse_log(log_path: String) -> Option<String> {
    classic_path_core::parse_xse_log(&PathBuf::from(log_path))
        .ok()
        .map(|p| p.to_string_lossy().to_string())
}

// ============================================================================
// 2. PathValidator free functions
// ============================================================================

/// Check if a path exists in the filesystem.
///
/// @param path - The path to check.
/// @returns `true` if the path exists, `false` otherwise.
#[napi]
pub fn is_valid_path(path: String) -> bool {
    classic_path_core::is_valid_path(&PathBuf::from(path))
}

/// Check if a path is restricted for custom scans.
///
/// Restricted paths include system directories (Windows, Program Files),
/// root directories, and other sensitive locations.
///
/// @param path - The path to check.
/// @returns `true` if the path is restricted, `false` if safe for custom scans.
#[napi]
pub fn is_restricted_path(path: String) -> bool {
    classic_path_core::is_restricted_path(&PathBuf::from(path))
}

/// Check if a path points to a valid executable file.
///
/// Validates that the path exists, is a file, and has a recognized
/// executable extension (.exe, .app, or no extension).
///
/// @param path - The path to check.
/// @returns `true` if the path is a valid executable, `false` otherwise.
#[napi]
pub fn is_valid_executable_path(path: String) -> bool {
    classic_path_core::is_valid_executable_path(&PathBuf::from(path))
}

/// Validate a custom scan path.
///
/// Ensures the path exists, is a directory, and is not restricted.
///
/// @param path - The path to validate for custom scanning.
/// @throws if the path is invalid or restricted.
#[napi]
pub fn validate_custom_scan_path(path: String) -> Result<()> {
    classic_path_core::validate_custom_scan_path(&PathBuf::from(path)).map_err(to_napi_err)
}

/// Validate that required files exist in a directory.
///
/// @param directory - The directory to check.
/// @param requiredFiles - Array of file names that must exist.
/// @throws if the directory or any required file does not exist.
#[napi]
pub fn validate_required_files(directory: String, required_files: Vec<String>) -> Result<()> {
    classic_path_core::validate_required_files(&PathBuf::from(directory), &required_files)
        .map_err(to_napi_err)
}

/// Validate a settings path with optional required files.
///
/// @param path - The path to validate.
/// @param settingName - Name of the setting (for error messages).
/// @param requiredFiles - Optional array of required file names, or null.
/// @throws if validation fails.
#[napi]
pub fn validate_settings_path(
    path: String,
    setting_name: String,
    required_files: Option<Vec<String>>,
) -> Result<()> {
    classic_path_core::validate_settings_path(
        &PathBuf::from(path),
        &setting_name,
        required_files.as_deref(),
    )
    .map_err(to_napi_err)
}

/// Validate all common settings paths (game, docs, optional custom scan).
///
/// @param gamePath - Game installation path.
/// @param docsPath - Documents folder path.
/// @param customScanPath - Optional custom scan path, or null.
/// @param gameExe - Game executable name (e.g., "Fallout4.exe").
/// @throws if any validation fails.
#[napi]
pub fn validate_settings_paths(
    game_path: String,
    docs_path: String,
    custom_scan_path: Option<String>,
    game_exe: String,
) -> Result<()> {
    let game_path_buf = PathBuf::from(game_path);
    let docs_path_buf = PathBuf::from(docs_path);
    let custom_scan_path_buf = custom_scan_path.map(PathBuf::from);

    classic_path_core::validate_settings_paths(
        &game_path_buf,
        &docs_path_buf,
        custom_scan_path_buf.as_deref(),
        &game_exe,
    )
    .map_err(to_napi_err)
}

/// Check if the drive exists (Windows only, no-op on other platforms).
///
/// @param path - The path whose drive to check.
/// @throws if the drive does not exist (Windows only).
#[napi]
pub fn check_drive_exists(path: String) -> Result<()> {
    classic_path_core::check_drive_exists(&PathBuf::from(path)).map_err(to_napi_err)
}

/// Check read permissions for a path.
///
/// For directories, checks if contents can be listed.
/// For files, checks if the file can be opened for reading.
///
/// @param path - The path to check.
/// @throws if read access is denied.
#[napi]
pub fn check_read_permissions(path: String) -> Result<()> {
    classic_path_core::check_read_permissions(&PathBuf::from(path)).map_err(to_napi_err)
}

/// Check write permissions for a path.
///
/// Tests write access by creating and removing a temporary file
/// in the directory (or parent directory for files).
///
/// @param path - The path to check.
/// @throws if write access is denied.
#[napi]
pub fn check_write_permissions(path: String) -> Result<()> {
    classic_path_core::check_write_permissions(&PathBuf::from(path)).map_err(to_napi_err)
}

/// Comprehensive path validation with permission checks.
///
/// Validates: drive exists (Windows), path exists, optional read/write permissions.
///
/// @param path - The path to validate.
/// @param checkRead - Whether to verify read permissions (default: true).
/// @param checkWrite - Whether to verify write permissions (default: false).
/// @throws if any check fails.
#[napi]
pub fn validate_path_with_permissions(
    path: String,
    check_read: Option<bool>,
    check_write: Option<bool>,
) -> Result<()> {
    classic_path_core::validate_path_with_permissions(
        &PathBuf::from(path),
        check_read.unwrap_or(true),
        check_write.unwrap_or(false),
    )
    .map_err(to_napi_err)
}

// ============================================================================
// 3. DocsPathFinder class
// ============================================================================

/// Multi-strategy documents path finder.
///
/// Locates the game's documents folder (containing INI files, saves, and logs)
/// by checking cached paths, Windows registry, or home directory.
///
/// Construct with `new DocsPathFinder(relativePath)`.
#[napi]
pub struct DocsPathFinder {
    inner: classic_path_core::DocsPathFinder,
}

#[napi]
impl DocsPathFinder {
    /// Create a new DocsPathFinder.
    ///
    /// @param relativePath - Path relative to documents folder (e.g., "My Games\\Fallout4").
    #[napi(constructor)]
    pub fn new(relative_path: String) -> Self {
        Self {
            inner: classic_path_core::DocsPathFinder::new(relative_path),
        }
    }

    /// Opt in to a Steam-application-ID-aware Linux Proton documents
    /// path lookup.
    ///
    /// When set, `findDocsPath` on Linux will first try the
    /// Steam/Proton compatdata prefix for the given app ID before
    /// falling back to `~/.local/share/<relativePath>`. When NOT
    /// set (the default from the constructor), the Proton lookup is
    /// skipped entirely and `findDocsPath` on Linux goes straight to
    /// `~/.local/share/<relativePath>`.
    ///
    /// This is an opt-in because DocsPathFinder is a game-agnostic
    /// helper. For example, a Fallout 4 caller should pass
    /// `377160`, while a Skyrim caller should pass that game's
    /// Steam app ID (or not call this method at all if Proton
    /// fallback is unwanted).
    ///
    /// @param appId - The Steam application ID for the game whose
    ///                Proton documents prefix should be searched.
    #[napi]
    pub fn set_steam_app_id(&mut self, app_id: u32) {
        self.inner = self.inner.clone().with_steam_app_id(app_id);
    }

    /// Find the documents folder path using multiple strategies.
    ///
    /// Tries cached path, Windows registry, home directory, in order.
    /// Returns the first valid path found, or null if all strategies fail.
    ///
    /// @param cachedPath - Optional cached path from settings, or null.
    /// @returns The documents folder path as a string, or null if not found.
    #[napi]
    pub fn find_docs_path(&self, cached_path: Option<String>) -> Option<String> {
        self.inner
            .find_docs_path(cached_path.as_deref())
            .ok()
            .map(|p| p.to_string_lossy().to_string())
    }

    /// Validate that a documents path exists and is a directory.
    ///
    /// @param path - The path to validate.
    /// @throws if the path doesn't exist or isn't a directory.
    #[napi]
    pub fn validate_docs_path(&self, path: String) -> Result<()> {
        self.inner
            .validate_docs_path(&PathBuf::from(path))
            .map_err(to_napi_err)
    }

    /// Validate that required INI files exist in the documents path.
    ///
    /// @param docsPath - The documents folder path.
    /// @param requiredInis - Array of INI file names that must exist.
    /// @throws if any required INI file is missing or invalid.
    #[napi]
    pub fn validate_ini_files(&self, docs_path: String, required_inis: Vec<String>) -> Result<()> {
        let ini_refs: Vec<&str> = required_inis.iter().map(|s| s.as_str()).collect();
        self.inner
            .validate_ini_files(&PathBuf::from(docs_path), &ini_refs)
            .map_err(to_napi_err)
    }

    /// Get the relative path within documents folder.
    #[napi(getter)]
    pub fn relative_path(&self) -> String {
        self.inner.relative_path().to_string()
    }
}

// ============================================================================
// 4. BackupManager class
// ============================================================================

/// Version-aware backup manager for configuration files.
///
/// Creates backups organized by game version extracted from XSE logs.
///
/// Construct with `new BackupManager(backupRoot)`.
#[napi]
pub struct BackupManager {
    inner: classic_path_core::BackupManager,
}

#[napi]
impl BackupManager {
    /// Create a new BackupManager.
    ///
    /// @param backupRoot - Root directory where backups will be stored.
    #[napi(constructor)]
    pub fn new(backup_root: String) -> Self {
        Self {
            inner: classic_path_core::BackupManager::new(backup_root),
        }
    }

    /// Extract version information from an XSE log file.
    ///
    /// @param xseLogPath - Path to the XSE log file.
    /// @returns An XseVersion instance with the extracted version.
    /// @throws if the log file doesn't exist or contains no version.
    #[napi]
    pub fn extract_version_from_xse_log(&self, xse_log_path: String) -> Result<XseVersion> {
        self.inner
            .extract_version_from_xse_log(&PathBuf::from(xse_log_path))
            .map(|v| XseVersion { inner: v })
            .map_err(to_napi_err)
    }

    /// Create a backup of a file with version metadata.
    ///
    /// Directory structure: `backupRoot/<version_sanitized>/<filename>`.
    ///
    /// @param sourceFile - Path to the file to back up.
    /// @param version - XseVersion for organizing the backup.
    /// @returns Path to the created backup file.
    /// @throws if the source file doesn't exist or copy fails.
    #[napi]
    pub fn create_backup(&self, source_file: String, version: &XseVersion) -> Result<String> {
        self.inner
            .create_backup(&PathBuf::from(source_file), &version.inner)
            .map(|p| p.to_string_lossy().to_string())
            .map_err(to_napi_err)
    }

    /// Get the backup root directory path.
    #[napi(getter)]
    pub fn backup_root(&self) -> String {
        self.inner.backup_root().to_string_lossy().to_string()
    }

    /// List all version directories in the backup root.
    ///
    /// @returns Array of version directory names (sorted).
    /// @throws if the backup directory can't be read.
    #[napi]
    pub fn list_versions(&self) -> Result<Vec<String>> {
        self.inner.list_versions().map_err(to_napi_err)
    }

    /// Get the path to a specific version's backup directory.
    ///
    /// @param version - The XseVersion to look up.
    /// @returns Path to the version's backup directory.
    #[napi]
    pub fn get_version_path(&self, version: &XseVersion) -> String {
        self.inner
            .get_version_path(&version.inner)
            .to_string_lossy()
            .to_string()
    }
}

// ============================================================================
// 5. XseVersion class
// ============================================================================

/// Version information extracted from XSE log files.
///
/// Contains the full version string and provides a sanitized form
/// suitable for directory names.
///
/// Construct with `new XseVersion(version)`.
#[napi]
pub struct XseVersion {
    inner: classic_path_core::XseVersion,
}

#[napi]
impl XseVersion {
    /// Create a new XseVersion from a version string.
    ///
    /// @param version - Full version string (e.g., "1.10.163.0").
    #[napi(constructor)]
    pub fn new(version: String) -> Self {
        Self {
            inner: classic_path_core::XseVersion::new(version),
        }
    }

    /// Get the full version string (e.g., "1.10.163.0").
    #[napi]
    pub fn full_version(&self) -> String {
        self.inner.full_version().to_string()
    }

    /// Get a sanitized version suitable for directory names (dots replaced with underscores).
    ///
    /// Example: "1.10.163.0" becomes "1_10_163_0".
    #[napi]
    pub fn sanitized(&self) -> String {
        self.inner.sanitized()
    }

    /// Get a human-readable string representation.
    #[napi(js_name = "toString")]
    pub fn to_string_repr(&self) -> String {
        format!("XseVersion('{}')", self.inner.full_version())
    }
}

// ============================================================================
// 6. IniCheckResult object
// ============================================================================

/// Result of an INI file validation check.
///
/// Contains information about the validation status and any issues detected.
#[napi(object)]
pub struct JsIniCheckResult {
    /// The name of the INI file that was checked.
    pub ini_name: String,
    /// Whether the INI file exists.
    pub exists: bool,
    /// Whether the INI file is valid and parseable.
    pub is_valid: bool,
    /// Human-readable message describing the check result.
    pub message: String,
    /// Optional issue identifier (e.g., "missing", "corrupted", "missing_archive_section"),
    /// or undefined if there's no issue.
    pub issue: Option<String>,
    /// Whether this result indicates a problem.
    pub has_issue: bool,
}

impl From<classic_path_core::IniCheckResult> for JsIniCheckResult {
    fn from(r: classic_path_core::IniCheckResult) -> Self {
        let has_issue = r.has_issue();
        Self {
            ini_name: r.ini_name,
            exists: r.exists,
            is_valid: r.is_valid,
            message: r.message,
            issue: r.issue,
            has_issue,
        }
    }
}

// ============================================================================
// 7. DocumentsChecker class
// ============================================================================

/// Read-only documents configuration checker.
///
/// Validates documents folder configuration and INI files without
/// modifying any files, reporting issues for the caller to handle.
///
/// Construct with `new DocumentsChecker(gameName)`.
#[napi]
pub struct DocumentsChecker {
    inner: classic_path_core::DocumentsChecker,
}

#[napi]
impl DocumentsChecker {
    /// Create a new DocumentsChecker.
    ///
    /// @param gameName - Name of the game (e.g., "Fallout4").
    #[napi(constructor)]
    pub fn new(game_name: String) -> Self {
        Self {
            inner: classic_path_core::DocumentsChecker::new(game_name),
        }
    }

    /// Check if OneDrive is detected in the documents path.
    ///
    /// @param docsPath - The documents folder path to check.
    /// @returns Warning message if OneDrive detected, or null otherwise.
    #[napi]
    pub fn check_onedrive_in_path(&self, docs_path: String) -> Option<String> {
        self.inner.check_onedrive_in_path(&PathBuf::from(docs_path))
    }

    /// Validate an INI file in the documents folder.
    ///
    /// Checks existence, parseability, and game-specific requirements
    /// (e.g., [Archive] section in Custom.ini).
    ///
    /// @param docsPath - The documents folder path.
    /// @param iniName - Name of the INI file (e.g., "Fallout4.ini").
    /// @returns An IniCheckResult object with the validation status.
    /// @throws on I/O errors (not for missing/invalid files).
    #[napi]
    pub fn validate_ini_file(
        &self,
        docs_path: String,
        ini_name: String,
    ) -> Result<JsIniCheckResult> {
        self.inner
            .validate_ini_file(&PathBuf::from(docs_path), &ini_name)
            .map(JsIniCheckResult::from)
            .map_err(to_napi_err)
    }

    /// Run all document checks for the game.
    ///
    /// Performs OneDrive detection, main INI validation, Custom INI validation,
    /// and Prefs INI validation.
    ///
    /// @param docsPath - The documents folder path.
    /// @returns Array of check result messages (only non-empty results).
    /// @throws on I/O errors.
    #[napi]
    pub fn run_all_checks(&self, docs_path: String) -> Result<Vec<String>> {
        self.inner
            .run_all_checks(&PathBuf::from(docs_path))
            .map_err(to_napi_err)
    }

    /// Get the game name.
    #[napi(getter)]
    pub fn game_name(&self) -> String {
        self.inner.game_name().to_string()
    }
}

// ============================================================================
// 8. Platform utilities
// ============================================================================

/// Get the system documents path (Windows: registry query, Linux: home directory).
///
/// @returns The system documents path, or null if detection fails.
#[napi]
pub fn get_system_documents_path() -> Option<String> {
    classic_path_core::get_system_documents_path()
        .ok()
        .map(|p| p.to_string_lossy().to_string())
}

/// Remove the read-only attribute from a file (Windows only, no-op on other platforms).
///
/// @param filePath - Path to the file.
/// @throws if permissions cannot be modified.
#[napi]
#[cfg(target_os = "windows")]
pub fn remove_readonly(file_path: String) -> Result<()> {
    classic_path_core::remove_readonly(&PathBuf::from(file_path)).map_err(to_napi_err)
}

/// Remove the read-only attribute (stub for non-Windows platforms).
#[napi]
#[cfg(not(target_os = "windows"))]
pub fn remove_readonly(_file_path: String) -> Result<()> {
    Ok(())
}

/// Query Windows registry for a game installation path.
///
/// Searches Bethesda, Steam, and optionally GOG registry entries.
///
/// @param gameName - Game name (e.g., "Fallout4").
/// @param vrSuffix - VR suffix (e.g., " VR"), or empty string.
/// @param tryGog - Whether to check GOG registry as fallback.
/// @returns The game path from registry, or null if not found.
#[napi]
#[cfg(target_os = "windows")]
pub fn query_game_registry(game_name: String, vr_suffix: String, try_gog: bool) -> Option<String> {
    classic_path_core::query_game_registry(&game_name, &vr_suffix, try_gog)
        .ok()
        .map(|p| p.to_string_lossy().to_string())
}

/// Query Windows registry for game path (stub for non-Windows platforms).
///
/// Always returns null on non-Windows platforms.
#[napi]
#[cfg(not(target_os = "windows"))]
pub fn query_game_registry(
    _game_name: String,
    _vr_suffix: String,
    _try_gog: bool,
) -> Option<String> {
    None
}

/// Parse Steam library VDF to find a game installation path (Linux only).
///
/// On Windows, always returns null (Steam paths use registry instead).
///
/// @param gameSteamId - Steam application ID (e.g., 377160 for Fallout 4).
/// @returns The library path containing the game, or null if not found.
#[napi]
pub fn parse_steam_library(game_steam_id: u32) -> Option<String> {
    classic_path_core::parse_steam_library(game_steam_id)
        .ok()
        .map(|p| p.to_string_lossy().to_string())
}
