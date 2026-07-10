//! Game scanning bindings (classic-scangame-core)
//!
//! Exposes 8 checker classes (BA2Scanner, ConfigDuplicateDetector, EnbChecker, etc.)
//! for game installation analysis to JavaScript/TypeScript.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::str::FromStr;

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
    BA2Scanner, ConfigDuplicateDetector, CrashgenChecker, GameSetupCheck, GameSetupIntake,
    GameSetupIntakeResult, IniValidator, LogProcessor, UnpackedScanner,
};
use classic_shared_core::GameId;
use napi::bindgen_prelude::*;

use crate::crashgen_rules::{JsCrashgenSettingsRules, js_rules_to_core};

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
    pub fn new(
        plugins_path: String,
        crashgen_name: String,
        settings_rules: Option<JsCrashgenSettingsRules>,
    ) -> Self {
        Self {
            inner: CrashgenChecker::new_with_rules(
                Path::new(&plugins_path),
                crashgen_name,
                js_rules_to_core(settings_rules),
            ),
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
    let mut checker = JsCrashgenChecker::new(plugins_path, crashgen_name, None);
    checker.check()
}

#[napi]
pub fn check_crashgen_config_with_rules(
    plugins_path: String,
    crashgen_name: String,
    settings_rules: Option<JsCrashgenSettingsRules>,
) -> Result<JsCrashgenCheckResult> {
    let mut checker = JsCrashgenChecker::new(plugins_path, crashgen_name, settings_rules);
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
    game_version: GameVersion,
}

#[napi]
impl JsXseChecker {
    /// Create a new XSE checker.
    ///
    /// @param pluginsPath - Path to the F4SE/SKSE plugins directory.
    /// @param gameVersion - Detected game version (default: "Original").
    #[napi(constructor)]
    pub fn new(plugins_path: String, game_version: Option<String>) -> Result<Self> {
        let version = parse_game_version(game_version.as_deref().unwrap_or("Original"));

        // Validate that the path exists
        let _ = CoreXseChecker::new(&plugins_path, version).map_err(to_napi_err)?;

        Ok(Self {
            plugins_path,
            game_version: version,
        })
    }

    /// Perform the validation check.
    ///
    /// @returns Validation result string ("CorrectVersion", "WrongVersion", "NotFound",
    ///          "VersionNotDetected", "PluginsPathNotFound").
    #[napi]
    pub fn check(&self) -> Result<String> {
        let checker =
            CoreXseChecker::new(&self.plugins_path, self.game_version).map_err(to_napi_err)?;

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
        let checker =
            CoreXseChecker::new(&self.plugins_path, self.game_version).map_err(to_napi_err)?;

        Ok(checker.validate())
    }
}

/// Parse a game version string to the core enum.
fn parse_game_version(s: &str) -> GameVersion {
    match s {
        "Null" => GameVersion::Null,
        "Original" => GameVersion::Original,
        "NextGen" => GameVersion::NextGen,
        "AnniversaryEdition" | "AE" => GameVersion::AnniversaryEdition,
        "Vr" | "VR" => GameVersion::Vr,
        _ => GameVersion::Original,
    }
}

/// Get Address Library info for a specific game version.
///
/// @param version - Game version string
///   ("Original", "NextGen", "AnniversaryEdition"/"AE", "Vr"/"VR").
/// @returns Address Library information object.
#[napi]
pub fn get_address_lib_info(version: String) -> JsAddressLibInfo {
    let info = match version.as_str() {
        "Vr" | "VR" => AddressLibInfo::vr(),
        "NextGen" => AddressLibInfo::next_gen(),
        "AnniversaryEdition" | "AE" => AddressLibInfo::anniversary_edition(),
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
/// @param gameVersion - Detected game version string.
/// @returns Formatted validation message.
#[napi]
pub fn check_xse_plugins(plugins_path: String, game_version: String) -> Result<String> {
    let version = parse_game_version(&game_version);
    let checker = CoreXseChecker::new(&plugins_path, version).map_err(to_napi_err)?;
    Ok(checker.validate())
}

// ============================================================================
// 10. Game Scan Orchestrator
// ============================================================================

/// Convert a JS game target string to the core DDS GameTarget enum.
fn parse_game_target_for_scan(s: &str) -> classic_file_io_core::dds::GameTarget {
    match s {
        "SkyrimSE" | "SkyrimSe" => classic_file_io_core::dds::GameTarget::SkyrimSE,
        _ => classic_file_io_core::dds::GameTarget::Fallout4,
    }
}

/// Configuration for a game scan operation.
///
/// Provides all paths and settings the orchestrator needs to run
/// game integrity checks and mod scans.
#[napi(object)]
pub struct JsGameScanConfig {
    /// Path to the game root directory.
    pub game_path: String,
    /// Path to the docs folder (for log scanning).
    pub docs_path: Option<String>,
    /// Path to the mods folder.
    pub mods_path: Option<String>,
    /// XSE acronym (e.g., "F4SE", "SKSE").
    pub xse_acronym: String,
    /// XSE script file patterns -> expected hashes.
    pub xse_scriptfiles: HashMap<String, Vec<String>>,
    /// Path to F4SE/SKSE plugins directory.
    pub plugins_path: Option<String>,
    /// Whether in VR mode.
    pub is_vr: bool,
    /// Detected game version string ("Original", "NextGen", "Vr", etc.).
    pub game_version: String,
    /// Crashgen plugin name (e.g., "Buffout4").
    pub crashgen_name: String,
    /// Optional crashgen settings rules loaded from YAML.
    pub crashgen_settings_rules: Option<JsCrashgenSettingsRules>,
    /// Wrye Bash warning patterns.
    pub wrye_warnings: HashMap<String, String>,
    /// Log error catch patterns.
    pub log_catch_errors: Vec<String>,
    /// Log file exclude patterns.
    pub log_exclude_files: Vec<String>,
    /// Log error exclude patterns.
    pub log_exclude_errors: Vec<String>,
    /// Game target for DDS validation ("Fallout4" or "SkyrimSE").
    pub game_target: String,
    /// Game name string (e.g., "Fallout4").
    pub game_name: String,
}

/// Convert a JS scan config to the core GameScanConfig.
fn js_scan_config_to_core(
    config: &JsGameScanConfig,
) -> classic_scangame_core::orchestrator::GameScanConfig {
    classic_scangame_core::orchestrator::GameScanConfig {
        game_path: PathBuf::from(&config.game_path),
        docs_path: config.docs_path.as_ref().map(PathBuf::from),
        mods_path: config.mods_path.as_ref().map(PathBuf::from),
        xse_acronym: config.xse_acronym.clone(),
        xse_scriptfiles: config.xse_scriptfiles.clone(),
        plugins_path: config.plugins_path.as_ref().map(PathBuf::from),
        is_vr: config.is_vr,
        game_version: parse_game_version(&config.game_version),
        crashgen_name: config.crashgen_name.clone(),
        crashgen_settings_rules: js_rules_to_core(config.crashgen_settings_rules.clone()),
        wrye_warnings: config.wrye_warnings.clone(),
        log_catch_errors: config.log_catch_errors.clone(),
        log_exclude_files: config.log_exclude_files.clone(),
        log_exclude_errors: config.log_exclude_errors.clone(),
        game_target: parse_game_target_for_scan(&config.game_target),
        game_name: config.game_name.clone(),
    }
}

/// Convert a core ConfigIssue to the existing JsConfigIssue.
fn config_issue_to_js(issue: classic_scangame_core::ini::ConfigIssue) -> JsConfigIssue {
    JsConfigIssue {
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
    }
}

/// Result of a single check task.
#[napi(object)]
pub struct JsCheckResult {
    /// Name of the check.
    pub name: String,
    /// Formatted output text.
    pub output: String,
}

/// Combined result of all game integrity checks.
#[napi(object)]
pub struct JsGameScanResult {
    /// Formatted report text from all checks.
    pub report: String,
    /// Detected configuration issues (read-only).
    pub config_issues: Vec<JsConfigIssue>,
    /// Individual check results.
    pub check_results: Vec<JsCheckResult>,
    /// Any errors from failed checks (non-fatal).
    pub errors: Vec<String>,
}

/// Combined result of mod scanning (unpacked + archived).
#[napi(object)]
pub struct JsModScanResult {
    /// Formatted report text.
    pub report: String,
    /// Count of unpacked issues found.
    pub unpacked_issue_count: u32,
    /// Count of archived issues found.
    pub archived_issue_count: u32,
    /// Any errors from scanning.
    pub errors: Vec<String>,
}

/// Run all game integrity checks concurrently.
///
/// Executes XSE validation, crashgen checking, ENB detection,
/// log error scanning, Wrye Bash analysis, and mod INI scanning
/// as concurrent tasks.
#[napi]
pub async fn run_game_checks(config: JsGameScanConfig) -> napi::Result<JsGameScanResult> {
    let core_config = js_scan_config_to_core(&config);
    let handle = classic_shared_core::get_runtime().handle().clone();

    handle
        .spawn(async move {
            let orchestrator =
                classic_scangame_core::orchestrator::GameScanOrchestrator::new(core_config);
            orchestrator.run_game_checks().await
        })
        .await
        .map_err(|e| to_napi_err(format!("Task join error: {e}")))?
        .map(|result| JsGameScanResult {
            report: result.report,
            config_issues: result
                .config_issues
                .into_iter()
                .map(config_issue_to_js)
                .collect(),
            check_results: result
                .check_results
                .into_iter()
                .map(|r| JsCheckResult {
                    name: r.name,
                    output: r.output,
                })
                .collect(),
            errors: result.errors,
        })
        .map_err(to_napi_err)
}

/// Run mod file scans (unpacked + archived) concurrently.
///
/// Scans both loose/unpacked mod files and BA2 archives for issues.
#[napi]
pub async fn run_mod_scans(config: JsGameScanConfig) -> napi::Result<JsModScanResult> {
    let core_config = js_scan_config_to_core(&config);
    let handle = classic_shared_core::get_runtime().handle().clone();

    handle
        .spawn(async move {
            let orchestrator =
                classic_scangame_core::orchestrator::GameScanOrchestrator::new(core_config);
            orchestrator.run_mod_scans().await
        })
        .await
        .map_err(|e| to_napi_err(format!("Task join error: {e}")))?
        .map(|result| JsModScanResult {
            report: result.report,
            unpacked_issue_count: result.unpacked_issue_count as u32,
            archived_issue_count: result.archived_issue_count as u32,
            errors: result.errors,
        })
        .map_err(to_napi_err)
}

// ============================================================================
// 11. Crashgen Check Orchestrator
// ============================================================================

/// Full crash generator check report.
#[napi(object)]
pub struct JsCrashgenReport {
    /// Formatted message string.
    pub message: String,
    /// Structured list of configuration issues detected.
    pub issues: Vec<JsTomlConfigIssue>,
    /// Name of the crash generator being checked.
    pub crashgen_name: String,
    /// Path to the configuration file that was checked (if found).
    pub config_path: Option<String>,
    /// Set of installed plugin DLL names (lowercase).
    pub installed_plugins: Vec<String>,
}

/// Run a full crash generator configuration check.
///
/// Locates config files, detects plugins, validates settings,
/// and produces a structured report.
///
/// @param pluginsPath - Path to the game's plugin directory (e.g., Data/F4SE/Plugins).
/// @param crashgenName - Name of crash generator (e.g., "Buffout4").
#[napi]
pub fn check_crashgen_full(
    plugins_path: String,
    crashgen_name: String,
) -> napi::Result<JsCrashgenReport> {
    let report =
        classic_scangame_core::crashgen_orchestrator::CrashgenCheckOrchestrator::check_with_rules(
            Path::new(&plugins_path),
            &crashgen_name,
            None,
        )
        .map_err(to_napi_err)?;

    Ok(JsCrashgenReport {
        message: report.message,
        issues: report
            .issues
            .into_iter()
            .map(|i| JsTomlConfigIssue {
                file_path: i.file_path.to_string_lossy().to_string(),
                section: i.section,
                setting: i.setting,
                current_value: i.current_value,
                recommended_value: i.recommended_value,
                description: i.description,
                severity: match i.severity {
                    TomlIssueSeverity::Error => "Error".to_string(),
                    TomlIssueSeverity::Warning => "Warning".to_string(),
                    TomlIssueSeverity::Info => "Info".to_string(),
                },
            })
            .collect(),
        crashgen_name: report.crashgen_name,
        config_path: report.config_path.map(|p| p.to_string_lossy().to_string()),
        installed_plugins: report.installed_plugins,
    })
}

#[napi]
pub fn check_crashgen_full_with_rules(
    plugins_path: String,
    crashgen_name: String,
    settings_rules: Option<JsCrashgenSettingsRules>,
) -> napi::Result<JsCrashgenReport> {
    let report =
        classic_scangame_core::crashgen_orchestrator::CrashgenCheckOrchestrator::check_with_rules(
            Path::new(&plugins_path),
            &crashgen_name,
            js_rules_to_core(settings_rules),
        )
        .map_err(to_napi_err)?;

    Ok(JsCrashgenReport {
        message: report.message,
        issues: report
            .issues
            .into_iter()
            .map(|i| JsTomlConfigIssue {
                file_path: i.file_path.to_string_lossy().to_string(),
                section: i.section,
                setting: i.setting,
                current_value: i.current_value,
                recommended_value: i.recommended_value,
                description: i.description,
                severity: match i.severity {
                    TomlIssueSeverity::Error => "Error".to_string(),
                    TomlIssueSeverity::Warning => "Warning".to_string(),
                    TomlIssueSeverity::Info => "Info".to_string(),
                },
            })
            .collect(),
        crashgen_name: report.crashgen_name,
        config_path: report.config_path.map(|p| p.to_string_lossy().to_string()),
        installed_plugins: report.installed_plugins,
    })
}

// ============================================================================
// 12. Wrye Bash Parser
// ============================================================================

/// An issue found in the Wrye Bash plugin checker report.
#[napi(object)]
pub struct JsWryeIssue {
    /// Section title from the report (e.g., "Missing Masters", "ESL Capable").
    pub section_title: String,
    /// Plugin names associated with this section.
    pub plugins: Vec<String>,
    /// Warning message from the YAML database, if any.
    pub warning_message: Option<String>,
    /// Issue severity ("Info", "Warning", "Error").
    pub severity: String,
}

/// Wrye Bash ModChecker.html report parser.
///
/// Extracts sections (h3 headers) and their associated plugin lists from
/// the HTML report. Matches sections against a warnings dictionary.
#[napi]
pub struct JsWryeBashParser {
    inner: classic_scangame_core::wrye::WryeBashParser,
}

#[napi]
impl JsWryeBashParser {
    /// Create a new Wrye Bash parser with warning messages.
    ///
    /// @param wryeWarnings - Map of warning name substrings to warning message text.
    #[napi(constructor)]
    pub fn new(wrye_warnings: HashMap<String, String>) -> Self {
        Self {
            inner: classic_scangame_core::wrye::WryeBashParser::new(wrye_warnings),
        }
    }

    /// Parse an HTML Wrye Bash report and extract issues.
    ///
    /// @param htmlContent - Raw HTML string from ModChecker.html.
    /// @returns Array of issue objects.
    #[napi]
    pub fn parse(&self, html_content: String) -> Vec<JsWryeIssue> {
        self.inner
            .parse(&html_content)
            .into_iter()
            .map(wrye_issue_to_js)
            .collect()
    }

    /// Format parsed issues into a complete report string.
    ///
    /// @param issues - Array of JsWryeIssue objects from parse().
    /// @returns Formatted report string.
    #[napi]
    pub fn format_report(issues: Vec<JsWryeIssue>) -> String {
        let core_issues: Vec<classic_scangame_core::wrye::WryeIssue> =
            issues.into_iter().map(js_wrye_issue_to_core).collect();
        classic_scangame_core::wrye::WryeBashParser::format_report(&core_issues)
    }
}

/// Convert a core WryeIssue to the JS DTO.
fn wrye_issue_to_js(issue: classic_scangame_core::wrye::WryeIssue) -> JsWryeIssue {
    JsWryeIssue {
        section_title: issue.section_title,
        plugins: issue.plugins,
        warning_message: issue.warning_message,
        severity: match issue.severity {
            classic_scangame_core::wrye::WryeSeverity::Info => "Info".to_string(),
            classic_scangame_core::wrye::WryeSeverity::Warning => "Warning".to_string(),
            classic_scangame_core::wrye::WryeSeverity::Error => "Error".to_string(),
        },
    }
}

/// Convert a JS WryeIssue back to the core type for formatting.
fn js_wrye_issue_to_core(issue: JsWryeIssue) -> classic_scangame_core::wrye::WryeIssue {
    classic_scangame_core::wrye::WryeIssue {
        section_title: issue.section_title,
        plugins: issue.plugins,
        warning_message: issue.warning_message,
        severity: match issue.severity.as_str() {
            "Warning" => classic_scangame_core::wrye::WryeSeverity::Warning,
            "Error" => classic_scangame_core::wrye::WryeSeverity::Error,
            _ => classic_scangame_core::wrye::WryeSeverity::Info,
        },
    }
}

// ============================================================================
// 13. Mod INI Scanner
// ============================================================================

/// A file with VSync enabled.
#[napi(object)]
pub struct JsVsyncEntry {
    /// Path to the config file.
    pub file_path: String,
    /// Setting name that has VSync enabled.
    pub setting: String,
}

/// A duplicate configuration file entry.
#[napi(object)]
pub struct JsModDuplicateEntry {
    /// Lowercase filename.
    pub file_name: String,
    /// All paths where this file was found.
    pub paths: Vec<String>,
}

/// Result of a mod INI scan.
#[napi(object)]
pub struct JsModIniScanResult {
    /// Formatted report message for display.
    pub message: String,
    /// Structured list of detected configuration issues.
    pub issues: Vec<JsConfigIssue>,
    /// List of files with VSync enabled.
    pub vsync_files: Vec<JsVsyncEntry>,
    /// Duplicate files detected.
    pub duplicates: Vec<JsModDuplicateEntry>,
}

/// Scan mod INI files for configuration issues.
///
/// Checks VSync settings, console commands, mod-specific problems,
/// and duplicate configuration files.
///
/// @param gameRoot - Root directory of the game installation.
/// @param gameName - Game name (e.g., "Fallout4").
#[napi]
pub fn scan_mod_inis(game_root: String, game_name: String) -> napi::Result<JsModIniScanResult> {
    let result =
        classic_scangame_core::mod_ini::ModIniScanner::scan(Path::new(&game_root), &game_name)
            .map_err(to_napi_err)?;

    Ok(JsModIniScanResult {
        message: result.message,
        issues: result.issues.into_iter().map(config_issue_to_js).collect(),
        vsync_files: result
            .vsync_files
            .into_iter()
            .map(|v| JsVsyncEntry {
                file_path: v.file_path.to_string_lossy().to_string(),
                setting: v.setting,
            })
            .collect(),
        duplicates: result
            .duplicates
            .into_iter()
            .map(|d| JsModDuplicateEntry {
                file_name: d.file_name,
                paths: d
                    .paths
                    .into_iter()
                    .map(|p| p.to_string_lossy().to_string())
                    .collect(),
            })
            .collect(),
    })
}

// ============================================================================
// 14. Game Setup Intake
// ============================================================================

/// Options for running Game Setup Intake from JavaScript.
#[napi(object)]
pub struct JsGameSetupIntakeOptions {
    /// Stable game identifier, such as "Fallout4".
    pub game_id: String,
    /// Selected setup version, or "auto" to detect from the executable.
    pub game_version: Option<String>,
    /// Optional game installation root.
    pub game_root: Option<String>,
    /// Optional game executable path.
    pub game_exe_path: Option<String>,
    /// Optional documents root.
    pub docs_root: Option<String>,
    /// Optional XSE log path for loader version detection.
    pub xse_log_path: Option<String>,
}

/// Typed Game Setup Check result.
#[napi(object)]
pub struct JsGameSetupCheck {
    /// Stable check kind identifier.
    pub kind: String,
    /// Stable check state identifier.
    pub state: String,
    /// Human-readable summary.
    pub message: String,
    /// Additional detail lines.
    pub details: Vec<String>,
}

/// One path discovered by Game Setup Intake that the caller may choose to persist.
#[napi(object)]
pub struct JsGameSetupPathUpdate {
    /// Stable proposal kind, currently `game_root` or `docs_root`.
    pub kind: String,
    /// Resolved path represented as a JavaScript string.
    ///
    /// UTF-8-representable paths are exact; other native values use replacement characters.
    pub path: String,
}

/// Result of running Game Setup Intake.
#[napi(object)]
pub struct JsGameSetupIntakeResult {
    /// Rust-rendered report for display surfaces.
    pub rendered_report: String,
    /// Top-level intake status.
    pub status: String,
    /// Whether any diagnostic checks failed.
    pub has_errors: bool,
    /// Number of intake checks.
    pub total_checks: u32,
    /// Number of failed intake checks.
    pub failed_checks: u32,
    /// Number of user actions required before all checks can run.
    pub action_count: u32,
    /// Number of detected paths that callers may persist.
    pub path_update_count: u32,
    /// Ordered detected path proposals; Game Setup Intake does not persist them.
    ///
    /// UTF-8-representable paths are exact; other native path values use replacement
    /// characters because JavaScript exposes this field as a string.
    pub path_updates: Vec<JsGameSetupPathUpdate>,
    /// Resolved game root, when known.
    pub game_root: Option<String>,
    /// Resolved documents root, when known.
    pub docs_root: Option<String>,
    /// Typed check results for structured consumers.
    pub checks: Vec<JsGameSetupCheck>,
}

/// Result of checking if paths need Game Setup Intake detection.
#[napi(object)]
pub struct JsPathDetectionResult {
    /// Whether game path needs detection.
    pub needs_game_path: bool,
    /// Whether docs path needs detection.
    pub needs_docs_path: bool,
}

fn optional_path(value: Option<String>) -> Option<PathBuf> {
    value.and_then(|path| {
        if path.trim().is_empty() {
            None
        } else {
            Some(PathBuf::from(path))
        }
    })
}

/// Build a Rust Game Setup Intake from JavaScript options.
fn build_game_setup_intake(options: JsGameSetupIntakeOptions) -> Result<GameSetupIntake> {
    let game_id = GameId::from_str(&options.game_id).map_err(to_napi_err)?;
    let game_version = options.game_version.as_deref().unwrap_or("auto");
    let mut intake = GameSetupIntake::new(game_id, game_version);
    if let Some(game_root) = optional_path(options.game_root) {
        intake = intake.with_game_root(game_root);
    }
    if let Some(game_exe_path) = optional_path(options.game_exe_path) {
        intake = intake.with_game_exe_path(game_exe_path);
    }
    if let Some(docs_root) = optional_path(options.docs_root) {
        intake = intake.with_docs_root(docs_root);
    }
    if let Some(xse_log_path) = optional_path(options.xse_log_path) {
        intake = intake.with_xse_log_path(xse_log_path);
    }
    Ok(intake)
}

fn game_setup_check_to_js(check: GameSetupCheck) -> JsGameSetupCheck {
    JsGameSetupCheck {
        kind: check.kind.as_str().to_string(),
        state: check.state.as_str().to_string(),
        message: check.message,
        details: check.details,
    }
}

/// Converts one Rust-owned Game Setup path proposal into its NAPI DTO.
fn game_setup_path_update_to_js(
    update: classic_scangame_core::GameSetupPathUpdate,
) -> JsGameSetupPathUpdate {
    JsGameSetupPathUpdate {
        kind: update.kind,
        path: update.path.to_string_lossy().into_owned(),
    }
}

/// Converts a core intake result into its NAPI DTO without changing proposal order.
///
/// `path_update_count` is derived from the emitted proposal vector. Paths use the
/// binding's existing lossy string convention because JavaScript has no `OsString`.
fn game_setup_result_to_js(result: GameSetupIntakeResult) -> JsGameSetupIntakeResult {
    let has_errors = result.has_errors();
    let total_checks = result.total_checks() as u32;
    let failed_checks = result.failed_checks() as u32;
    let path_updates: Vec<_> = result
        .path_updates
        .into_iter()
        .map(game_setup_path_update_to_js)
        .collect();
    let path_update_count = path_updates.len() as u32;
    JsGameSetupIntakeResult {
        rendered_report: result.rendered_report,
        status: result.status.as_str().to_string(),
        has_errors,
        total_checks,
        failed_checks,
        action_count: result.actions.len() as u32,
        path_update_count,
        path_updates,
        game_root: result
            .paths
            .game_root
            .map(|path| path.to_string_lossy().into_owned()),
        docs_root: result
            .paths
            .docs_root
            .map(|path| path.to_string_lossy().into_owned()),
        checks: result
            .checks
            .into_iter()
            .map(game_setup_check_to_js)
            .collect(),
    }
}

/// Run Game Setup Intake and return both rendered and typed diagnostics.
#[napi]
pub fn run_game_setup_intake(options: JsGameSetupIntakeOptions) -> Result<JsGameSetupIntakeResult> {
    build_game_setup_intake(options).map(|intake| game_setup_result_to_js(intake.run()))
}

/// Normalize a raw Game Setup Intake version selection.
#[napi]
pub fn normalize_game_setup_version_selection(version: Option<String>) -> String {
    classic_scangame_core::normalize_game_setup_version_selection(version.as_deref().unwrap_or(""))
}

/// Check if paths need Game Setup Intake auto-detection.
///
/// @param gamePath - Current game path setting (empty or null means not configured).
/// @param docsPath - Current documents path setting (empty or null means not configured).
/// @returns Object indicating which paths need detection.
#[napi]
pub fn game_setup_needs_path_detection(
    game_path: Option<String>,
    docs_path: Option<String>,
) -> JsPathDetectionResult {
    let (needs_game, needs_docs) = classic_scangame_core::game_setup_needs_path_detection(
        game_path.as_deref(),
        docs_path.as_deref(),
    );
    JsPathDetectionResult {
        needs_game_path: needs_game,
        needs_docs_path: needs_docs,
    }
}
