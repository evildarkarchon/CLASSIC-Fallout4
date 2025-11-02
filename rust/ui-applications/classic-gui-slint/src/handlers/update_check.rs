//! Update checking handlers for GitHub releases
//!
//! This module provides update checking functionality by querying the GitHub API
//! for the latest release and comparing it with the current version.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use semver::Version;

/// GitHub release information from API
#[derive(Debug, Deserialize)]
struct GithubRelease {
    /// Tag name (e.g., "v8.0.0")
    tag_name: String,
    /// Release notes in markdown format
    body: String,
}

/// Update information returned to the UI
#[derive(Debug, Clone)]
pub struct UpdateInfo {
    /// Latest version string (without 'v' prefix)
    pub version: String,
    /// Release notes in markdown format
    pub release_notes: String,
}

/// Check for updates on GitHub
///
/// Queries the GitHub API for the latest release and compares it with the current version.
///
/// # Arguments
/// * `current_version` - Current application version (e.g., "8.0.0")
///
/// # Returns
/// * `Ok(Some(UpdateInfo))` - Update available
/// * `Ok(None)` - No update available (current version is latest or newer)
/// * `Err(anyhow::Error)` - Failed to check for updates
///
/// # Example
/// ```rust,no_run
/// use classic_gui_slint::handlers::update_check::check_for_updates;
///
/// let current_version = "8.0.0";
/// match check_for_updates(current_version).await {
///     Ok(Some(info)) => println!("Update available: {}", info.version),
///     Ok(None) => println!("Already up to date"),
///     Err(e) => eprintln!("Update check failed: {}", e),
/// }
/// ```
pub async fn check_for_updates(current_version: &str) -> Result<Option<UpdateInfo>> {
    tracing::info!("Checking for updates (current version: {})", current_version);

    // GitHub API endpoint for latest release
    let url = "https://api.github.com/repos/evildarkarchon/CLASSIC-Fallout4/releases/latest";

    // Create HTTP client with User-Agent header (required by GitHub API)
    let client = reqwest::Client::builder()
        .user_agent("CLASSIC-Slint")
        .build()
        .context("Failed to create HTTP client")?;

    // Fetch latest release info
    let response = client
        .get(url)
        .send()
        .await
        .context("Failed to fetch GitHub release data")?;

    // Check if request was successful
    if !response.status().is_success() {
        anyhow::bail!(
            "GitHub API returned error status: {}",
            response.status()
        );
    }

    let release: GithubRelease = response
        .json()
        .await
        .context("Failed to parse GitHub release JSON")?;

    // Extract version from tag (remove 'v' prefix if present)
    let latest_version = release.tag_name.trim_start_matches('v');

    tracing::debug!(
        "Latest GitHub release: {} (tag: {})",
        latest_version,
        release.tag_name
    );

    // Compare versions
    if version_is_newer(latest_version, current_version)? {
        tracing::info!("Update available: {} -> {}", current_version, latest_version);
        Ok(Some(UpdateInfo {
            version: latest_version.to_string(),
            release_notes: release.body,
        }))
    } else {
        tracing::info!("No update available (current: {}, latest: {})", current_version, latest_version);
        Ok(None)
    }
}

/// Compare two semantic versions
///
/// Determines if the latest version is newer than the current version.
///
/// # Arguments
/// * `latest` - Latest version string (e.g., "8.0.1")
/// * `current` - Current version string (e.g., "8.0.0")
///
/// # Returns
/// * `Ok(true)` - Latest version is newer
/// * `Ok(false)` - Latest version is same or older
/// * `Err(anyhow::Error)` - Failed to parse version strings
///
/// # Examples
/// ```
/// use classic_gui_slint::handlers::update_check::version_is_newer;
///
/// assert!(version_is_newer("8.0.1", "8.0.0").unwrap());
/// assert!(!version_is_newer("8.0.0", "8.0.1").unwrap());
/// assert!(!version_is_newer("8.0.0", "8.0.0").unwrap());
/// ```
pub fn version_is_newer(latest: &str, current: &str) -> Result<bool> {
    // Parse versions using semver
    let latest_v = Version::parse(latest)
        .with_context(|| format!("Failed to parse latest version: {}", latest))?;

    let current_v = Version::parse(current)
        .with_context(|| format!("Failed to parse current version: {}", current))?;

    Ok(latest_v > current_v)
}

/// User preference for update checking
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdatePreferences {
    /// Don't check for updates again
    pub dont_check_again: bool,
    /// Last version that was skipped
    pub skipped_version: Option<String>,
}

impl Default for UpdatePreferences {
    fn default() -> Self {
        Self {
            dont_check_again: false,
            skipped_version: None,
        }
    }
}

impl UpdatePreferences {
    /// Load update preferences from config file
    ///
    /// Attempts to load from `update_preferences.json` in the current directory.
    ///
    /// # Returns
    /// * `Ok(UpdatePreferences)` - Loaded preferences or default if file doesn't exist
    /// * `Err(anyhow::Error)` - Failed to read or parse preferences
    pub async fn load() -> Result<Self> {
        let path = std::path::PathBuf::from("update_preferences.json");

        if !path.exists() {
            tracing::debug!("Update preferences file not found, using defaults");
            return Ok(Self::default());
        }

        let content = tokio::fs::read_to_string(&path)
            .await
            .context("Failed to read update preferences file")?;

        let prefs: UpdatePreferences = serde_json::from_str(&content)
            .context("Failed to parse update preferences JSON")?;

        tracing::debug!("Loaded update preferences: {:?}", prefs);
        Ok(prefs)
    }

    /// Save update preferences to config file
    ///
    /// Saves to `update_preferences.json` in the current directory.
    ///
    /// # Returns
    /// * `Ok(())` - Preferences saved successfully
    /// * `Err(anyhow::Error)` - Failed to serialize or write preferences
    pub async fn save(&self) -> Result<()> {
        let path = std::path::PathBuf::from("update_preferences.json");

        let json = serde_json::to_string_pretty(self)
            .context("Failed to serialize update preferences")?;

        tokio::fs::write(&path, json)
            .await
            .context("Failed to write update preferences file")?;

        tracing::debug!("Saved update preferences: {:?}", self);
        Ok(())
    }

    /// Mark version as skipped
    ///
    /// Sets the skipped_version to the provided version.
    pub fn skip_version(&mut self, version: String) {
        self.skipped_version = Some(version);
    }

    /// Set "don't check again" preference
    ///
    /// When set to true, the application will not check for updates automatically.
    pub fn set_dont_check_again(&mut self, value: bool) {
        self.dont_check_again = value;
    }

    /// Check if update checking should be skipped
    ///
    /// Returns true if either:
    /// - "don't check again" is set
    /// - The available version was previously skipped
    pub fn should_skip(&self, available_version: &str) -> bool {
        if self.dont_check_again {
            return true;
        }

        if let Some(ref skipped) = self.skipped_version {
            if skipped == available_version {
                return true;
            }
        }

        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version_comparison() {
        // Newer versions
        assert!(version_is_newer("8.0.1", "8.0.0").unwrap());
        assert!(version_is_newer("8.1.0", "8.0.0").unwrap());
        assert!(version_is_newer("9.0.0", "8.0.0").unwrap());

        // Same version
        assert!(!version_is_newer("8.0.0", "8.0.0").unwrap());

        // Older versions
        assert!(!version_is_newer("8.0.0", "8.0.1").unwrap());
        assert!(!version_is_newer("8.0.0", "8.1.0").unwrap());
        assert!(!version_is_newer("8.0.0", "9.0.0").unwrap());
    }

    #[test]
    fn test_version_parsing_errors() {
        assert!(version_is_newer("invalid", "8.0.0").is_err());
        assert!(version_is_newer("8.0.0", "invalid").is_err());
        assert!(version_is_newer("invalid", "invalid").is_err());
    }

    #[test]
    fn test_update_preferences_default() {
        let prefs = UpdatePreferences::default();
        assert!(!prefs.dont_check_again);
        assert!(prefs.skipped_version.is_none());
    }

    #[test]
    fn test_update_preferences_skip_version() {
        let mut prefs = UpdatePreferences::default();
        assert!(!prefs.should_skip("8.0.1"));

        prefs.skip_version("8.0.1".to_string());
        assert!(prefs.should_skip("8.0.1"));
        assert!(!prefs.should_skip("8.0.2"));
    }

    #[test]
    fn test_update_preferences_dont_check_again() {
        let mut prefs = UpdatePreferences::default();
        assert!(!prefs.should_skip("8.0.1"));

        prefs.set_dont_check_again(true);
        assert!(prefs.should_skip("8.0.1"));
        assert!(prefs.should_skip("9.0.0"));
    }

    #[tokio::test]
    async fn test_preferences_serialization() {
        let temp_dir = tempfile::tempdir().unwrap();
        let original_dir = std::env::current_dir().unwrap();

        // Change to temp directory
        std::env::set_current_dir(&temp_dir).unwrap();

        let mut prefs = UpdatePreferences::default();
        prefs.skip_version("8.0.1".to_string());
        prefs.set_dont_check_again(true);

        // Save
        prefs.save().await.unwrap();

        // Load
        let loaded = UpdatePreferences::load().await.unwrap();
        assert_eq!(loaded.dont_check_again, true);
        assert_eq!(loaded.skipped_version, Some("8.0.1".to_string()));

        // Restore original directory
        std::env::set_current_dir(original_dir).unwrap();
    }
}
