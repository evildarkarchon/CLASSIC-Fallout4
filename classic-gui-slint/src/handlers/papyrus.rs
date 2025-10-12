// Papyrus monitoring handlers
use anyhow::{Context, Result};
use crate::app_state::SharedAppState;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

/// Global monitoring state (shared across function calls)
static MONITORING_ACTIVE: AtomicBool = AtomicBool::new(false);

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
async fn start_monitoring(state: SharedAppState) -> Result<()> {
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

    // TODO: Phase 8 - Implement actual file watcher
    // 1. Use notify crate to watch Papyrus log file
    // 2. Parse log entries for errors/warnings
    // 3. Update statistics in real-time
    // 4. Show monitoring dialog with live stats

    tracing::info!("Papyrus monitoring started (file watcher not yet implemented)");
    tracing::info!("Note: Full implementation coming in Phase 8");

    Ok(())
}

/// Stops Papyrus log monitoring
async fn stop_monitoring() -> Result<()> {
    tracing::info!("Stopping Papyrus monitoring...");

    // TODO: Phase 8 - Stop file watcher
    // 1. Stop notify watcher
    // 2. Close monitoring dialog
    // 3. Save final statistics

    tracing::info!("Papyrus monitoring stopped");

    Ok(())
}

/// Checks if Papyrus monitoring is currently active
pub fn is_monitoring_active() -> bool {
    MONITORING_ACTIVE.load(Ordering::SeqCst)
}
