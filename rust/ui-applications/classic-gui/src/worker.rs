//! Worker module - Background operations with progress callbacks
//!
//! Provides the worker thread pattern for long-running operations that
//! need to report progress to the UI without blocking.

use std::time::Duration;

use slint::Weak;
use tokio_util::sync::CancellationToken;

/// Simulated scan operation demonstrating the worker pattern
///
/// This function demonstrates:
/// 1. Progress callbacks to UI thread via upgrade_in_event_loop
/// 2. Cooperative cancellation via CancellationToken
/// 3. Non-blocking execution on Tokio runtime
///
/// In Phase 21, this will be replaced with actual OrchestratorCore scan logic.
pub async fn simulate_scan<W>(
    window_weak: Weak<W>,
    cancel_token: CancellationToken,
) -> Result<String, String>
where
    W: slint::ComponentHandle + 'static,
    W: ScanWindowProperties,
{
    // Simulated files to scan
    let files = vec![
        "crash-2024-01-15-08-30-00.log",
        "crash-2024-01-16-12-45-30.log",
        "crash-2024-01-17-03-20-15.log",
        "crash-2024-01-18-09-55-45.log",
        "crash-2024-01-19-14-10-00.log",
    ];
    let total = files.len() as f32;

    for (i, file) in files.iter().enumerate() {
        // Check for cancellation
        if cancel_token.is_cancelled() {
            // Update UI to show cancelled state
            let _ = window_weak.upgrade_in_event_loop(|window| {
                window.set_scan_progress(0.0);
                window.set_scan_status("Cancelled".into());
                window.set_scan_in_progress(false);
            });
            return Err("Scan cancelled by user".to_string());
        }

        // Simulate processing time (500ms per file)
        tokio::time::sleep(Duration::from_millis(500)).await;

        // Calculate progress and update UI
        let progress = ((i + 1) as f32 / total) * 100.0;
        let status = format!("{:.0}% - Scanning {}...", progress, file);

        let _ = window_weak.upgrade_in_event_loop(move |window| {
            window.set_scan_progress(progress);
            window.set_scan_status(status.into());
        });
    }

    // Scan complete
    let _ = window_weak.upgrade_in_event_loop(|window| {
        window.set_scan_progress(100.0);
        window.set_scan_status("Complete - 5 logs scanned, 0 issues found".into());
        window.set_scan_in_progress(false);
    });

    Ok(format!("Scanned {} files successfully", files.len()))
}

/// Trait for windows that support scan progress updates
///
/// This trait abstracts the Slint-generated properties so the worker
/// module doesn't depend on specific generated code.
pub trait ScanWindowProperties {
    /// Set the current scan progress (0-100)
    fn set_scan_progress(&self, value: f32);
    /// Set the status message displayed during scan
    fn set_scan_status(&self, value: slint::SharedString);
    /// Set whether a scan is currently in progress
    fn set_scan_in_progress(&self, value: bool);
}
