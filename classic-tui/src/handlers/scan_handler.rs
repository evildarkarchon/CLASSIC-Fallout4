use crate::app::ScanResults;
use crate::events::ScanMessage;
use anyhow::{Context, Result};
use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
use std::path::PathBuf;
use tokio::sync::mpsc;

/// Handler for scan operations
///
/// Integrates with classic-scanlog-core to perform actual crash log analysis
/// using pure Rust business logic (no PyO3 overhead).
pub struct ScanHandler {
    /// Optional crash logs directory to scan
    scan_path: Option<PathBuf>,
    /// Optional mods folder for mod detection (reserved for future use)
    #[allow(dead_code)]
    mods_folder: Option<PathBuf>,
}

impl ScanHandler {
    /// Create a new scan handler with default paths
    pub fn new() -> Self {
        Self {
            scan_path: None,
            mods_folder: None,
        }
    }

    /// Create a new scan handler with custom paths
    pub fn with_paths(scan_path: Option<PathBuf>, mods_folder: Option<PathBuf>) -> Self {
        Self {
            scan_path,
            mods_folder,
        }
    }

    /// Start a crash log scan using classic-scanlog-core
    pub async fn start_crash_scan(&self, tx: mpsc::Sender<ScanMessage>) -> Result<()> {
        tx.send(ScanMessage::output(
            "Initializing crash log analysis...".to_string(),
        ))
        .await?;

        // Create analysis configuration
        let config = AnalysisConfig::new("Fallout4".to_string(), false);
        let orchestrator =
            OrchestratorCore::new(config).context("Failed to create orchestrator")?;

        // Determine scan directory
        let scan_dir = self.scan_path.clone().unwrap_or_else(|| {
            PathBuf::from("C:\\Users\\Username\\Documents\\My Games\\Fallout4\\F4SE\\Crash Logs")
        });

        tx.send(ScanMessage::output(format!(
            "Scanning directory: {}",
            scan_dir.display()
        )))
        .await?;

        // Find crash log files
        let log_files = find_crash_logs(&scan_dir).await?;
        let total_logs = log_files.len();

        if total_logs == 0 {
            tx.send(ScanMessage::output(
                "No crash logs found in directory.".to_string(),
            ))
            .await?;
            tx.send(ScanMessage::completed(ScanResults {
                scanned_count: 0,
                patterns_matched: 0,
                formids_resolved: 0,
                suspects_count: 0,
            }))
            .await?;
            return Ok(());
        }

        tx.send(ScanMessage::output(format!(
            "Found {} crash log(s) to analyze",
            total_logs
        )))
        .await?;

        // Process each log with progress updates
        let mut total_formids = 0;
        let mut _total_plugins = 0;
        let mut total_suspects = 0;

        for (idx, log_path) in log_files.iter().enumerate() {
            let progress = (idx + 1) as f64 / total_logs as f64;
            tx.send(ScanMessage::progress(progress)).await?;

            tx.send(ScanMessage::output(format!(
                "Analyzing log {}/{}: {}",
                idx + 1,
                total_logs,
                log_path.file_name().unwrap_or_default().to_string_lossy()
            )))
            .await?;

            match orchestrator
                .process_log(log_path.to_string_lossy().to_string())
                .await
            {
                Ok(result) => {
                    total_formids += result.formid_count;
                    _total_plugins += result.plugin_count;
                    total_suspects += result.suspect_count;

                    tx.send(ScanMessage::output(format!(
                        "  ✓ Processed in {}ms - {} FormIDs, {} plugins, {} suspects",
                        result.processing_time_ms,
                        result.formid_count,
                        result.plugin_count,
                        result.suspect_count
                    )))
                    .await?;
                }
                Err(e) => {
                    tx.send(ScanMessage::output(format!("  ✗ Error: {}", e)))
                        .await?;
                }
            }
        }

        // Send completion
        let results = ScanResults {
            scanned_count: total_logs,
            patterns_matched: total_suspects,
            formids_resolved: total_formids,
            suspects_count: total_suspects,
        };

        tx.send(ScanMessage::completed(results)).await?;
        tx.send(ScanMessage::output(
            "\nCrash log scan completed successfully!".to_string(),
        ))
        .await?;

        Ok(())
    }

    /// Start a game files scan (placeholder for Phase 5)
    ///
    /// This will be implemented in a future phase to scan game files
    /// for integrity and mod conflicts.
    pub async fn start_game_scan(&self, tx: mpsc::Sender<ScanMessage>) -> Result<()> {
        tx.send(ScanMessage::output(
            "Game files scan not yet implemented.".to_string(),
        ))
        .await?;

        tx.send(ScanMessage::output(
            "This feature will be added in Phase 5.".to_string(),
        ))
        .await?;

        // Placeholder results
        let results = ScanResults {
            scanned_count: 0,
            patterns_matched: 0,
            formids_resolved: 0,
            suspects_count: 0,
        };

        tx.send(ScanMessage::completed(results)).await?;
        Ok(())
    }
}

/// Find crash log files in the specified directory
async fn find_crash_logs(dir: &PathBuf) -> Result<Vec<PathBuf>> {
    use tokio::fs;

    if !dir.exists() {
        anyhow::bail!("Scan directory does not exist: {}", dir.display());
    }

    let mut logs = Vec::new();
    let mut entries = fs::read_dir(dir).await?;

    while let Some(entry) = entries.next_entry().await? {
        let path = entry.path();
        if path.is_file() {
            if let Some(ext) = path.extension() {
                // Look for .log or .txt files
                if ext == "log" || ext == "txt" {
                    logs.push(path);
                }
            }
        }
    }

    // Sort by modification time (newest first)
    logs.sort_by_key(|p| {
        std::fs::metadata(p)
            .and_then(|m| m.modified())
            .unwrap_or(std::time::SystemTime::UNIX_EPOCH)
    });
    logs.reverse();

    Ok(logs)
}

impl Default for ScanHandler {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use tokio::fs;

    #[tokio::test]
    async fn test_crash_scan_handler_no_logs() {
        // Create a temp directory with no log files
        let temp_dir = tempdir().unwrap();
        let scan_path = temp_dir.path().to_path_buf();

        let handler = ScanHandler::with_paths(Some(scan_path), None);
        let (tx, mut rx) = mpsc::channel(100);

        // Spawn scan in background
        let handle = tokio::spawn(async move { handler.start_crash_scan(tx).await });

        // Collect messages
        let mut output_lines = 0;
        let mut completed = false;

        while let Some(msg) = rx.recv().await {
            match msg {
                ScanMessage::Output(_) => output_lines += 1,
                ScanMessage::Completed(results) => {
                    assert_eq!(results.scanned_count, 0);
                    completed = true;
                    break;
                }
                ScanMessage::Error(_) => panic!("Unexpected error"),
                _ => {}
            }
        }

        // Wait for scan to finish
        handle.await.unwrap().unwrap();

        assert!(output_lines > 0);
        assert!(completed);
    }

    #[tokio::test]
    async fn test_crash_scan_handler_with_logs() {
        // Create a temp directory with test log files
        let temp_dir = tempdir().unwrap();
        let scan_path = temp_dir.path().to_path_buf();

        // Create a few test log files
        for i in 1..=3 {
            let log_path = scan_path.join(format!("crash-{}.log", i));
            fs::write(&log_path, format!("Test crash log {}\nSome crash data", i))
                .await
                .unwrap();
        }

        let handler = ScanHandler::with_paths(Some(scan_path), None);
        let (tx, mut rx) = mpsc::channel(100);

        // Spawn scan in background
        let handle = tokio::spawn(async move { handler.start_crash_scan(tx).await });

        // Collect messages
        let mut progress_updates = 0;
        let mut output_lines = 0;
        let mut completed = false;

        while let Some(msg) = rx.recv().await {
            match msg {
                ScanMessage::Progress(_) => progress_updates += 1,
                ScanMessage::Output(_) => output_lines += 1,
                ScanMessage::Completed(results) => {
                    assert_eq!(results.scanned_count, 3);
                    completed = true;
                    break;
                }
                ScanMessage::Error(_) => panic!("Unexpected error"),
            }
        }

        // Wait for scan to finish
        handle.await.unwrap().unwrap();

        assert!(progress_updates > 0, "Should have progress updates");
        assert!(output_lines > 0, "Should have output lines");
        assert!(completed, "Should complete successfully");
    }

    #[tokio::test]
    async fn test_game_scan_handler() {
        let handler = ScanHandler::new();
        let (tx, mut rx) = mpsc::channel(100);

        // Spawn scan in background
        let handle = tokio::spawn(async move { handler.start_game_scan(tx).await });

        // Collect messages
        let mut messages = Vec::new();

        while let Some(msg) = rx.recv().await {
            messages.push(msg);
            if matches!(messages.last(), Some(ScanMessage::Completed(_))) {
                break;
            }
        }

        // Wait for scan to finish
        handle.await.unwrap().unwrap();

        // Should have output and completed messages (game scan is placeholder)
        assert!(
            messages.iter().any(|m| matches!(m, ScanMessage::Output(_))),
            "Should have output messages"
        );
        assert!(
            messages
                .iter()
                .any(|m| matches!(m, ScanMessage::Completed(_))),
            "Should have completed message"
        );
    }

    #[tokio::test]
    async fn test_find_crash_logs() {
        let temp_dir = tempdir().unwrap();
        let scan_path = temp_dir.path().to_path_buf();

        // Create various file types
        fs::write(scan_path.join("crash1.log"), "test")
            .await
            .unwrap();
        fs::write(scan_path.join("crash2.txt"), "test")
            .await
            .unwrap();
        fs::write(scan_path.join("readme.md"), "test")
            .await
            .unwrap();
        fs::write(scan_path.join("data.json"), "test")
            .await
            .unwrap();

        let logs = find_crash_logs(&scan_path).await.unwrap();

        // Should find only .log and .txt files
        assert_eq!(logs.len(), 2);
        assert!(logs.iter().all(
            |p| p.extension() == Some("log".as_ref()) || p.extension() == Some("txt".as_ref())
        ));
    }

    #[tokio::test]
    async fn test_find_crash_logs_nonexistent_dir() {
        let nonexistent = PathBuf::from("/nonexistent/directory");
        let result = find_crash_logs(&nonexistent).await;

        assert!(result.is_err(), "Should fail with nonexistent directory");
    }
}
