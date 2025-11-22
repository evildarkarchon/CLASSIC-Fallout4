#![allow(unused_imports)]
// Scan operation handlers
use anyhow::{Context, Result};
use classic_config_core::YamlSource;
use classic_file_io_core::LogCollector;
use classic_scanlog_core::{AnalysisConfig, OrchestratorCore};
use classic_scangame_core::ini::{ConfigIssue as IniConfigIssue, IniValidator, IssueSeverity};
use classic_scangame_core::toml::{CrashgenChecker, TomlConfigIssue};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Mutex;

use crate::app_state::SharedAppState;

/// Global scan lock to prevent duplicate scan operations
///
/// This mutex ensures that only one scan operation can run at a time,
/// preventing resource conflicts and race conditions.
static SCAN_LOCK: Mutex<bool> = Mutex::new(false);

/// Scan lock guard - automatically releases lock when dropped
///
/// This RAII guard ensures the scan lock is always released,
/// even if the scan operation panics or returns early.
struct ScanLockGuard;

impl Drop for ScanLockGuard {
    fn drop(&mut self) {
        if let Ok(mut lock) = SCAN_LOCK.lock() {
            *lock = false;
            tracing::debug!("Scan lock released");
        }
    }
}

/// Attempt to acquire the scan lock
///
/// # Returns
/// * `Ok(ScanLockGuard)` - Lock acquired successfully
/// * `Err(anyhow::Error)` - Another scan is already in progress
fn acquire_scan_lock() -> Result<ScanLockGuard> {
    let mut lock = SCAN_LOCK
        .lock()
        .map_err(|e| anyhow::anyhow!("Scan lock poisoned: {}", e))?;

    if *lock {
        anyhow::bail!("A scan operation is already in progress. Please wait for it to complete.");
    }

    *lock = true;
    tracing::debug!("Scan lock acquired");
    Ok(ScanLockGuard)
}

/// Result of a scan operation
#[derive(Debug)]
pub struct ScanResult {
    pub success: bool,
    pub message: String,
    pub summary_details: Vec<String>,
    pub fcx_issues_report: Vec<String>,
    #[allow(dead_code)]
    pub processing_time_ms: u64
}

/// Handles the crash logs scan operation
///
/// Scans crash logs in the game directory using classic-scanlog-core
pub async fn handle_scan_crash_logs(state: SharedAppState) -> Result<ScanResult> {
    tracing::info!("Starting crash logs scan...");

    // Pause file watcher to prevent I/O contention
    {
        let state_guard = state.read();
        state_guard.file_watcher().pause();
    }

    // Wrap scan logic to ensure watcher is resumed even if scan fails
    let result = async {
        // Acquire scan lock to prevent duplicate operations
        let _lock_guard = acquire_scan_lock()?;

        let start_time = std::time::Instant::now();

        // Load configuration from AppState
        let config = create_config_from_state(state.clone()).await?;

        // Create orchestrator
        let orchestrator =
            OrchestratorCore::new(config).context("Failed to create crash log orchestrator")?;

        // Find crash logs using AppState paths and LogCollector
        let crash_logs = find_crash_logs(state.clone()).await?; // Use state.clone() as find_crash_logs takes SharedAppState

        if crash_logs.is_empty() {
            tracing::warn!("No crash logs found");
            return Ok(ScanResult {
                success: false,
                message: "No crash logs found".to_string(),
                summary_details: vec!["No crash log files were found in the game directory.".to_string()],
                fcx_issues_report: Vec::new(),
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

        let summary_details = vec![
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
                format!(
                    "Scanned {} log(s): {} succeeded, {} failed",
                    results.len(),
                    successful,
                    failed
                )
            },
            summary_details,
            fcx_issues_report: Vec::new(),
            processing_time_ms,
        })
    }.await;

    // Resume file watcher
    {
        let state_guard = state.read();
        state_guard.file_watcher().resume();
    }

    result
}

/// Handles the game files scan operation
///
/// Scans game files for issues using classic-file-io-core
pub async fn handle_scan_game_files(state: SharedAppState) -> Result<ScanResult> {
    tracing::info!("Starting game files scan...");

    // Pause file watcher to prevent I/O contention
    {
        let state_guard = state.read();
        state_guard.file_watcher().pause();
    }

    // Wrap scan logic to ensure watcher is resumed even if scan fails
    let result = async {
        // Acquire scan lock to prevent duplicate operations
        let _lock_guard = acquire_scan_lock()?;

        let start_time = std::time::Instant::now();

        // Get game root, docs root, game name and fcx mode from AppState
        let (game_root, docs_root, game_name, fcx_mode) = {
            let state_guard = state.read();
            (
                state_guard.game_root().clone(),
                state_guard.docs_root().cloned(),
                state_guard.game_name().to_string(),
                state_guard.fcx_mode(),
            )
        };

        let crashgen_name = YamlSource::Game
            .load(&game_name)
            .await
            .context("Failed to load game YAML configuration for crashgen name")?
            ["CrashGen"]["Name"]
            .as_str()
            .unwrap_or("Buffout4") // Default to Buffout4 if not found
            .to_string();

        tracing::debug!("Scanning game files in: {}", game_root.display());

        // Check if game directory exists
        if !game_root.exists() || !game_root.is_dir() {
            return Ok(ScanResult {
                success: false,
                message: "Game directory not found".to_string(),
                summary_details: vec![
                    format!("Path: {}", game_root.display()),
                    "Please check your game configuration.".to_string(),
                ],
                fcx_issues_report: Vec::new(),
                processing_time_ms: start_time.elapsed().as_millis() as u64,
            });
        }

        let mut fcx_issues_report: Vec<String> = Vec::new();
        let mut summary_details: Vec<String> = Vec::new();
        let message: String; // Declare as immutable, assign later

        if fcx_mode {
            fcx_issues_report.push("* NOTICE: FCX MODE IS ENABLED. CLASSIC IS PERFORMING A DEEP SCAN OF GAME FILES AND CONFIGURATIONS. *\n\n".to_string());

            // --- INI Validation ---
            let mut ini_validator = IniValidator::new(&game_name);
            let config_files_map = ini_validator.scan_config_files(&game_root)?;

            for file_path in config_files_map.values() {
                if let Err(e) = ini_validator.load_ini(file_path) {
                    tracing::warn!("Failed to load INI file {}: {}", file_path.display(), e);
                    fcx_issues_report.push(format!("* WARNING: Could not load INI file: {} - {}\n", file_path.display(), e));
                }
            }

            let ini_issues = ini_validator.detect_all_issues(&config_files_map);
            if !ini_issues.is_empty() {
                fcx_issues_report.push("\n--- DETECTED INI CONFIGURATION ISSUES ---\n".to_string());
                for issue in ini_issues {
                    fcx_issues_report.push(format!(
                        "[{:?}] File: {}\n  Section: {}\n  Setting: {}\n  Current: {}\n  Recommended: {}\n  Description: {}\n",
                        issue.severity,
                        issue.file_path.display(),
                        issue.section,
                        issue.setting,
                        issue.current_value,
                        issue.recommended_value,
                        issue.description
                    ));
                }
            }

            // --- TOML (Crashgen) Validation ---
            if let Some(docs) = docs_root {
                let plugins_path = docs.join(&game_name).join("F4SE").join("Plugins"); // Adjust F4SE path if needed
                let mut crashgen_checker = CrashgenChecker::new(&plugins_path, &crashgen_name);

                let (crashgen_report_str, toml_issues) = crashgen_checker.check()?;
                
                if !crashgen_report_str.is_empty() {
                    fcx_issues_report.push("\n--- CRASHGEN CONFIGURATION REPORT ---\n".to_string());
                    fcx_issues_report.push(crashgen_report_str);
                }

                if !toml_issues.is_empty() {
                    fcx_issues_report.push("\n--- DETECTED CRASHGEN TOML ISSUES ---\n".to_string());
                    for issue in toml_issues {
                        fcx_issues_report.push(format!(
                            "[{:?}] File: {}\n  Section: {}\n  Setting: {}\n  Current: {:?}\n  Recommended: {:?}\n  Description: {}\n",
                            issue.severity,
                            issue.file_path.display(),
                            issue.section,
                            issue.setting,
                            issue.current_value,
                            issue.recommended_value,
                            issue.description
                        ));
                    }
                }
            } else {
                fcx_issues_report.push("* WARNING: Documents root not found. Skipping Crashgen TOML config check. *\n".to_string());
            }

            if fcx_issues_report.len() > 1 { // More than just the initial notice
                message = "FCX Mode scan completed with detected issues.".to_string();
                summary_details.push("Detailed issues found in FCX Report tab.".to_string());
            } else {
                message = "FCX Mode scan completed. No issues detected.".to_string();
                summary_details.push("No configuration issues were detected.".to_string());
            }

        } else {
            message = "FCX Mode is disabled.".to_string();
            summary_details.push("* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES *\n".to_string());
            summary_details.push("[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ]\n".to_string());
        }

        let processing_time_ms = start_time.elapsed().as_millis() as u64;

        tracing::info!(
            "Game files scan completed in {}ms. FCX Mode: {}",
            processing_time_ms,
            if fcx_mode { "Enabled" } else { "Disabled" }
        );

        Ok(ScanResult {
            success: true, // If FCX scan runs, it's successful in its operation, even if issues are found
            message,
            summary_details,
            fcx_issues_report,
            processing_time_ms,
        })
    }.await;

    // Resume file watcher
    {
        let state_guard = state.read();
        state_guard.file_watcher().resume();
    }

    result
}

/// Creates analysis configuration from AppState
///
/// Loads configuration values from AppState including game name, settings, and
/// game-specific YAML configuration (crash generator info, game version, XSE acronym).
async fn create_config_from_state(state: SharedAppState) -> Result<AnalysisConfig> {
    // Use scope block to ensure guard is dropped before async operations
    let (game_name, fcx_mode) = {
        let state_guard = state.read();
        (state_guard.game_name().to_string(), state_guard.fcx_mode())
    }; // Guard is definitely dropped here

    let mut config = AnalysisConfig::new(game_name.clone(), fcx_mode);

    // Load game-specific configuration from YAML
    let yaml_data = YamlSource::Game
        .load(&game_name)
        .await
        .context("Failed to load game YAML configuration")?;

    // Extract crash generator configuration
    config.crashgen_name = yaml_data["CrashGen"]["Name"]
        .as_str()
        .unwrap_or("Unknown Crash Generator")
        .to_string();
    config.crashgen_latest = yaml_data["CrashGen"]["Latest"]
        .as_str()
        .unwrap_or("Unknown Version")
        .to_string();
    config.game_version = yaml_data["Game"]["Version"]
        .as_str()
        .unwrap_or("Unknown Version")
        .to_string();
    config.xse_acronym = yaml_data["XSE"]["Acronym"]
        .as_str()
        .unwrap_or("XSE")
        .to_string();

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
    // Use scope block to ensure guard is dropped before async operations
    let (docs_root, custom_folder, game_name) = {
        let state_guard = state.read();
        (
            state_guard.docs_root().cloned(),
            state_guard.scan_folder().cloned(),
            state_guard.game_name().to_string(),
        )
    }; // Guard is definitely dropped here

    // Load XSE acronym from game YAML
    let yaml_data = YamlSource::Game
        .load(&game_name)
        .await
        .context("Failed to load game YAML configuration")?;

    let xse_acronym = yaml_data["XSE"]["Acronym"]
        .as_str()
        .unwrap_or("XSE")
        .to_string();

    // Build XSE folder path using game-specific XSE acronym (e.g., My Games/Fallout4/F4SE)
    let xse_folder = docs_root.as_ref().and_then(|docs| {
        let parent = docs.parent()?;
        let game_dir = parent.join(&game_name);
        let xse_dir = game_dir.join(&xse_acronym);
        if xse_dir.exists() {
            Some(xse_dir)
        } else {
            None
        }
    });

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
