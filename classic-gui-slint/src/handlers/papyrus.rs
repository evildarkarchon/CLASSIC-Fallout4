// Papyrus monitoring handlers
use anyhow::{Context, Result};
use crate::app_state::SharedAppState;
use notify::{EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::channel;
use parking_lot::Mutex;

/// Global monitoring state (shared across function calls)
static MONITORING_ACTIVE: AtomicBool = AtomicBool::new(false);

/// Global file watcher handle (needs to be kept alive)
static WATCHER: Mutex<Option<RecommendedWatcher>> = Mutex::new(None);

/// Statistics for Papyrus log monitoring
#[derive(Debug, Clone, Default)]
pub struct PapyrusStats {
    pub errors: i32,
    pub warnings: i32,
    pub info: i32,
    pub recent_entries: Vec<String>,
}

impl PapyrusStats {
    pub fn clear(&mut self) {
        self.errors = 0;
        self.warnings = 0;
        self.info = 0;
        self.recent_entries.clear();
    }

    pub fn add_entry(&mut self, line: &str) {
        // Parse log entry for severity
        if line.contains("error") || line.contains("ERROR") {
            self.errors += 1;
        } else if line.contains("warning") || line.contains("WARNING") {
            self.warnings += 1;
        } else {
            self.info += 1;
        }

        // Keep only last 100 entries
        self.recent_entries.push(line.to_string());
        if self.recent_entries.len() > 100 {
            self.recent_entries.remove(0);
        }
    }
}

/// Global statistics (shared across function calls)
static STATS: Mutex<PapyrusStats> = Mutex::new(PapyrusStats {
    errors: 0,
    warnings: 0,
    info: 0,
    recent_entries: Vec::new(),
});

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

    // Clear previous statistics
    STATS.lock().clear();

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

        for event_result in rx {
            match event_result {
                Ok(event) => {
                    // Only process modify events for the Papyrus log
                    if matches!(event.kind, EventKind::Modify(_)) {
                        if event.paths.iter().any(|p| p.file_name() == papyrus_log_path.file_name()) {
                            tracing::debug!("Papyrus log modified");

                            // Read and process new log entries
                            if let Ok(content) = std::fs::read_to_string(&papyrus_log_path) {
                                // Process only the last few lines (new entries)
                                let lines: Vec<&str> = content.lines().collect();
                                if let Some(last_line) = lines.last() {
                                    let mut stats = STATS.lock();
                                    stats.add_entry(last_line);
                                    tracing::trace!(
                                        "Stats updated: E={} W={} I={}",
                                        stats.errors,
                                        stats.warnings,
                                        stats.info
                                    );
                                }
                            }
                        }
                    }
                }
                Err(e) => {
                    tracing::error!("File watcher error: {}", e);
                }
            }

            // Check if monitoring is still active
            if !MONITORING_ACTIVE.load(Ordering::SeqCst) {
                tracing::info!("Monitoring stopped, exiting watcher thread");
                break;
            }
        }

        tracing::info!("File watcher thread exited");
    });

    tracing::info!("Papyrus monitoring started successfully");
    Ok(())
}

/// Stops Papyrus log monitoring
pub async fn stop_monitoring() -> Result<()> {
    tracing::info!("Stopping Papyrus monitoring...");

    // Remove the watcher (this will stop watching)
    *WATCHER.lock() = None;

    tracing::info!("Papyrus monitoring stopped");
    Ok(())
}

/// Clear Papyrus monitoring statistics
pub fn clear_papyrus_stats() {
    STATS.lock().clear();
    tracing::info!("Papyrus statistics cleared");
}
