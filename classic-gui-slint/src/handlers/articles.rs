//! Articles tab handlers
//!
//! Handles URL opening for resource links in the Articles tab.

use anyhow::{Context, Result};
use tracing::{debug, error, info, warn};

/// Opens a URL in the default browser.
///
/// This uses the `open` crate to launch the URL in the system's default browser.
/// Logs success or failure with appropriate tracing messages.
///
/// # Arguments
///
/// * `url` - The URL to open (e.g., "https://www.nexusmods.com/fallout4/mods/56255")
///
/// # Returns
///
/// * `Ok(())` if the URL was opened successfully
/// * `Err` if the URL could not be opened
///
/// # Example
///
/// ```rust
/// handle_open_url("https://github.com/evildarkarchon/CLASSIC-Fallout4");
/// ```
pub fn handle_open_url(url: &str) -> Result<()> {
    debug!("Opening URL: {}", url);

    // Validate that the URL is not empty
    if url.trim().is_empty() {
        warn!("Attempted to open empty URL");
        return Err(anyhow::anyhow!("URL cannot be empty"));
    }

    // Use the `open` crate to launch the URL in the default browser
    open::that(url).context(format!("Failed to open URL: {}", url))?;

    info!("Successfully opened URL: {}", url);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_handle_open_url_empty() {
        // Empty URL should fail
        let result = handle_open_url("");
        assert!(result.is_err());
    }

    #[test]
    fn test_handle_open_url_whitespace() {
        // Whitespace-only URL should fail
        let result = handle_open_url("   ");
        assert!(result.is_err());
    }

    // Note: We can't test actual URL opening in unit tests as it would open a browser
    // Integration tests would be needed for that
}
