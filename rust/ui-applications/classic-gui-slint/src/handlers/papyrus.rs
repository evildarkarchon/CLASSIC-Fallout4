// Papyrus monitoring handlers
//
// This module provides Papyrus log monitoring for the GUI using PapyrusAnalyzer
// from classic-scanlog-core. It manages the monitoring lifecycle and provides
// statistics to the Slint UI.

use anyhow::{Context, Result};
use crate::app_state::SharedAppState;
use classic_scanlog_core::papyrus::{PapyrusAnalyzer, PapyrusStats};
use notify::{EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use parking_lot::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::channel;

/// Global monitoring state (shared across function calls)
static MONITORING_ACTIVE: AtomicBool = AtomicBool::new(false);

/// Global file watcher handle (needs to be kept alive)
static WATCHER: Mutex<Option<RecommendedWatcher>> = Mutex::new(None);

/// Global analyzer instance (shared across function calls)
static ANALYZER: Mutex<Option<PapyrusAnalyzer>> = Mutex::new(None);

/// Toggles Papyrus log monitoring on/off
///
/// # Arguments
/// * `monitoring` - Current monitoring state (true = monitoring active)
/// * `state` - Application state for accessing configuration
///
/// # Returns
/// Returns the new monitoring state
pub async fn toggle_papyrus_monitoring(monitoring: bool, state: SharedAppState) -> Result<bool> {
    let new_state = !monitoring;

    if new_state {
        start_monitoring(state).await?;
    } else {
        stop_monitoring().await?;
    }

    MONITORING_ACTIVE.store(new_state, Ordering::SeqCst);
    Ok(new_state)
}

/// Starts Papyrus log monitoring
///
/// Initializes the PapyrusAnalyzer from core and sets up file watching.
/// Uses "tail -f" behavior to only process new log entries.
pub async fn start_monitoring(state: SharedAppState) -> Result<()> {
    tracing::info!("Starting Papyrus monitoring...");

    // Get documents directory from AppState for Papyrus log location
    let docs_root = {
        let state_guard = state.read();
        state_guard.docs_root().cloned()
    };

    // Get the documents directory or return error if not configured
    let docs = docs_root.ok_or_else(|| {
        anyhow::anyhow!("Documents directory not configured. Please check your game settings.")
    })?;

    // Papyrus logs are typically in Documents/My Games/{Game}/Logs/Script/
    let papyrus_log_path = docs.join("Logs/Script/Papyrus.0.log");

    tracing::info!("Monitoring Papyrus log at: {}", papyrus_log_path.display());

    // Check if log file exists
    if !papyrus_log_path.exists() {
        anyhow::bail!(
            "Papyrus log file not found at: {}\n\n\
             The log file will be created when the game starts.\n\
             Please ensure:\n\
             - Papyrus logging is enabled in your game INI files\n\
             - The game has been run at least once",
            papyrus_log_path.display()
        );
    }

    // Create analyzer from core library
    let mut analyzer = PapyrusAnalyzer::new(papyrus_log_path.clone());

    // Start monitoring from END of file (ignore history)
    analyzer.start_monitoring()
        .context("Failed to initialize Papyrus analyzer")?;

    tracing::info!("Analyzer initialized with tail -f behavior");

    // Store analyzer globally
    *ANALYZER.lock() = Some(analyzer);

    // Create file watcher
    let (tx, rx) = channel();
    let mut watcher = notify::recommended_watcher(tx)
        .context("Failed to create file watcher")?;

    // Watch the log file directory (watching the file directly doesn't work reliably)
    let log_dir = papyrus_log_path.parent().ok_or_else(|| {
        anyhow::anyhow!("Failed to get log directory path")
    })?;

    watcher.watch(log_dir, RecursiveMode::NonRecursive)
        .context("Failed to start watching log directory")?;

    // Store watcher globally so it stays alive
    *WATCHER.lock() = Some(watcher);

    // Spawn background thread to handle file events
    std::thread::spawn(move || {
        tracing::info!("File watcher thread started");

        loop {
            // Check shutdown flag before waiting for events
            if !MONITORING_ACTIVE.load(Ordering::SeqCst) {
                tracing::info!("Monitoring stopped, exiting watcher thread");
                break;
            }

            // Use recv_timeout to allow periodic shutdown checks
            match rx.recv_timeout(std::time::Duration::from_secs(1)) {
                Ok(event_result) => {
                    match event_result {
                        Ok(event) => {
                            // Only process modify events for the Papyrus log
                            if matches!(event.kind, EventKind::Modify(_)) {
                                if event.paths.iter().any(|p| p.file_name() == papyrus_log_path.file_name()) {
                                    tracing::debug!("Papyrus log modified");

                                    // Check for updates using core analyzer
                                    let mut analyzer_guard = ANALYZER.lock();
                                    if let Some(analyzer) = analyzer_guard.as_mut() {
                                        match analyzer.check_for_updates() {
                                            Ok(Some((new_lines, stats))) => {
                                                tracing::debug!(
                                                    "Processed {} new lines. Stats: E={} W={} D={} S={}",
                                                    new_lines.len(),
                                                    stats.errors,
                                                    stats.warnings,
                                                    stats.dumps,
                                                    stats.stacks
                                                );
                                            }
                                            Ok(None) => {
                                                // No updates
                                            }
                                            Err(e) => {
                                                tracing::error!("Failed to check for updates: {}", e);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        Err(e) => {
                            tracing::error!("File watcher error: {}", e);
                        }
                    }
                }
                Err(std::sync::mpsc::RecvTimeoutError::Timeout) => {
                    // Timeout is expected, continue loop
                }
                Err(e) => {
                    tracing::error!("Channel error: {}", e);
                    break;
                }
            }
        }

        tracing::info!("File watcher thread exiting");
    });

    Ok(())
}

/// Stops Papyrus log monitoring
pub async fn stop_monitoring() -> Result<()> {
    tracing::info!("Stopping Papyrus monitoring...");

    // Clear the watcher (which stops watching)
    *WATCHER.lock() = None;

    // Clear the analyzer
    *ANALYZER.lock() = None;

    tracing::info!("Papyrus monitoring stopped");
    Ok(())
}

/// Gets the current Papyrus statistics
///
/// Returns the current statistics from the analyzer, or default stats if not monitoring.
pub fn get_current_stats() -> PapyrusStats {
    let analyzer_guard = ANALYZER.lock();
    if let Some(analyzer) = analyzer_guard.as_ref() {
        analyzer.stats().clone()
    } else {
        PapyrusStats::default()
    }
}

/// Clears the current Papyrus statistics and resets monitoring position
///
/// This resets the analyzer to start monitoring from the beginning of the log file.
pub fn clear_stats() {
    let mut analyzer_guard = ANALYZER.lock();
    if let Some(analyzer) = analyzer_guard.as_mut() {
        analyzer.reset();
        tracing::info!("Papyrus statistics cleared");
    }
}
