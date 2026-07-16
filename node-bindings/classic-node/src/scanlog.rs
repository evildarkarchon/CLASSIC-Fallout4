//! Scanlog bindings for classic-scanlog-core
//!
//! Exposes independently useful crash-log parsing and analysis utilities to
//! JavaScript/TypeScript. Complete Crash Log Scan Runs are available only
//! through the final contract in `crate::scan_run`.
//!
//! ## Sync Utilities
//! Parsing utilities (`parseLogSegments`, `extractFormIds`, `extractPluginList`,
//! `detectCrashPattern`) are synchronous and operate on string content directly.

use classic_scanlog_core::ConfigIssue;
use classic_scanlog_core::parser::LogParser;
use classic_scanlog_core::segment_key;

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Detect crashgen settings section markers within parser `settings` lines.
///
/// The parser's `settings` segment now includes all pre-`SYSTEM SPECS:` lines.
/// For Node's `header` field we preserve legacy behavior by only exposing lines
/// after known crashgen settings markers.
fn is_settings_header_marker(line: &str) -> bool {
    let trimmed = line.trim();
    trimmed.eq_ignore_ascii_case("[Compatibility]") || trimmed.eq_ignore_ascii_case("[Patches]")
}

#[napi(object)]
pub struct JsFcxConfigIssue {
    pub file_path: String,
    pub section: Option<String>,
    pub setting: String,
    pub current_value: String,
    pub recommended_value: String,
    pub description: String,
    pub severity: String,
}

impl From<&ConfigIssue> for JsFcxConfigIssue {
    fn from(issue: &ConfigIssue) -> Self {
        Self {
            file_path: issue.file_path.clone(),
            section: issue.section.clone(),
            setting: issue.setting.clone(),
            current_value: issue.current_value.clone(),
            recommended_value: issue.recommended_value.clone(),
            description: issue.description.clone(),
            severity: issue.severity.clone(),
        }
    }
}

/// JavaScript-compatible parsed log segments.
///
/// Contains the various sections extracted from a crash log.
#[napi(object)]
pub struct JsLogSegments {
    /// Header/compatibility section lines
    pub header: Vec<String>,
    /// System specs section lines
    pub system: Vec<String>,
    /// Probable call stack section lines
    pub stack: Vec<String>,
    /// Modules section lines
    pub modules: Vec<String>,
    /// Plugins section lines
    pub plugins: Vec<String>,
    /// Number of segments found
    pub segment_count: u32,
}

// ============================================================================
// Synchronous Parsing Utilities
// ============================================================================

/// Parse crash log content into structured segments.
///
/// Splits the log content into sections (header, system, stack, modules, plugins)
/// using the SIMD-optimized parser. This is a synchronous operation.
///
/// @param content - The full crash log file content as a string.
/// @returns A `JsLogSegments` object with the extracted sections.
#[napi]
pub fn parse_log_segments(content: String) -> napi::Result<JsLogSegments> {
    let parser = LogParser::new(None).map_err(to_napi_err)?;

    let lines: Vec<String> = content.lines().map(String::from).collect();

    let all_sections = parser.parse_all_sections(&lines);
    let header = all_sections
        .get(segment_key::SETTINGS)
        .and_then(|settings| {
            settings
                .iter()
                .position(|line| is_settings_header_marker(line))
                .map(|idx| settings[idx + 1..].to_vec())
        })
        .unwrap_or_default();
    let system = all_sections
        .get(segment_key::SYSTEM)
        .cloned()
        .unwrap_or_default();
    let stack = all_sections
        .get(segment_key::CALLSTACK)
        .cloned()
        .unwrap_or_default();
    let modules = all_sections
        .get(segment_key::MODULES)
        .cloned()
        .unwrap_or_default();
    let plugins = all_sections
        .get(segment_key::PLUGINS)
        .cloned()
        .unwrap_or_default();
    let segment_count = [
        header.as_slice(),
        system.as_slice(),
        stack.as_slice(),
        modules.as_slice(),
        plugins.as_slice(),
    ]
    .iter()
    .filter(|section| !section.is_empty())
    .count() as u32;

    Ok(JsLogSegments {
        header,
        system,
        stack,
        modules,
        plugins,
        segment_count,
    })
}

/// Extract FormID hex strings from crash log content.
///
/// Searches for Bethesda game FormIDs (8-character hex identifiers) in the
/// provided text. Uses SIMD-optimized regex matching.
///
/// @param content - The crash log content (or a section of it) to search.
/// @returns An array of FormID strings (hex values without "0x" prefix).
#[napi]
pub fn extract_form_ids(content: String) -> napi::Result<Vec<String>> {
    let parser = LogParser::new(None).map_err(to_napi_err)?;
    let lines: Vec<String> = content.lines().map(String::from).collect();
    Ok(parser.extract_formids(&lines))
}

/// Extract plugin names from crash log content.
///
/// Searches for Bethesda game plugin entries (e.g., `[00] Fallout4.esm`)
/// and returns just the plugin filenames.
///
/// @param content - The crash log content (or plugin section) to search.
/// @returns An array of plugin filename strings (e.g., "Fallout4.esm").
#[napi]
pub fn extract_plugin_list(content: String) -> napi::Result<Vec<String>> {
    let parser = LogParser::new(None).map_err(to_napi_err)?;
    let lines: Vec<String> = content.lines().map(String::from).collect();
    let plugins = parser.extract_plugins(&lines);
    // Return just the plugin names (first element of each tuple)
    Ok(plugins.into_iter().map(|(name, _index)| name).collect())
}

/// Detect the crash pattern from crash log content.
///
/// Analyzes the log header for known crash patterns (e.g., "ACCESS_VIOLATION",
/// "STACK_OVERFLOW", "STACK_BUFFER_OVERRUN"). Returns the pattern name if
/// detected, or `undefined` if no known pattern is found.
///
/// @param content - The crash log content to analyze.
/// @returns The crash pattern name, or `undefined` if none detected.
#[napi]
pub fn detect_crash_pattern(content: String) -> Option<String> {
    // Known crash patterns to detect in the main error line
    let known_patterns: &[(&str, &str)] = &[
        ("EXCEPTION_ACCESS_VIOLATION", "ACCESS_VIOLATION"),
        ("EXCEPTION_STACK_OVERFLOW", "STACK_OVERFLOW"),
        ("EXCEPTION_INT_DIVIDE_BY_ZERO", "INT_DIVIDE_BY_ZERO"),
        ("EXCEPTION_BREAKPOINT", "BREAKPOINT"),
        ("EXCEPTION_ILLEGAL_INSTRUCTION", "ILLEGAL_INSTRUCTION"),
        ("EXCEPTION_STACK_BUFFER_OVERRUN", "STACK_BUFFER_OVERRUN"),
        ("STATUS_HEAP_CORRUPTION", "HEAP_CORRUPTION"),
        ("0xC0000005", "ACCESS_VIOLATION"),
        ("0xC00000FD", "STACK_OVERFLOW"),
        ("0xC0000094", "INT_DIVIDE_BY_ZERO"),
        ("0x80000003", "BREAKPOINT"),
        ("0xC000001D", "ILLEGAL_INSTRUCTION"),
        ("0xC0000409", "STACK_BUFFER_OVERRUN"),
    ];

    // Search the first 30 lines for the main error / unhandled exception
    let upper = content.to_uppercase();
    for line in upper.lines().take(30) {
        if line.contains("UNHANDLED EXCEPTION")
            || line.contains("EXCEPTION_")
            || line.contains("0XC000")
        {
            for (pattern, name) in known_patterns {
                if line.contains(pattern) {
                    return Some(name.to_string());
                }
            }
        }
    }

    None
}

// ============================================================================
// VR Log Detection
// ============================================================================

/// Detect if crash log content is from a VR game.
///
/// Checks for VR-specific markers (e.g. "Fallout4VR.exe", "Fallout4VR.esm")
/// in the log content, case-insensitively.
///
/// @param content - The crash log content to check.
/// @returns `true` if VR markers are found, `false` otherwise.
#[napi]
pub fn detect_vr_log(content: String) -> bool {
    classic_scanlog_core::detect_vr_log(&content)
}

// ============================================================================
// GPU Detection
// ============================================================================

/// GPU information detected from system specs.
#[napi(object)]
pub struct JsGpuInfo {
    /// Primary GPU name (e.g. "Nvidia AD104 [GeForce RTX 4070]")
    pub primary: String,
    /// Secondary GPU name, if present
    pub secondary: Option<String>,
    /// GPU manufacturer (e.g. "AMD", "Nvidia", "Intel", "Unknown")
    pub manufacturer: String,
    /// Rival GPU manufacturer for compatibility checks
    pub rival: Option<String>,
}

/// Detect GPU information from system specification lines.
///
/// Parses lines from the SYSTEM SPECS section of a crash log to identify
/// the primary and secondary GPUs, manufacturer, and rival vendor.
///
/// @param systemLines - Array of system specification lines from the crash log.
/// @returns A `JsGpuInfo` object with the detected GPU information.
#[napi]
pub fn detect_gpu_info(system_lines: Vec<String>) -> JsGpuInfo {
    let info = classic_scanlog_core::gpu_detector::GpuDetector::get_gpu_info(&system_lines);
    JsGpuInfo {
        primary: info.primary,
        secondary: info.secondary,
        manufacturer: info.manufacturer,
        rival: info.rival,
    }
}

// ============================================================================
// Crashgen Version Checking
// ============================================================================

/// Parsed crash generator version components.
#[napi(object)]
pub struct JsCrashgenVersionInfo {
    /// Major version number (e.g. 1 in "1.28.0")
    pub major: u32,
    /// Minor version number (e.g. 28 in "1.28.0")
    pub minor: u32,
    /// Patch version number (e.g. 0 in "1.28.0")
    pub patch: u32,
}

/// Crashgen version validation status returned to JavaScript.
#[napi(string_enum)]
pub enum JsCrashgenVersionStatus {
    /// Detected version matches one of the supported versions.
    Valid,
    /// Detected version is older than the supported range.
    Outdated,
    /// Detected version is newer than any known supported version.
    NewerThanKnown,
    /// No supported versions were provided or version parsing failed.
    NoSupportedVersion,
}

/// Parse a crash generator version string into components.
///
/// Accepts various formats: "1.28.0", "v1.28.0", "Buffout 4 v1.28.0".
/// Returns `undefined` if parsing fails.
///
/// @param versionStr - The version string to parse.
/// @returns Parsed version components, or `undefined` on failure.
#[napi]
pub fn parse_crashgen_version(version_str: String) -> Option<JsCrashgenVersionInfo> {
    classic_scanlog_core::version::CrashgenVersion::parse(&version_str).map(|v| {
        JsCrashgenVersionInfo {
            major: v.major as u32,
            minor: v.minor as u32,
            patch: v.patch as u32,
        }
    })
}

/// Check a crash generator version against a list of valid versions.
///
/// Returns one of: "Valid", "Outdated", "NewerThanKnown", "NoSupportedVersion".
///
/// @param detected - The detected version string (e.g. "1.28.6" or "Buffout 4 v1.28.6").
/// @param validVersions - Array of valid version strings to check against.
/// @returns A status string indicating the validation result.
#[napi]
pub fn check_crashgen_version_status(
    detected: String,
    valid_versions: Vec<String>,
) -> JsCrashgenVersionStatus {
    let valid_refs: Vec<&str> = valid_versions.iter().map(|s| s.as_str()).collect();
    let status =
        classic_scanlog_core::version::check_crashgen_version_status(&detected, &valid_refs);
    match status {
        classic_scanlog_core::version::CrashgenVersionStatus::Valid => {
            JsCrashgenVersionStatus::Valid
        }
        classic_scanlog_core::version::CrashgenVersionStatus::Outdated => {
            JsCrashgenVersionStatus::Outdated
        }
        classic_scanlog_core::version::CrashgenVersionStatus::NewerThanKnown => {
            JsCrashgenVersionStatus::NewerThanKnown
        }
        classic_scanlog_core::version::CrashgenVersionStatus::NoSupportedVersion => {
            JsCrashgenVersionStatus::NoSupportedVersion
        }
    }
}

// ============================================================================
// Papyrus Analysis
// ============================================================================

/// Papyrus log analysis statistics.
#[napi(object)]
pub struct JsPapyrusStats {
    /// Number of "Dumping Stacks" entries (plural)
    pub dumps: u32,
    /// Number of "Dumping Stack" entries (singular)
    pub stacks: u32,
    /// Number of warning messages
    pub warnings: u32,
    /// Number of error messages
    pub errors: u32,
    /// Total lines processed from the log file
    pub lines_processed: u32,
}

/// Analyze a Papyrus log file and return statistics.
///
/// Reads the Papyrus log at the given path and collects statistics about
/// dumps, stacks, warnings, and errors.
///
/// @param logPath - Absolute path to the Papyrus log file.
/// @returns A `JsPapyrusStats` object with the analysis results.
#[napi]
pub fn analyze_papyrus_log(log_path: String) -> napi::Result<JsPapyrusStats> {
    let mut analyzer =
        classic_scanlog_core::papyrus::PapyrusAnalyzer::new(std::path::PathBuf::from(&log_path));
    let stats = analyzer.analyze_full().map_err(to_napi_err)?;
    Ok(JsPapyrusStats {
        dumps: stats.dumps as u32,
        stacks: stats.stacks as u32,
        warnings: stats.warnings as u32,
        errors: stats.errors as u32,
        lines_processed: stats.lines_processed as u32,
    })
}
