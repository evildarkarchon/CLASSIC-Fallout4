//! Game scanning bindings (classic-scangame-core)
//!
//! Exposes 8 checker classes (BA2Scanner, ConfigDuplicateDetector, EnbChecker, etc.)
//! for game installation analysis to JavaScript/TypeScript.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use classic_scangame_core::enb::{EnbChecker, EnbConfigResult, EnbResult};
use classic_scangame_core::ini::IssueSeverity;
use classic_scangame_core::integrity::{
    CheckType, GameIntegrityChecker, IntegrityCheckResult as CoreIntegrityCheckResult,
    IntegrityConfig,
};
use classic_scangame_core::toml::TomlIssueSeverity;
use classic_scangame_core::xse::{
    AddressLibInfo, GameVersion, ValidationResult, XseChecker as CoreXseChecker,
};
use classic_scangame_core::{
    BA2Scanner, ConfigDuplicateDetector, CrashgenChecker, IniValidator, LogProcessor,
    UnpackedScanner,
};
use napi::bindgen_prelude::*;

/// Convert any Display error to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

// ============================================================================
// 1. BA2 Scanner
// ============================================================================

/// Issues detected during BA2 archive scanning.
#[napi(object)]
pub struct JsBa2Issues {
    /// Texture dimension issues (odd-numbered dimensions)
    pub tex_dims: Vec<String>,
    /// Texture format issues (non-DDS textures)
    pub tex_frmt: Vec<String>,
    /// Sound format issues (MP3/M4A instead of XWM)
    pub snd_frmt: Vec<String>,
    /// XSE script files detected
    pub xse_file: Vec<String>,
}

/// BA2 archive scanner for validating Fallout 4 BA2 archives.
///
/// Scans archives for texture dimension issues, format problems,
/// sound format issues, and XSE script detection.
#[napi(js_name = "JsBa2Scanner")]
pub struct JsBa2Scanner {
    inner: BA2Scanner,
}

#[allow(clippy::new_without_default)]
#[napi]
impl JsBa2Scanner {
    /// Create a new BA2 scanner with default XSE patterns (f4se, skse, nvse, obse).
    #[napi(constructor)]
    pub fn new() -> Self {
        Self {
            inner: BA2Scanner::new(),
        }
    }

    /// Create a scanner with custom XSE patterns.
    #[napi(factory)]
    pub fn with_xse_patterns(patterns: Vec<String>) -> Self {
        Self {
            inner: BA2Scanner::with_xse_patterns(patterns),
        }
    }

    /// Scan a single BA2 archive for issues.
    ///
    /// @param archivePath - Path to the BA2 archive file.
    /// @returns Issues detected in the archive.
    #[napi]
    pub fn scan_archive(&self, archive_path: String) -> Result<JsBa2Issues> {
        let issues = self
            .inner
            .scan_archive(Path::new(&archive_path))
            .map_err(to_napi_err)?;

        Ok(JsBa2Issues {
            tex_dims: issues.tex_dims,
            tex_frmt: issues.tex_frmt,
            snd_frmt: issues.snd_frmt,
            xse_file: issues.xse_file,
        })
    }

    /// Find all BA2 files in a directory (recursively).
    ///
    /// Excludes "prp - main.ba2".
    ///
    /// @param dir - Directory to search.
    /// @returns Array of BA2 file path strings.
    #[napi]
    pub fn find_ba2_files(&self, dir: String) -> Vec<String> {
        self.inner
            .find_ba2_files(Path::new(&dir))
            .into_iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect()
    }
}

/// Convenience function: find and scan all BA2 archives in a directory.
///
/// @param rootPath - Root directory to search.
/// @returns Array of `{ path, issues }` objects for each BA2 file found.
#[napi]
pub fn scan_all_ba2_archives(root_path: String) -> Result<Vec<JsBa2ScanResult>> {
    let scanner = BA2Scanner::new();
    let ba2_files = scanner.find_ba2_files(Path::new(&root_path));

    let results = scanner.scan_archives_batch(&ba2_files);

    let mut output = Vec::new();
    for (path, result) in ba2_files.into_iter().zip(results) {
        match result {
            Ok(issues) => {
                output.push(JsBa2ScanResult {
                    path: path.to_string_lossy().to_string(),
                    issues: JsBa2Issues {
                        tex_dims: issues.tex_dims,
                        tex_frmt: issues.tex_frmt,
                        snd_frmt: issues.snd_frmt,
                        xse_file: issues.xse_file,
                    },
                });
            }
            Err(e) => return Err(to_napi_err(e)),
        }
    }

    Ok(output)
}

/// Result of scanning a single BA2 archive.
#[napi(object)]
pub struct JsBa2ScanResult {
    /// Path to the archive that was scanned.
    pub path: String,
    /// Issues found in the archive.
    pub issues: JsBa2Issues,
}

// ============================================================================
// 2. Config Duplicate Detector
// ============================================================================

/// Duplicate group information.
#[napi(object)]
pub struct JsDuplicateGroup {
    /// The canonical (first encountered) file path.
    pub original: String,
    /// List of duplicate file paths.
    pub duplicates: Vec<String>,
}

/// Configuration file duplicate detector.
///
/// Scans directories for duplicate configuration files using SHA256 hashing,
/// text similarity analysis, and INI structure comparison.
#[napi]
pub struct JsConfigDuplicateDetector {
    inner: ConfigDuplicateDetector,
}

#[allow(clippy::new_without_default)]
#[napi]
impl JsConfigDuplicateDetector {
    /// Create a new duplicate detector with default whitelist (F4EE).
    #[napi(constructor)]
    pub fn new() -> Self {
        Self {
            inner: ConfigDuplicateDetector::new(),
        }
    }

    /// Create a detector with custom whitelist patterns.
    #[napi(factory)]
    pub fn with_whitelist(whitelist: Vec<String>) -> Self {
        Self {
            inner: ConfigDuplicateDetector::with_whitelist(whitelist),
        }
    }

    /// Detect duplicate configuration files in the specified directory.
    ///
    /// @param rootPath - Root directory to scan.
    /// @returns Array of `JsDuplicateGroup` objects.
    #[napi]
    pub fn detect_duplicates(&mut self, root_path: String) -> Result<Vec<JsDuplicateGroup>> {
        self.inner
            .scan_directory(Path::new(&root_path))
            .map_err(to_napi_err)?;

        let duplicates = self.inner.get_duplicates();

        Ok(duplicates
            .values()
            .map(|group| JsDuplicateGroup {
                original: group.canonical.to_string_lossy().to_string(),
                duplicates: group
                    .duplicates
                    .iter()
                    .map(|p| p.to_string_lossy().to_string())
                    .collect(),
            })
            .collect())
    }

    /// Get a map of duplicate files: lowercase filename -> array of all paths.
    ///
    /// @param rootPath - Root directory to scan.
    /// @returns Record mapping filename to array of path strings.
    #[napi]
    pub fn get_duplicate_map(&mut self, root_path: String) -> Result<HashMap<String, Vec<String>>> {
        let scan_result = self
            .inner
            .scan_directory(Path::new(&root_path))
            .map_err(to_napi_err)?;

        Ok(scan_result
            .into_iter()
            .map(|(filename, paths)| {
                (
                    filename,
                    paths
                        .into_iter()
                        .map(|p| p.to_string_lossy().to_string())
                        .collect(),
                )
            })
            .collect())
    }
}

/// Convenience function to detect config duplicates without creating an instance.
///
/// @param rootPath - Root directory to scan.
/// @returns Array of `JsDuplicateGroup` objects.
#[napi]
pub fn detect_config_duplicates(root_path: String) -> Result<Vec<JsDuplicateGroup>> {
    let mut detector = JsConfigDuplicateDetector::new();
    detector.detect_duplicates(root_path)
}

// ============================================================================
// 3. ENB Checker
// ============================================================================

/// ENB binary detection result.
#[napi(string_enum)]
pub enum JsEnbResult {
    /// ENB fully installed (d3d11.dll + d3dcompiler_46e.dll)
    Present,
    /// Only some ENB files found (partial installation)
    Partial,
    /// No ENB files detected
    NotInstalled,
}

/// ENB configuration check result.
#[napi(string_enum)]
pub enum JsEnbConfigResult {
    /// enbseries.ini exists and is readable
    Valid,
    /// enbseries.ini not found
    NotFound,
    /// enbseries.ini exists but cannot be read
    Unreadable,
}

/// Combined ENB validation result.
#[napi(object)]
pub struct JsEnbValidationResult {
    /// Whether ENB binaries are present ("Present", "Partial", "NotInstalled")
    pub binaries: String,
    /// Whether ENB config is valid ("Valid", "NotFound", "Unreadable")
    pub config: String,
    /// Whether ENB is present (binaries exist, including partial)
    pub is_present: bool,
    /// Whether ENB is fully configured (binaries + config)
    pub is_fully_configured: bool,
}

/// ENB detection checker.
///
/// Checks for ENB binaries (d3d11.dll, d3dcompiler_46e.dll) and
/// configuration (enbseries.ini) in the game directory.
#[napi]
pub struct JsEnbChecker {
    inner: EnbChecker,
}

#[napi]
impl JsEnbChecker {
    /// Create a new ENB checker for the specified game directory.
    ///
    /// @param gamePath - Path to the game installation directory.
    #[napi(constructor)]
    pub fn new(game_path: String) -> Self {
        Self {
            inner: EnbChecker::new(game_path),
        }
    }

    /// Check if ENB binaries exist.
    ///
    /// @returns "Present", "Partial", or "NotInstalled".
    #[napi]
    pub fn check_binaries(&self) -> String {
        match self.inner.check_binaries() {
            EnbResult::Present => "Present".to_string(),
            EnbResult::Partial => "Partial".to_string(),
            EnbResult::NotInstalled => "NotInstalled".to_string(),
        }
    }

    /// Check if ENB config (enbseries.ini) exists and is readable.
    ///
    /// @returns "Valid", "NotFound", or "Unreadable".
    #[napi]
    pub fn check_config(&self) -> String {
        match self.inner.check_config() {
            EnbConfigResult::Valid => "Valid".to_string(),
            EnbConfigResult::NotFound => "NotFound".to_string(),
            EnbConfigResult::Unreadable => "Unreadable".to_string(),
        }
    }

    /// Perform combined validation of ENB binaries and configuration.
    ///
    /// @returns Validation result with binaries status, config status, and boolean flags.
    #[napi]
    pub fn validate(&self) -> JsEnbValidationResult {
        let result = self.inner.validate();
        let binaries_str = match result.binaries {
            EnbResult::Present => "Present",
            EnbResult::Partial => "Partial",
            EnbResult::NotInstalled => "NotInstalled",
        };
        let config_str = match result.config {
            EnbConfigResult::Valid => "Valid",
            EnbConfigResult::NotFound => "NotFound",
            EnbConfigResult::Unreadable => "Unreadable",
        };

        JsEnbValidationResult {
            binaries: binaries_str.to_string(),
            config: config_str.to_string(),
            is_present: result.is_present(),
            is_fully_configured: result.is_fully_configured(),
        }
    }

    /// Format a user-friendly message based on ENB validation.
    ///
    /// @returns Formatted message string.
    #[napi]
    pub fn format_message(&self) -> String {
        let result = self.inner.validate();
        self.inner.format_message(&result)
    }
}

/// Convenience function to check ENB installation.
///
/// @param gamePath - Path to the game installation directory.
/// @returns Combined validation result.
#[napi]
pub fn check_enb(game_path: String) -> JsEnbValidationResult {
    let checker = JsEnbChecker::new(game_path);
    checker.validate()
}

// ============================================================================
// 4. INI Validator
// ============================================================================

/// Issue severity level.
#[napi(string_enum)]
pub enum JsIssueSeverity {
    /// Error level issue
    Error,
    /// Warning level issue
    Warning,
    /// Informational issue
    Info,
}

/// Configuration issue detected in an INI file.
#[napi(object)]
pub struct JsConfigIssue {
    /// Path to the configuration file
    pub file_path: String,
    /// Section name in the INI file
    pub section: String,
    /// Setting name
    pub setting: String,
    /// Current value of the setting
    pub current_value: String,
    /// Recommended value to fix the issue
    pub recommended_value: String,
    /// Description of the issue
    pub description: String,
    /// Severity level ("Error", "Warning", "Info")
    pub severity: String,
}

/// INI file validator for game configuration files.
///
/// Validates game configuration files and detects issues such as
/// VSync conflicts, console command settings, and mod configuration problems.
#[napi]
pub struct JsIniValidator {
    inner: IniValidator,
}

#[napi]
impl JsIniValidator {
    /// Create a new INI validator for the specified game.
    ///
    /// @param gameName - Name of the game (e.g., "Fallout4").
    #[napi(constructor)]
    pub fn new(game_name: String) -> Self {
        Self {
            inner: IniValidator::new(game_name),
        }
    }

    /// Validate INI files in a game directory and return a formatted report.
    ///
    /// Scans for configuration files, checks VSync settings, console commands,
    /// and other known issues.
    ///
    /// @param gameRoot - Root directory of the game installation.
    /// @returns Formatted validation report string.
    #[napi]
    pub fn validate_inis(&mut self, game_root: String) -> Result<String> {
        self.inner
            .validate_inis(Path::new(&game_root))
            .map_err(to_napi_err)
    }

    /// Detect all known configuration issues from a config files map.
    ///
    /// @param configFiles - Record mapping lowercase filenames to file paths.
    /// @returns Array of `JsConfigIssue` objects.
    #[napi]
    pub fn detect_all_issues(&self, config_files: HashMap<String, String>) -> Vec<JsConfigIssue> {
        let config_map: HashMap<String, PathBuf> = config_files
            .into_iter()
            .map(|(k, v)| (k, PathBuf::from(v)))
            .collect();

        let issues = self.inner.detect_all_issues(&config_map);

        issues
            .into_iter()
            .map(|issue| JsConfigIssue {
                file_path: issue.file_path.to_string_lossy().to_string(),
                section: issue.section,
                setting: issue.setting,
                current_value: issue.current_value,
                recommended_value: issue.recommended_value,
                description: issue.description,
                severity: match issue.severity {
                    IssueSeverity::Error => "Error".to_string(),
                    IssueSeverity::Warning => "Warning".to_string(),
                    IssueSeverity::Info => "Info".to_string(),
                },
            })
            .collect()
    }

    /// Scan a game root for configuration files.
    ///
    /// @param gameRoot - Root directory of the game installation.
    /// @returns Record mapping lowercase filenames to file paths.
    #[napi]
    pub fn scan_config_files(&self, game_root: String) -> Result<HashMap<String, String>> {
        let files = self
            .inner
            .scan_config_files(Path::new(&game_root))
            .map_err(to_napi_err)?;

        Ok(files
            .into_iter()
            .map(|(k, v)| (k, v.to_string_lossy().to_string()))
            .collect())
    }
}

// ============================================================================
// 5. Integrity Checker
// ============================================================================

/// Type of integrity check performed.
#[napi(string_enum)]
pub enum JsCheckType {
    /// Executable version check
    ExecutableVersion,
    /// Installation location check
    InstallationLocation,
}

/// Result of an integrity check.
#[napi(object)]
pub struct JsIntegrityCheckResult {
    /// Whether the check passed
    pub is_valid: bool,
    /// Message describing the check result
    pub message: String,
    /// Type of check performed ("ExecutableVersion" or "InstallationLocation")
    pub check_type: String,
}

/// Configuration for game integrity checking.
#[napi(object)]
pub struct JsIntegrityConfig {
    /// Path to the game executable
    pub game_exe_path: String,
    /// Valid SHA256 hashes for known game versions
    pub valid_exe_hashes: Vec<String>,
    /// Game root name (e.g., "Fallout 4")
    pub root_name: String,
    /// Path to Steam INI (indicates outdated installation if present)
    pub steam_ini_path: Option<String>,
    /// Warning message for Program Files installation
    pub root_warn: Option<String>,
}

/// Game integrity checker.
///
/// Validates game executable version via SHA256 hashing
/// and checks installation location (Program Files detection).
#[napi]
pub struct JsGameIntegrityChecker {
    inner: GameIntegrityChecker,
}

#[napi]
impl JsGameIntegrityChecker {
    /// Create a new game integrity checker.
    ///
    /// @param config - Integrity checking configuration.
    #[napi(constructor)]
    pub fn new(config: JsIntegrityConfig) -> Self {
        let mut core_config = IntegrityConfig::new(
            PathBuf::from(&config.game_exe_path),
            config.valid_exe_hashes,
            config.root_name,
        );

        if let Some(steam_ini) = config.steam_ini_path {
            core_config = core_config.with_steam_ini(PathBuf::from(steam_ini));
        }

        if let Some(root_warn) = config.root_warn {
            core_config = core_config.with_root_warn(root_warn);
        }

        Self {
            inner: GameIntegrityChecker::new(core_config),
        }
    }

    /// Check if game executable is up to date.
    ///
    /// Calculates the SHA256 hash of the game executable and compares
    /// it against known valid hashes.
    ///
    /// @returns Integrity check result with status and message.
    #[napi]
    pub fn check_executable_version(&self) -> Result<JsIntegrityCheckResult> {
        self.inner
            .check_executable_version()
            .map(convert_integrity_result)
            .map_err(to_napi_err)
    }

    /// Verify game is installed outside of Program Files.
    ///
    /// @returns Integrity check result with status and message.
    #[napi]
    pub fn check_installation_location(&self) -> Result<JsIntegrityCheckResult> {
        self.inner
            .check_installation_location()
            .map(convert_integrity_result)
            .map_err(to_napi_err)
    }

    /// Run all integrity checks and return combined results.
    ///
    /// @returns Array of integrity check results.
    #[napi]
    pub fn run_all_checks(&self) -> Result<Vec<JsIntegrityCheckResult>> {
        self.inner
            .run_all_checks()
            .map(|results| results.into_iter().map(convert_integrity_result).collect())
            .map_err(to_napi_err)
    }

    /// Run all checks and return combined message string.
    ///
    /// @returns Combined message string from all checks.
    #[napi]
    pub fn run_full_check(&self) -> Result<String> {
        self.inner.run_full_check().map_err(to_napi_err)
    }
}

/// Convert a core IntegrityCheckResult to the JS DTO.
fn convert_integrity_result(r: CoreIntegrityCheckResult) -> JsIntegrityCheckResult {
    JsIntegrityCheckResult {
        is_valid: r.is_valid,
        message: r.message,
        check_type: match r.check_type {
            CheckType::ExecutableVersion => "ExecutableVersion".to_string(),
            CheckType::InstallationLocation => "InstallationLocation".to_string(),
        },
    }
}

// ============================================================================
// 6. Log Processor
// ============================================================================

/// Log error entry detected during scanning.
#[napi(object)]
pub struct JsLogErrorEntry {
    /// Path to the log file
    pub file_path: String,
    /// Error lines found in the log (limited to last 50)
    pub errors: Vec<String>,
    /// Total number of errors found (before truncation)
    pub total_errors: u32,
}

/// Log file processor for error detection.
///
/// Scans directories for log files and detects errors based on configurable
/// include/exclude patterns. Uses Aho-Corasick for efficient multi-pattern matching.
#[napi]
pub struct JsLogProcessor {
    inner: LogProcessor,
}

#[napi]
impl JsLogProcessor {
    /// Create a new log processor with pattern configuration.
    ///
    /// @param catchErrors - Patterns to match for error detection (case-insensitive).
    /// @param excludeFiles - File name patterns to exclude.
    /// @param excludeErrors - Error patterns to exclude (case-insensitive).
    #[napi(constructor)]
    pub fn new(
        catch_errors: Vec<String>,
        exclude_files: Vec<String>,
        exclude_errors: Vec<String>,
    ) -> Result<Self> {
        let processor =
            LogProcessor::new(catch_errors, exclude_files, exclude_errors).map_err(to_napi_err)?;
        Ok(Self { inner: processor })
    }

    /// Process all log files in a directory and return a formatted error report.
    ///
    /// @param logDir - Directory containing log files to scan.
    /// @returns Formatted error report string.
    #[napi]
    pub fn process_logs(&self, log_dir: String) -> Result<String> {
        self.inner
            .process_logs(Path::new(&log_dir))
            .map_err(to_napi_err)
    }

    /// Get configured error patterns.
    ///
    /// @returns Array of error pattern strings.
    #[napi]
    pub fn error_patterns(&self) -> Vec<String> {
        self.inner.error_patterns().to_vec()
    }
}

/// Convenience function to process logs without creating a processor instance.
///
/// @param logDir - Directory containing log files.
/// @param catchErrors - Patterns to match for error detection.
/// @param excludeFiles - File name patterns to exclude.
/// @param excludeErrors - Error patterns to exclude.
/// @returns Formatted error report string.
#[napi]
pub fn process_game_logs(
    log_dir: String,
    catch_errors: Vec<String>,
    exclude_files: Vec<String>,
    exclude_errors: Vec<String>,
) -> Result<String> {
    let processor = JsLogProcessor::new(catch_errors, exclude_files, exclude_errors)?;
    processor.process_logs(log_dir)
}

// ============================================================================
// 7. TOML / Crashgen Checker
// ============================================================================

/// TOML issue severity level.
#[napi(string_enum)]
pub enum JsTomlIssueSeverity {
    /// Error level issue
    Error,
    /// Warning level issue
    Warning,
    /// Informational issue
    Info,
}

/// Configuration issue detected in a TOML file.
#[napi(object)]
pub struct JsTomlConfigIssue {
    /// Path to the TOML configuration file
    pub file_path: String,
    /// Section name in the TOML file
    pub section: String,
    /// Setting name
    pub setting: String,
    /// Current value of the setting
    pub current_value: String,
    /// Recommended value to fix the issue
    pub recommended_value: String,
    /// Description of the issue
    pub description: String,
    /// Severity level ("Error", "Warning", "Info")
    pub severity: String,
}

/// Crashgen check result (report + issues).
#[napi(object)]
pub struct JsCrashgenCheckResult {
    /// Formatted report string
    pub report: String,
    /// Array of detected configuration issues
    pub issues: Vec<JsTomlConfigIssue>,
}

/// Buffout4/Crash Generator TOML configuration checker.
///
/// Validates crash generator TOML configuration and detects plugin conflicts
/// (X-Cell, Achievements, F4EE/Looks Menu, BakaScrapHeap).
#[napi]
pub struct JsCrashgenChecker {
    inner: CrashgenChecker,
}

#[napi]
impl JsCrashgenChecker {
    /// Create a new TOML configuration checker.
    ///
    /// @param pluginsPath - Path to the plugins directory (e.g., Data/F4SE/Plugins).
    /// @param crashgenName - Name of crash generator (e.g., "Buffout4").
    #[napi(constructor)]
    pub fn new(plugins_path: String, crashgen_name: String) -> Self {
        Self {
            inner: CrashgenChecker::new(Path::new(&plugins_path), crashgen_name),
        }
    }

    /// Check TOML configuration for issues.
    ///
    /// @returns Object with `report` string and `issues` array.
    #[napi]
    pub fn check(&mut self) -> Result<JsCrashgenCheckResult> {
        let (report, issues) = self.inner.check().map_err(to_napi_err)?;

        let js_issues = issues
            .into_iter()
            .map(|issue| JsTomlConfigIssue {
                file_path: issue.file_path.to_string_lossy().to_string(),
                section: issue.section,
                setting: issue.setting,
                current_value: issue.current_value,
                recommended_value: issue.recommended_value,
                description: issue.description,
                severity: match issue.severity {
                    TomlIssueSeverity::Error => "Error".to_string(),
                    TomlIssueSeverity::Warning => "Warning".to_string(),
                    TomlIssueSeverity::Info => "Info".to_string(),
                },
            })
            .collect();

        Ok(JsCrashgenCheckResult {
            report,
            issues: js_issues,
        })
    }
}

/// Convenience function to check crashgen config without creating an instance.
///
/// @param pluginsPath - Path to plugins directory.
/// @param crashgenName - Name of crash generator.
/// @returns Object with `report` string and `issues` array.
#[napi]
pub fn check_crashgen_config(
    plugins_path: String,
    crashgen_name: String,
) -> Result<JsCrashgenCheckResult> {
    let mut checker = JsCrashgenChecker::new(plugins_path, crashgen_name);
    checker.check()
}

// ============================================================================
// 8. Unpacked Scanner
// ============================================================================

/// Issues detected during unpacked mod scanning.
#[napi(object)]
pub struct JsUnpackedIssues {
    /// Animation data directories detected
    pub animdata: Vec<String>,
    /// Texture format issues (TGA/PNG instead of DDS)
    pub tex_frmt: Vec<String>,
    /// Sound format issues (MP3/M4A instead of XWM)
    pub snd_frmt: Vec<String>,
    /// XSE script files detected
    pub xse_file: Vec<String>,
    /// Previs/Precombine files detected
    pub previs: Vec<String>,
    /// DDS files found (paths for batch dimension checking)
    pub dds_files: Vec<String>,
}

/// Unpacked mod scanner.
///
/// Scans mod directories for loose files that should be in BA2 archives,
/// detecting texture format issues, sound format issues, XSE scripts,
/// animation data, and previs/precombine files.
#[napi]
pub struct JsUnpackedScanner {
    inner: UnpackedScanner,
}

#[allow(clippy::new_without_default)]
#[napi]
impl JsUnpackedScanner {
    /// Create a new unpacked scanner.
    #[napi(constructor)]
    pub fn new() -> Self {
        Self {
            inner: UnpackedScanner::new(),
        }
    }

    /// Scan a directory for unpacked file issues.
    ///
    /// @param rootPath - Root directory to scan (typically game Data folder).
    /// @param xseScriptfiles - List of XSE script filenames to detect (e.g., ["f4se.dll"]).
    /// @returns Issues object with categorized problems.
    #[napi]
    pub fn scan_directory(
        &self,
        root_path: String,
        xse_scriptfiles: Vec<String>,
    ) -> Result<JsUnpackedIssues> {
        let issues = self
            .inner
            .scan_directory(Path::new(&root_path), &xse_scriptfiles)
            .map_err(to_napi_err)?;

        Ok(JsUnpackedIssues {
            animdata: issues.animdata.into_iter().collect(),
            tex_frmt: issues.tex_frmt.into_iter().collect(),
            snd_frmt: issues.snd_frmt.into_iter().collect(),
            xse_file: issues.xse_file.into_iter().collect(),
            previs: issues.previs.into_iter().collect(),
            dds_files: issues
                .dds_files
                .into_iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect(),
        })
    }
}

/// Convenience function to scan for unpacked files.
///
/// @param rootPath - Root directory to scan.
/// @param xseScriptfiles - List of XSE script filenames to detect.
/// @returns Issues object with categorized problems.
#[napi]
pub fn scan_unpacked_files(
    root_path: String,
    xse_scriptfiles: Vec<String>,
) -> Result<JsUnpackedIssues> {
    let scanner = JsUnpackedScanner::new();
    scanner.scan_directory(root_path, xse_scriptfiles)
}

// ============================================================================
// 9. XSE Checker
// ============================================================================

/// Game version enum for XSE validation.
#[napi(string_enum)]
pub enum JsGameVersion {
    /// No version detected
    Null,
    /// Original/Old Gen version
    Original,
    /// Next Gen version
    NextGen,
    /// Anniversary Edition version
    AnniversaryEdition,
    /// VR version
    Vr,
}

/// XSE validation result.
#[napi(string_enum)]
pub enum JsValidationResult {
    /// Correct Address Library version installed
    CorrectVersion,
    /// Wrong Address Library version installed
    WrongVersion,
    /// Address Library not found
    NotFound,
    /// Version could not be detected
    VersionNotDetected,
    /// Plugins path not found
    PluginsPathNotFound,
}

/// Address Library version information.
#[napi(object)]
pub struct JsAddressLibInfo {
    /// Game version string ("Null", "Original", "NextGen", "AnniversaryEdition", "Vr")
    pub version: String,
    /// Filename of the Address Library file
    pub filename: String,
    /// Human-readable description
    pub description: String,
    /// Nexus Mods URL for download
    pub url: String,
}

/// XSE plugin checker for validating Address Library installation.
///
/// Checks that the correct version of the Address Library file is installed
/// for the detected game version (VR vs non-VR).
#[napi]
pub struct JsXseChecker {
    // Store config to recreate checker (XseChecker is not Clone)
    plugins_path: String,
    is_vr_mode: bool,
    game_version: GameVersion,
}

#[napi]
impl JsXseChecker {
    /// Create a new XSE checker.
    ///
    /// @param pluginsPath - Path to the F4SE/SKSE plugins directory.
    /// @param isVrMode - Whether the game is running in VR mode (default: false).
    /// @param gameVersion - Detected game version (default: "Original").
    #[napi(constructor)]
    pub fn new(
        plugins_path: String,
        is_vr_mode: Option<bool>,
        game_version: Option<String>,
    ) -> Result<Self> {
        let vr_mode = is_vr_mode.unwrap_or(false);
        let version = parse_game_version(game_version.as_deref().unwrap_or("Original"));

        // Validate that the path exists
        let _ = CoreXseChecker::new(&plugins_path, vr_mode, version).map_err(to_napi_err)?;

        Ok(Self {
            plugins_path,
            is_vr_mode: vr_mode,
            game_version: version,
        })
    }

    /// Perform the validation check.
    ///
    /// @returns Validation result string ("CorrectVersion", "WrongVersion", "NotFound",
    ///          "VersionNotDetected", "PluginsPathNotFound").
    #[napi]
    pub fn check(&self) -> Result<String> {
        let checker = CoreXseChecker::new(&self.plugins_path, self.is_vr_mode, self.game_version)
            .map_err(to_napi_err)?;

        Ok(match checker.check() {
            ValidationResult::CorrectVersion => "CorrectVersion".to_string(),
            ValidationResult::WrongVersion => "WrongVersion".to_string(),
            ValidationResult::NotFound => "NotFound".to_string(),
            ValidationResult::VersionNotDetected => "VersionNotDetected".to_string(),
            ValidationResult::PluginsPathNotFound => "PluginsPathNotFound".to_string(),
        })
    }

    /// Perform validation and return formatted message.
    ///
    /// @returns Formatted message string with validation result.
    #[napi]
    pub fn validate(&self) -> Result<String> {
        let checker = CoreXseChecker::new(&self.plugins_path, self.is_vr_mode, self.game_version)
            .map_err(to_napi_err)?;

        Ok(checker.validate())
    }
}

/// Parse a game version string to the core enum.
fn parse_game_version(s: &str) -> GameVersion {
    match s {
        "Null" => GameVersion::Null,
        "Original" => GameVersion::Original,
        "NextGen" => GameVersion::NextGen,
        "AnniversaryEdition" => GameVersion::AnniversaryEdition,
        "Vr" | "VR" => GameVersion::Vr,
        _ => GameVersion::Original,
    }
}

/// Get Address Library info for a specific game version.
///
/// @param version - Game version string ("Original", "NextGen", "AnniversaryEdition", "Vr").
/// @returns Address Library information object.
#[napi]
pub fn get_address_lib_info(version: String) -> JsAddressLibInfo {
    let info = match version.as_str() {
        "Vr" | "VR" => AddressLibInfo::vr(),
        "NextGen" => AddressLibInfo::next_gen(),
        "AnniversaryEdition" => AddressLibInfo::anniversary_edition(),
        _ => AddressLibInfo::original(),
    };

    JsAddressLibInfo {
        version,
        filename: info.filename,
        description: info.description,
        url: info.url,
    }
}

/// Convenience function to validate XSE plugins.
///
/// @param pluginsPath - Path to F4SE/SKSE plugins directory.
/// @param isVrMode - Whether the game is running in VR mode.
/// @param gameVersion - Detected game version string.
/// @returns Formatted validation message.
#[napi]
pub fn check_xse_plugins(
    plugins_path: String,
    is_vr_mode: bool,
    game_version: String,
) -> Result<String> {
    let version = parse_game_version(&game_version);
    let checker = CoreXseChecker::new(&plugins_path, is_vr_mode, version).map_err(to_napi_err)?;
    Ok(checker.validate())
}
