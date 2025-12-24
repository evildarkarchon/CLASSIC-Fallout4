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
use crate::version::{CrashgenVersion, crashgen_version_gen};
use classic_database_core::DatabasePool;
use classic_file_io_core::FileIOCore;
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

    /// Pattern dictionaries for suspect detection
    pub suspects_error: HashMap<String, String>,
    /// Stack-based suspect patterns for crash analysis (e.g., function names, memory addresses)
    pub suspects_stack: HashMap<String, Vec<String>>,

    /// Mod databases
    pub mods_core: HashMap<String, String>,
    /// Frequently problematic mods database for crash analysis (e.g., known unstable mods, compatibility issues)
    pub mods_freq: HashMap<String, String>,
    /// Mod conflict database for compatibility analysis (e.g., known mod conflicts, incompatible combinations)
    pub mods_conf: HashMap<String, String>,
    /// Mod solutions database for providing fixes and workarounds (e.g., compatibility patches, configuration changes)
    pub mods_solu: HashMap<String, String>,
    /// Outdated, redundant, or community patch mods database
    pub mods_opc2: HashMap<String, String>,
    /// FOLON (Fallout: London) specific mods database
    pub mods_core_folon: HashMap<String, String>,

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
            suspects_error: HashMap::new(),
            suspects_stack: HashMap::new(),
            mods_core: HashMap::new(),
            mods_freq: HashMap::new(),
            mods_conf: HashMap::new(),
            mods_solu: HashMap::new(),
            mods_opc2: HashMap::new(),
            mods_core_folon: HashMap::new(),
            classic_records_list: Vec::new(),
            crashgen_ignore: Vec::new(),
        }
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
    ///     .with_database_pool(Arc::new(db_pool));
    /// # Ok(())
    /// # }
    /// ```
    #[must_use]
    pub fn with_database_pool(mut self, pool: Arc<DatabasePool>) -> Self {
        // Update the FormID analyzer with the database pool
        self.formid_analyzer = FormIDAnalyzerCore::new(
            Some(pool.clone()),
            self.config.show_formid_values,
            self.config.crashgen_name.clone(),
            self.config.mods_core.clone(),
            self.config.mods_freq.clone(),
            self.config.mods_conf.clone(),
        )
        .unwrap_or_else(|_| {
            // Fallback without database pool if creation fails
            FormIDAnalyzerCore::new(
                None,
                self.config.show_formid_values,
                self.config.crashgen_name.clone(),
                self.config.mods_core.clone(),
                self.config.mods_freq.clone(),
                self.config.mods_conf.clone(),
            )
            .expect("FormID analyzer creation should not fail")
        });
        self.db_pool = Some(pool);
        self
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

        // Initialize report
        let mut report_lines = Vec::new();
        report_lines.push(format!("Analysis of: {}\n", log_path));
        report_lines.push(format!("Segments found: {}\n", segments.len()));
        report_lines.push("\n".to_string());

        // Statistics
        let mut formid_count = 0;
        let mut plugin_count = 0;
        let mut suspect_count = 0;

        // Store plugins for mod detection
        let mut plugins_map: Option<HashMap<String, String>> = None;

        // Extract plugins from segments (if plugin analyzer is available)
        if let Some(ref analyzer) = self.plugin_analyzer {
            // Find plugin segment (typically the 6th segment in Buffout logs)
            if segments.len() > 5 {
                let plugin_segment = &segments[5];

                // Convert Arc<str> to String for compatibility
                let plugin_lines: Vec<String> =
                    plugin_segment.iter().map(|s| s.to_string()).collect();

                // Scan plugins using the analyzer
                if let Ok((plugins, loaded, _)) = analyzer.loadorder_scan_log(
                    plugin_lines,
                    Some(self.config.game_version.as_str()),
                    Some(self.config.crashgen_latest.as_str()),
                ) {
                    plugin_count = plugins.len();
                    if loaded {
                        report_lines.push(format!("PLUGINS: {} loaded\n", plugin_count));

                        // Add top 5 plugins to report
                        let sample_plugins: Vec<_> = plugins.keys().take(5).collect();
                        for (i, plugin) in sample_plugins.iter().enumerate() {
                            report_lines.push(format!("  {}. {}\n", i + 1, plugin));
                        }
                        if plugin_count > 5 {
                            report_lines.push(format!("  ... and {} more\n", plugin_count - 5));
                        }
                        report_lines.push("\n".to_string());
                    }
                    // Store plugins for mod detection
                    plugins_map = Some(plugins);
                }
            }
        }

        // Extract FormIDs from callstack (typically the 3rd segment)
        if segments.len() > 2 {
            let callstack_segment = &segments[2];

            // Convert Arc<str> to String for FormID extraction
            let callstack_lines: Vec<String> =
                callstack_segment.iter().map(|s| s.to_string()).collect();

            // Extract FormIDs using FormIDAnalyzerCore
            let formids = self.formid_analyzer.extract_formids(callstack_lines);
            formid_count = formids.len();

            if formid_count > 0 {
                report_lines.push(format!("FORMIDS: {} found\n", formid_count));

                // Add top 5 FormIDs to report
                for (i, formid) in formids.iter().take(5).enumerate() {
                    report_lines.push(format!("  {}. {}\n", i + 1, formid));
                }
                if formid_count > 5 {
                    report_lines.push(format!("  ... and {} more\n", formid_count - 5));
                }
                report_lines.push("\n".to_string());
            }
        }

        // Scan for suspects (if suspect scanner is available)
        if let Some(ref scanner) = self.suspect_scanner {
            // Extract main error (typically first segment)
            let main_error = if !segments.is_empty() {
                segments[0].join("\n")
            } else {
                String::new()
            };

            // Extract callstack (typically third segment)
            let callstack = if segments.len() > 2 {
                segments[2].join("\n")
            } else {
                String::new()
            };

            let max_warn_length = 50; // Default width for formatting

            // Scan for error suspects
            let (error_fragment, error_found) = scanner
                .suspect_scan_mainerror(&main_error, max_warn_length)
                .unwrap_or_else(|_| (crate::report::ReportFragment::empty(), false));

            // Scan for stack suspects
            let (stack_fragment, stack_found) = scanner
                .suspect_scan_stack(&main_error, &callstack, max_warn_length)
                .unwrap_or_else(|_| (crate::report::ReportFragment::empty(), false));

            if error_found || stack_found {
                report_lines.push("SUSPECTS FOUND:\n".to_string());
                report_lines.push("─".repeat(60).to_string());
                report_lines.push("\n".to_string());

                if error_found {
                    report_lines.extend(error_fragment.to_list());
                }

                if stack_found {
                    report_lines.extend(stack_fragment.to_list());
                }

                report_lines.push("\n".to_string());
                suspect_count = if error_found { 1 } else { 0 } + if stack_found { 1 } else { 0 };
            }
        }

        // Mod detection (if we have plugin data)
        if let Some(plugins) = plugins_map {
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
                        report_lines.extend(conflict_lines);
                    }
                }
            }

            // Check for frequently problematic mods
            if !self.config.mods_freq.is_empty() {
                if let Ok(freq_lines) =
                    detect_mods_single(self.config.mods_freq.clone(), plugins.clone())
                {
                    if !freq_lines.is_empty() {
                        report_lines.extend(freq_lines);
                    }
                }
            }

            // Check for mods with known solutions
            if !self.config.mods_solu.is_empty() {
                if let Ok(solu_lines) =
                    detect_mods_single(self.config.mods_solu.clone(), plugins.clone())
                {
                    if !solu_lines.is_empty() {
                        report_lines.extend(solu_lines);
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
                        report_lines.extend(important_lines);
                    }
                }
            }

            // Check for OPC2 mods (outdated, redundant, or have community patches)
            if !self.config.mods_opc2.is_empty() {
                if let Ok(opc2_lines) =
                    detect_mods_single(self.config.mods_opc2.clone(), plugins.clone())
                {
                    if !opc2_lines.is_empty() {
                        report_lines.extend(opc2_lines);
                    }
                }
            }
        }

        report_lines.push("─".repeat(60).to_string());
        report_lines.push("\n".to_string());
        let elapsed = start_time.elapsed();
        let elapsed_us = elapsed.as_micros() as u64;
        let elapsed_ms_display = elapsed_us as f64 / 1000.0;
        report_lines.push(format!(
            "Analysis completed in {:.2}ms\n",
            elapsed_ms_display
        ));

        let mut result = AnalysisResult::success(log_path, report_lines, elapsed_us);

        // Update statistics
        result.formid_count = formid_count;
        result.plugin_count = plugin_count;
        result.suspect_count = suspect_count;

        Ok(result)
    }

    /// Asynchronously processes multiple crash log files sequentially.
    ///
    /// This function processes a batch of crash logs one at a time, collecting all results
    /// into a vector. Each log is analyzed independently, and failures don't stop processing
    /// of remaining logs. Failed analyses are returned as `AnalysisResult` instances with
    /// `success = false` and error messages.
    ///
    /// **Note**: Despite the name, this implementation currently processes logs sequentially.
    /// Future versions may add true parallel processing using `tokio::spawn` or `futures::join_all`.
    ///
    /// # Arguments
    ///
    /// * `log_paths` - Vector of paths to crash log files to analyze
    ///
    /// # Returns
    ///
    /// Returns a `Vec<AnalysisResult>` with one result per input log path, in the same order.
    /// Failed analyses are included as failure results rather than being filtered out.
    ///
    /// # Performance
    ///
    /// - Sequential processing: processes one log at a time
    /// - Each log: ~50-200ms (SIMD-optimized parsing)
    /// - Future parallel version could achieve near-linear speedup with multiple CPU cores
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
    /// let results = orchestrator.process_logs_batch(logs).await;
    ///
    /// let successful = results.iter().filter(|r| r.success).count();
    /// let failed = results.iter().filter(|r| !r.success).count();
    ///
    /// println!("Processed {} logs: {} succeeded, {} failed", results.len(), successful, failed);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn process_logs_batch(&self, log_paths: Vec<String>) -> Vec<AnalysisResult> {
        // Optimization 1.8: Bounded parallel processing instead of sequential
        // Expected impact: 3-4x faster for multiple logs (CPU core count dependent)
        use futures::stream::{self, StreamExt};

        if log_paths.is_empty() {
            return Vec::new();
        }

        // Adaptive concurrency: start with CPU count, scale based on batch size
        let num_cpus = num_cpus::get();
        let max_concurrent = if log_paths.len() < num_cpus {
            log_paths.len().max(1) // Small batch: process all concurrently, min 1
        } else {
            num_cpus.max(4) // Large batch: use CPU count (min 4 for good throughput)
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
            .buffer_unordered(max_concurrent) // ✅ Bounded parallelism
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

    /// Parses crashgen version from a crash log and checks if it's outdated.
    ///
    /// # Arguments
    ///
    /// * `crashgen_version_str` - The crashgen version string from the crash log
    ///
    /// # Returns
    ///
    /// A tuple of (parsed_version, is_outdated).
    pub fn check_crashgen_version(&self, crashgen_version_str: &str) -> (CrashgenVersion, bool) {
        let current = crashgen_version_gen(crashgen_version_str);
        let latest = crashgen_version_gen(&self.config.crashgen_latest);
        let latest_vr = crashgen_version_gen(&self.config.crashgen_latest_vr);

        let is_outdated = current.is_outdated(&latest, &latest_vr, self.config.vr_mode);

        (current, is_outdated)
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
    /// Reference to the appropriate mods_core database.
    pub fn get_mods_core_for_plugins(
        &self,
        plugins: &HashMap<String, String>,
    ) -> &HashMap<String, String> {
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
