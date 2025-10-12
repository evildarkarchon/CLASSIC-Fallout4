// Scan operation handlers
use anyhow::{Context, Result};
use classic_file_io_core::LogCollector;
use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
use std::path::PathBuf;

use crate::app_state::SharedAppState;

/// Result of a scan operation
#[derive(Debug)]
pub struct ScanResult {
    pub success: bool,
    pub message: String,
    pub details: Vec<String>,
    pub processing_time_ms: u64,
}

/// Handles the crash logs scan operation
///
/// Scans crash logs in the game directory using classic-scanlog-core
pub async fn handle_scan_crash_logs(state: SharedAppState) -> Result<ScanResult> {
    tracing::info!("Starting crash logs scan...");
    let start_time = std::time::Instant::now();

    // Load configuration from AppState
    let config = create_config_from_state(state.clone())?;

    // Create orchestrator
    let orchestrator = OrchestratorCore::new(config)
        .context("Failed to create crash log orchestrator")?;

    // Find crash logs using AppState paths and LogCollector
    let crash_logs = find_crash_logs(state).await?;

    if crash_logs.is_empty() {
        tracing::warn!("No crash logs found");
        return Ok(ScanResult {
            success: false,
            message: "No crash logs found".to_string(),
            details: vec!["No crash log files were found in the game directory.".to_string()],
            processing_time_ms: start_time.elapsed().as_millis() as u64,
        });
    }

    tracing::info!("Found {} crash log(s)", crash_logs.len());

    // Process logs
    let results = orchestrator.process_logs_batch(crash_logs).await;

    // Analyze results
    let successful = results.iter().filter(|r| r.success).count();
    let failed = results.iter().filter(|r| !r.success).count();
    let total_time: u64 = results.iter().map(|r| r.processing_time_ms).sum();

    let details = vec![
        format!("Total logs processed: {}", results.len()),
        format!("Successful: {}", successful),
        format!("Failed: {}", failed),
        format!("Total processing time: {}ms", total_time),
    ];

    let processing_time_ms = start_time.elapsed().as_millis() as u64;

    tracing::info!(
        "Crash logs scan completed: {}/{} succeeded in {}ms",
        successful,
        results.len(),
        processing_time_ms
    );

    Ok(ScanResult {
        success: failed == 0,
        message: if failed == 0 {
            format!("Successfully scanned {} crash log(s)", successful)
        } else {
            format!("Scanned {} log(s): {} succeeded, {} failed", results.len(), successful, failed)
        },
        details,
        processing_time_ms,
    })
}

/// Handles the game files scan operation
///
/// Scans game files for issues using classic-file-io-core
pub async fn handle_scan_game_files(state: SharedAppState) -> Result<ScanResult> {
    tracing::info!("Starting game files scan...");
    let start_time = std::time::Instant::now();

    // Get game root from AppState
    let game_root = {
        let state_guard = state.read();
        state_guard.game_root().clone()
    };

    tracing::debug!("Scanning game files in: {}", game_root.display());

    // Check if game directory exists
    if !game_root.exists() || !game_root.is_dir() {
        return Ok(ScanResult {
            success: false,
            message: "Game directory not found".to_string(),
            details: vec![
                format!("Path: {}", game_root.display()),
                "Please check your game configuration.".to_string(),
            ],
            processing_time_ms: start_time.elapsed().as_millis() as u64,
        });
    }

    // Scan for common file types
    let mut files_scanned = 0;
    let mut details = Vec::new();

    // Count plugin files (.esp, .esm, .esl)
    let plugin_exts = ["esp", "esm", "esl"];
    let mut plugin_count = 0;

    // Count texture files (.dds)
    let mut dds_count = 0;

    // Walk the Data directory
    let data_dir = game_root.join("Data");
    if data_dir.exists() {
        for entry in walkdir::WalkDir::new(&data_dir)
            .max_depth(2)  // Don't go too deep for performance
            .into_iter()
            .filter_map(|e| e.ok())
        {
            if let Some(ext) = entry.path().extension() {
                let ext_str = ext.to_string_lossy().to_lowercase();

                if plugin_exts.contains(&ext_str.as_str()) {
                    plugin_count += 1;
                } else if ext_str == "dds" {
                    dds_count += 1;
                }

                files_scanned += 1;
            }
        }
    }

    // Build detailed results
    details.push(format!("Scanned {} file(s) in game directory", files_scanned));
    details.push(format!("Plugin files found: {}", plugin_count));
    details.push(format!("DDS texture files found: {}", dds_count));
    details.push("".to_string());
    details.push("Note: Full integrity checking coming in future updates".to_string());

    let processing_time_ms = start_time.elapsed().as_millis() as u64;

    tracing::info!(
        "Game files scan completed: {} files scanned in {}ms",
        files_scanned,
        processing_time_ms
    );

    Ok(ScanResult {
        success: true,
        message: format!("Successfully scanned {} files", files_scanned),
        details,
        processing_time_ms,
    })
}

/// Creates analysis configuration from AppState
///
/// Loads configuration values from AppState including game name and settings
fn create_config_from_state(state: SharedAppState) -> Result<AnalysisConfig> {
    let state_guard = state.read();

    let game_name = state_guard.game_name().to_string();
    let fcx_mode = state_guard.fcx_mode();

    let mut config = AnalysisConfig::new(game_name, fcx_mode);

    // TODO: Load these values from YAML configuration
    config.crashgen_name = "Buffout 4".to_string();
    config.crashgen_latest = "1.28.6".to_string();
    config.game_version = "1.10.163".to_string();
    config.xse_acronym = "F4SE".to_string();

    Ok(config)
}

/// Finds crash logs in the game directory using LogCollector
///
/// Uses AppState to get the correct game documents directory and custom scan paths.
/// This handles:
/// - Copying logs from game's XSE folder (My Games) to Crash Logs
/// - Moving logs from working directory to Crash Logs
/// - Collecting from custom scan folder if configured
async fn find_crash_logs(state: SharedAppState) -> Result<Vec<String>> {
    let state_guard = state.read();

    // Get paths from AppState
    let docs_root = state_guard.docs_root().cloned();
    let custom_folder = state_guard.scan_folder().cloned();

    // Build XSE folder path (e.g., My Games/Fallout4/F4SE)
    let xse_folder = docs_root.as_ref().and_then(|docs| {
        let parent = docs.parent()?;
        let game_dir = parent.join(state_guard.game_name());
        let xse_dir = game_dir.join("F4SE"); // TODO: Get from config
        if xse_dir.exists() {
            Some(xse_dir)
        } else {
            None
        }
    });

    drop(state_guard); // Release lock before async operations

    // Use current directory as base (where Crash Logs folder will be created)
    let base_folder = std::env::current_dir().unwrap_or_default();

    tracing::info!(
        "Collecting crash logs - XSE folder: {:?}, Custom folder: {:?}",
        xse_folder,
        custom_folder
    );

    // Create LogCollector
    let collector = LogCollector::new(base_folder, xse_folder, custom_folder);

    // Collect all crash logs (this copies/moves files as needed)
    let crash_logs = collector
        .collect_all()
        .await
        .context("Failed to collect crash logs")?;

    // Convert PathBuf to String for orchestrator
    let log_paths: Vec<String> = crash_logs
        .into_iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect();

    tracing::info!("LogCollector found {} crash log(s)", log_paths.len());

    Ok(log_paths)
}
