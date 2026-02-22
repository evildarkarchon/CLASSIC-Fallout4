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

use crate::error::Result;
use crate::fcx_handler::FcxModeHandler;
use crate::formid_analyzer::FormIDAnalyzerCore;
use crate::gpu_detector::GpuDetector;
use crate::mod_detector::{detect_mods_double, detect_mods_important, detect_mods_single};
use crate::parser::LogParser;
use crate::plugin_analyzer::PluginAnalyzer;
use crate::record_scanner::RecordScanner;
use crate::report::ReportGenerator;
use crate::settings_validator::SettingsValidator;
use crate::suspect_scanner::SuspectScanner;
use crate::version::{
    CrashgenVersion, CrashgenVersionStatus, check_crashgen_version_status, crashgen_version_gen,
};
use classic_database_core::DatabasePool;
use classic_file_io_core::FileIOCore;
use classic_version_registry_core::{GameVersion as RegistryGameVersion, get_version_registry};
use indexmap::IndexMap;
use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::path::Path;
use std::sync::Arc;

/// Analysis configuration
///
/// Contains all necessary configuration data for analyzing crash logs.
/// This struct matches the fields from Python's `ClassicScanLogsInfo`.
#[derive(Clone)]
pub struct AnalysisConfig {
    /// Game name (e.g., "Fallout4")
    pub game: String,

    /// VR mode enabled
    pub vr_mode: bool,

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

    /// New/updated game version (for compatibility checks)
    pub game_version_new: String,

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

    /// Pattern dictionaries for suspect detection (IndexMap preserves YAML key order for Python parity)
    pub suspects_error: IndexMap<String, String>,
    /// Stack-based suspect patterns for crash analysis (IndexMap preserves YAML key order for Python parity)
    pub suspects_stack: IndexMap<String, Vec<String>>,

    /// Mod databases (IndexMap preserves YAML key order for Python parity)
    pub mods_core: IndexMap<String, String>,
    /// Frequently problematic mods database for crash analysis (IndexMap preserves YAML key order)
    pub mods_freq: IndexMap<String, String>,
    /// Mod conflict database for compatibility analysis (IndexMap preserves YAML key order)
    pub mods_conf: IndexMap<String, String>,
    /// Mod solutions database for providing fixes and workarounds (IndexMap preserves YAML key order)
    pub mods_solu: IndexMap<String, String>,
    /// Outdated, redundant, or community patch mods database (IndexMap preserves YAML key order)
    pub mods_opc2: IndexMap<String, String>,
    /// FOLON (Fallout: London) specific mods database (IndexMap preserves YAML key order)
    pub mods_core_folon: IndexMap<String, String>,

    /// Named records list for RecordScanner
    pub classic_records_list: Vec<String>,

    /// Settings to ignore when validating crashgen configuration
    pub crashgen_ignore: Vec<String>,
}

impl AnalysisConfig {
    /// Creates a new analysis configuration with default values for all optional fields.
    ///
    /// This constructor initializes an `AnalysisConfig` with the specified game and VR mode,
    /// setting all other fields (crash generator info, game versions, ignore lists, pattern dictionaries,
    /// mod databases) to empty defaults. These fields should be populated before analysis begins.
    ///
    /// # Arguments
    ///
    /// * `game` - The game name (e.g., "Fallout4", "Skyrim")
    /// * `vr_mode` - Whether VR mode is enabled for this game
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
    /// let mut config = AnalysisConfig::new("Fallout4".to_string(), false);
    ///
    /// // Populate with additional configuration
    /// config.crashgen_name = "Buffout 4".to_string();
    /// config.game_version = "1.10.163".to_string();
    /// config.xse_acronym = "F4SE".to_string();
    ///
    /// // Add ignore lists
    /// config.ignore_plugins = vec!["Fallout4.esm".to_string()];
    /// ```
    pub fn new(game: String, vr_mode: bool) -> Self {
        Self {
            game,
            vr_mode,
            crashgen_name: String::new(),
            crashgen_latest: String::new(),
            crashgen_latest_vr: String::new(),
            game_version: String::new(),
            game_version_vr: String::new(),
            game_version_new: String::new(),
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
            suspects_error: IndexMap::new(),
            suspects_stack: IndexMap::new(),
            mods_core: IndexMap::new(),
            mods_freq: IndexMap::new(),
            mods_conf: IndexMap::new(),
            mods_solu: IndexMap::new(),
            mods_opc2: IndexMap::new(),
            mods_core_folon: IndexMap::new(),
            classic_records_list: Vec::new(),
            crashgen_ignore: Vec::new(),
        }
    }
}

/// Build an `AnalysisConfig` from a [`YamlDataCore`] instance and runtime settings.
///
/// This is the canonical way to create an `AnalysisConfig` from loaded YAML data.
/// It uses VR-aware accessors to select the correct crashgen name, ignore list,
/// and game root name based on the `vr_mode` parameter.
///
/// # Arguments
///
/// * `yaml` - Reference to the loaded YAML configuration data
/// * `game` - Game identifier (e.g., "Fallout4", "Skyrim")
/// * `vr_mode` - Whether VR mode is active for this analysis
/// * `show_formid_values` - Whether to include FormID value lookups in reports
/// * `fcx_mode` - Whether FCX (enhanced analysis) mode is enabled
/// * `simplify_logs` - Whether to remove specified strings from crash logs
/// * `remove_list` - Strings to remove when `simplify_logs` is enabled
pub fn build_analysis_config_from_yaml(
    yaml: &classic_config_core::YamlDataCore,
    game: &str,
    vr_mode: bool,
    show_formid_values: bool,
    fcx_mode: bool,
    simplify_logs: bool,
    remove_list: Vec<String>,
) -> AnalysisConfig {
    AnalysisConfig {
        game: game.to_string(),
        vr_mode,
        crashgen_name: yaml.get_crashgen_name(vr_mode).to_string(),
        crashgen_latest: yaml.crashgen_latest_og.clone(),
        crashgen_latest_vr: yaml.crashgen_latest_vr.clone(),
        game_version: yaml.game_version.clone(),
        game_version_vr: yaml.game_version_vr.clone(),
        game_version_new: yaml.game_version_new.clone(),
        xse_acronym: yaml.xse_acronym.clone(),
        game_root_name: yaml.get_game_root_name(vr_mode).to_string(),
        classic_version: yaml.classic_version.clone(),
        ignore_plugins: yaml.game_ignore_plugins.clone(),
        ignore_records: yaml.game_ignore_records.clone(),
        ignore_list: yaml.ignore_list.clone(),
        show_formid_values,
        fcx_mode,
        simplify_logs,
        remove_list,
        suspects_error: yaml.suspects_error_list.clone(),
        suspects_stack: yaml.suspects_stack_list.clone(),
        mods_core: yaml.game_mods_core.clone(),
        mods_freq: yaml.game_mods_freq.clone(),
        mods_conf: yaml.game_mods_conf.clone(),
        mods_solu: yaml.game_mods_solu.clone(),
        mods_opc2: yaml.game_mods_opc2.clone(),
        mods_core_folon: yaml.game_mods_core_folon.clone(),
        classic_records_list: yaml.classic_records_list.clone(),
        crashgen_ignore: yaml.get_crashgen_ignore(vr_mode).to_vec(),
    }
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
/// * `module_lines` - Lines from the MODULES segment
///
/// # Returns
///
/// A HashSet of lowercase module names (DLL filenames only)
fn extract_module_names(module_lines: &[Arc<str>]) -> HashSet<String> {
    // Pre-compiled regex pattern to extract module name (everything up to .dll)
    // Pattern: (.*?\.dll)\s*v?.* - captures filename.dll, ignoring version info
    static MODULE_PATTERN: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"(?i)(.*?\.dll)\s*v?.*").unwrap());

    let mut result = HashSet::new();

    for line in module_lines {
        let text = line.trim();
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
    /// let mut config = AnalysisConfig::new("Fallout4".to_string(), false);
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
        // Initialize plugin analyzer if ignore lists are available
        let plugin_analyzer = if !config.ignore_plugins.is_empty() || !config.ignore_list.is_empty()
        {
            Some(PluginAnalyzer::new(
                config.ignore_plugins.clone(),
                config.ignore_list.clone(),
                config.crashgen_name.clone(),
                config.game_version.clone(),
                config.game_version_vr.clone(),
                config.game_version_new.clone(),
            )?)
        } else {
            None
        };

        // Initialize suspect scanner if suspect patterns are available
        let suspect_scanner =
            if !config.suspects_error.is_empty() || !config.suspects_stack.is_empty() {
                Some(SuspectScanner::new(
                    config.suspects_error.clone(),
                    config.suspects_stack.clone(),
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

        // Initialize settings validator
        let settings_validator =
            SettingsValidator::new(config.crashgen_name.clone(), config.crashgen_ignore.clone());

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
    /// let config = AnalysisConfig::new("Fallout4".to_string(), false);
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
    /// let config = AnalysisConfig::new("Fallout4".to_string(), false);
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
        use crate::report::{ReportComposer, ReportFragment};

        let start_time = std::time::Instant::now();

        // Read log file
        use std::path::Path;
        let log_content = self.file_io.read_file(Path::new(&log_path)).await?;

        // Convert to lines and apply preprocessing (matches Python's _reformat_crash_data_inline)
        // This handles:
        // 1. Removing lines containing strings from remove_list (if simplify_logs enabled)
        // 2. Normalizing bracket padding in PLUGINS section (e.g., "[ 1]" -> "[01]")
        let raw_lines: Vec<String> = log_content.lines().map(String::from).collect();
        let processed_lines = self.reformat_crash_data_inline(&raw_lines);

        // Convert to Arc<str> for efficient memory sharing during parsing
        let lines: Vec<Arc<str>> = processed_lines
            .iter()
            .map(|s| Arc::from(s.as_str()))
            .collect();

        // Parse log into segments
        let segments = self.parser.parse_segments(&lines);

        // Create ReportGenerator and ReportComposer for proper formatting
        let report_gen = self.create_report_generator();
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

        // Generate header
        composer.add(report_gen.generate_header(crashlog_filename));

        // Extract header info (crashgen version, main error) from the raw processed lines
        // We use processed_lines because header is in the first ~20 lines before segmentation
        let header_info = self
            .parser
            .parse_crash_header(&processed_lines)
            .unwrap_or_default();

        // Get crashgen version from header info
        let crashgen_version_str = header_info
            .get("crashgen_version")
            .cloned()
            .unwrap_or_default();

        // Get detected game version from header info (used for list-based version validation)
        let detected_game_version_str =
            header_info.get("game_version").cloned().unwrap_or_default();

        // Get main error - from header parsing or fallback to first "Unhandled exception" line
        let main_error = header_info.get("main_error").cloned().unwrap_or_else(|| {
            // Fallback: search processed_lines for Unhandled exception
            processed_lines
                .iter()
                .find(|line| line.starts_with("Unhandled exception"))
                .cloned()
                .unwrap_or_default()
        });

        // Check crashgen version status using list-based validation for the detected game version
        let crashgen_status = if crashgen_version_str.trim().is_empty() {
            None
        } else {
            let (_parsed, status) = self.check_crashgen_version_for_detected_game(
                &crashgen_version_str,
                &detected_game_version_str,
            );
            Some(status)
        };

        // Generate error section
        composer.add(report_gen.generate_error_section_with_status(
            &main_error,
            &crashgen_version_str,
            crashgen_status,
        ));

        // Store plugins for mod detection - IndexMap preserves load order for Python parity
        let mut plugins_map: Option<IndexMap<String, String>> = None;

        // Extract plugins from segments (if plugin analyzer is available)
        if let Some(ref analyzer) = self.plugin_analyzer {
            // Find plugin segment - scan backwards from end to find segment with game plugins
            // Game plugins have format: "[XX] PluginName.esp" or "[FE:XXX] PluginName.esl"
            // The Rust parser may return different segment counts depending on crash log format
            let plugin_segment_opt = segments.iter().rev().find(|seg| {
                // Check if segment contains game plugin entries
                seg.iter().any(|line| {
                    let trimmed = line.trim();
                    // Game plugins start with [XX] or [FE:XXX] and end with .esp/.esm/.esl
                    trimmed.starts_with('[')
                        && (trimmed.contains(".esp")
                            || trimmed.contains(".esm")
                            || trimmed.contains(".esl"))
                })
            });

            if let Some(plugin_segment) = plugin_segment_opt {
                // Convert Arc<str> to String for compatibility
                let plugin_lines: Vec<String> =
                    plugin_segment.iter().map(|s| s.to_string()).collect();

                // Scan plugins using the analyzer (limit flags unused for now, may need in future)
                if let Ok((plugins, _limit_triggered, _limit_disabled)) = analyzer
                    .loadorder_scan_log(
                        plugin_lines,
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
            // Use the main_error extracted from header parsing (not segments[0]!)
            // segments[0] contains crashgen settings, not the main error line

            // Extract callstack (segment 2: PROBABLE CALL STACK)
            let callstack = if segments.len() > 2 {
                segments[2].join("\n")
            } else {
                String::new()
            };

            let max_warn_length = 50; // Default width for formatting

            // Scan for error suspects (using header-extracted main_error)
            let (error_fragment, error_found) = scanner
                .suspect_scan_mainerror(&main_error, max_warn_length)
                .unwrap_or_else(|_| (ReportFragment::empty(), false));

            // Scan for stack suspects (using header-extracted main_error)
            let (stack_fragment, stack_found) = scanner
                .suspect_scan_stack(&main_error, &callstack, max_warn_length)
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

        // Extract XSE modules for settings validation (segment 3)
        let xse_modules_for_settings: HashSet<String> = if segments.len() > 3 {
            extract_module_names(&segments[3])
        } else {
            HashSet::new()
        };

        // Parse crashgen settings from Compatibility segment (segment 0)
        // Format: "key: value" (TOML-like with colon separator)
        // Skip section headers like [Compatibility], [Crashlog], [Fixes], etc.
        let crashgen_settings: HashMap<String, String> = if !segments.is_empty() {
            segments[0]
                .iter()
                .filter_map(|line| {
                    let line = line.trim();
                    // Skip section headers (lines starting with '[')
                    if line.starts_with('[') {
                        return None;
                    }
                    // Settings use colon as separator (e.g., "F4EE: true")
                    if let Some(colon_pos) = line.find(':') {
                        let key = line[..colon_pos].trim().to_string();
                        let value = line[colon_pos + 1..].trim().to_string();
                        if !key.is_empty() {
                            Some((key, value))
                        } else {
                            None
                        }
                    } else {
                        None
                    }
                })
                .collect()
        } else {
            HashMap::new()
        };

        // Add settings validation section
        if !crashgen_settings.is_empty() {
            let mut settings_fragments = Vec::new();

            // Achievements check
            if let Ok(achievements_fragment) =
                self.settings_validator.scan_buffout_achievements_setting(
                    xse_modules_for_settings.clone(),
                    &crashgen_settings,
                )
            {
                if !achievements_fragment.is_empty() {
                    settings_fragments.push(achievements_fragment);
                }
            }

            // Memory Manager check (check for X-Cell and Baka ScrapHeap)
            let has_xcell = [
                "x-cell-fo4.dll",
                "x-cell-og.dll",
                "x-cell-ng2.dll",
                "x-cell-ae.dll",
                "addictol.dll",
            ]
            .iter()
            .any(|dll| xse_modules_for_settings.contains(*dll));
            let has_old_xcell = false; // Would need version check
            let has_baka_scrapheap = xse_modules_for_settings.contains("bakascrapheap.dll");
            if let Ok(memory_fragment) = self
                .settings_validator
                .scan_buffout_memorymanagement_settings(
                    &crashgen_settings,
                    has_xcell,
                    has_old_xcell,
                    has_baka_scrapheap,
                )
            {
                if !memory_fragment.is_empty() {
                    settings_fragments.push(memory_fragment);
                }
            }

            // ArchiveLimit check
            if let Ok(archive_fragment) = self.settings_validator.scan_archivelimit_setting(
                &crashgen_settings,
                None, // Version parsing would go here
            ) {
                if !archive_fragment.is_empty() {
                    settings_fragments.push(archive_fragment);
                }
            }

            // LooksMenu check
            if let Ok(looksmenu_fragment) = self.settings_validator.scan_buffout_looksmenu_setting(
                &crashgen_settings,
                xse_modules_for_settings.clone(),
            ) {
                if !looksmenu_fragment.is_empty() {
                    settings_fragments.push(looksmenu_fragment);
                }
            }

            if !settings_fragments.is_empty() {
                composer.add(report_gen.generate_settings_section_header());
                for settings_fragment in settings_fragments {
                    composer.add(settings_fragment);
                }
            }
        }

        // Mod detection (if we have plugin data)
        if let Some(ref plugins) = plugins_map {
            // Extract GPU info from system segment (segment 1)
            let gpu_rival_string: Option<String> = if segments.len() > 1 {
                let system_segment: Vec<String> =
                    segments[1].iter().map(|s| s.to_string()).collect();
                let gpu_info = GpuDetector::get_gpu_info(&system_segment);
                gpu_info.rival
            } else {
                None
            };
            let gpu_rival = gpu_rival_string.as_deref();

            // Extract XSE modules from MODULES segment (segment 3)
            let xse_modules: HashSet<String> = if segments.len() > 3 {
                extract_module_names(&segments[3])
            } else {
                HashSet::new()
            };

            // Check for conflicting mods
            if !self.config.mods_conf.is_empty() {
                if let Ok(conflict_lines) =
                    detect_mods_double(self.config.mods_conf.clone(), plugins.clone())
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
                if let Ok(solu_lines) =
                    detect_mods_single(self.config.mods_solu.clone(), plugins.clone())
                {
                    if !solu_lines.is_empty() {
                        composer.add(report_gen.generate_mod_check_header("HAVE SOLUTIONS"));
                        composer.add(ReportFragment::from_lines(solu_lines));
                    }
                }
            }

            // Check for important core mods with GPU considerations
            if !self.config.mods_core.is_empty() {
                if let Ok(important_lines) = detect_mods_important(
                    self.config.mods_core.clone(),
                    plugins.clone(),
                    gpu_rival,
                    xse_modules.clone(),
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

            // Check for OPC2 mods (outdated, redundant, or have community patches)
            if !self.config.mods_opc2.is_empty() {
                if let Ok(opc2_lines) =
                    detect_mods_single(self.config.mods_opc2.clone(), plugins.clone())
                {
                    if !opc2_lines.is_empty() {
                        composer.add(report_gen.generate_mod_check_header(
                            "Are Outdated, Redundant, or Have Community Patches",
                        ));
                        composer.add(ReportFragment::from_lines(opc2_lines));
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
                    // Get callstack segment (segment 2) for plugin matching
                    let segment_callstack_lower: Vec<String> = if segments.len() > 2 {
                        segments[2].iter().map(|s| s.to_lowercase()).collect()
                    } else {
                        Vec::new()
                    };

                    // Convert plugins to lowercase set for matching
                    let crashlog_plugins_lower: HashSet<String> =
                        plugins.keys().map(|k| k.to_lowercase()).collect();

                    // Call plugin_match to find plugins in crash stack
                    if let Ok(plugin_match_lines) =
                        analyzer.plugin_match(segment_callstack_lower, crashlog_plugins_lower)
                    {
                        // Add the header and the plugin match results
                        composer.add(report_gen.generate_plugin_suspect_header());
                        composer.add(ReportFragment::from_lines(plugin_match_lines));
                    }
                }
            }
        }

        // Extract FormIDs from callstack segment (segment 2 includes registers/stack
        // since it spans from PROBABLE CALL STACK: to MODULES:)
        // FormIDs are ALWAYS shown regardless of show_formid_values setting.
        // The show_formid_values setting only controls whether database descriptions are included.
        if segments.len() > 2 {
            let callstack_segment = &segments[2];

            // Convert Arc<str> to String for FormID extraction
            let callstack_lines: Vec<String> =
                callstack_segment.iter().map(|s| s.to_string()).collect();

            // Extract FormIDs using FormIDAnalyzerCore
            let formids = self.formid_analyzer.extract_formids(callstack_lines);
            formid_count = formids.len();

            if formid_count > 0 {
                // Match FormIDs against plugins for proper formatting
                // Format: plugin_name | FormID (or plugin_name | FormID | db_value)
                let empty_plugins = IndexMap::new();
                let plugins_ref = plugins_map.as_ref().unwrap_or(&empty_plugins);

                let formid_report_lines = self
                    .formid_analyzer
                    .formid_match(formids, plugins_ref)
                    .await?;

                composer.add(report_gen.generate_formid_section_header());
                composer.add(ReportFragment::from_lines(formid_report_lines));
            }
        }

        // Add Named Records section (scan callstack for named records)
        if let Some(ref record_scanner) = self.record_scanner {
            if segments.len() > 2 {
                let callstack_segment = &segments[2];
                let callstack_lines: Vec<String> =
                    callstack_segment.iter().map(|s| s.to_string()).collect();

                let (record_report, _matches) = record_scanner.scan_named_records(&callstack_lines);
                if !record_report.is_empty() {
                    composer.add(report_gen.generate_record_section_header());
                    composer.add(ReportFragment::from_lines(record_report));
                }
            }
        }

        // Add footer (timing is tracked in AnalysisResult, not in report - matches Python)
        let elapsed = start_time.elapsed();
        let elapsed_us = elapsed.as_micros() as u64;

        composer.add(report_gen.generate_footer());

        // Compose final report
        let final_report = composer.compose();
        let report_lines = final_report.to_list();

        let mut result = AnalysisResult::success(log_path, report_lines, elapsed_us);

        // Update statistics
        result.formid_count = formid_count;
        result.plugin_count = plugin_count;
        result.suspect_count = suspect_count;

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
    /// let config = AnalysisConfig::new("Fallout4".to_string(), false);
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
        let concurrency = match max_concurrent {
            Some(n) => n.max(1), // User-specified, minimum 1
            None => {
                // Adaptive concurrency: start with CPU count, scale based on batch size
                let num_cpus = num_cpus::get();
                if log_paths.len() < num_cpus {
                    log_paths.len().max(1) // Small batch: process all concurrently, min 1
                } else {
                    num_cpus.max(4) // Large batch: use CPU count (min 4 for good throughput)
                }
            }
        };

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
    /// let config = AnalysisConfig::new("Fallout4".to_string(), false);
    /// let orchestrator = OrchestratorCore::new(config)?;
    ///
    /// // Access configuration after creation
    /// let config_ref = orchestrator.config();
    /// println!("Analyzing game: {}", config_ref.game);
    /// println!("VR mode: {}", config_ref.vr_mode);
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
    /// This matches Python's `_detect_incomplete_log()` logic.
    ///
    /// # Arguments
    ///
    /// * `segment_plugin` - The plugin segment from the parsed crash log
    ///
    /// # Returns
    ///
    /// `true` if the log is incomplete (plugin segment is empty or too short).
    pub fn detect_incomplete_log(&self, segment_plugin: &[String]) -> bool {
        // Python considers log incomplete if plugin segment is missing or empty
        segment_plugin.is_empty() || segment_plugin.len() < 2
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

    /// Creates a SettingsValidator configured for this orchestrator.
    ///
    /// # Returns
    ///
    /// A `SettingsValidator` instance configured with the crashgen name
    /// and ignore settings from the analysis configuration.
    pub fn create_settings_validator(&self) -> SettingsValidator {
        SettingsValidator::new(
            self.config.crashgen_name.clone(),
            self.config.crashgen_ignore.clone(),
        )
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
            self.config.vr_mode,
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

    /// Checks if the game is running FOLON (Fallout: London) based on plugins.
    ///
    /// # Arguments
    ///
    /// * `plugins` - Map of plugin names to their data
    ///
    /// # Returns
    ///
    /// `true` if FOLON (londonworldspace.esm) is detected.
    pub fn detect_folon(&self, plugins: &HashMap<String, String>) -> bool {
        plugins
            .keys()
            .any(|name| name.to_lowercase().contains("londonworldspace.esm"))
    }

    /// Returns the appropriate mods_core database based on whether FOLON is detected.
    ///
    /// When FOLON (Fallout: London) is detected and a FOLON-specific mod database is
    /// available, returns that database. Otherwise, returns the standard mods_core.
    ///
    /// # Arguments
    ///
    /// * `plugins` - Map of plugin names to their data (used to detect FOLON)
    ///
    /// # Returns
    ///
    /// Reference to the appropriate mods_core database (IndexMap preserves YAML order).
    pub fn get_mods_core_for_plugins(
        &self,
        plugins: &HashMap<String, String>,
    ) -> &IndexMap<String, String> {
        if self.detect_folon(plugins) && !self.config.mods_core_folon.is_empty() {
            &self.config.mods_core_folon
        } else {
            &self.config.mods_core
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
    /// let config = AnalysisConfig::new("Fallout4".to_string(), false);
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

    fn make_yaml_data(classic_version: &str) -> classic_config_core::YamlDataCore {
        classic_config_core::YamlDataCore {
            classic_game_hints: Vec::new(),
            classic_records_list: Vec::new(),
            classic_version: classic_version.to_string(),
            classic_version_date: String::new(),
            crashgen_name: "Buffout 4".to_string(),
            crashgen_name_vr: "Buffout 4 VR".to_string(),
            crashgen_latest_og: String::new(),
            crashgen_latest_vr: String::new(),
            crashgen_ignore: Vec::new(),
            crashgen_ignore_vr: Vec::new(),
            warn_noplugins: String::new(),
            warn_outdated: String::new(),
            xse_acronym: "F4SE".to_string(),
            game_ignore_plugins: Vec::new(),
            game_ignore_records: Vec::new(),
            ignore_list: Vec::new(),
            suspects_error_list: IndexMap::new(),
            suspects_stack_list: IndexMap::new(),
            game_mods_conf: IndexMap::new(),
            game_mods_core: IndexMap::new(),
            game_mods_core_folon: IndexMap::new(),
            game_mods_freq: IndexMap::new(),
            game_mods_opc2: IndexMap::new(),
            game_mods_solu: IndexMap::new(),
            autoscan_text: String::new(),
            game_version: String::new(),
            game_version_new: String::new(),
            game_version_vr: String::new(),
            game_root_name: "Fallout4".to_string(),
            game_root_name_vr: "Fallout4VR".to_string(),
        }
    }

    #[test]
    fn build_analysis_config_does_not_double_prefix_classic_version() {
        let yaml = make_yaml_data("CLASSIC v9.0.0");

        let config = build_analysis_config_from_yaml(
            &yaml,
            "Fallout4",
            false,
            false,
            false,
            false,
            Vec::new(),
        );

        assert_eq!(config.classic_version, "CLASSIC v9.0.0");
    }

    #[test]
    fn check_crashgen_version_for_detected_game_validates_addictol_for_ae() {
        let config = AnalysisConfig::new("Fallout4".to_string(), false);
        let orchestrator = OrchestratorCore::new(config).unwrap();

        let (_parsed, status) = orchestrator.check_crashgen_version_for_detected_game(
            "Addictol v1.0.0 Feb 16 2026 08:02:06",
            "Fallout 4 v1.11.191",
        );

        assert_eq!(status, crate::version::CrashgenVersionStatus::Valid);
    }
}
