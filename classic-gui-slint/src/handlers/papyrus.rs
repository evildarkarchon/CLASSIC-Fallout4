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

/// File position tracker for tail -f behavior (tracks last read position)
static FILE_POSITION: Mutex<u64> = Mutex::new(0);

/// Statistics for Papyrus log monitoring
#[derive(Debug, Clone, Default)]
pub struct PapyrusStats {
    pub errors: i32,
    pub warnings: i32,
    pub info: i32,
    pub dumps: i32,      // NEW: Stack dumps count
    pub stacks: i32,     // NEW: Stack frames count
    pub recent_entries: Vec<String>,
}

impl PapyrusStats {
    pub fn clear(&mut self) {
        self.errors = 0;
        self.warnings = 0;
        self.info = 0;
        self.dumps = 0;
        self.stacks = 0;
        self.recent_entries.clear();
    }

    /// Calculate dumps-to-stacks ratio
    ///
    /// Returns the ratio of dumps to stacks as a percentage.
    /// Returns 0.0 if there are no stacks to avoid division by zero.
    pub fn dumps_to_stacks_ratio(&self) -> f32 {
        if self.stacks == 0 {
            return 0.0;
        }
        (self.dumps as f32 / self.stacks as f32) * 100.0
    }

    pub fn add_entry(&mut self, line: &str) {
        let line_lower = line.to_lowercase();

        // Parse log entry for severity
        if line_lower.contains("error") {
            self.errors += 1;
        } else if line_lower.contains("warning") {
            self.warnings += 1;
        } else {
            self.info += 1;
        }

        // Parse for dumps and stacks
        // Papyrus dumps typically contain "stack dump" or "dumping stack"
        if line_lower.contains("stack dump") || line_lower.contains("dumping stack") {
            self.dumps += 1;
        }

        // Papyrus stack frames typically start with indentation and contain function names
        // Example: "  [None].Game.GetFormFromFile() - "<native>" Line ?"
        // or start with numbers like "[09/22/2024 - 01:23:45PM] "
        if line_lower.contains("stack frame") ||
           (line.trim_start().starts_with('[') && line.contains(").") && line.contains("() -")) ||
           line.trim_start().starts_with("  [") {
            self.stacks += 1;
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
    dumps: 0,
    stacks: 0,
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

    // Initialize file position to current end of file (skip historical data)
    // This ensures we only process NEW log entries from THIS monitoring session
    let initial_position = std::fs::metadata(&papyrus_log_path)
        .context("Failed to read log file metadata")?
        .len();
    *FILE_POSITION.lock() = initial_position;
    tracing::info!("Starting monitoring at file position: {} bytes (skipping historical data)", initial_position);

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

                            // Read only NEW log entries (tail -f behavior)
                            match std::fs::File::open(&papyrus_log_path) {
                                Ok(mut file) => {
                                    use std::io::{BufRead, BufReader, Seek, SeekFrom};

                                    // Get current file position
                                    let last_position = *FILE_POSITION.lock();

                                    // Seek to last read position
                                    if let Err(e) = file.seek(SeekFrom::Start(last_position)) {
                                        tracing::error!("Failed to seek to position {}: {}", last_position, e);
                                        continue;
                                    }

                                    // Read all new lines from last position to end
                                    let reader = BufReader::new(file);
                                    let mut new_lines_count = 0;

                                    for line_result in reader.lines() {
                                        match line_result {
                                            Ok(line) => {
                                                // Process this new line
                                                let mut stats = STATS.lock();
                                                stats.add_entry(&line);
                                                new_lines_count += 1;
                                            }
                                            Err(e) => {
                                                tracing::warn!("Failed to read line: {}", e);
                                                break;
                                            }
                                        }
                                    }

                                    // Update file position to current end
                                    if let Ok(metadata) = std::fs::metadata(&papyrus_log_path) {
                                        let new_position = metadata.len();
                                        *FILE_POSITION.lock() = new_position;

                                        if new_lines_count > 0 {
                                            let stats = STATS.lock();
                                            tracing::debug!(
                                                "Processed {} new lines. Stats: E={} W={} I={} D={} S={} Ratio={:.2}%",
                                                new_lines_count,
                                                stats.errors,
                                                stats.warnings,
                                                stats.info,
                                                stats.dumps,
                                                stats.stacks,
                                                stats.dumps_to_stacks_ratio()
                                            );
                                        }
                                    }
                                }
                                Err(e) => {
                                    tracing::error!("Failed to open log file: {}", e);
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

    // Reset file position for next session
    *FILE_POSITION.lock() = 0;

    tracing::info!("Papyrus monitoring stopped");
    Ok(())
}

/// Clear Papyrus monitoring statistics
pub fn clear_papyrus_stats() {
    STATS.lock().clear();
    tracing::info!("Papyrus statistics cleared");
}

/// Get current Papyrus monitoring statistics
///
/// Returns a clone of the current statistics
pub fn get_papyrus_stats() -> PapyrusStats {
    STATS.lock().clone()
}
