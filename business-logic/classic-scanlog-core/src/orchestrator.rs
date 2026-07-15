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
    detect_mods_double, detect_mods_freq, detect_mods_important, detect_mods_solutions,
};
use crate::parser::LogParser;
use crate::plugin_analyzer::PluginAnalyzer;
use crate::record_scanner::RecordScanner;
use crate::report::{
    AutoscanReportAssembler, AutoscanReportContribution, AutoscanReportFacts, ModGuidanceGroup,
    ReportFragment, ReportGenerator, write_autoscan_report,
};
use crate::scan_run::CrashLogScanSetupResult;
use crate::segment_key;
use crate::settings_validator::SettingsValidator;
use crate::suspect_scanner::SuspectScanner;
use crate::version::{
    CrashgenVersion, CrashgenVersionStatus, check_crashgen_version_status,
    check_crashgen_version_status_with_exceptions, crashgen_version_gen,
    is_fake_bot_compatible_buffout_version,
};
use classic_config_core::{
    ConfigLayout, CoreModEntry, CrashgenSettingsSnapshot, ModConflictEntry, ModSolutionEntry,
    SuspectErrorRule, SuspectStackRule,
};
use classic_database_core::DatabasePool;
use classic_file_io_core::FileIOCore;
use classic_version_registry_core::{
    CrashgenConfig, GameVersion as RegistryGameVersion, VersionInfo, get_version_registry,
};
use indexmap::IndexMap;
use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, LazyLock};

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

/// Batch lifecycle events emitted by the core batch scan driver.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BatchScanEventKind {
    /// The log has been accepted into the batch.
    Queued,
    /// The log's worker has started.
    Started,
    /// The log reported a single-log scan phase transition.
    Phase,
    /// The log finished successfully.
    Completed,
    /// The log finished with a per-log failure result.
    Failed,
}

/// Core batch progress event independent of any binding-specific DTOs.
#[derive(Clone, Debug)]
pub struct BatchScanEvent {
    /// Original index in the input path list.
    pub input_index: usize,
    /// Log path associated with this event.
    pub log_path: String,
    /// Event kind.
    pub kind: BatchScanEventKind,
    /// Current coarse scan phase.
    pub phase: ScanProgressPhase,
    /// Number of completed logs at event emit time.
    pub completed: usize,
    /// Total number of logs in the batch.
    pub total: usize,
    /// Whether the terminal event represents a successful scan.
    pub success: bool,
}

/// Options for eventful batch scanning.
#[derive(Clone, Default)]
pub struct BatchScanOptions {
    /// Optional maximum number of concurrent log processing tasks.
    pub max_concurrent: Option<usize>,
    /// Return indexed results in input order instead of completion order.
    pub preserve_order: bool,
    /// Optional cooperative cancellation flag checked before each log starts.
    pub cancellation: Option<Arc<AtomicBool>>,
}

/// A batch result with stable input index metadata.
#[derive(Clone)]
pub struct IndexedAnalysisResult {
    /// Original index in the input path list.
    pub input_index: usize,
    /// Completion ordinal for this result.
    pub completed: usize,
    /// Total number of logs in the batch.
    pub total: usize,
    /// Per-log analysis result.
    pub result: AnalysisResult,
}

const READY_BATCH_PROGRESS_DRAIN_MAX_EMPTY_YIELDS: usize = 2;

async fn drain_ready_batch_progress_events(
    progress_rx: &mut tokio::sync::mpsc::UnboundedReceiver<BatchScanEvent>,
) -> Vec<BatchScanEvent> {
    let mut events = Vec::new();
    let mut empty_yields_remaining = READY_BATCH_PROGRESS_DRAIN_MAX_EMPTY_YIELDS;

    loop {
        match progress_rx.try_recv() {
            Ok(event) => {
                events.push(event);
                empty_yields_remaining = READY_BATCH_PROGRESS_DRAIN_MAX_EMPTY_YIELDS;
            }
            Err(tokio::sync::mpsc::error::TryRecvError::Empty) if empty_yields_remaining > 0 => {
                empty_yields_remaining -= 1;
                tokio::task::yield_now().await;
            }
            Err(tokio::sync::mpsc::error::TryRecvError::Empty) => break,
            Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => break,
        }
    }

    events
}

struct ScanAnalysisContext {
    processed_lines: Vec<String>,
    combined_crash_lines: Vec<String>,
    combined_crash_text: String,
    combined_crash_lower_lines: Vec<String>,
    plugin_lines: Vec<String>,
    xse_modules_for_settings: HashSet<String>,
    crashgen_settings: CrashgenSettingsSnapshot,
    system_segment_lines: Vec<String>,
}

struct CrashgenScanContext {
    crashlog_filename: String,
    crashgen_version_str: String,
    main_error: String,
    fake_bot_compatible_mode: bool,
    effective_crashgen_name: String,
    crashgen_status: Option<CrashgenVersionStatus>,
    crashgen_version: Option<(u32, u32, u32)>,
    config_layout: ConfigLayout,
}

struct SuspectScanFragments {
    fragments: Vec<ReportFragment>,
    count: usize,
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

        let crashgen_settings = parse_crashgen_settings_snapshot(
            segments
                .get(segment_key::SETTINGS)
                .map(Vec::as_slice)
                .unwrap_or_default(),
        );

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

/// Parse crashgen setting lines into a section-aware snapshot for rule evaluation.
fn parse_crashgen_settings_snapshot(lines: &[Arc<str>]) -> CrashgenSettingsSnapshot {
    let mut snapshot = CrashgenSettingsSnapshot::new();
    let mut current_section: Option<String> = None;

    for line in lines {
        let line = line.trim();
        if line.starts_with('[') {
            current_section = Some(line.to_string());
            continue;
        }

        let Some((key, value)) = line.split_once(':') else {
            continue;
        };

        match current_section.as_deref() {
            Some(section) => snapshot.insert(section, key, value.trim().to_string()),
            None => snapshot.insert_unscoped(key, value.trim().to_string()),
        }
    }

    snapshot
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

    /// Bare SemVer string sourced from `CLASSIC_Info.version` in `CLASSIC Main.yaml`
    /// (e.g., "v8.0.0"). Display-decorated forms like "CLASSIC v8.0.0" are constructed
    /// at format time by consumers such as `ReportGenerator`.
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
    /// Structured frequently problematic mods database for crash analysis.
    pub mods_freq: Vec<ModSolutionEntry>,
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
            classic_version: String::new(),
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
            mods_freq: Vec::new(),
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
    use std::collections::HashMap;

    let mut entries: HashMap<String, CrashgenEntry> = HashMap::new();
    let mut default_entry = CrashgenEntry::default_entry();

    for (name, raw_entry) in raw {
        let ignore_keys: std::collections::HashSet<String> =
            raw_entry.ignore_keys.iter().cloned().collect();

        let entry = CrashgenEntry {
            display_section: raw_entry.display_section.clone(),
            ignore_keys,
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
    static MODULE_PATTERN: LazyLock<Regex> =
        LazyLock::new(|| match Regex::new(r"(?i)(.*?\.dll)\s*v?.*") {
            Ok(regex) => regex,
            Err(error) => panic!("invalid static regex MODULE_PATTERN: {error}"),
        });

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
    /// Immutable setup snapshot owned by the enclosing Crash Log Scan Run.
    scan_run_setup: Option<Arc<CrashLogScanSetupResult>>,
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

    fn crashgen_config_matches_name(config: &CrashgenConfig, crashgen_name: &str) -> bool {
        config.name.eq_ignore_ascii_case(crashgen_name)
            || (!config.acronym.is_empty() && config.acronym.eq_ignore_ascii_case(crashgen_name))
    }

    /// Returns a non-empty crashgen name after trimming caller-provided whitespace.
    fn trimmed_crashgen_name(crashgen_name: &str) -> Option<&str> {
        let crashgen_name = crashgen_name.trim();
        if crashgen_name.is_empty() {
            None
        } else {
            Some(crashgen_name)
        }
    }

    /// Reports whether a registry product label appears in a normalized crashgen header.
    fn crashgen_label_matches_version_string(label: &str, crashgen_version_str: &str) -> bool {
        let label = label.trim();
        !label.is_empty() && crashgen_version_str.contains(&label.to_ascii_lowercase())
    }

    /// Infers the crashgen product name from the detected crashgen version header.
    ///
    /// The public version helper does not receive the scan path's resolved effective name, so
    /// this derives the registry name from labels already embedded in normal crash log headers.
    fn crashgen_name_from_version_string<'a>(
        version_info: &'a VersionInfo,
        crashgen_version_str: &str,
    ) -> Option<&'a str> {
        let crashgen_version_str = crashgen_version_str.to_ascii_lowercase();
        version_info
            .crashgen_versions
            .iter()
            .find(|config| {
                Self::crashgen_label_matches_version_string(&config.name, &crashgen_version_str)
                    || Self::crashgen_label_matches_version_string(
                        &config.acronym,
                        &crashgen_version_str,
                    )
            })
            .map(|config| config.name.as_str())
    }

    fn crashgen_configs_for_name<'a>(
        version_info: &'a VersionInfo,
        crashgen_name: &str,
    ) -> Vec<&'a CrashgenConfig> {
        let crashgen_name = crashgen_name.trim();
        if crashgen_name.is_empty() {
            return version_info.crashgen_versions.iter().collect();
        }

        let matching_configs: Vec<&CrashgenConfig> = version_info
            .crashgen_versions
            .iter()
            .filter(|config| Self::crashgen_config_matches_name(config, crashgen_name))
            .collect();

        if matching_configs.is_empty() {
            version_info.crashgen_versions.iter().collect()
        } else {
            matching_configs
        }
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
            scan_run_setup: None,
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

    /// Attaches the immutable setup snapshot evaluated for the enclosing scan run.
    ///
    /// Every log analyzed by this orchestrator shares the same snapshot, so report
    /// assembly cannot observe setup facts from another sequential or overlapping run.
    pub(crate) fn set_scan_run_setup(&mut self, setup: Option<Arc<CrashLogScanSetupResult>>) {
        self.scan_run_setup = setup;
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
        let context = self.prepare_scan_context(&log_path).await?;

        enter_phase(ScanProgressPhase::Parse);
        let crashgen = self.resolve_crashgen_context(&log_path, &context);

        enter_phase(ScanProgressPhase::Analyze);
        let mut contributions = self.collect_settings_contributions(&context, &crashgen);

        // Store plugins for mod detection - IndexMap preserves load order for Python parity
        let (plugins_map, plugin_count) = self.collect_plugins(&context);
        let suspect_fragments = self.collect_suspect_fragments(&context, &crashgen.main_error);
        contributions.extend(suspect_fragments.fragments.into_iter().map(|fragment| {
            AutoscanReportContribution::CrashSuspectFinding {
                lines: fragment.to_list(),
            }
        }));

        // Mod detection (if we have plugin data)
        if let Some(ref plugins) = plugins_map {
            contributions.extend(self.collect_mod_contributions(&context, plugins));
            contributions.extend(self.collect_plugin_match_contributions(
                &context,
                plugins,
                &crashgen.effective_crashgen_name,
            ));
        }

        let (formid_record_contributions, formid_count) = self
            .collect_formid_and_record_contributions(
                &context,
                plugins_map.as_ref(),
                &crashgen.effective_crashgen_name,
            )
            .await?;
        contributions.extend(formid_record_contributions);

        enter_phase(ScanProgressPhase::Finalize);

        let report_lines = AutoscanReportAssembler::new().assemble(
            &AutoscanReportFacts {
                classic_version: self.config.classic_version.clone(),
                crashlog_filename: crashgen.crashlog_filename.clone(),
                main_error: crashgen.main_error.clone(),
                crashgen_name: crashgen.effective_crashgen_name.clone(),
                crashgen_version: crashgen.crashgen_version_str.clone(),
                crashgen_status: crashgen.crashgen_status,
                fake_bot_compatible_mode: crashgen.fake_bot_compatible_mode,
                fcx_setup: self.scan_run_setup.clone(),
            },
            contributions,
        );

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
        result.suspect_count = suspect_fragments.count;

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
        self.process_logs_batch_with_events(
            log_paths,
            BatchScanOptions {
                max_concurrent,
                preserve_order: false,
                cancellation: None,
            },
            |_| {},
        )
        .await
        .into_iter()
        .map(|indexed| indexed.result)
        .collect()
    }

    /// Process multiple logs with indexed results and core lifecycle events.
    pub async fn process_logs_batch_with_events<F>(
        &self,
        log_paths: Vec<String>,
        options: BatchScanOptions,
        mut on_event: F,
    ) -> Vec<IndexedAnalysisResult>
    where
        F: FnMut(BatchScanEvent),
    {
        use futures::stream::{self, StreamExt};
        use tokio::sync::mpsc;

        let total = log_paths.len();
        if total == 0 {
            return Vec::new();
        }

        let concurrency = resolve_batch_concurrency(total, options.max_concurrent);
        let indexed_paths: Vec<(usize, String)> = log_paths.into_iter().enumerate().collect();

        for (input_index, log_path) in &indexed_paths {
            on_event(BatchScanEvent {
                input_index: *input_index,
                log_path: log_path.clone(),
                kind: BatchScanEventKind::Queued,
                phase: ScanProgressPhase::Setup,
                completed: 0,
                total,
                success: false,
            });
        }

        let (progress_tx, mut progress_rx) = mpsc::unbounded_channel::<BatchScanEvent>();
        let completed_counter = Arc::new(AtomicUsize::new(0));
        let cancellation = options.cancellation.clone();

        let mut tasks = stream::iter(indexed_paths)
            .map(|(input_index, log_path)| {
                let progress_tx = progress_tx.clone();
                let completed_counter = Arc::clone(&completed_counter);
                let cancellation = cancellation.clone();
                async move {
                    // Cancellation before admission keeps the log queued; a
                    // Started event would contradict its terminal non-start disposition.
                    if cancellation
                        .as_ref()
                        .is_some_and(|cancel| cancel.load(Ordering::Relaxed))
                    {
                        return (
                            input_index,
                            log_path.clone(),
                            ScanProgressPhase::Setup,
                            AnalysisResult::failure(log_path, "Cancelled by user".to_string()),
                        );
                    }

                    let _ = progress_tx.send(BatchScanEvent {
                        input_index,
                        log_path: log_path.clone(),
                        kind: BatchScanEventKind::Started,
                        phase: ScanProgressPhase::Setup,
                        completed: completed_counter.load(Ordering::Relaxed),
                        total,
                        success: false,
                    });

                    let mut last_phase = ScanProgressPhase::Setup;
                    let result = match self
                        .process_log_with_progress(log_path.clone(), |phase| {
                            last_phase = phase;
                            let _ = progress_tx.send(BatchScanEvent {
                                input_index,
                                log_path: log_path.clone(),
                                kind: BatchScanEventKind::Phase,
                                phase,
                                completed: completed_counter.load(Ordering::Relaxed),
                                total,
                                success: false,
                            });
                        })
                        .await
                    {
                        Ok(result) => result,
                        Err(e) => AnalysisResult::failure(log_path.clone(), e.to_string()),
                    };
                    (input_index, log_path, last_phase, result)
                }
            })
            .buffer_unordered(concurrency);

        let mut completed = 0usize;
        let mut indexed_results = Vec::with_capacity(total);
        while completed < total {
            tokio::select! {
                biased;
                maybe_event = progress_rx.recv() => {
                    if let Some(event) = maybe_event {
                        on_event(event);
                    }
                }
                maybe_result = tasks.next() => {
                    let Some((input_index, scanned_path, last_phase, result)) = maybe_result else {
                        break;
                    };
                    for event in drain_ready_batch_progress_events(&mut progress_rx).await {
                        on_event(event);
                    }
                    completed += 1;
                    completed_counter.store(completed, Ordering::Relaxed);
                    on_event(BatchScanEvent {
                        input_index,
                        log_path: result.log_path.clone(),
                        kind: if result.success {
                            BatchScanEventKind::Completed
                        } else {
                            BatchScanEventKind::Failed
                        },
                        phase: last_phase,
                        completed,
                        total,
                        success: result.success,
                    });
                    indexed_results.push(IndexedAnalysisResult {
                        input_index,
                        completed,
                        total,
                        result: if result.log_path.is_empty() {
                            AnalysisResult {
                                log_path: scanned_path,
                                ..result
                            }
                        } else {
                            result
                        },
                    });
                }
            }
        }

        drop(tasks);
        drop(progress_tx);
        while let Ok(event) = progress_rx.try_recv() {
            on_event(event);
        }

        if options.preserve_order {
            indexed_results.sort_by_key(|result| result.input_index);
        }
        indexed_results
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
                if let Some((indent, rest)) = line.split_once('[')
                    && let Some((fid, name)) = rest.split_once(']')
                {
                    // Only modify if spaces exist inside brackets
                    if fid.contains(' ') {
                        let modified_line =
                            format!("{}[{}]{}", indent, fid.replace(' ', "0"), name);
                        processed_lines.push_front(modified_line);
                        continue;
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

    async fn prepare_scan_context(&self, log_path: &str) -> Result<ScanAnalysisContext> {
        let log_content = self.file_io.read_file(Path::new(log_path)).await?;
        let raw_lines: Vec<String> = log_content.lines().map(String::from).collect();
        let processed_lines = self.reformat_crash_data_inline(&raw_lines);
        Ok(ScanAnalysisContext::from_processed_lines(
            &self.parser,
            processed_lines,
        ))
    }

    fn resolve_crashgen_context(
        &self,
        log_path: &str,
        context: &ScanAnalysisContext,
    ) -> CrashgenScanContext {
        let crashlog_filename = Path::new(log_path)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or(log_path)
            .to_string();

        let header_info = self
            .parser
            .parse_crash_header(&context.processed_lines)
            .unwrap_or_default();
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
        let detected_game_version_str =
            header_info.get("game_version").cloned().unwrap_or_default();
        let main_error = header_info.get("main_error").cloned().unwrap_or_else(|| {
            context
                .processed_lines
                .iter()
                .find(|line| line.starts_with("Unhandled exception"))
                .cloned()
                .unwrap_or_default()
        });
        let crashgen_status = if crashgen_version_str.trim().is_empty() || fake_bot_compatible_mode
        {
            None
        } else {
            let (_parsed, status) = self
                .check_crashgen_version_for_detected_game_with_crashgen_name(
                    &crashgen_version_str,
                    &detected_game_version_str,
                    &effective_crashgen_name,
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

        CrashgenScanContext {
            crashlog_filename,
            crashgen_version_str,
            main_error,
            fake_bot_compatible_mode,
            effective_crashgen_name,
            crashgen_status,
            crashgen_version,
            config_layout,
        }
    }

    fn collect_settings_contributions(
        &self,
        context: &ScanAnalysisContext,
        crashgen: &CrashgenScanContext,
    ) -> Vec<AutoscanReportContribution> {
        let settings_validator = if !context.crashgen_settings.is_empty() {
            if crashgen
                .effective_crashgen_name
                .eq_ignore_ascii_case(&self.config.crashgen_name)
            {
                self.settings_validator.clone()
            } else {
                Self::settings_validator_for_crashgen(
                    &self.config,
                    &crashgen.effective_crashgen_name,
                )
            }
        } else {
            self.settings_validator.clone()
        };

        if !crashgen.fake_bot_compatible_mode
            && !context.crashgen_settings.is_empty()
            && let Ok(contributions) = settings_validator.scan_all_settings_contributions(
                &context.crashgen_settings,
                &context.xse_modules_for_settings,
                crashgen.crashgen_version,
                crashgen.config_layout,
            )
        {
            return contributions;
        }

        Vec::new()
    }

    fn collect_plugins(
        &self,
        context: &ScanAnalysisContext,
    ) -> (Option<IndexMap<String, String>>, usize) {
        let Some(ref analyzer) = self.plugin_analyzer else {
            return (None, 0);
        };
        if context.plugin_lines.is_empty() {
            return (None, 0);
        }
        analyzer
            .loadorder_scan_log(
                &context.plugin_lines,
                Some(self.config.game_version.as_str()),
                Some(self.config.crashgen_latest.as_str()),
            )
            .map_or((None, 0), |(plugins, _limit_triggered, _limit_disabled)| {
                let plugin_count = plugins.len();
                (Some(plugins), plugin_count)
            })
    }

    fn collect_suspect_fragments(
        &self,
        context: &ScanAnalysisContext,
        main_error: &str,
    ) -> SuspectScanFragments {
        let Some(ref scanner) = self.suspect_scanner else {
            return SuspectScanFragments {
                fragments: Vec::new(),
                count: 0,
            };
        };

        let max_warn_length = 50;
        let (error_fragment, error_found) = scanner
            .suspect_scan_mainerror(main_error, max_warn_length)
            .unwrap_or_else(|_| (ReportFragment::empty(), false));
        let (stack_fragment, stack_found) = scanner
            .suspect_scan_stack(main_error, &context.combined_crash_text, max_warn_length)
            .unwrap_or_else(|_| (ReportFragment::empty(), false));
        let dll_fragment =
            SuspectScanner::check_dll_crash(main_error).unwrap_or_else(|_| ReportFragment::empty());

        let mut fragments = Vec::new();
        if error_found {
            fragments.push(error_fragment);
        }
        if stack_found {
            fragments.push(stack_fragment);
        }
        if !dll_fragment.is_empty() {
            fragments.push(dll_fragment);
        }

        let count = fragments.len();
        SuspectScanFragments { fragments, count }
    }

    fn collect_mod_contributions(
        &self,
        context: &ScanAnalysisContext,
        plugins: &IndexMap<String, String>,
    ) -> Vec<AutoscanReportContribution> {
        let mut contributions = Vec::new();
        let user_gpu_string: Option<String> = if context.system_segment_lines.is_empty() {
            None
        } else {
            let gpu_info = GpuDetector::get_gpu_info(&context.system_segment_lines);
            let mfr = gpu_info.manufacturer.as_str();
            if mfr == "Unknown" {
                None
            } else {
                Some(mfr.to_lowercase())
            }
        };
        let user_gpu = user_gpu_string.as_deref();

        if !self.config.mods_conf.is_empty()
            && let Ok(conflict_lines) = detect_mods_double(&self.config.mods_conf, plugins.clone())
            && !conflict_lines.is_empty()
        {
            contributions.push(AutoscanReportContribution::ModGuidance {
                group: ModGuidanceGroup::MayConflict,
                lines: conflict_lines,
            });
        }

        if !self.config.mods_freq.is_empty()
            && let Ok(freq_lines) = detect_mods_freq(&self.config.mods_freq, plugins)
            && !freq_lines.is_empty()
        {
            contributions.push(AutoscanReportContribution::ModGuidance {
                group: ModGuidanceGroup::FrequentCrashes,
                lines: freq_lines,
            });
        }

        if !self.config.mods_solu.is_empty()
            && let Ok(solu_lines) = detect_mods_solutions(&self.config.mods_solu, plugins)
            && !solu_lines.is_empty()
        {
            contributions.push(AutoscanReportContribution::ModGuidance {
                group: ModGuidanceGroup::HasSolutions,
                lines: solu_lines,
            });
        }

        if !self.config.mods_core.is_empty()
            && let Ok(important_lines) = detect_mods_important(
                &self.config.mods_core,
                plugins,
                user_gpu,
                &context.xse_modules_for_settings,
            )
            && !important_lines.is_empty()
        {
            contributions.push(AutoscanReportContribution::ModGuidance {
                group: ModGuidanceGroup::ImportantMods,
                lines: important_lines,
            });
        }

        contributions
    }

    fn collect_plugin_match_contributions(
        &self,
        context: &ScanAnalysisContext,
        plugins: &IndexMap<String, String>,
        effective_crashgen_name: &str,
    ) -> Vec<AutoscanReportContribution> {
        let Some(ref analyzer) = self.plugin_analyzer else {
            return Vec::new();
        };
        if plugins.is_empty() {
            return Vec::new();
        }

        let crashlog_plugins_lower: HashSet<String> =
            plugins.keys().map(|key| key.to_lowercase()).collect();
        analyzer
            .plugin_match_with_crashgen_name_from_lowered(
                &context.combined_crash_lower_lines,
                &crashlog_plugins_lower,
                effective_crashgen_name,
            )
            .map_or_else(
                |_| Vec::new(),
                |plugin_match_lines| {
                    vec![AutoscanReportContribution::PluginEvidence {
                        lines: plugin_match_lines,
                    }]
                },
            )
    }

    async fn collect_formid_and_record_contributions(
        &self,
        context: &ScanAnalysisContext,
        plugins_map: Option<&IndexMap<String, String>>,
        effective_crashgen_name: &str,
    ) -> Result<(Vec<AutoscanReportContribution>, usize)> {
        let mut contributions = Vec::new();
        let mut formid_count = 0;
        if !context.combined_crash_lines.is_empty() {
            let formids = self
                .formid_analyzer
                .extract_formids(context.combined_crash_lines.clone());
            formid_count = formids.len();

            if formid_count > 0 {
                let empty_plugins = IndexMap::new();
                let plugins_ref = plugins_map.unwrap_or(&empty_plugins);
                let formid_report_lines = self
                    .formid_analyzer
                    .formid_match_with_crashgen_name(formids, plugins_ref, effective_crashgen_name)
                    .await?;

                contributions.push(AutoscanReportContribution::FormIdFinding {
                    lines: formid_report_lines,
                });
            }
        }

        if let Some(ref record_scanner) = self.record_scanner
            && !context.combined_crash_lines.is_empty()
        {
            let (record_report, _matches) = record_scanner
                .try_scan_named_records_with_crashgen_name_and_lowercase(
                    &context.combined_crash_lines,
                    &context.combined_crash_lower_lines,
                    effective_crashgen_name,
                )?;
            if !record_report.is_empty() {
                contributions.push(AutoscanReportContribution::NamedRecordFinding {
                    lines: record_report,
                });
            }
        }

        Ok((contributions, formid_count))
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

    /// Checks crashgen version against a list of supported version floors.
    ///
    /// This supports multiple configured version floors per game version.
    ///
    /// # Arguments
    ///
    /// * `crashgen_version_str` - The crashgen version string from the crash log
    /// * `valid_versions` - Slice of supported version floor strings for the game version
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

    /// Checks crashgen version using the detected game version and registry-backed version floors.
    pub fn check_crashgen_version_for_detected_game(
        &self,
        crashgen_version_str: &str,
        detected_game_version_str: &str,
    ) -> (CrashgenVersion, CrashgenVersionStatus) {
        self.check_crashgen_version_for_detected_game_with_name(
            crashgen_version_str,
            detected_game_version_str,
            None,
        )
    }

    fn check_crashgen_version_for_detected_game_with_crashgen_name(
        &self,
        crashgen_version_str: &str,
        detected_game_version_str: &str,
        crashgen_name: &str,
    ) -> (CrashgenVersion, CrashgenVersionStatus) {
        self.check_crashgen_version_for_detected_game_with_name(
            crashgen_version_str,
            detected_game_version_str,
            Some(crashgen_name),
        )
    }

    fn check_crashgen_version_for_detected_game_with_name(
        &self,
        crashgen_version_str: &str,
        detected_game_version_str: &str,
        crashgen_name: Option<&str>,
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

        let (floor_versions, exception_versions) = match match_result.version_info {
            Some(ref version_info) => {
                let effective_crashgen_name = crashgen_name
                    .and_then(Self::trimmed_crashgen_name)
                    .or_else(|| {
                        Self::crashgen_name_from_version_string(version_info, crashgen_version_str)
                    })
                    .or_else(|| Self::trimmed_crashgen_name(&self.config.crashgen_name));

                let matching_configs = effective_crashgen_name.map_or_else(
                    || version_info.crashgen_versions.iter().collect::<Vec<_>>(),
                    |name| Self::crashgen_configs_for_name(version_info, name),
                );

                let mut floor_versions = Vec::new();
                let mut exception_versions = Vec::new();
                for config in matching_configs {
                    if config.exact_match {
                        exception_versions.push(config.version.as_str());
                    } else {
                        floor_versions.push(config.version.as_str());
                    }
                }

                (floor_versions, exception_versions)
            }
            None => (Vec::new(), Vec::new()),
        };

        let status = check_crashgen_version_status_with_exceptions(
            crashgen_version_str,
            &floor_versions,
            &exception_versions,
        );
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
    ) -> classic_config_core::ConfigLayout {
        if self
            .parse_detected_game_version(detected_game_version_str)
            .is_some()
        {
            classic_config_core::ConfigLayout::Og
        } else {
            classic_config_core::ConfigLayout::Unknown
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
                async move { write_autoscan_report(&file_io, &log_path, &report_lines).await }
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

    pub(crate) async fn write_autoscan_report(
        &self,
        log_path: &Path,
        report_lines: &[String],
    ) -> Result<PathBuf> {
        write_autoscan_report(&self.file_io, log_path, report_lines).await
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
#[path = "orchestrator_tests.rs"]
mod tests;
