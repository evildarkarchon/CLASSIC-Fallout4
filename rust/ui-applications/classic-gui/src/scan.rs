//! Scan orchestration module - Real crash log analysis
//!
//! Connects LogCollector (log discovery) and OrchestratorCore (analysis)
//! to the Slint GUI with progress reporting and cooperative cancellation.

use std::path::PathBuf;

use classic_file_io_core::LogCollector;
use classic_scanlog_core::{AnalysisConfig, AnalysisResult, OrchestratorCore};
use slint::Weak;
use tokio_util::sync::CancellationToken;

use crate::worker::ScanWindowProperties;

/// Result of a scan operation
///
/// Tracks all analysis results, error counts, and cancellation state.
/// Used by the UI completion handler to display final status.
pub struct ScanResult {
    /// Reports from successfully analyzed logs
    pub reports: Vec<AnalysisResult>,
    /// Number of logs that encountered errors
    pub error_count: usize,
    /// Total logs attempted (for cancelled display)
    pub attempted: usize,
    /// Total logs found
    pub total: usize,
    /// Whether scan was cancelled
    pub cancelled: bool,
}

impl ScanResult {
    /// Create a result for a completed scan
    fn complete(reports: Vec<AnalysisResult>, errors: usize) -> Self {
        let total = reports.len() + errors;
        Self {
            reports,
            error_count: errors,
            attempted: total,
            total,
            cancelled: false,
        }
    }

    /// Create a result for a cancelled scan with partial results preserved
    fn cancelled(reports: Vec<AnalysisResult>, attempted: usize, total: usize) -> Self {
        Self {
            error_count: 0,
            reports,
            attempted,
            total,
            cancelled: true,
        }
    }

    /// Format the scan result as a human-readable status message
    ///
    /// Returns contextual messages:
    /// - `"No crash logs found"` for empty discovery
    /// - `"Scanned N logs"` for successful completion
    /// - `"Scanned N logs (M errors)"` for completion with errors
    /// - `"Cancelled (X of Y logs)"` for user cancellation
    pub fn format_status(&self) -> String {
        if self.total == 0 {
            "No crash logs found".to_string()
        } else if self.cancelled {
            format!("Cancelled ({} of {} logs)", self.attempted, self.total)
        } else if self.error_count > 0 {
            format!(
                "Scanned {} logs ({} errors)",
                self.total, self.error_count
            )
        } else {
            format!("Scanned {} logs", self.total)
        }
    }

    /// Check if scan completed successfully with results
    ///
    /// Returns `true` only when the scan was not cancelled and produced
    /// at least one analysis report. Used to decide whether to auto-switch
    /// to the Results tab.
    pub fn has_results(&self) -> bool {
        !self.cancelled && !self.reports.is_empty()
    }
}

/// Scan crash logs using LogCollector for discovery and OrchestratorCore for analysis
///
/// This async function coordinates the full scan workflow:
/// 1. Discovery phase: Uses LogCollector to find crash logs (indeterminate progress)
/// 2. Analysis phase: Processes each log with OrchestratorCore (determinate progress)
///
/// Progress is reported to the UI via `upgrade_in_event_loop` after each log.
/// Cancellation is checked before each log via `CancellationToken`.
///
/// # Arguments
///
/// * `window_weak` - Weak reference to the Slint window for progress updates
/// * `cancel_token` - Token for cooperative cancellation
/// * `crash_log_path` - Base folder path for log discovery
pub async fn scan_crash_logs<W>(
    window_weak: Weak<W>,
    cancel_token: CancellationToken,
    crash_log_path: String,
) -> Result<ScanResult, String>
where
    W: slint::ComponentHandle + ScanWindowProperties + 'static,
{
    // Phase 1: Log discovery (indeterminate progress)
    update_status(&window_weak, "Discovering crash logs...", -1.0);

    let base_folder = PathBuf::from(&crash_log_path);
    let collector = LogCollector::new(base_folder, None, None);

    let log_paths = collector
        .collect_all()
        .await
        .map_err(|e| format!("Failed to collect logs: {}", e))?;

    if log_paths.is_empty() {
        return Err("No crash logs found".to_string());
    }

    let total = log_paths.len();

    // Switch from indeterminate to determinate progress (0%)
    update_status(
        &window_weak,
        &format!("Found {} crash logs, analyzing...", total),
        0.0,
    );

    // Create OrchestratorCore with default config for Fallout4
    let orchestrator = create_orchestrator()
        .map_err(|e| format!("Failed to initialize scanner: {}", e))?;

    // Phase 2: Analysis (determinate progress)
    let mut results = Vec::new();
    let mut errors = 0;

    for (i, path) in log_paths.iter().enumerate() {
        // Check for cancellation before each log
        if cancel_token.is_cancelled() {
            return Ok(ScanResult::cancelled(results, i, total));
        }

        let filename = path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();
        let progress = ((i + 1) as f32 / total as f32) * 100.0;

        update_progress(&window_weak, progress, &filename);

        match orchestrator
            .process_log(path.to_string_lossy().to_string())
            .await
        {
            Ok(result) => results.push(result),
            Err(_) => errors += 1,
        }
    }

    Ok(ScanResult::complete(results, errors))
}

/// Create an OrchestratorCore with default Fallout4 configuration
///
/// Uses minimal AnalysisConfig suitable for basic crash log scanning.
/// Full configuration (suspect patterns, mod databases) will be loaded
/// from YAML settings in Phase 24 (Settings).
fn create_orchestrator() -> Result<OrchestratorCore, String> {
    let config = AnalysisConfig::new("Fallout4".to_string(), false);
    OrchestratorCore::new(config).map_err(|e| format!("OrchestratorCore init failed: {}", e))
}

/// Update scan status with indeterminate or determinate progress
fn update_status<W>(window_weak: &Weak<W>, status: &str, progress: f32)
where
    W: slint::ComponentHandle + ScanWindowProperties + 'static,
{
    let status = status.to_string();
    let _ = window_weak.upgrade_in_event_loop(move |window| {
        window.set_scan_progress(progress);
        window.set_scan_status(status.into());
    });
}

/// Update scan progress with percentage and current filename
fn update_progress<W>(window_weak: &Weak<W>, progress: f32, filename: &str)
where
    W: slint::ComponentHandle + ScanWindowProperties + 'static,
{
    let status = format!("{:.0}% - Scanning {}...", progress, filename);
    let _ = window_weak.upgrade_in_event_loop(move |window| {
        window.set_scan_progress(progress);
        window.set_scan_status(status.into());
    });
}
