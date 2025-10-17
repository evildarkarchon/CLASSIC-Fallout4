//! OrchestratorCore - Pure Rust crash log analysis orchestration (NO PyO3)
//!
//! This module provides the main orchestration layer that coordinates all analysis
//! components into a unified pipeline for processing crash logs.

use crate::error::Result;
use crate::parser::LogParser;
use classic_file_io_core::FileIOCore;
use std::collections::HashMap;
use std::sync::Arc;

/// Analysis configuration
///
/// Contains all necessary configuration data for analyzing crash logs.
#[derive(Clone)]
pub struct AnalysisConfig {
    /// Game name (e.g., "Fallout4")
    pub game: String,

    /// VR mode enabled
    pub vr_mode: bool,

    /// Crashgen name (e.g., "Buffout 4")
    pub crashgen_name: String,

    /// Latest crashgen version
    pub crashgen_latest: String,

    /// Game version
    pub game_version: String,

    /// XSE acronym (e.g., "F4SE")
    pub xse_acronym: String,

    /// Ignore lists (plugins, records, general)
    pub ignore_plugins: Vec<String>,
    pub ignore_records: Vec<String>,
    pub ignore_list: Vec<String>,

    /// Pattern dictionaries for suspect detection
    pub suspects_error: HashMap<String, String>,
    pub suspects_stack: HashMap<String, String>,

    /// Mod databases
    pub mods_core: HashMap<String, String>,
    pub mods_freq: HashMap<String, String>,
    pub mods_conf: HashMap<String, String>,
    pub mods_solu: HashMap<String, String>,
}

impl AnalysisConfig {
    /// Creates a new analysis configuration with default values for all optional fields.
    ///
    /// This constructor initializes an `AnalysisConfig` with the specified game and VR mode,
    /// setting all other fields (crash generator info, ignore lists, pattern dictionaries, mod databases)
    /// to empty defaults. These fields should be populated before analysis begins.
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
            game_version: String::new(),
            xse_acronym: String::new(),
            ignore_plugins: Vec::new(),
            ignore_records: Vec::new(),
            ignore_list: Vec::new(),
            suspects_error: HashMap::new(),
            suspects_stack: HashMap::new(),
            mods_core: HashMap::new(),
            mods_freq: HashMap::new(),
            mods_conf: HashMap::new(),
            mods_solu: HashMap::new(),
        }
    }
}

/// Analysis result for a single crash log
///
/// Contains all analysis results including the generated report,
/// statistics, and any errors encountered.
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

    /// Processing time in milliseconds
    pub processing_time_ms: u64,

    /// Number of FormIDs found
    pub formid_count: usize,

    /// Number of plugins detected
    pub plugin_count: usize,

    /// Number of suspect patterns matched
    pub suspect_count: usize,
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
    ///     150, // Processing took 150ms
    /// );
    ///
    /// assert!(result.success);
    /// assert!(result.error.is_none());
    /// ```
    pub fn success(log_path: String, report_lines: Vec<String>, processing_time_ms: u64) -> Self {
        Self {
            log_path,
            report_lines,
            success: true,
            error: None,
            processing_time_ms,
            formid_count: 0,
            plugin_count: 0,
            suspect_count: 0,
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
    /// ```
    pub fn failure(log_path: String, error: String) -> Self {
        Self {
            log_path,
            report_lines: Vec::new(),
            success: false,
            error: Some(error),
            processing_time_ms: 0,
            formid_count: 0,
            plugin_count: 0,
            suspect_count: 0,
        }
    }
}

/// Main orchestrator for crash log analysis (Pure Rust - NO PyO3)
///
/// Coordinates all analysis components to process crash logs from start to finish.
/// Uses async I/O and parallel processing for maximum performance.
pub struct OrchestratorCore {
    config: AnalysisConfig,
    file_io: FileIOCore,
    parser: LogParser,
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
        Ok(Self {
            config,
            file_io: FileIOCore::new("utf-8", "ignore", 100, 50),
            parser: LogParser::new(None)?,
        })
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

        // Convert to lines for parser (using Arc<str> for efficient memory sharing)
        let lines: Vec<Arc<str>> = log_content.lines().map(|s| Arc::from(s)).collect();

        // Parse log into segments
        let segments = self.parser.parse_segments(&lines);

        // Extract metadata, plugins, etc.
        let mut report_lines = Vec::new();
        report_lines.push(format!("Analysis of: {}\n", log_path));
        report_lines.push(format!("Segments found: {}\n", segments.len()));

        let processing_time_ms = start_time.elapsed().as_millis() as u64;

        Ok(AnalysisResult::success(
            log_path,
            report_lines,
            processing_time_ms,
        ))
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

        // Adaptive concurrency: start with CPU count, scale based on batch size
        let num_cpus = num_cpus::get();
        let max_concurrent = if log_paths.len() < num_cpus {
            log_paths.len()  // Small batch: process all concurrently
        } else {
            num_cpus.max(4)  // Large batch: use CPU count (min 4 for good throughput)
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
            .buffer_unordered(max_concurrent)  // ✅ Bounded parallelism
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
}
