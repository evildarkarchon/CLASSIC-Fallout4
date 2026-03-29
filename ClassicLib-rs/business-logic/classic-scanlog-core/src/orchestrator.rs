//! OrchestratorCore - Pure Rust crash log analysis orchestration (NO PyO3)
//!
//! This module provides the main orchestration layer that coordinates all analysis
//! components into a unified pipeline for processing crash logs.
//!
//! The orchestrator achieves feature parity with Python's `OrchestratorCore`, providing:
//! - Report generation with Python-identical output
//! - Version checking and validation
//! - Crash data reformatting (simplify logs)
//! - Incomplete/failed log detection with statistics
//! - Full analysis pipeline integration

use crate::crashgen_registry::{CrashgenEntry, CrashgenRegistry};
use crate::error::Result;
use crate::fcx_handler::FcxModeHandler;
use crate::formid_analyzer::FormIDAnalyzerCore;
use crate::gpu_detector::GpuDetector;
use crate::mod_detector::{
    detect_mods_double, detect_mods_important, detect_mods_single, detect_mods_solutions,
};
use crate::parser::LogParser;
use crate::plugin_analyzer::PluginAnalyzer;
use crate::record_scanner::RecordScanner;
use crate::report::ReportGenerator;
use crate::segment_key;
use crate::settings_validator::SettingsValidator;
use crate::suspect_scanner::SuspectScanner;
use crate::version::{
    CrashgenVersion, CrashgenVersionStatus, check_crashgen_version_status, crashgen_version_gen,
    is_fake_bot_compatible_buffout_version,
};
use classic_config_core::{
    CoreModEntry, ModConflictEntry, ModSolutionEntry, SuspectErrorRule, SuspectStackRule,
};
use classic_database_core::DatabasePool;
use classic_file_io_core::FileIOCore;
use classic_version_registry_core::{
    GameVersion as RegistryGameVersion, VersionInfo, get_version_registry,
};
use indexmap::IndexMap;
use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::path::Path;
use std::sync::Arc;

/// Coarse-grained scan progress phases emitted at orchestration boundaries.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ScanProgressPhase {
    /// File read and initial setup work.
    Setup,
    /// Log parsing and shared context construction.
    Parse,
    /// Analyzer execution over prepared shared data.
    Analyze,
    /// Report composition and result finalization.
    Finalize,
}

struct ScanAnalysisContext {
    processed_lines: Vec<String>,
    combined_crash_lines: Vec<String>,
    combined_crash_text: String,
    combined_crash_lower_lines: Vec<String>,
    plugin_lines: Vec<String>,
    xse_modules_for_settings: HashSet<String>,
    crashgen_settings: HashMap<String, String>,
    system_segment_lines: Vec<String>,
}

/// Resolve the effective concurrency for batch log processing.
#[must_use]
pub fn resolve_batch_concurrency(total_logs: usize, max_concurrent: Option<usize>) -> usize {
    if total_logs == 0 {
        return 1;
    }

    match max_concurrent {
        Some(n) => n.max(1),
        None => {
            let num_cpus = num_cpus::get();
            if total_logs < num_cpus {
                total_logs.max(1)
            } else {
                num_cpus.max(4)
            }
        }
    }
}

impl ScanAnalysisContext {
    fn from_processed_lines(parser: &LogParser, processed_lines: Vec<String>) -> Self {
        let processed_line_arcs: Vec<Arc<str>> = processed_lines
            .iter()
            .map(|line| Arc::from(line.as_str()))
            .collect();
        let segments = parser.parse_all_sections_arc(&processed_line_arcs);

        Self::from_arc_sections(processed_lines, &segments)
    }

    fn from_arc_sections(
        processed_lines: Vec<String>,
        segments: &HashMap<String, Vec<Arc<str>>>,
    ) -> Self {
        let combined_crash_lines: Vec<String> = [
            segment_key::CALLSTACK,
            segment_key::REGISTERS,
            segment_key::STACK_DUMP,
        ]
        .into_iter()
        .filter_map(|key| segments.get(key))
        .flat_map(|segment_lines| segment_lines.iter().map(|line| line.to_string()))
        .collect();
        let combined_crash_text = combined_crash_lines.join("\n");
        let combined_crash_lower_lines = combined_crash_lines
            .iter()
            .map(|line| line.to_lowercase())
            .collect();

        let plugin_lines = segments
            .get(segment_key::PLUGINS)
            .map(|segment_lines| segment_lines.iter().map(|line| line.to_string()).collect())
            .unwrap_or_default();

        let xse_modules_for_settings = {
            let mods = segments
                .get(segment_key::MODULES)
                .map(Vec::as_slice)
                .unwrap_or_default();
            let xse = segments
                .get(segment_key::XSE_MODULES)
                .map(Vec::as_slice)
                .unwrap_or_default();
            extract_module_names(mods.iter().chain(xse.iter()))
        };

        let crashgen_settings = segments
            .get(segment_key::SETTINGS)
            .map_or(&[][..], Vec::as_slice)
            .iter()
            .filter_map(|line| {
                let line = line.trim();
                if line.starts_with('[') {
                    return None;
                }

                line.find(':').and_then(|colon_pos| {
                    let key = line[..colon_pos].trim().to_string();
                    let value = line[colon_pos + 1..].trim().to_string();
                    if key.is_empty() {
                        None
                    } else {
                        Some((key, value))
                    }
                })
            })
            .collect();

        let system_segment_lines = segments
            .get(segment_key::SYSTEM)
            .map(|segment_lines| segment_lines.iter().map(|line| line.to_string()).collect())
            .unwrap_or_default();

        Self {
            processed_lines,
            combined_crash_lines,
            combined_crash_text,
            combined_crash_lower_lines,
            plugin_lines,
            xse_modules_for_settings,
            crashgen_settings,
            system_segment_lines,
        }
    }
}

/// Analysis configuration
///
/// Contains all necessary configuration data for analyzing crash logs.
/// This struct matches the fields from Python's `ClassicScanLogsInfo`.
#[derive(Clone)]
pub struct AnalysisConfig {
    /// Game name (e.g., "Fallout4")
    pub game: String,

    /// Registry-backed selected version metadata, if available.
    selected_version: Option<VersionInfo>,

    /// Crashgen name (e.g., "Buffout 4")
    pub crashgen_name: String,

    /// Latest crashgen version (OG/non-VR)
    pub crashgen_latest: String,

    /// Latest crashgen version for VR variant
    pub crashgen_latest_vr: String,

    /// Game version
    pub game_version: String,

    /// Game version for VR variant (if applicable)
    pub game_version_vr: String,

    /// XSE acronym (e.g., "F4SE")
    pub xse_acronym: String,

    /// Game root name (e.g., "Fallout4" from Main_Root_Name setting)
    pub game_root_name: String,

    /// CLASSIC version string (e.g., "CLASSIC v8.0.0")
    pub classic_version: String,

    /// Ignore lists (plugins, records, general)
    pub ignore_plugins: Vec<String>,
    /// Records to ignore during analysis (e.g., FormIDs, record types)
    pub ignore_records: Vec<String>,
    /// General items to ignore during analysis (catch-all ignore list)
    pub ignore_list: Vec<String>,

    /// Whether to show FormID values in reports (requires database pool)
    pub show_formid_values: bool,

    /// Whether FCX mode is enabled
    pub fcx_mode: bool,

    /// Whether to simplify logs by removing specified strings
    pub simplify_logs: bool,

    /// List of strings to remove from crash logs when simplify_logs is enabled
    pub remove_list: Vec<String>,

    /// Structured main-error suspect rules.
    pub suspect_error_rules: Vec<SuspectErrorRule>,
    /// Structured stack suspect rules.
    pub suspect_stack_rules: Vec<SuspectStackRule>,

    /// Structured core / important mod entries for recommended-mod checks
    pub mods_core: Vec<CoreModEntry>,
    /// Frequently problematic mods database for crash analysis (IndexMap preserves YAML key order)
    pub mods_freq: IndexMap<String, String>,
    /// Mod conflict entries for compatibility analysis
    pub mods_conf: Vec<ModConflictEntry>,
    /// Structured mod solution entries for fixes and workarounds.
    pub mods_solu: Vec<ModSolutionEntry>,
    /// Named records list for RecordScanner
    pub classic_records_list: Vec<String>,

    /// Per-crashgen settings registry loaded from YAML.
    ///
    /// Used by the orchestrator to resolve the `CrashgenEntry` for `SettingsValidator`.
    pub crashgen_registry: CrashgenRegistry,
}

impl AnalysisConfig {
    /// Creates a new analysis configuration with default values for all optional fields.
    ///
    /// This constructor initializes an `AnalysisConfig` with the specified game and selected
    /// game-version mode,
    /// setting all other fields (crash generator info, game versions, ignore lists, pattern dictionaries,
    /// mod databases) to empty defaults. These fields should be populated before analysis begins.
    ///
    /// # Arguments
    ///
    /// * `game` - The game name (e.g., "Fallout4", "Skyrim")
    /// * `selected_game_version` - Selected mode
    ///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", or "VR")
    ///
    /// # Returns
    ///
    /// A new `AnalysisConfig` instance with default values for all optional fields.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::AnalysisConfig;
    ///
    /// // Create configuration for Fallout 4 (non-VR)
    /// let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    ///
    /// // Populate with additional configuration
    /// config.crashgen_name = "Buffout 4".to_string();
    /// config.game_version = "1.10.163".to_string();
    /// config.xse_acronym = "F4SE".to_string();
    ///
    /// // Add ignore lists
    /// config.ignore_plugins = vec!["Fallout4.esm".to_string()];
    /// ```
    pub fn new(game: String, selected_game_version: String) -> Self {
        let selected_version =
            classic_config_core::resolve_registry_version_info(&game, &selected_game_version);

        Self {
            game,
            selected_version,
            crashgen_name: String::new(),
            crashgen_latest: String::new(),
            crashgen_latest_vr: String::new(),
            game_version: String::new(),
            game_version_vr: String::new(),
            xse_acronym: String::new(),
            game_root_name: String::new(),
            classic_version: "CLASSIC".to_string(),
            ignore_plugins: Vec::new(),
            ignore_records: Vec::new(),
            ignore_list: Vec::new(),
            show_formid_values: false,
            fcx_mode: false,
            simplify_logs: false,
            remove_list: Vec::new(),
            suspect_error_rules: Vec::new(),
            suspect_stack_rules: Vec::new(),
            mods_core: Vec::new(),
            mods_freq: IndexMap::new(),
            mods_conf: Vec::new(),
            mods_solu: Vec::new(),
            classic_records_list: Vec::new(),
            crashgen_registry: CrashgenRegistry::default(),
        }
    }
}

/// Build an `AnalysisConfig` from a [`YamlDataCore`] instance and runtime settings.
///
/// This is the canonical way to create an `AnalysisConfig` from loaded YAML data.
/// Static metadata is sourced from Version Registry (single source of truth),
/// with YAML used only as a compatibility fallback when registry data is absent.
///
/// # Arguments
///
/// * `yaml` - Reference to the loaded YAML configuration data
/// * `game` - Game identifier (e.g., "Fallout4", "Skyrim")
/// * `selected_game_version` - Selected mode
///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", or "VR")
/// * `show_formid_values` - Whether to include FormID value lookups in reports
/// * `fcx_mode` - Whether FCX (enhanced analysis) mode is enabled
/// * `simplify_logs` - Whether to remove specified strings from crash logs
/// * `remove_list` - Strings to remove when `simplify_logs` is enabled
pub fn build_analysis_config_from_yaml(
    yaml: &classic_config_core::YamlDataCore,
    game: &str,
    selected_game_version: &str,
    show_formid_values: bool,
    fcx_mode: bool,
    simplify_logs: bool,
    remove_list: Vec<String>,
) -> AnalysisConfig {
    let registry_game_id = match yaml.get_game_root_name().trim() {
        "" => game,
        root_name => root_name,
    };
    let selected_version =
        classic_config_core::resolve_registry_version_info(registry_game_id, selected_game_version);
    let game_version_vr =
        classic_config_core::resolve_registry_version_info(registry_game_id, "VR")
            .map(|info| classic_config_core::format_registry_game_version(&info.version))
            .unwrap_or_default();
    let registry_crashgen = selected_version
        .as_ref()
        .and_then(|info| info.crashgen_versions.first());

    let crashgen_name = registry_crashgen
        .map(|c| c.name.as_str())
        .filter(|name| !name.is_empty())
        .unwrap_or_else(|| yaml.get_crashgen_name())
        .to_string();
    let crashgen_latest = registry_crashgen
        .map(|c| c.version.as_str())
        .filter(|version| !version.is_empty())
        .unwrap_or(yaml.crashgen_latest_og.as_str())
        .to_string();
    let xse_acronym = selected_version
        .as_ref()
        .and_then(|info| info.xse.as_ref())
        .map(|xse| xse.acronym.as_str())
        .filter(|acronym| !acronym.is_empty())
        .unwrap_or(yaml.xse_acronym.as_str())
        .to_string();
    let game_version = selected_version
        .as_ref()
        .map(|info| classic_config_core::format_registry_game_version(&info.version))
        .unwrap_or_else(|| yaml.game_version.clone());

    AnalysisConfig {
        game: game.to_string(),
        selected_version,
        crashgen_name,
        crashgen_latest,
        crashgen_latest_vr: String::new(), // VR-specific data now provided by Version Registry
        game_version,
        game_version_vr,
        xse_acronym,
        game_root_name: yaml.get_game_root_name().to_string(),
        classic_version: yaml.classic_version.clone(),
        ignore_plugins: yaml.game_ignore_plugins.clone(),
        ignore_records: yaml.game_ignore_records.clone(),
        ignore_list: yaml.ignore_list.clone(),
        show_formid_values,
        fcx_mode,
        simplify_logs,
        remove_list,
        suspect_error_rules: yaml.suspect_error_rules.clone(),
        suspect_stack_rules: yaml.suspect_stack_rules.clone(),
        mods_core: yaml.game_mods_core.clone(),
        mods_freq: yaml.game_mods_freq.clone(),
        mods_conf: yaml.game_mods_conf.clone(),
        mods_solu: yaml.game_mods_solu.clone(),
        classic_records_list: yaml.classic_records_list.clone(),
        crashgen_registry: build_crashgen_registry(&yaml.crashgen_registry),
    }
}

/// Build a `CrashgenRegistry` from raw `CrashgenEntryRaw` data loaded from YAML.
fn build_crashgen_registry(
    raw: &std::collections::HashMap<String, classic_config_core::CrashgenEntryRaw>,
) -> CrashgenRegistry {
    use crate::crashgen_registry::CheckId;
    use std::collections::HashMap;

    let mut entries: HashMap<String, CrashgenEntry> = HashMap::new();
    let mut default_entry = CrashgenEntry::default_entry();

    for (name, raw_entry) in raw {
        let ignore_keys: std::collections::HashSet<String> =
            raw_entry.ignore_keys.iter().cloned().collect();
        let checks: Vec<CheckId> = raw_entry
            .checks
            .iter()
            .filter_map(|s| CheckId::parse(s))
            .collect();

        let entry = CrashgenEntry {
            display_section: raw_entry.display_section.clone(),
            ignore_keys,
            checks,
            settings_rules: raw_entry.settings_rules.clone(),
        };

        if name == "default" {
            default_entry = entry;
        } else {
            entries.insert(name.clone(), entry);
        }
    }

    CrashgenRegistry::new(entries, default_entry)
}

/// Analysis result for a single crash log
///
/// Contains all analysis results including the generated report,
/// statistics, and any errors encountered. This struct matches the
/// return type from Python's `OrchestratorCore.process_crash_log()`.
#[derive(Clone)]
pub struct AnalysisResult {
    /// Path to the log file that was analyzed
    pub log_path: String,

    /// Generated report lines
    pub report_lines: Vec<String>,

    /// Whether analysis succeeded
    pub success: bool,

    /// Error message if analysis failed
    pub error: Option<String>,

    /// Processing time in microseconds (for sub-millisecond precision)
    pub processing_time_us: u64,

    /// Processing time in milliseconds (derived from microseconds, minimum 1ms for non-zero processing)
    pub processing_time_ms: u64,

    /// Number of FormIDs found
    pub formid_count: usize,

    /// Number of plugins detected
    pub plugin_count: usize,

    /// Number of suspect patterns matched
    pub suspect_count: usize,

    // === Python-compatible statistics (Counter[str]) ===
    /// Number of logs successfully scanned (always 1 for single log, decremented on failure)
    pub scanned: u32,

    /// Number of logs detected as incomplete (missing plugin segment)
    pub incomplete: u32,

    /// Number of logs that failed to scan (too short or parse error)
    pub failed: u32,

    /// Whether the scan triggered a failure condition (for Python compatibility)
    pub trigger_scan_failed: bool,
}

impl AnalysisResult {
    /// Creates a new successful analysis result with the generated report and statistics.
    ///
    /// Use this constructor when crash log analysis completes successfully. The result will have
    /// `success = true` and no error message. Statistics fields (formid_count, plugin_count, suspect_count)
    /// are initialized to 0 and should be populated after analysis.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the crash log file that was analyzed
    /// * `report_lines` - Generated report lines from the analysis
    /// * `processing_time_ms` - Time taken to process the log in milliseconds
    ///
    /// # Returns
    ///
    /// A new `AnalysisResult` instance marked as successful with the provided data.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::AnalysisResult;
    ///
    /// let report = vec![
    ///     "Analysis of: crash-2024-01-01.log".to_string(),
    ///     "Segments found: 5".to_string(),
    /// ];
    ///
    /// let result = AnalysisResult::success(
    ///     "crash-2024-01-01.log".to_string(),
    ///     report,
    ///     150_000, // Processing took 150ms (150,000 microseconds)
    /// );
    ///
    /// assert!(result.success);
    /// assert!(result.error.is_none());
    /// ```
    pub fn success(log_path: String, report_lines: Vec<String>, processing_time_us: u64) -> Self {
        // Calculate milliseconds from microseconds, with minimum of 1ms for non-zero processing
        let processing_time_ms = if processing_time_us > 0 {
            (processing_time_us / 1000).max(1)
        } else {
            0
        };
        Self {
            log_path,
            report_lines,
            success: true,
            error: None,
            processing_time_us,
            processing_time_ms,
            formid_count: 0,
            plugin_count: 0,
            suspect_count: 0,
            // Default statistics - will be updated during processing
            scanned: 1,
            incomplete: 0,
            failed: 0,
            trigger_scan_failed: false,
        }
    }

    /// Creates a new failed analysis result with an error message.
    ///
    /// Use this constructor when crash log analysis fails due to an error (file I/O error,
    /// parsing error, etc.). The result will have `success = false`, an empty report,
    /// zero processing time, and all statistics set to 0.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the crash log file that failed to analyze
    /// * `error` - Error message describing why the analysis failed
    ///
    /// # Returns
    ///
    /// A new `AnalysisResult` instance marked as failed with the error message.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::AnalysisResult;
    ///
    /// let result = AnalysisResult::failure(
    ///     "crash-2024-01-01.log".to_string(),
    ///     "File not found or inaccessible".to_string(),
    /// );
    ///
    /// assert!(!result.success);
    /// assert!(result.error.is_some());
    /// assert_eq!(result.report_lines.len(), 0);
    /// assert_eq!(result.processing_time_ms, 0);
    /// assert_eq!(result.processing_time_us, 0);
    /// ```
    pub fn failure(log_path: String, error: String) -> Self {
        Self {
            log_path,
            report_lines: Vec::new(),
            success: false,
            error: Some(error),
            processing_time_us: 0,
            processing_time_ms: 0,
            formid_count: 0,
            plugin_count: 0,
            suspect_count: 0,
            // Failed logs have scanned=0, failed=1
            scanned: 0,
            incomplete: 0,
            failed: 1,
            trigger_scan_failed: true,
        }
    }

    /// Mark this result as having an incomplete log (missing plugin segment).
    ///
    /// This updates the statistics to indicate the log was incomplete.
    pub fn mark_incomplete(&mut self) {
        self.incomplete = 1;
    }

    /// Mark this result as failed (too short or parse error).
    ///
    /// This updates the statistics to indicate scan failure.
    pub fn mark_failed(&mut self) {
        self.scanned = 0;
        self.failed = 1;
        self.trigger_scan_failed = true;
    }
}

/// Extract module names (DLL filenames) from module segment lines
///
/// This function extracts just the module filename (e.g., "f4se_loader.dll")
/// from module lines that may include version info (e.g., "f4se_loader.dll v0.6.20").
///
/// # Arguments
///
/// * `module_lines` - Lines from the MODULES/XSE_MODULES segments
///
/// # Returns
///
/// A HashSet of lowercase module names (DLL filenames only)
fn extract_module_names<'a, T, I>(module_lines: I) -> HashSet<String>
where
    T: AsRef<str> + 'a,
    I: IntoIterator<Item = &'a T>,
{
    // Pre-compiled regex pattern to extract module name (everything up to .dll)
    // Pattern: (.*?\.dll)\s*v?.* - captures filename.dll, ignoring version info
    static MODULE_PATTERN: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"(?i)(.*?\.dll)\s*v?.*").unwrap());

    let mut result = HashSet::new();

    for line in module_lines {
        let text = (*line).as_ref().trim();
        if text.is_empty() {
            continue;
        }

        if let Some(captures) = MODULE_PATTERN.captures(text) {
            if let Some(module_name) = captures.get(1) {
                result.insert(module_name.as_str().to_lowercase());
            }
        } else {
            // If no pattern match, add the whole line
            result.insert(text.to_lowercase());
        }
    }

    result
}

/// Main orchestrator for crash log analysis (Pure Rust - NO PyO3)
///
/// Coordinates all analysis components to process crash logs from start to finish.
/// Uses async I/O and parallel processing for maximum performance.
///
/// The orchestrator supports optional database pool integration for FormID lookups,
/// context manager pattern for resource management, and loadorder.txt override support.
pub struct OrchestratorCore {
    config: AnalysisConfig,
    file_io: FileIOCore,
    parser: LogParser,
    plugin_analyzer: Option<PluginAnalyzer>,
    formid_analyzer: FormIDAnalyzerCore,
    suspect_scanner: Option<SuspectScanner>,
    /// Record scanner for named record detection
    record_scanner: Option<RecordScanner>,
    /// Settings validator for crash generator settings
    settings_validator: SettingsValidator,
    /// Optional database pool for async FormID lookups
    db_pool: Option<Arc<DatabasePool>>,
    /// Whether the orchestrator has been initialized via async_enter
    initialized: bool,
}

impl OrchestratorCore {
    fn has_real_buffout_module(xse_modules: &HashSet<String>) -> bool {
        xse_modules.contains("buffout4.dll") || xse_modules.contains("buffout4ae.dll")
    }

    fn is_fake_bot_compatible_mode(
        crashgen_version_str: &str,
        xse_modules: &HashSet<String>,
    ) -> bool {
        is_fake_bot_compatible_buffout_version(crashgen_version_str)
            || (crashgen_version_str
                .to_ascii_lowercase()
                .contains("buffout")
                && !Self::has_real_buffout_module(xse_modules))
    }

    /// Build a settings validator from `AnalysisConfig`.
    fn settings_validator_from_config(config: &AnalysisConfig) -> SettingsValidator {
        Self::settings_validator_for_crashgen(config, &config.crashgen_name)
    }

    /// Build a settings validator for a specific crashgen name.
    fn settings_validator_for_crashgen(
        config: &AnalysisConfig,
        crashgen_name: &str,
    ) -> SettingsValidator {
        let entry = config.crashgen_registry.lookup(crashgen_name).clone();
        SettingsValidator::new(crashgen_name.to_string(), entry)
    }

    /// Resolve the effective crashgen name for settings validation for a single log.
    fn resolve_effective_crashgen_name(
        &self,
        crashgen_version_str: &str,
        xse_modules: &HashSet<String>,
    ) -> String {
        if crashgen_version_str
            .to_ascii_lowercase()
            .contains("addictol")
        {
            return "Addictol".to_string();
        }

        let has_addictol = xse_modules.contains("addictol.dll");
        let has_buffout = Self::has_real_buffout_module(xse_modules);
        if has_addictol && !has_buffout {
            return "Addictol".to_string();
        }

        self.config.crashgen_name.clone()
    }

    /// Creates a new crash log analysis orchestrator with the specified configuration.
    ///
    /// This constructor initializes the orchestrator with:
    /// - The provided analysis configuration
    /// - A new `FileIOCore` instance with UTF-8 encoding and ignore error handling
    /// - A new `LogParser` instance for pattern matching and segmentation
    ///
    /// The orchestrator is ready to process crash logs immediately after creation.
    ///
    /// # Arguments
    ///
    /// * `config` - Analysis configuration containing game settings, ignore lists, and pattern dictionaries
    ///
    /// # Returns
    ///
    /// Returns `Ok(OrchestratorCore)` if initialization succeeds.
    ///
    /// # Errors
    ///
    /// Returns `Err(ScanLogError)` if:
    /// - `LogParser` initialization fails (invalid regex patterns)
    /// - `FileIOCore` initialization fails (invalid encoding parameters)
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// // Create configuration
    /// let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    /// config.crashgen_name = "Buffout 4".to_string();
    /// config.game_version = "1.10.163".to_string();
    ///
    /// // Create orchestrator
    /// let orchestrator = OrchestratorCore::new(config)?;
    ///
    /// // Ready to process crash logs
    /// # Ok(())
    /// # }
    /// ```
    pub fn new(config: AnalysisConfig) -> Result<Self> {
        // Plugin parsing is needed for all mod-detection paths, even when the
        // ignore lists are empty.
        let plugin_analyzer = Some(PluginAnalyzer::new(
            config.ignore_plugins.clone(),
            config.ignore_list.clone(),
            config.crashgen_name.clone(),
            config.game_version.clone(),
            config.game_version_vr.clone(),
        )?);

        // Initialize suspect scanner if suspect patterns are available
        let suspect_scanner =
            if !config.suspect_error_rules.is_empty() || !config.suspect_stack_rules.is_empty() {
                Some(SuspectScanner::new(
                    config.suspect_error_rules.clone(),
                    config.suspect_stack_rules.clone(),
                ))
            } else {
                None
            };

        // Extract values before moving config
        let show_formid_values = config.show_formid_values;
        let crashgen_name = config.crashgen_name.clone();
        let mods_core = config.mods_core.clone();
        let mods_freq = config.mods_freq.clone();
        let mods_conf = config.mods_conf.clone();

        // Initialize record scanner if we have records list
        let record_scanner = if !config.classic_records_list.is_empty() {
            Some(RecordScanner::new(
                config.classic_records_list.clone(),
                config.ignore_records.clone(),
                config.crashgen_name.clone(),
            ))
        } else {
            None
        };

        // Resolve per-crashgen registry entry and build the settings validator.
        // The entry is resolved once at construction time from the crashgen name.
        let settings_validator = Self::settings_validator_from_config(&config);

        Ok(Self {
            config,
            file_io: FileIOCore::new("utf-8", "ignore", 100, 50),
            parser: LogParser::new(None)?,
            plugin_analyzer,
            formid_analyzer: FormIDAnalyzerCore::new(
                None, // No database pool initially
                show_formid_values,
                crashgen_name,
                mods_core,
                mods_freq,
                mods_conf,
            )?,
            suspect_scanner,
            record_scanner,
            settings_validator,
            db_pool: None,
            initialized: false,
        })
    }

    /// Builder method to attach a database pool for async FormID lookups.
    ///
    /// The database pool enables rich FormID resolution, providing descriptive names
    /// for FormIDs found in crash logs. Without a database pool, only FormID hex values
    /// and plugin associations are shown.
    ///
    /// # Arguments
    ///
    /// * `pool` - The database connection pool to use for FormID lookups
    ///
    /// # Returns
    ///
    /// The orchestrator instance with the database pool attached.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
    /// use classic_database_core::DatabasePool;
    /// use std::sync::Arc;
    /// use std::time::Duration;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    /// let db_pool = DatabasePool::new(Some(10), Duration::from_secs(300), "Fallout4".to_string());
    ///
    /// let orchestrator = OrchestratorCore::new(config)?
    ///     .with_database_pool(Arc::new(db_pool))?;
    /// # Ok(())
    /// # }
    /// ```
    pub fn with_database_pool(mut self, pool: Arc<DatabasePool>) -> Result<Self> {
        self.formid_analyzer = FormIDAnalyzerCore::new(
            Some(pool.clone()),
            self.config.show_formid_values,
            self.config.crashgen_name.clone(),
            self.config.mods_core.clone(),
            self.config.mods_freq.clone(),
            self.config.mods_conf.clone(),
        )?;
        self.db_pool = Some(pool);
        Ok(self)
    }

    /// Attaches a database pool for async FormID lookups on an existing orchestrator.
    ///
    /// Unlike [`with_database_pool`](Self::with_database_pool) which consumes `self` (builder pattern),
    /// this method takes `&mut self` and can be called after construction. This is
    /// needed when the orchestrator is already owned (e.g., inside a PyO3 `#[pyclass]`).
    ///
    /// # Arguments
    ///
    /// * `pool` - The database connection pool to use for FormID lookups
    pub fn attach_database_pool(&mut self, pool: Arc<DatabasePool>) -> Result<()> {
        self.formid_analyzer = FormIDAnalyzerCore::new(
            Some(pool.clone()),
            self.config.show_formid_values,
            self.config.crashgen_name.clone(),
            self.config.mods_core.clone(),
            self.config.mods_freq.clone(),
            self.config.mods_conf.clone(),
        )?;
        self.db_pool = Some(pool);
        Ok(())
    }

    /// Returns whether this orchestrator has a database pool attached.
    ///
    /// This can be used to determine if rich FormID resolution is available.
    #[must_use]
    pub fn has_database_pool(&self) -> bool {
        self.db_pool.is_some()
    }

    /// Returns a reference to the database pool, if available.
    #[must_use]
    pub fn database_pool(&self) -> Option<&Arc<DatabasePool>> {
        self.db_pool.as_ref()
    }

    /// Async context manager entry - initializes resources.
    ///
    /// This method should be called before processing logs to initialize any
    /// async resources. Currently initializes the database pool if paths are provided.
    ///
    /// # Arguments
    ///
    /// * `db_paths` - Optional list of database file paths to initialize
    ///
    /// # Returns
    ///
    /// Returns `Ok(())` on success.
    ///
    /// # Errors
    ///
    /// Returns `Err(ScanLogError)` if database initialization fails.
    pub async fn async_enter(&mut self, db_paths: Option<Vec<std::path::PathBuf>>) -> Result<()> {
        if let (Some(pool), Some(paths)) = (&self.db_pool, db_paths) {
            pool.initialize(paths).await.map_err(|e| {
                crate::error::ScanLogError::ParseError(format!("Database init failed: {}", e))
            })?;
        }
        self.initialized = true;
        Ok(())
    }

    /// Async context manager exit - cleans up resources.
    ///
    /// This method should be called after processing is complete to clean up
    /// any async resources. The database pool is managed by the singleton pattern
    /// and is NOT closed here to allow reuse.
    ///
    /// # Returns
    ///
    /// Returns `Ok(())` on success.
    pub async fn async_exit(&mut self) -> Result<()> {
        // Database pool is managed by singleton and not closed here
        // This allows reuse across multiple orchestrator instances
        self.initialized = false;
        Ok(())
    }

    /// Returns whether the orchestrator has been initialized via async_enter.
    #[must_use]
    pub fn is_initialized(&self) -> bool {
        self.initialized
    }

    /// Asynchronously processes a single crash log file and generates an analysis report.
    ///
    /// This function performs a complete analysis pipeline:
    /// 1. Reads the crash log file using async I/O
    /// 2. Splits the content into lines
    /// 3. Parses the log into segments using SIMD-optimized parsing
    /// 4. Generates a basic analysis report with segment count
    /// 5. Measures and reports processing time
    ///
    /// The function uses efficient async I/O and parallel processing where applicable.
    /// More detailed analysis (FormID extraction, plugin detection, mod detection) can be
    /// added by extending the implementation.
    ///
    /// # Arguments
    ///
    /// * `log_path` - Path to the crash log file to analyze
    ///
    /// # Returns
    ///
    /// Returns `Ok(AnalysisResult)` containing:
    /// - Generated report lines
    /// - Processing statistics
    /// - Processing time in milliseconds
    ///
    /// # Errors
    ///
    /// Returns `Err(ScanLogError)` if:
    /// - File cannot be read (not found, permission denied, etc.)
    /// - File encoding cannot be detected or converted
    /// - Parsing fails due to invalid log format
    ///
    /// # Performance
    ///
    /// - Uses async I/O for non-blocking file operations
    /// - SIMD-optimized log segmentation (20-40x faster than Python)
    /// - Typical processing time: 50-200ms per log file
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    /// let orchestrator = OrchestratorCore::new(config)?;
    ///
    /// let result = orchestrator.process_log("crash-2024-01-01.log".to_string()).await?;
    ///
    /// if result.success {
    ///     println!("Analysis completed in {}ms", result.processing_time_ms);
    ///     for line in result.report_lines {
    ///         print!("{}", line);
    ///     }
    /// }
    /// # Ok(())
    /// # }
    /// ```
    pub async fn process_log(&self, log_path: String) -> Result<AnalysisResult> {
        self.process_log_with_progress(log_path, |_| {}).await
    }

    /// Processes a single log while reporting coarse phase transitions.
    pub async fn process_log_with_progress<F>(
        &self,
        log_path: String,
        mut on_phase: F,
    ) -> Result<AnalysisResult>
    where
        F: FnMut(ScanProgressPhase),
    {
        use crate::report::{ReportComposer, ReportFragment};

        let start_time = std::time::Instant::now();
        let diagnostics_enabled = std::env::var_os("CLASSIC_SCAN_DIAGNOSTICS").is_some();
        let mut phase_started = diagnostics_enabled.then_some(start_time);
        let mut phase_timings_us = diagnostics_enabled.then(Vec::new);

        let mut enter_phase = |phase: ScanProgressPhase| {
            if let (Some(phase_started), Some(phase_timings_us)) =
                (phase_started.as_mut(), phase_timings_us.as_mut())
            {
                let now = std::time::Instant::now();
                if let Some((_, last_elapsed)) = phase_timings_us.last_mut() {
                    let elapsed_us = now.duration_since(*phase_started).as_micros() as u64;
                    *last_elapsed = elapsed_us;
                }
                *phase_started = now;
                phase_timings_us.push((phase, 0));
            }
            on_phase(phase);
        };

        enter_phase(ScanProgressPhase::Setup);

        // Read log file
        use std::path::Path;
        let log_content = self.file_io.read_file(Path::new(&log_path)).await?;

        // Convert to lines and apply preprocessing (matches Python's _reformat_crash_data_inline)
        // This handles:
        // 1. Removing lines containing strings from remove_list (if simplify_logs enabled)
        // 2. Normalizing bracket padding in PLUGINS section (e.g., "[ 1]" -> "[01]")
        let raw_lines: Vec<String> = log_content.lines().map(String::from).collect();
        let processed_lines = self.reformat_crash_data_inline(&raw_lines);

        enter_phase(ScanProgressPhase::Parse);
        let context = ScanAnalysisContext::from_processed_lines(&self.parser, processed_lines);

        // Create ReportComposer for proper formatting
        let mut composer = ReportComposer::new();

        // Statistics
        let mut formid_count = 0;
        let mut plugin_count = 0;
        let mut suspect_count = 0;

        // Extract filename from path for header
        let crashlog_filename = Path::new(&log_path)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or(&log_path);

        // Extract header info (crashgen version, main error) from the raw processed lines
        // We use processed_lines because header is in the first ~20 lines before segmentation
        let header_info = self
            .parser
            .parse_crash_header(&context.processed_lines)
            .unwrap_or_default();

        // Get crashgen version from header info
        let crashgen_version_str = header_info
            .get("crashgen_version")
            .cloned()
            .unwrap_or_default();

        let fake_bot_compatible_mode = Self::is_fake_bot_compatible_mode(
            &crashgen_version_str,
            &context.xse_modules_for_settings,
        );

        let effective_crashgen_name = if fake_bot_compatible_mode {
            self.config.crashgen_name.clone()
        } else {
            self.resolve_effective_crashgen_name(
                &crashgen_version_str,
                &context.xse_modules_for_settings,
            )
        };

        // Create ReportGenerator for this log using effective crashgen name.
        let report_gen = self.create_report_generator_with_crashgen_name(&effective_crashgen_name);

        // Generate header
        composer.add(report_gen.generate_header(crashlog_filename));

        // Get detected game version from header info (used for list-based version validation)
        let detected_game_version_str =
            header_info.get("game_version").cloned().unwrap_or_default();

        // Get main error - from header parsing or fallback to first "Unhandled exception" line
        let main_error = header_info.get("main_error").cloned().unwrap_or_else(|| {
            // Fallback: search processed_lines for Unhandled exception
            context
                .processed_lines
                .iter()
                .find(|line| line.starts_with("Unhandled exception"))
                .cloned()
                .unwrap_or_default()
        });

        // Check crashgen version status using list-based validation for the detected game version
        let crashgen_status = if crashgen_version_str.trim().is_empty() || fake_bot_compatible_mode
        {
            None
        } else {
            let (_parsed, status) = self.check_crashgen_version_for_detected_game(
                &crashgen_version_str,
                &detected_game_version_str,
            );
            Some(status)
        };

        let crashgen_version = {
            let parsed = crashgen_version_gen(&crashgen_version_str);
            if parsed.major == 0 && parsed.minor == 0 && parsed.patch == 0 {
                None
            } else {
                Some(parsed.to_tuple())
            }
        };
        let config_layout = self.derive_scanlog_config_layout(&detected_game_version_str);

        enter_phase(ScanProgressPhase::Analyze);

        // Parse crashgen settings once so rule buckets can influence report placement.
        let settings_validator = if !context.crashgen_settings.is_empty() {
            if effective_crashgen_name.eq_ignore_ascii_case(&self.config.crashgen_name) {
                self.settings_validator.clone()
            } else {
                Self::settings_validator_for_crashgen(&self.config, &effective_crashgen_name)
            }
        } else {
            self.settings_validator.clone()
        };

        let mut error_information_fragments: Vec<ReportFragment> = Vec::new();
        let mut settings_fragments: Vec<ReportFragment> = Vec::new();
        if !fake_bot_compatible_mode
            && !context.crashgen_settings.is_empty()
            && let Ok(bucketed_settings_fragments) = settings_validator.scan_all_settings_bucketed(
                &context.crashgen_settings,
                &context.xse_modules_for_settings,
                crashgen_version,
                config_layout,
            )
        {
            for bucketed_fragment in bucketed_settings_fragments {
                match bucketed_fragment.bucket {
                    classic_crashgen_settings_core::RuleReportBucket::Settings => {
                        settings_fragments.push(bucketed_fragment.fragment);
                    }
                    classic_crashgen_settings_core::RuleReportBucket::ErrorInformation => {
                        error_information_fragments.push(bucketed_fragment.fragment);
                    }
                }
            }
        }

        // Generate error section
        let error_section = report_gen.generate_error_section_with_status_and_fake_mode(
            &main_error,
            &crashgen_version_str,
            crashgen_status,
            fake_bot_compatible_mode,
        );
        composer.add(Self::append_error_information_fragments(
            error_section,
            error_information_fragments,
        ));

        // Store plugins for mod detection - IndexMap preserves load order for Python parity
        let mut plugins_map: Option<IndexMap<String, String>> = None;

        // Extract plugins from segments (if plugin analyzer is available)
        if let Some(ref analyzer) = self.plugin_analyzer {
            if !context.plugin_lines.is_empty() {
                // Scan plugins using the analyzer (limit flags unused for now, may need in future)
                if let Ok((plugins, _limit_triggered, _limit_disabled)) = analyzer
                    .loadorder_scan_log(
                        &context.plugin_lines,
                        Some(self.config.game_version.as_str()),
                        Some(self.config.crashgen_latest.as_str()),
                    )
                {
                    plugin_count = plugins.len();
                    // Store plugins for mod detection
                    plugins_map = Some(plugins);
                }
            }
        }

        // Scan for suspects (if suspect scanner is available)
        let mut found_suspect = false;
        let mut suspect_fragments: Vec<ReportFragment> = Vec::new();

        if let Some(ref scanner) = self.suspect_scanner {
            // Use the main_error extracted from header parsing (not settings segment!)
            // Use combined crash data (CALLSTACK + REGISTERS + STACK_DUMP) for suspect scanning
            let max_warn_length = 50; // Default width for formatting

            // Scan for error suspects (using header-extracted main_error)
            let (error_fragment, error_found) = scanner
                .suspect_scan_mainerror(&main_error, max_warn_length)
                .unwrap_or_else(|_| (ReportFragment::empty(), false));

            // Scan for stack suspects (using header-extracted main_error)
            let (stack_fragment, stack_found) = scanner
                .suspect_scan_stack(&main_error, &context.combined_crash_text, max_warn_length)
                .unwrap_or_else(|_| (ReportFragment::empty(), false));

            // Check for DLL crash pattern (using header-extracted main_error)
            let dll_fragment = SuspectScanner::check_dll_crash(&main_error)
                .unwrap_or_else(|_| ReportFragment::empty());

            if error_found {
                suspect_fragments.push(error_fragment);
                found_suspect = true;
            }

            if stack_found {
                suspect_fragments.push(stack_fragment);
                found_suspect = true;
            }

            if !dll_fragment.is_empty() {
                suspect_fragments.push(dll_fragment);
                found_suspect = true;
            }

            suspect_count = suspect_fragments.len();
        }

        // Add suspect section
        composer.add(report_gen.generate_suspect_section_header());
        for fragment in suspect_fragments {
            composer.add(fragment);
        }
        composer.add(report_gen.generate_suspect_found_footer(found_suspect));

        // Add FCX mode notice
        let fcx_handler = if self.config.fcx_mode {
            FcxModeHandler::enabled()
        } else {
            FcxModeHandler::disabled()
        };
        composer.add(fcx_handler.get_fcx_messages());

        if !settings_fragments.is_empty() {
            composer.add(report_gen.generate_settings_section_header());
            for settings_fragment in settings_fragments {
                composer.add(settings_fragment);
            }
        }

        // Mod detection (if we have plugin data)
        if let Some(ref plugins) = plugins_map {
            // Extract GPU vendor from system segment
            let user_gpu_string: Option<String> = {
                if context.system_segment_lines.is_empty() {
                    None
                } else {
                    let gpu_info = GpuDetector::get_gpu_info(&context.system_segment_lines);
                    let mfr = gpu_info.manufacturer.as_str();
                    if mfr == "Unknown" {
                        None
                    } else {
                        Some(mfr.to_lowercase())
                    }
                }
            };
            let user_gpu = user_gpu_string.as_deref();

            // Extract XSE modules from combined MODULES+XSE_MODULES (task 4.5)
            // Check for conflicting mods
            if !self.config.mods_conf.is_empty() {
                if let Ok(conflict_lines) =
                    detect_mods_double(&self.config.mods_conf, plugins.clone())
                {
                    if !conflict_lines.is_empty() {
                        composer.add(
                            report_gen.generate_mod_check_header("May Conflict With Each Other"),
                        );
                        composer.add(ReportFragment::from_lines(conflict_lines));
                    }
                }
            }

            // Check for frequently problematic mods
            if !self.config.mods_freq.is_empty() {
                if let Ok(freq_lines) =
                    detect_mods_single(self.config.mods_freq.clone(), plugins.clone())
                {
                    if !freq_lines.is_empty() {
                        composer.add(
                            report_gen.generate_mod_check_header("Can Cause Frequent Crashes"),
                        );
                        composer.add(ReportFragment::from_lines(freq_lines));
                    }
                }
            }

            // Check for mods with known solutions
            if !self.config.mods_solu.is_empty() {
                if let Ok(solu_lines) = detect_mods_solutions(&self.config.mods_solu, plugins) {
                    if !solu_lines.is_empty() {
                        composer.add(report_gen.generate_mod_check_header("HAVE SOLUTIONS"));
                        composer.add(ReportFragment::from_lines(solu_lines));
                    }
                }
            }

            // Check for important core mods with GPU considerations
            if !self.config.mods_core.is_empty() {
                if let Ok(important_lines) = detect_mods_important(
                    &self.config.mods_core,
                    plugins,
                    user_gpu,
                    &context.xse_modules_for_settings,
                ) {
                    if !important_lines.is_empty() {
                        // Use direct header to match Python format exactly
                        composer.add(ReportFragment::from_lines(vec![
                            "### Checking for Important Mods\n\n".to_string(),
                        ]));
                        composer.add(ReportFragment::from_lines(important_lines));
                    }
                }
            }
        }

        // Add Plugin-related Errors section (only when plugins are detected - matches Python behavior)
        // This section uses plugin_match to find plugins mentioned in the crash stack
        if let Some(ref analyzer) = self.plugin_analyzer {
            if let Some(ref plugins) = plugins_map {
                // Only show section if we have plugins to check (matches Python behavior)
                if !plugins.is_empty() {
                    // Convert plugins to lowercase set for matching
                    let crashlog_plugins_lower: HashSet<String> =
                        plugins.keys().map(|k| k.to_lowercase()).collect();

                    // Call plugin_match to find plugins in crash stack
                    if let Ok(plugin_match_lines) = analyzer
                        .plugin_match_with_crashgen_name_from_lowered(
                            &context.combined_crash_lower_lines,
                            &crashlog_plugins_lower,
                            &effective_crashgen_name,
                        )
                    {
                        // Add the header and the plugin match results
                        composer.add(report_gen.generate_plugin_suspect_header());
                        composer.add(ReportFragment::from_lines(plugin_match_lines));
                    }
                }
            }
        }

        // Extract FormIDs from callstack segment (task 4.4)
        // FormIDs are ALWAYS shown regardless of show_formid_values setting.
        if !context.combined_crash_lines.is_empty() {
            // Extract FormIDs using FormIDAnalyzerCore
            let formids = self
                .formid_analyzer
                .extract_formids(context.combined_crash_lines.clone());
            formid_count = formids.len();

            if formid_count > 0 {
                // Match FormIDs against plugins for proper formatting
                // Format: plugin_name | FormID (or plugin_name | FormID | db_value)
                let empty_plugins = IndexMap::new();
                let plugins_ref = plugins_map.as_ref().unwrap_or(&empty_plugins);

                let formid_report_lines = self
                    .formid_analyzer
                    .formid_match_with_crashgen_name(formids, plugins_ref, &effective_crashgen_name)
                    .await?;

                composer.add(report_gen.generate_formid_section_header());
                composer.add(ReportFragment::from_lines(formid_report_lines));
            }
        }

        // Add Named Records section (scan callstack for named records) (task 4.4)
        if let Some(ref record_scanner) = self.record_scanner {
            if !context.combined_crash_lines.is_empty() {
                let (record_report, _matches) = record_scanner
                    .scan_named_records_with_crashgen_name_and_lowercase(
                        &context.combined_crash_lines,
                        &context.combined_crash_lower_lines,
                        &effective_crashgen_name,
                    );
                if !record_report.is_empty() {
                    composer.add(report_gen.generate_record_section_header());
                    composer.add(ReportFragment::from_lines(record_report));
                }
            }
        }

        enter_phase(ScanProgressPhase::Finalize);

        composer.add(report_gen.generate_footer());

        // Compose final report
        let final_report = composer.compose();
        let report_lines = final_report.to_list();

        if let (Some(phase_started), Some(phase_timings_us)) =
            (phase_started.as_ref(), phase_timings_us.as_mut())
            && let Some((_, last_elapsed)) = phase_timings_us.last_mut()
        {
            *last_elapsed = std::time::Instant::now()
                .duration_since(*phase_started)
                .as_micros() as u64;
        }

        let elapsed_us = start_time.elapsed().as_micros() as u64;
        let mut result = AnalysisResult::success(log_path, report_lines, elapsed_us);

        // Update statistics
        result.formid_count = formid_count;
        result.plugin_count = plugin_count;
        result.suspect_count = suspect_count;

        if let Some(phase_timings_us) = phase_timings_us.as_ref() {
            let phase_summary = phase_timings_us
                .iter()
                .map(|(phase, elapsed_us)| format!("{phase:?}={elapsed_us}us"))
                .collect::<Vec<_>>()
                .join(", ");
            log::debug!(
                "scan diagnostics [{}]: total_us={}, phases=[{}]",
                result.log_path,
                elapsed_us,
                phase_summary
            );
        }

        Ok(result)
    }

    /// Asynchronously processes multiple crash log files in parallel.
    ///
    /// This function processes a batch of crash logs concurrently using bounded parallelism,
    /// collecting all results into a vector. Each log is analyzed independently, and failures
    /// don't stop processing of remaining logs. Failed analyses are returned as `AnalysisResult`
    /// instances with `success = false` and error messages.
    ///
    /// # Arguments
    ///
    /// * `log_paths` - Vector of paths to crash log files to analyze
    /// * `max_concurrent` - Optional maximum number of concurrent log processing tasks.
    ///   If `None`, uses adaptive concurrency based on CPU count and batch size.
    ///   If `Some(n)`, uses exactly `n` concurrent tasks (minimum 1).
    ///
    /// # Returns
    ///
    /// Returns a `Vec<AnalysisResult>` with one result per input log path.
    /// Note: Results may not be in the same order as input due to parallel processing.
    /// Failed analyses are included as failure results rather than being filtered out.
    ///
    /// # Performance
    ///
    /// - Parallel processing with bounded concurrency
    /// - Each log: ~50-200ms (SIMD-optimized parsing)
    /// - Near-linear speedup with multiple CPU cores when `max_concurrent` allows
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    /// let orchestrator = OrchestratorCore::new(config)?;
    ///
    /// let logs = vec![
    ///     "crash-2024-01-01.log".to_string(),
    ///     "crash-2024-01-02.log".to_string(),
    ///     "crash-2024-01-03.log".to_string(),
    /// ];
    ///
    /// // Auto-detect optimal concurrency
    /// let results = orchestrator.process_logs_batch(logs.clone(), None).await;
    ///
    /// // Or specify exact concurrency level
    /// let results = orchestrator.process_logs_batch(logs, Some(4)).await;
    ///
    /// let successful = results.iter().filter(|r| r.success).count();
    /// let failed = results.iter().filter(|r| !r.success).count();
    ///
    /// println!("Processed {} logs: {} succeeded, {} failed", results.len(), successful, failed);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn process_logs_batch(
        &self,
        log_paths: Vec<String>,
        max_concurrent: Option<usize>,
    ) -> Vec<AnalysisResult> {
        use futures::stream::{self, StreamExt};

        if log_paths.is_empty() {
            return Vec::new();
        }

        // Determine concurrency level
        let concurrency = resolve_batch_concurrency(log_paths.len(), max_concurrent);

        stream::iter(log_paths)
            .map(|log_path| {
                let log_path_clone = log_path.clone();
                async move {
                    match self.process_log(log_path.clone()).await {
                        Ok(result) => result,
                        Err(e) => AnalysisResult::failure(log_path_clone, e.to_string()),
                    }
                }
            })
            .buffer_unordered(concurrency)
            .collect()
            .await
    }

    /// Returns a reference to the orchestrator's analysis configuration.
    ///
    /// Provides read-only access to the configuration used by this orchestrator instance.
    /// Useful for inspecting game settings, ignore lists, and pattern dictionaries after
    /// orchestrator creation.
    ///
    /// # Returns
    ///
    /// A reference to the `AnalysisConfig` used by this orchestrator.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    /// let orchestrator = OrchestratorCore::new(config)?;
    ///
    /// // Access configuration after creation
    /// let config_ref = orchestrator.config();
    /// println!("Analyzing game: {}", config_ref.game);
    /// println!("Configured game: {}", config_ref.game);
    /// # Ok(())
    /// # }
    /// ```
    pub fn config(&self) -> &AnalysisConfig {
        &self.config
    }

    // ============================================================================
    // Python-compatible helper methods
    // ============================================================================

    /// Reformats crash data inline as part of the processing pipeline.
    ///
    /// This method matches Python's `_reformat_crash_data_inline()` behavior exactly:
    /// 1. Iterates from bottom to top to detect the PLUGINS section
    /// 2. Removes entire lines containing strings from `remove_list` if `simplify_logs` is enabled
    /// 3. Pads brackets (replaces spaces with zeros) within the PLUGINS section
    ///
    /// The PLUGINS section is detected by finding the "PLUGINS:" marker while iterating
    /// from the bottom of the file upward. Lines below (and including) "PLUGINS:" are
    /// considered part of the plugins section.
    ///
    /// # Arguments
    ///
    /// * `lines` - The crash log lines to reformat
    ///
    /// # Returns
    ///
    /// A new vector of reformatted lines with:
    /// - Lines containing remove_list strings filtered out (if simplify_logs enabled)
    /// - Bracket padding applied in the PLUGINS section
    ///
    /// # Example
    ///
    /// ```text
    /// Before: "[ 1] MyMod.esp"
    /// After:  "[01] MyMod.esp"
    /// ```
    pub fn reformat_crash_data_inline(&self, lines: &[String]) -> Vec<String> {
        use std::collections::VecDeque;

        // Use VecDeque for O(1) prepend operations (like Python's deque)
        let mut processed_lines: VecDeque<String> = VecDeque::with_capacity(lines.len());

        // State for tracking if currently in the PLUGINS section
        // Start as true because we iterate from bottom, and PLUGINS is typically at the end
        let mut in_plugins_section = true;

        // Pre-compute remove set for efficiency
        let should_simplify = self.config.simplify_logs && !self.config.remove_list.is_empty();

        // Iterate over lines from bottom to top (like Python's reversed())
        for line in lines.iter().rev() {
            // Check if we're exiting the PLUGINS section (going upward)
            if in_plugins_section && line.starts_with("PLUGINS:") {
                in_plugins_section = false;
            }

            // Remove entire lines if Simplify Logs is enabled and line contains a remove string
            if should_simplify
                && self
                    .config
                    .remove_list
                    .iter()
                    .any(|remove_str| line.contains(remove_str))
            {
                // Skip this line entirely (don't add to processed_lines)
                continue;
            }

            // Reformat lines within the PLUGINS section (bracket padding)
            if in_plugins_section && line.contains('[') {
                // Replace all spaces inside the load order [brackets] with 0s.
                // This maintains consistency between different versions of Buffout 4.
                // Example: "[ 1]" -> "[01]", "[  A]" -> "[00A]"
                if let Some((indent, rest)) = line.split_once('[') {
                    if let Some((fid, name)) = rest.split_once(']') {
                        // Only modify if spaces exist inside brackets
                        if fid.contains(' ') {
                            let modified_line =
                                format!("{}[{}]{}", indent, fid.replace(' ', "0"), name);
                            processed_lines.push_front(modified_line);
                            continue;
                        }
                    }
                }
                // If format is unexpected, keep original line
                processed_lines.push_front(line.clone());
            } else {
                // Line is not in PLUGINS section or doesn't need modification
                processed_lines.push_front(line.clone());
            }
        }

        // Convert VecDeque to Vec (already in correct order due to push_front)
        processed_lines.into_iter().collect()
    }

    /// Detects if a crash log is incomplete (missing plugin segment).
    ///
    /// Uses the named segment map: checks whether the `plugins` segment is empty.
    ///
    /// # Arguments
    ///
    /// * `segments` - Named segment map from `parse_all_sections_arc`
    ///
    /// # Returns
    ///
    /// `true` if the plugins segment is empty or absent.
    pub fn detect_incomplete_log(&self, segments: &HashMap<String, Vec<Arc<str>>>) -> bool {
        segments
            .get(segment_key::PLUGINS)
            .map(|p| p.is_empty())
            .unwrap_or(true)
    }

    /// Compat overload: detect incomplete log from a plain string slice.
    ///
    /// Used by callers that still pass a `&[String]` plugins segment.
    pub fn detect_incomplete_log_slice(&self, segment_plugin: &[String]) -> bool {
        segment_plugin.is_empty()
    }

    /// Detects if a crash log has failed (too short to analyze).
    ///
    /// This matches Python's `_detect_failed_log()` logic.
    ///
    /// # Arguments
    ///
    /// * `crash_data` - The full crash log data
    ///
    /// # Returns
    ///
    /// `true` if the log is too short (fewer than 20 lines).
    pub fn detect_failed_log(&self, crash_data: &[String]) -> bool {
        // Python considers log failed if it has fewer than 20 lines
        crash_data.len() < 20
    }

    /// Creates a ReportGenerator configured for this orchestrator.
    ///
    /// # Returns
    ///
    /// A `ReportGenerator` instance configured with the current CLASSIC version
    /// and crashgen name from the analysis configuration.
    pub fn create_report_generator(&self) -> ReportGenerator {
        ReportGenerator::with_config(
            self.config.classic_version.clone(),
            self.config.crashgen_name.clone(),
        )
    }

    /// Creates a ReportGenerator configured with an explicit crashgen name.
    pub fn create_report_generator_with_crashgen_name(
        &self,
        crashgen_name: &str,
    ) -> ReportGenerator {
        ReportGenerator::with_config(
            self.config.classic_version.clone(),
            crashgen_name.to_string(),
        )
    }

    fn append_error_information_fragments(
        error_section: crate::report::ReportFragment,
        extra_fragments: Vec<crate::report::ReportFragment>,
    ) -> crate::report::ReportFragment {
        if extra_fragments.is_empty() {
            return error_section;
        }

        let mut lines = error_section.to_list();
        let separator = if matches!(lines.last(), Some(line) if line == "---\n\n") {
            lines.pop().unwrap_or_default()
        } else {
            "---\n\n".to_string()
        };

        for fragment in extra_fragments {
            lines.extend(fragment.to_list());
        }
        lines.push(separator);

        crate::report::ReportFragment::from_lines(lines)
    }

    /// Creates a SettingsValidator configured for this orchestrator.
    ///
    /// # Returns
    ///
    /// A `SettingsValidator` instance configured from the crashgen registry entry.
    pub fn create_settings_validator(&self) -> SettingsValidator {
        Self::settings_validator_from_config(&self.config)
    }

    /// Creates a RecordScanner configured for this orchestrator.
    ///
    /// # Returns
    ///
    /// A `RecordScanner` instance configured with the classic records list
    /// and ignore records from the analysis configuration.
    pub fn create_record_scanner(&self) -> RecordScanner {
        RecordScanner::new(
            self.config.classic_records_list.clone(),
            self.config.ignore_records.clone(),
            self.config.crashgen_name.clone(),
        )
    }

    /// Creates an FcxModeHandler configured for this orchestrator.
    ///
    /// # Returns
    ///
    /// An `FcxModeHandler` instance based on the fcx_mode setting.
    pub fn create_fcx_handler(&self) -> FcxModeHandler {
        FcxModeHandler::new(self.config.fcx_mode)
    }

    /// Checks crashgen version against a list of valid versions.
    ///
    /// This is the new list-based version validation that supports multiple valid
    /// versions per game version (e.g., FO4_OG supports both 1.28.6 and 1.37.0).
    ///
    /// # Arguments
    ///
    /// * `crashgen_version_str` - The crashgen version string from the crash log
    /// * `valid_versions` - Slice of valid version strings for the game version
    ///
    /// # Returns
    ///
    /// A tuple of (parsed_version, CrashgenVersionStatus).
    pub fn check_crashgen_version_list(
        &self,
        crashgen_version_str: &str,
        valid_versions: &[&str],
    ) -> (CrashgenVersion, CrashgenVersionStatus) {
        let current = crashgen_version_gen(crashgen_version_str);
        let status = check_crashgen_version_status(crashgen_version_str, valid_versions);
        (current, status)
    }

    /// Checks crashgen version using the detected game version and registry-backed valid versions.
    pub fn check_crashgen_version_for_detected_game(
        &self,
        crashgen_version_str: &str,
        detected_game_version_str: &str,
    ) -> (CrashgenVersion, CrashgenVersionStatus) {
        let current = crashgen_version_gen(crashgen_version_str);

        let Some(detected_game_version) =
            self.parse_detected_game_version(detected_game_version_str)
        else {
            return (current, CrashgenVersionStatus::NoSupportedVersion);
        };

        let registry = get_version_registry();
        let match_result = registry.match_version(
            &detected_game_version,
            &self.config.game,
            self.config
                .selected_version
                .as_ref()
                .is_some_and(|info| info.is_vr),
        );

        let valid_versions: Vec<&str> = match match_result.version_info {
            Some(ref version_info) => version_info.get_crashgen_version_strings(),
            None => Vec::new(),
        };

        let status = check_crashgen_version_status(crashgen_version_str, &valid_versions);
        (current, status)
    }

    /// Parse the detected game version header into a registry-compatible version object.
    fn parse_detected_game_version(
        &self,
        detected_game_version_str: &str,
    ) -> Option<RegistryGameVersion> {
        let parsed = crashgen_version_gen(detected_game_version_str);
        if parsed.major == 0 && parsed.minor == 0 && parsed.patch == 0 {
            return None;
        }

        let major = u32::try_from(parsed.major).ok()?;
        let minor = u32::try_from(parsed.minor).ok()?;
        let patch = u32::try_from(parsed.patch).ok()?;
        Some(RegistryGameVersion::new(major, minor, patch, 0))
    }

    fn derive_scanlog_config_layout(
        &self,
        detected_game_version_str: &str,
    ) -> classic_crashgen_settings_core::ConfigLayout {
        if self
            .parse_detected_game_version(detected_game_version_str)
            .is_some()
        {
            classic_crashgen_settings_core::ConfigLayout::Og
        } else {
            classic_crashgen_settings_core::ConfigLayout::Unknown
        }
    }

    // ============================================================================
    // Loadorder.txt support
    // ============================================================================

    /// Checks if a loadorder.txt file exists in the specified directory.
    ///
    /// # Arguments
    ///
    /// * `dir_path` - Directory path to check for loadorder.txt
    ///
    /// # Returns
    ///
    /// `true` if loadorder.txt exists.
    pub fn check_loadorder_exists(dir_path: &Path) -> bool {
        dir_path.join("loadorder.txt").exists()
    }

    /// Asynchronously loads plugins from loadorder.txt file.
    ///
    /// This method reads the loadorder.txt file, skips the first line (header),
    /// and returns a map of plugin names to their origin marker ("LO").
    ///
    /// # Arguments
    ///
    /// * `loadorder_path` - Path to the loadorder.txt file
    ///
    /// # Returns
    ///
    /// Returns `Ok((plugins, fragment))` where:
    /// - `plugins` is a HashMap of plugin names to origin markers
    /// - `fragment` is a ReportFragment with loading status
    ///
    /// # Errors
    ///
    /// Returns `Err(ScanLogError)` if file cannot be read.
    pub async fn load_loadorder_async(
        &self,
        loadorder_path: &Path,
    ) -> Result<(HashMap<String, String>, crate::report::ReportFragment)> {
        use crate::report::ReportFragment;

        let mut lines = vec![
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n".to_string(),
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n".to_string(),
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n".to_string(),
        ];

        let mut loadorder_plugins: HashMap<String, String> = HashMap::new();
        let loadorder_origin = "LO".to_string();

        // Read the file using FileIOCore
        match self.file_io.read_file(loadorder_path).await {
            Ok(content) => {
                let loadorder_data: Vec<&str> = content.lines().collect();

                // Skip the header line (first line)
                if loadorder_data.len() > 1 {
                    for plugin_entry in &loadorder_data[1..] {
                        let plugin_entry = plugin_entry.trim();
                        if !plugin_entry.is_empty() && !loadorder_plugins.contains_key(plugin_entry)
                        {
                            loadorder_plugins
                                .insert(plugin_entry.to_string(), loadorder_origin.clone());
                        }
                    }
                }
            }
            Err(e) => {
                lines.push(format!("Error reading loadorder.txt: {}\n", e));
            }
        }

        Ok((loadorder_plugins, ReportFragment::from_lines(lines)))
    }

    // ============================================================================
    // Batch report writing
    // ============================================================================

    /// Writes batch reports to files asynchronously.
    ///
    /// This method processes a batch of reports, generating autoscan filenames
    /// (replacing the extension with `-AUTOSCAN.md`) and writing concurrently.
    ///
    /// # Arguments
    ///
    /// * `reports` - Vector of tuples containing (log_path, report_lines, scan_failed)
    ///
    /// # Returns
    ///
    /// Returns `Ok(Vec<PathBuf>)` with paths of successfully written reports.
    ///
    /// # Errors
    ///
    /// Returns `Err(ScanLogError)` if any write operation fails.
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
    /// use std::path::PathBuf;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    /// let orchestrator = OrchestratorCore::new(config)?;
    ///
    /// let reports = vec![
    ///     (PathBuf::from("crash.log"), vec!["Report content".to_string()], false),
    /// ];
    ///
    /// let written_paths = orchestrator.write_reports_batch(reports).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn write_reports_batch(
        &self,
        reports: Vec<(std::path::PathBuf, Vec<String>, bool)>,
    ) -> Result<Vec<std::path::PathBuf>> {
        use futures::future::join_all;

        let write_futures: Vec<_> = reports
            .into_iter()
            .map(|(log_path, report_lines, _scan_failed)| {
                let file_io = self.file_io.clone();
                async move {
                    // Generate autoscan filename: crash.log -> crash-AUTOSCAN.md
                    let stem = log_path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("unknown");
                    let autoscan_name = format!("{}-AUTOSCAN.md", stem);
                    let autoscan_path = log_path.with_file_name(autoscan_name);

                    // Join report lines
                    let content = report_lines.join("");

                    // Write using FileIOCore
                    match file_io.write_file(&autoscan_path, &content).await {
                        Ok(_) => Ok(autoscan_path),
                        Err(e) => Err(crate::error::ScanLogError::ReportError(format!(
                            "Failed to write report {}: {}",
                            autoscan_path.display(),
                            e
                        ))),
                    }
                }
            })
            .collect();

        // Execute all writes concurrently
        let results = join_all(write_futures).await;

        // Collect successful writes
        let mut written_paths = Vec::new();
        for result in results {
            match result {
                Ok(path) => written_paths.push(path),
                Err(e) => {
                    // Log error but continue with other writes
                    log::warn!("Report write failed: {}", e);
                }
            }
        }

        Ok(written_paths)
    }

    // ============================================================================
    // Feature completeness check
    // ============================================================================

    /// Checks if this orchestrator has all features required for Rust-first processing.
    ///
    /// A feature-complete orchestrator can replace Python's OrchestratorCore for
    /// both single-log and batch processing. This includes:
    /// - Plugin analysis support
    /// - Suspect scanning support
    /// - Optional database pool (not required for feature completeness)
    ///
    /// # Returns
    ///
    /// `true` if all required features are available.
    #[must_use]
    pub fn is_feature_complete(&self) -> bool {
        // Required features:
        // 1. Plugin analyzer must be available
        // 2. Suspect scanner must be available
        // Database pool is optional (degrades gracefully)
        self.plugin_analyzer.is_some() && self.suspect_scanner.is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use classic_shared_core::get_runtime;
    use tempfile::tempdir;

    const FIXTURE_LOG_SMALL: &str = include_str!("../benches/fixtures/crash-0DB9300.log");
    const FIXTURE_LOG_LARGE: &str =
        include_str!("../benches/fixtures/crash-2022-06-05-12-58-02.log");

    fn make_fixture_orchestrator() -> OrchestratorCore {
        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        config.crashgen_latest = "1.26.2".to_string();
        config.game_version = "1.10.163".to_string();
        config.game_version_vr = "1.2.72".to_string();
        config.xse_acronym = "F4SE".to_string();
        OrchestratorCore::new(config).expect("fixture orchestrator should build")
    }

    struct FixtureLog {
        _temp: tempfile::TempDir,
        path: String,
    }

    fn write_fixture_log(filename: &str, contents: &str) -> FixtureLog {
        let temp = tempdir().expect("tempdir should succeed");
        let log_path = temp.path().join(filename);
        std::fs::write(&log_path, contents).expect("fixture log write should succeed");
        FixtureLog {
            _temp: temp,
            path: log_path.to_string_lossy().to_string(),
        }
    }

    fn make_yaml_data(classic_version: &str) -> classic_config_core::YamlDataCore {
        classic_config_core::YamlDataCore {
            classic_game_hints: Vec::new(),
            classic_records_list: Vec::new(),
            classic_version: classic_version.to_string(),
            classic_version_date: String::new(),
            crashgen_name: "Buffout 4".to_string(),
            crashgen_latest_og: String::new(),
            crashgen_ignore: Vec::new(),
            warn_noplugins: String::new(),
            warn_outdated: String::new(),
            xse_acronym: "F4SE".to_string(),
            game_ignore_plugins: Vec::new(),
            game_ignore_records: Vec::new(),
            ignore_list: Vec::new(),
            suspect_error_rules: Vec::new(),
            suspect_stack_rules: Vec::new(),
            game_mods_conf: Vec::new(),
            game_mods_core: Vec::new(),
            game_mods_freq: IndexMap::new(),
            game_mods_solu: Vec::new(),
            autoscan_text: String::new(),
            game_version: String::new(),
            game_root_name: "Fallout4".to_string(),
            crashgen_registry: std::collections::HashMap::new(),
        }
    }

    fn build_orchestrator_with_structured_mods_solu(mods_solu_yaml: &str) -> OrchestratorCore {
        let main_yaml = concat!(
            "CLASSIC_Info:\n",
            "  version: \"7.31.0\"\n",
            "  version_date: \"2024-01-15\"\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
        );
        let game_yaml = format!(
            concat!(
                "Game_Info:\n",
                "  XSE_Acronym: \"F4SE\"\n",
                "  GameVersion: \"1.10.163\"\n",
                "  CRASHGEN_LatestVer: \"1.28.6\"\n",
                "  CRASHGEN_LogName: \"Buffout 4\"\n",
                "  Main_Root_Name: \"Fallout4\"\n",
                "{}"
            ),
            mods_solu_yaml
        );
        let ignore_yaml = "CLASSIC_Ignore_Fallout4: []\n";
        let yaml = classic_config_core::YamlDataCore::from_yaml_content(
            main_yaml,
            &game_yaml,
            ignore_yaml,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("structured Mods_SOLU yaml should load");
        let config = build_analysis_config_from_yaml(
            &yaml,
            "Fallout4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );

        OrchestratorCore::new(config).expect("orchestrator should build")
    }

    fn structured_mods_solu_log(plugins: &[(&str, &str)]) -> String {
        let mut lines = vec![
            "Fallout 4 v1.11.191".to_string(),
            "Buffout 4 v1.28.6".to_string(),
            "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000"
                .to_string(),
            String::new(),
            "PROBABLE CALL STACK:".to_string(),
            "stack frame".to_string(),
            "MODULES:".to_string(),
            "kernel32.dll v10.0.0".to_string(),
            "F4SE PLUGINS:".to_string(),
            "buffout4.dll v1.28.6".to_string(),
            "PLUGINS:".to_string(),
        ];

        lines.extend(
            plugins
                .iter()
                .map(|(plugin_id, plugin_name)| format!("[{plugin_id}] {plugin_name}")),
        );

        lines.extend([
            "REGISTERS:".to_string(),
            "RAX 0x0".to_string(),
            "STACK:".to_string(),
            "stack dump line".to_string(),
        ]);

        lines.join("\n")
    }

    #[test]
    fn build_analysis_config_does_not_double_prefix_classic_version() {
        let yaml = make_yaml_data("CLASSIC v9.0.0");

        let config = build_analysis_config_from_yaml(
            &yaml,
            "Fallout4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );

        assert_eq!(config.classic_version, "CLASSIC v9.0.0");
    }

    #[test]
    fn build_analysis_config_uses_registry_metadata_when_yaml_game_info_is_missing() {
        let mut yaml = make_yaml_data("CLASSIC v9.0.0");
        yaml.crashgen_name.clear();
        yaml.crashgen_latest_og.clear();
        yaml.xse_acronym.clear();
        yaml.game_version.clear();
        yaml.crashgen_registry.insert(
            "Buffout 4".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: "[Compatibility]".to_string(),
                ignore_keys: vec![],
                checks: vec!["achievements".to_string()],
                settings_rules_version: None,
                settings_rules: None,
            },
        );
        yaml.crashgen_registry.insert(
            "default".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: String::new(),
                ignore_keys: vec![],
                checks: vec![],
                settings_rules_version: None,
                settings_rules: None,
            },
        );

        let config = build_analysis_config_from_yaml(
            &yaml,
            "Fallout4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );

        assert_eq!(config.crashgen_name, "Buffout 4");
        assert!(!config.crashgen_latest.is_empty());
        assert_eq!(config.xse_acronym, "F4SE");
        // Auto mode resolves to the configured registry default for Fallout4.
        assert_eq!(config.game_version, "1.11.191");
        assert_eq!(config.game_version_vr, "1.2.72");
        assert!(
            !config
                .crashgen_registry
                .lookup(&config.crashgen_name)
                .checks
                .is_empty()
        );
    }

    #[test]
    fn build_analysis_config_resolves_registry_metadata_for_spaced_game_and_root_name() {
        let mut yaml = make_yaml_data("CLASSIC v9.0.0");
        yaml.game_root_name = "Fallout 4".to_string();
        yaml.crashgen_name.clear();
        yaml.crashgen_latest_og.clear();
        yaml.xse_acronym.clear();
        yaml.game_version.clear();

        let config = build_analysis_config_from_yaml(
            &yaml,
            "Fallout 4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );

        assert_eq!(config.crashgen_name, "Buffout 4");
        assert_eq!(config.game_version, "1.11.191");
        assert_eq!(config.game_version_vr, "1.2.72");
    }

    #[test]
    fn build_analysis_config_resolves_identical_metadata_for_spaced_and_compact_names() {
        let mut compact_yaml = make_yaml_data("CLASSIC v9.0.0");
        compact_yaml.crashgen_name.clear();
        compact_yaml.crashgen_latest_og.clear();
        compact_yaml.xse_acronym.clear();
        compact_yaml.game_version.clear();

        let mut spaced_yaml = compact_yaml.clone();
        spaced_yaml.game_root_name = "Fallout 4".to_string();

        let compact_config = build_analysis_config_from_yaml(
            &compact_yaml,
            "Fallout4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );
        let spaced_config = build_analysis_config_from_yaml(
            &spaced_yaml,
            "Fallout 4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );

        assert_eq!(spaced_config.crashgen_name, compact_config.crashgen_name);
        assert_eq!(
            spaced_config.crashgen_latest,
            compact_config.crashgen_latest
        );
        assert_eq!(spaced_config.xse_acronym, compact_config.xse_acronym);
        assert_eq!(spaced_config.game_version, compact_config.game_version);
        assert_eq!(
            spaced_config.game_version_vr,
            compact_config.game_version_vr
        );
    }

    #[test]
    fn orchestrator_plugin_limit_matches_vr_version_from_built_config() {
        let mut yaml = make_yaml_data("CLASSIC v9.0.0");
        yaml.game_ignore_plugins.push("Fallout4.esm".to_string());

        let config = build_analysis_config_from_yaml(
            &yaml,
            "Fallout4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );
        let orchestrator = OrchestratorCore::new(config).unwrap();
        let analyzer = orchestrator.plugin_analyzer.as_ref().unwrap();

        let segment = vec!["[FF] PluginLimit.esp".to_string()];
        let (triggered, disabled) = analyzer
            .check_plugin_limit(&segment, "1.2.72", "1.36.0")
            .unwrap();

        assert!(triggered);
        assert!(!disabled);
    }

    #[test]
    fn check_crashgen_version_for_detected_game_validates_addictol_for_ae() {
        let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let (_parsed, status) = orchestrator.check_crashgen_version_for_detected_game(
            "Addictol v1.0.0 Feb 16 2026 08:02:06",
            "Fallout 4 v1.11.191",
        );

        assert_eq!(status, crate::version::CrashgenVersionStatus::Valid);
    }

    #[test]
    fn resolve_effective_crashgen_name_prefers_addictol_header() {
        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let xse_modules = HashSet::new();
        let resolved = orchestrator
            .resolve_effective_crashgen_name("Addictol v1.0.0 Feb 16 2026 08:02:06", &xse_modules);

        assert_eq!(resolved, "Addictol");
    }

    #[test]
    fn resolve_effective_crashgen_name_uses_module_fallback_when_header_missing() {
        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let mut xse_modules = HashSet::new();
        xse_modules.insert("addictol.dll".to_string());
        let resolved = orchestrator.resolve_effective_crashgen_name("", &xse_modules);

        assert_eq!(resolved, "Addictol");
    }

    #[test]
    fn extract_module_names_accepts_chained_borrowed_iterators() {
        let mods = ["kernel32.dll v10.0.0", "user32.dll v10.0.0"];
        let xse = ["addictol.dll v1.0.0"];

        let extracted = extract_module_names(mods.iter().chain(xse.iter()));

        assert_eq!(extracted.len(), 3);
        assert!(extracted.contains("kernel32.dll"));
        assert!(extracted.contains("user32.dll"));
        assert!(extracted.contains("addictol.dll"));
    }

    #[test]
    fn scan_analysis_context_builds_from_arc_sections() {
        let parser = LogParser::new(None).unwrap();
        let processed_lines = vec![
            "[Compatibility]".to_string(),
            "Achievements: true".to_string(),
            "SYSTEM SPECS:".to_string(),
            "GPU #1: NVIDIA GeForce RTX 4090".to_string(),
            "PROBABLE CALL STACK:".to_string(),
            "stack frame".to_string(),
            "MODULES:".to_string(),
            "kernel32.dll v10.0.0".to_string(),
            "F4SE PLUGINS:".to_string(),
            "addictol.dll v1.0.0".to_string(),
            "PLUGINS:".to_string(),
            "[00] Fallout4.esm".to_string(),
            "REGISTERS:".to_string(),
            "RAX 0x0".to_string(),
            "STACK:".to_string(),
            "stack dump line".to_string(),
        ];
        let arc_lines: Vec<Arc<str>> = processed_lines
            .iter()
            .map(|line| Arc::from(line.as_str()))
            .collect();
        let segments = parser.parse_all_sections_arc(&arc_lines);

        let context = ScanAnalysisContext::from_arc_sections(processed_lines.clone(), &segments);

        assert_eq!(context.processed_lines, processed_lines);
        assert_eq!(
            context.combined_crash_lines,
            vec![
                "stack frame".to_string(),
                "RAX 0x0".to_string(),
                "stack dump line".to_string(),
            ]
        );
        assert_eq!(context.plugin_lines, vec!["[00] Fallout4.esm".to_string()]);
        assert_eq!(
            context.system_segment_lines,
            vec!["GPU #1: NVIDIA GeForce RTX 4090".to_string()]
        );
        assert_eq!(
            context.crashgen_settings.get("Achievements"),
            Some(&"true".to_string())
        );
        assert!(context.xse_modules_for_settings.contains("kernel32.dll"));
        assert!(context.xse_modules_for_settings.contains("addictol.dll"));
    }

    #[test]
    fn resolve_effective_crashgen_name_falls_back_for_ambiguous_modules() {
        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let mut xse_modules = HashSet::new();
        xse_modules.insert("addictol.dll".to_string());
        xse_modules.insert("buffout4.dll".to_string());
        let resolved = orchestrator.resolve_effective_crashgen_name("", &xse_modules);

        assert_eq!(resolved, "Buffout 4");
    }

    #[test]
    fn fake_bot_mode_treats_buffout4ae_dll_as_real_buffout() {
        let mut xse_modules = HashSet::new();
        xse_modules.insert("buffout4ae.dll".to_string());

        assert!(
            !OrchestratorCore::is_fake_bot_compatible_mode("Buffout 4 v1.28.6", &xse_modules),
            "buffout4ae.dll should count as a real Buffout module"
        );
    }

    #[test]
    fn create_report_generator_with_crashgen_name_updates_error_section_label() {
        let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let report_gen = orchestrator.create_report_generator_with_crashgen_name("Addictol");
        let fragment = report_gen.generate_error_section_with_status(
            "Unhandled exception",
            "Addictol v1.0.0",
            Some(crate::version::CrashgenVersionStatus::Valid),
        );
        let text = fragment.to_list().join("");

        assert!(text.contains("Detected Addictol Version"));
        assert!(text.contains("valid version of Addictol"));
        assert!(!text.contains("Detected Buffout 4 Version"));
    }

    #[test]
    fn settings_validator_routes_to_addictol_rules_and_avoids_scaffold() {
        use classic_crashgen_settings_core::{
            CrashgenSettingsRules, Predicate, PreflightAction, PreflightActionKind, PreflightRule,
            RuleReportBucket, RuleSeverity,
        };

        let mut raw_registry: HashMap<String, classic_config_core::CrashgenEntryRaw> =
            HashMap::new();
        raw_registry.insert(
            "Buffout 4".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: "[Compatibility]".to_string(),
                ignore_keys: vec![],
                checks: vec![],
                settings_rules_version: None,
                settings_rules: None,
            },
        );
        raw_registry.insert(
            "Addictol".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: "[Patches]".to_string(),
                ignore_keys: vec![],
                checks: vec![],
                settings_rules_version: Some(1),
                settings_rules: Some(CrashgenSettingsRules {
                    version: 1,
                    preflight: vec![PreflightRule {
                        id: "addictol_active".to_string(),
                        when: Predicate::Always,
                        action: PreflightAction {
                            kind: PreflightActionKind::Notice,
                            bucket: RuleReportBucket::Settings,
                            severity: RuleSeverity::Info,
                            message: "Addictol rules active".to_string(),
                            fix: None,
                        },
                    }],
                    checks: vec![],
                }),
            },
        );
        raw_registry.insert(
            "default".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: String::new(),
                ignore_keys: vec![],
                checks: vec![],
                settings_rules_version: None,
                settings_rules: None,
            },
        );

        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        config.crashgen_registry = build_crashgen_registry(&raw_registry);
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let mut xse_modules = HashSet::new();
        xse_modules.insert("addictol.dll".to_string());
        let effective_name = orchestrator
            .resolve_effective_crashgen_name("Addictol v1.0.0 Feb 16 2026 08:02:06", &xse_modules);
        assert_eq!(effective_name, "Addictol");

        let validator = OrchestratorCore::settings_validator_for_crashgen(
            &orchestrator.config,
            &effective_name,
        );
        let fragments = validator
            .scan_all_settings(
                &HashMap::new(),
                &xse_modules,
                None,
                classic_crashgen_settings_core::ConfigLayout::Unknown,
            )
            .unwrap();
        let all_lines: Vec<String> = fragments
            .iter()
            .flat_map(crate::report::ReportFragment::to_list)
            .collect();

        assert!(
            all_lines
                .iter()
                .any(|line| line.contains("Addictol rules active"))
        );
        assert!(
            !all_lines
                .iter()
                .any(|line| line.contains("scaffold (rules pending)"))
        );
    }

    #[test]
    fn process_log_promotes_bucketed_compatibility_notice_into_error_information() {
        use classic_crashgen_settings_core::{
            CrashgenSettingsRules, Predicate, PreflightAction, PreflightActionKind, PreflightRule,
            RuleReportBucket, RuleSeverity,
        };

        let mut raw_registry: HashMap<String, classic_config_core::CrashgenEntryRaw> =
            HashMap::new();
        raw_registry.insert(
            "Buffout 4".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: "[Compatibility]".to_string(),
                ignore_keys: vec![],
                checks: vec![],
                settings_rules_version: None,
                settings_rules: None,
            },
        );
        raw_registry.insert(
            "Addictol".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: "[Patches]".to_string(),
                ignore_keys: vec![],
                checks: vec![],
                settings_rules_version: Some(1),
                settings_rules: Some(CrashgenSettingsRules {
                    version: 1,
                    preflight: vec![PreflightRule {
                        id: "buffout_addictol_incompatible".to_string(),
                        when: Predicate::All(vec![
                            Predicate::PluginAny(vec!["addictol.dll".to_string()]),
                            Predicate::PluginAny(vec!["buffout4.dll".to_string()]),
                        ]),
                        action: PreflightAction {
                            kind: PreflightActionKind::NoticeAndSkipRemaining,
                            bucket: RuleReportBucket::ErrorInformation,
                            severity: RuleSeverity::Warning,
                            message: "{crashgen_name} and Buffout 4 are incompatible, remove one to avoid crashes.".to_string(),
                            fix: None,
                        },
                    }],
                    checks: vec![],
                }),
            },
        );
        raw_registry.insert(
            "default".to_string(),
            classic_config_core::CrashgenEntryRaw {
                display_section: String::new(),
                ignore_keys: vec![],
                checks: vec![],
                settings_rules_version: None,
                settings_rules: None,
            },
        );

        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        config.crashgen_registry = build_crashgen_registry(&raw_registry);
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let log_contents = [
            "Fallout 4 v1.11.191",
            "Addictol v1.0.0 Feb 16 2026 08:02:06",
            "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
            "",
            "[Patches]",
            "bThreads: true",
            "SYSTEM SPECS:",
            "GPU #1: NVIDIA GeForce RTX 4090",
            "PROBABLE CALL STACK:",
            "stack frame",
            "MODULES:",
            "kernel32.dll v10.0.0",
            "F4SE PLUGINS:",
            "addictol.dll v1.0.0",
            "buffout4.dll v1.28.6",
            "PLUGINS:",
            "[00] Fallout4.esm",
            "REGISTERS:",
            "RAX 0x0",
            "STACK:",
            "stack dump line",
        ]
        .join("\n");
        let fixture = write_fixture_log("bucketed-addictol.log", &log_contents);

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("bucketed fixture should process");
        let report_text = result.report_lines.join("");

        let status_line = "✅ *You have a valid version of Addictol!*";
        let compatibility_notice = "**# ⚠️ NOTICE : Addictol and Buffout 4 are incompatible, remove one to avoid crashes. #**";
        let suspect_header = "### Checking for Known Crash Messages, Errors and Suspects";

        assert!(result.success);
        assert!(report_text.contains("### Error Information"));
        assert!(report_text.contains(status_line));
        assert!(report_text.contains(compatibility_notice));
        assert!(!report_text.contains("### Checking for Settings-related Issues"));

        let status_index = report_text.find(status_line).unwrap();
        let notice_index = report_text.find(compatibility_notice).unwrap();
        let suspect_index = report_text.find(suspect_header).unwrap();
        assert!(status_index < notice_index);
        assert!(notice_index < suspect_index);
    }

    #[test]
    fn process_log_skips_fake_bot_compatible_buffout_version_and_settings_checks() {
        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let log_contents = [
            "Fallout 4 v1.11.191",
            "Buffout 4 v1.1.0",
            "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
            "",
            "[Compatibility]",
            "Achievements: true",
            "MemoryManager: true",
            "ArchiveLimit: false",
            "SYSTEM SPECS:",
            "GPU #1: NVIDIA GeForce RTX 4090",
            "PROBABLE CALL STACK:",
            "stack frame",
            "MODULES:",
            "kernel32.dll v10.0.0",
            "F4SE PLUGINS:",
            "fake-buffout.dll v1.0.0",
            "PLUGINS:",
            "[00] Fallout4.esm",
            "REGISTERS:",
            "RAX 0x0",
            "STACK:",
            "stack dump line",
        ]
        .join("\n");
        let fixture = write_fixture_log("fake-bot-compatible.log", &log_contents);

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("fake bot-compatible fixture should process");
        let report_text = result.report_lines.join("");

        assert!(result.success);
        assert!(report_text.contains("Bot Compatible Mode"));
        assert!(
            report_text.contains("Version checks and settings checks are disabled"),
            "report should explain why checks were skipped"
        );
        assert!(
            !report_text.contains("OUTDATED"),
            "fake bot-compatible logs should not emit outdated-version warnings"
        );
        assert!(
            !report_text.contains("### Checking for Settings-related Issues"),
            "fake bot-compatible logs should skip settings validation"
        );
    }

    #[test]
    fn process_log_skips_checks_when_buffout_header_lacks_buffout_module() {
        let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        config.crashgen_name = "Buffout 4".to_string();
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let log_contents = [
            "Fallout 4 v1.11.191",
            "Buffout 4 v1.28.6",
            "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
            "",
            "[Compatibility]",
            "Achievements: true",
            "MemoryManager: true",
            "SYSTEM SPECS:",
            "GPU #1: NVIDIA GeForce RTX 4090",
            "PROBABLE CALL STACK:",
            "stack frame",
            "MODULES:",
            "kernel32.dll v10.0.0",
            "F4SE PLUGINS:",
            "addictol.dll v1.1.0",
            "PLUGINS:",
            "[00] Fallout4.esm",
            "REGISTERS:",
            "RAX 0x0",
            "STACK:",
            "stack dump line",
        ]
        .join("\n");
        let fixture = write_fixture_log(
            "fake-bot-compatible-missing-buffout-module.log",
            &log_contents,
        );

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("missing buffout module fixture should process");
        let report_text = result.report_lines.join("");

        assert!(result.success);
        assert!(
            report_text.contains("Bot Compatible Mode"),
            "logs claiming Buffout 4 without buffout4.dll should be treated as bot-compatible"
        );
        assert!(
            !report_text.contains("### Checking for Settings-related Issues"),
            "missing buffout4.dll should suppress settings validation for fake Buffout logs"
        );
    }

    #[test]
    fn derive_config_layout_returns_og_for_valid_non_vr_version() {
        let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let layout = orchestrator.derive_scanlog_config_layout("Fallout 4 v1.10.163");
        assert_eq!(layout, classic_crashgen_settings_core::ConfigLayout::Og);
    }

    #[test]
    fn derive_config_layout_returns_og_for_valid_vr_version() {
        let config = AnalysisConfig::new("Fallout4".to_string(), "VR".to_string());
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let layout = orchestrator.derive_scanlog_config_layout("Fallout 4 VR v1.2.72");
        assert_eq!(layout, classic_crashgen_settings_core::ConfigLayout::Og);
    }

    #[test]
    fn derive_config_layout_returns_unknown_for_invalid_header_version() {
        let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let layout = orchestrator.derive_scanlog_config_layout("not a valid version line");
        assert_eq!(
            layout,
            classic_crashgen_settings_core::ConfigLayout::Unknown
        );
    }

    #[test]
    fn detect_incomplete_log_slice_matches_named_segment_semantics() {
        let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
        let orchestrator = OrchestratorCore::new(config).unwrap();

        // One plugin line should be considered complete by both APIs.
        let one_plugin = vec!["[00] Fallout4.esm".to_string()];
        assert!(!orchestrator.detect_incomplete_log_slice(&one_plugin));
    }

    #[test]
    fn process_log_with_progress_reports_monotonic_phases_for_fixture() {
        let orchestrator = make_fixture_orchestrator();
        let fixture = write_fixture_log("progress-fixture.log", FIXTURE_LOG_SMALL);
        let mut phases = Vec::new();

        let result = get_runtime().block_on(orchestrator.process_log_with_progress(
            fixture.path.clone(),
            |phase| {
                phases.push(phase);
            },
        ));

        let result = result.expect("fixture processing should succeed");
        assert!(result.success);
        assert_eq!(
            phases,
            vec![
                ScanProgressPhase::Setup,
                ScanProgressPhase::Parse,
                ScanProgressPhase::Analyze,
                ScanProgressPhase::Finalize,
            ]
        );
    }

    #[test]
    fn process_log_missing_fixture_returns_error_after_setup_phase() {
        let orchestrator = make_fixture_orchestrator();
        let mut phases = Vec::new();

        let result = get_runtime().block_on(
            orchestrator.process_log_with_progress("missing-fixture.log".to_string(), |phase| {
                phases.push(phase)
            }),
        );

        assert!(result.is_err());
        assert_eq!(phases, vec![ScanProgressPhase::Setup]);
    }

    #[test]
    fn process_log_large_fixture_preserves_basic_report_shape() {
        let orchestrator = make_fixture_orchestrator();
        let fixture = write_fixture_log("heavy-fixture.log", FIXTURE_LOG_LARGE);

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("large fixture should process");
        let report_text = result.report_lines.join("");

        assert!(result.success);
        assert!(report_text.contains("Generated by CLASSIC"));
        assert!(report_text.contains("Checking for Known Crash Messages, Errors and Suspects"));
        assert!(report_text.contains("### End of Report"));
    }

    #[test]
    fn process_log_ignores_legacy_mods_opc2_yaml_entries() {
        let main_yaml = concat!(
            "CLASSIC_Info:\n",
            "  version: \"7.31.0\"\n",
            "  version_date: \"2024-01-15\"\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
        );
        let game_yaml = concat!(
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "  GameVersion: \"1.10.163\"\n",
            "  CRASHGEN_LatestVer: \"1.28.6\"\n",
            "  CRASHGEN_LogName: \"Buffout 4\"\n",
            "  Main_Root_Name: \"Fallout4\"\n",
            "Mods_OPC2:\n",
            "  OpcMod: \"OPC2 mod\"\n",
        );
        let ignore_yaml = "CLASSIC_Ignore_Fallout4: []\n";
        let yaml = classic_config_core::YamlDataCore::from_yaml_content(
            main_yaml,
            game_yaml,
            ignore_yaml,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .expect("yaml fixture should load");
        let config = build_analysis_config_from_yaml(
            &yaml,
            "Fallout4",
            "auto",
            false,
            false,
            false,
            Vec::new(),
        );
        let orchestrator = OrchestratorCore::new(config).expect("orchestrator should build");

        let log_contents = [
            "Fallout 4 v1.11.191",
            "Buffout 4 v1.28.6",
            "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
            "",
            "PROBABLE CALL STACK:",
            "stack frame",
            "MODULES:",
            "kernel32.dll v10.0.0",
            "F4SE PLUGINS:",
            "buffout4.dll v1.28.6",
            "PLUGINS:",
            "[00] Fallout4.esm",
            "[01] OpcMod.esp",
            "REGISTERS:",
            "RAX 0x0",
            "STACK:",
            "stack dump line",
        ]
        .join("\n");
        let fixture = write_fixture_log("legacy-opc2.log", &log_contents);

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("fixture should process");
        let report_text = result.report_lines.join("");

        assert!(result.success);
        assert!(!report_text.contains(
            "### Checking For Mods That Are Outdated, Redundant, or Have Community Patches"
        ));
    }

    #[test]
    fn process_log_renders_structured_mods_solu_any_matches() {
        let orchestrator = build_orchestrator_with_structured_mods_solu(concat!(
            "Mods_SOLU:\n",
            "  - id: high-resolution-dlc\n",
            "    criteria:\n",
            "      any:\n",
            "        - DLCUltraHighResolution\n",
            "        - HighResPack\n",
            "    name: High Resolution DLC\n",
            "    description: |\n",
            "      Disable the official texture pack.\n",
            "      It causes crashes and stutter.\n"
        ));
        let log_contents = structured_mods_solu_log(&[("01", "DLCUltraHighResolution.esp")]);
        let processed_lines = orchestrator.reformat_crash_data_inline(
            &log_contents.lines().map(str::to_string).collect::<Vec<_>>(),
        );
        let context =
            ScanAnalysisContext::from_processed_lines(&orchestrator.parser, processed_lines);
        assert!(
            !context.plugin_lines.is_empty(),
            "plugin segment should not be empty"
        );

        let analyzer = orchestrator
            .plugin_analyzer
            .as_ref()
            .expect("orchestrator should have a plugin analyzer");
        let (plugins, _limit_triggered, _limit_disabled) = analyzer
            .loadorder_scan_log(
                &context.plugin_lines,
                Some(orchestrator.config.game_version.as_str()),
                Some(orchestrator.config.crashgen_latest.as_str()),
            )
            .expect("plugin analyzer should parse the fixture plugins");
        assert_eq!(
            plugins.get("DLCUltraHighResolution.esp"),
            Some(&"01".to_string())
        );
        assert!(
            !detect_mods_solutions(&orchestrator.config.mods_solu, &plugins)
                .expect("structured matcher should succeed")
                .is_empty(),
            "structured matcher should detect the configured entry"
        );

        let fixture = write_fixture_log("mods-solu-any.log", &log_contents);

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("fixture should process");
        let report_text = result.report_lines.join("");

        assert!(result.success);
        assert!(report_text.contains("### Checking For Mods That HAVE SOLUTIONS"));
        assert!(report_text.contains("FOUND : [01] High Resolution DLC"));
        assert!(report_text.contains("Disable the official texture pack."));
        assert!(report_text.contains("It causes crashes and stutter."));
    }

    #[test]
    fn process_log_requires_all_structured_mods_solu_criteria() {
        let orchestrator = build_orchestrator_with_structured_mods_solu(concat!(
            "Mods_SOLU:\n",
            "  - id: bodyslide-patch\n",
            "    criteria:\n",
            "      all:\n",
            "        - LooksMenu\n",
            "        - CBBE\n",
            "    name: BodySlide Patch\n",
            "    description: |\n",
            "      Install the compatibility patch.\n"
        ));
        let fixture = write_fixture_log(
            "mods-solu-all.log",
            &structured_mods_solu_log(&[("02", "LooksMenu.esp")]),
        );

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("fixture should process");
        let report_text = result.report_lines.join("");

        assert!(result.success);
        assert!(!report_text.contains("BodySlide Patch"));
        assert!(!report_text.contains("### Checking For Mods That HAVE SOLUTIONS"));
    }

    #[test]
    fn process_log_suppresses_structured_mods_solu_exceptions() {
        let orchestrator = build_orchestrator_with_structured_mods_solu(concat!(
            "Mods_SOLU:\n",
            "  - id: ebf-redux\n",
            "    criteria:\n",
            "      any:\n",
            "        - EveryonesBestFriend\n",
            "    exceptions:\n",
            "      - UFO4P\n",
            "    name: Everyone's Best Friend\n",
            "    description: |\n",
            "      Install the compatibility patch.\n"
        ));
        let fixture = write_fixture_log(
            "mods-solu-exception.log",
            &structured_mods_solu_log(&[("03", "EveryonesBestFriend.esp"), ("04", "UFO4P.esp")]),
        );

        let result = get_runtime()
            .block_on(orchestrator.process_log(fixture.path.clone()))
            .expect("fixture should process");
        let report_text = result.report_lines.join("");

        assert!(result.success);
        assert!(!report_text.contains("Everyone's Best Friend"));
        assert!(!report_text.contains("### Checking For Mods That HAVE SOLUTIONS"));
    }

    #[test]
    fn resolve_batch_concurrency_honors_manual_override() {
        assert_eq!(resolve_batch_concurrency(8, Some(3)), 3);
        assert_eq!(resolve_batch_concurrency(8, Some(0)), 1);
    }

    #[test]
    fn resolve_batch_concurrency_handles_empty_batches() {
        assert_eq!(resolve_batch_concurrency(0, None), 1);
    }
}
