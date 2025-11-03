//! Update checking functionality for GitHub releases.
//!
//! This module provides functionality to check for new releases of CLASSIC
//! on GitHub, compare versions, and provide update information to the user.
//!
//! # Examples
//!
//! ```no_run
//! use classic_ui_shared::update_check::{check_for_updates, UpdateStatus};
//!
//! # tokio_test::block_on(async {
//! match check_for_updates("8.0.0", "evildarkarchon/CLASSIC-Fallout4").await {
//!     Ok(UpdateStatus::UpdateAvailable(info)) => {
//!         println!("Update available: {} -> {}", info.current_version, info.latest_version);
//!     }
//!     Ok(UpdateStatus::UpToDate) => {
//!         println!("You're running the latest version!");
//!     }
//!     Err(e) => eprintln!("Failed to check for updates: {}", e),
//! }
//! # });
//! ```

use anyhow::{Context, Result};
use semver::Version;
use serde::{Deserialize, Serialize};

/// Information about an available update
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateInfo {
    /// The current version being run
    pub current_version: String,
    /// The latest available version
    pub latest_version: String,
    /// URL to the release page
    pub release_url: String,
    /// Release notes / body text
    pub release_notes: String,
    /// Release date
    pub published_at: String,
}

/// Result of checking for updates
#[derive(Debug, Clone)]
pub enum UpdateStatus {
    /// An update is available
    UpdateAvailable(UpdateInfo),
    /// The current version is up to date
    UpToDate,
}

/// GitHub API response for a release
#[derive(Debug, Deserialize)]
struct GitHubRelease {
    tag_name: String,
    html_url: String,
    body: String,
    published_at: String,
}

/// Check for updates by querying the GitHub API.
///
/// This function queries the GitHub API for the latest release and compares
/// it with the current version using semantic versioning.
///
/// # Arguments
///
/// * `current_version` - The current version string (e.g., "8.0.0")
/// * `repo` - The GitHub repository in "owner/repo" format
///
/// # Returns
///
/// Returns [`UpdateStatus`] indicating whether an update is available or if
/// the current version is up to date.
///
/// # Errors
///
/// Returns an error if:
/// - Network request fails
/// - GitHub API returns an error
/// - Version parsing fails
/// - Response JSON is malformed
///
/// # Examples
///
/// ```no_run
/// use classic_ui_shared::update_check::check_for_updates;
///
/// # tokio_test::block_on(async {
/// let status = check_for_updates("8.0.0", "evildarkarchon/CLASSIC-Fallout4").await?;
/// # Ok::<(), anyhow::Error>(())
/// # });
/// ```
pub async fn check_for_updates(current_version: &str, repo: &str) -> Result<UpdateStatus> {
    tracing::info!(
        "Checking for updates (current version: {})",
        current_version
    );

    // Parse current version
    let current = parse_version(current_version)
        .with_context(|| format!("Failed to parse current version: {}", current_version))?;

    // Build GitHub API URL
    let url = format!("https://api.github.com/repos/{}/releases/latest", repo);

    // Create HTTP client with user agent (required by GitHub API)
    let client = reqwest::Client::builder()
        .user_agent("CLASSIC-Fallout4")
        .build()
        .context("Failed to create HTTP client")?;

    // Fetch latest release info
    tracing::debug!("Fetching release info from: {}", url);
    let response = client
        .get(&url)
        .send()
        .await
        .context("Failed to fetch latest release info from GitHub")?;

    if !response.status().is_success() {
        return Err(anyhow::anyhow!(
            "GitHub API returned error: {}",
            response.status()
        ));
    }

    let release: GitHubRelease = response
        .json()
        .await
        .context("Failed to parse GitHub API response")?;

    // Parse latest version (strip 'v' prefix if present)
    let latest_version_str = release.tag_name.trim_start_matches('v');
    let latest = parse_version(latest_version_str)
        .with_context(|| format!("Failed to parse latest version: {}", latest_version_str))?;

    tracing::info!("Latest version: {}, Current version: {}", latest, current);

    // Compare versions
    if latest > current {
        tracing::info!("Update available: {} -> {}", current, latest);
        Ok(UpdateStatus::UpdateAvailable(UpdateInfo {
            current_version: current_version.to_string(),
            latest_version: latest.to_string(),
            release_url: release.html_url,
            release_notes: release.body,
            published_at: release.published_at,
        }))
    } else {
        tracing::info!("Already running the latest version");
        Ok(UpdateStatus::UpToDate)
    }
}

/// Parse a version string into a semantic version.
///
/// This function handles version strings with or without 'v' prefix and
/// normalizes them into proper semantic versions.
///
/// # Arguments
///
/// * `version_str` - Version string (e.g., "v8.0.0" or "8.0.0")
///
/// # Returns
///
/// Returns a parsed [`Version`] or an error if parsing fails.
///
/// # Errors
///
/// Returns an error if the version string is not a valid semantic version.
fn parse_version(version_str: &str) -> Result<Version> {
    // Remove 'v' prefix if present
    let clean_version = version_str.trim_start_matches('v');

    // Parse with semver
    Version::parse(clean_version)
        .with_context(|| format!("Invalid semantic version: {}", version_str))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_version() {
        // Test with 'v' prefix
        let version = parse_version("v8.0.0").expect("Failed to parse version");
        assert_eq!(version.major, 8);
        assert_eq!(version.minor, 0);
        assert_eq!(version.patch, 0);

        // Test without 'v' prefix
        let version = parse_version("8.0.0").expect("Failed to parse version");
        assert_eq!(version.major, 8);
        assert_eq!(version.minor, 0);
        assert_eq!(version.patch, 0);

        // Test pre-release version
        let version = parse_version("8.0.0-beta.1").expect("Failed to parse version");
        assert_eq!(version.major, 8);
        assert!(!version.pre.is_empty());
    }

    #[test]
    fn test_parse_invalid_version() {
        let result = parse_version("not-a-version");
        assert!(result.is_err());

        let result = parse_version("1.2");
        assert!(result.is_err());
    }

    #[test]
    fn test_version_comparison() {
        let v1 = parse_version("8.0.0").unwrap();
        let v2 = parse_version("8.0.1").unwrap();
        let v3 = parse_version("8.1.0").unwrap();
        let v4 = parse_version("9.0.0").unwrap();

        assert!(v2 > v1);
        assert!(v3 > v2);
        assert!(v4 > v3);
        assert!(v1 < v4);
    }

    // Note: Network tests are not included here as they would require
    // mocking the HTTP client or hitting actual GitHub API endpoints.
    // Integration tests for actual GitHub API calls should be in a
    // separate test module with #[ignore] attribute.
}
