// Settings and utility handlers
use anyhow::Result;

use crate::app_state::SharedAppState;

/// Displays the About dialog
pub fn show_about() -> Result<()> {
    tracing::info!("Showing About dialog...");

    // Get version from build-time environment
    const VERSION: &str = env!("CARGO_PKG_VERSION");
    const AUTHORS: &str = env!("CARGO_PKG_AUTHORS");

    // Create about message
    let about_message = format!(
        "CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker\n\n\
         Version: {}\n\
         Authors: {}\n\n\
         A high-performance hybrid Python-Rust desktop application\n\
         for analyzing crash logs from Bethesda games.\n\n\
         License: MIT\n\
         Repository: https://github.com/evildarkarchon/CLASSIC-Fallout4",
        VERSION,
        AUTHORS
    );

    // Use native message dialog
    rfd::MessageDialog::new()
        .set_title("About CLASSIC")
        .set_description(&about_message)
        .set_level(rfd::MessageLevel::Info)
        .show();

    tracing::debug!("About dialog shown");
    Ok(())
}

/// Displays the Help dialog for main options
pub fn show_help() -> Result<()> {
    tracing::info!("Showing Help dialog...");

    // Open CLASSIC documentation in browser
    const DOCS_URL: &str = "https://github.com/evildarkarchon/CLASSIC-Fallout4/blob/classic-next/README.md";

    open::that(DOCS_URL)?;
    tracing::debug!("Opened help documentation in browser");

    Ok(())
}

/// Opens the crash logs folder in the system file explorer
pub fn open_crash_logs_folder(state: SharedAppState) -> Result<()> {
    tracing::info!("Opening crash logs folder...");

    // Get docs root from AppState
    let docs_root = {
        let state_guard = state.read();
        state_guard.docs_root().cloned()
    };

    if let Some(docs_path) = docs_root {
        // Open in file explorer using 'open' crate
        open::that(&docs_path)?;
        tracing::debug!("Opened crash logs folder: {:?}", docs_path);
    } else {
        tracing::warn!("Crash logs folder path not configured");
        anyhow::bail!("Crash logs folder path not configured");
    }

    Ok(())
}
