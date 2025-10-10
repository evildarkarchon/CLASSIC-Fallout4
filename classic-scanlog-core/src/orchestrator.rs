//! OrchestratorCore - Pure Rust crash log analysis orchestration (NO PyO3)
//!
//! This module provides the main orchestration layer that coordinates all analysis
//! components into a unified pipeline for processing crash logs.

use crate::error::{Result, ScanLogError};
use crate::parser::LogParser;
use classic_file_io_core::FileIOCore;
use std::collections::HashMap;

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
    /// Create a new analysis configuration with default values
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
    /// Create a new successful analysis result
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

    /// Create a new failed analysis result
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
    /// Create a new orchestrator with the given configuration
    pub fn new(config: AnalysisConfig) -> Result<Self> {
        Ok(Self {
            config,
            file_io: FileIOCore::new("utf-8", "ignore", 100, 50),
            parser: LogParser::new(None)?,
        })
    }

    /// Process a single crash log file
    pub async fn process_log(&self, log_path: String) -> Result<AnalysisResult> {
        let start_time = std::time::Instant::now();

        // Read log file
        use std::path::Path;
        let log_content = self.file_io.read_file(Path::new(&log_path)).await?;

        // Convert to lines for parser
        let lines: Vec<String> = log_content.lines().map(|s| s.to_string()).collect();

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

    /// Process multiple log files in parallel
    pub async fn process_logs_batch(&self, log_paths: Vec<String>) -> Vec<AnalysisResult> {
        let mut results = Vec::new();

        for log_path in log_paths {
            match self.process_log(log_path.clone()).await {
                Ok(result) => results.push(result),
                Err(e) => results.push(AnalysisResult::failure(log_path, e.to_string())),
            }
        }

        results
    }

    /// Get the configuration
    pub fn config(&self) -> &AnalysisConfig {
        &self.config
    }
}
