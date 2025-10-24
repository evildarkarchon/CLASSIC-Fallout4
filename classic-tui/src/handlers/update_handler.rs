///! Update checking functionality for CLASSIC TUI.
///!
///! This module provides functionality to check for new releases on GitHub,
///! compare semantic versions, and notify users of available updates.

use anyhow::{Context, Result};
use serde::Deserialize;
use std::cmp::Ordering;

/// GitHub repository owner
const REPO_OWNER: &str = "evildarkarchon";
/// GitHub repository name
const REPO_NAME: &str = "CLASSIC-Fallout4";
/// Current application version (from Cargo.toml)
const CURRENT_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Information about an available update.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateInfo {
    /// Latest version tag (e.g., "v1.2.3")
    pub version: String,
    /// Release name/title
    pub name: String,
    /// Release body/notes
    pub body: String,
    /// URL to the release page
    pub html_url: String,
    /// Whether this is a prerelease
    pub prerelease: bool,
}

/// Response from GitHub API for latest release.
#[derive(Debug, Deserialize)]
struct GitHubRelease {
    /// Release tag name (e.g., "v1.2.3")
    tag_name: String,
    /// Release name/title
    name: String,
    /// Release body/notes (markdown)
    body: String,
    /// HTML URL to release page
    html_url: String,
    /// Whether this is a prerelease
    prerelease: bool,
}

/// Semantic version for comparison.
///
/// Follows semantic versioning 2.0.0 specification (MAJOR.MINOR.PATCH).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SemanticVersion {
    /// Major version number (breaking changes)
    pub major: u32,
    /// Minor version number (new features, backward compatible)
    pub minor: u32,
    /// Patch version number (bug fixes, backward compatible)
    pub patch: u32,
}

impl SemanticVersion {
    /// Parse a semantic version string.
    ///
    /// Accepts versions with or without 'v' prefix (e.g., "1.2.3" or "v1.2.3").
    ///
    /// # Arguments
    ///
    /// * `version` - Version string to parse
    ///
    /// # Returns
    ///
    /// Returns `Some(SemanticVersion)` if valid, `None` otherwise.
    ///
    /// # Examples
    ///
    /// ```
    /// use classic_tui::handlers::update_handler::SemanticVersion;
    ///
    /// let v1 = SemanticVersion::parse("1.2.3").unwrap();
    /// let v2 = SemanticVersion::parse("v1.2.3").unwrap();
    /// assert_eq!(v1, v2);
    /// ```
    pub fn parse(version: &str) -> Option<Self> {
        // Remove 'v' prefix if present
        let version = version.strip_prefix('v').unwrap_or(version);

        // Split by '.' and parse each component
        let parts: Vec<&str> = version.split('.').collect();
        if parts.len() != 3 {
            return None;
        }

        let major = parts[0].parse().ok()?;
        let minor = parts[1].parse().ok()?;
        let patch = parts[2].parse().ok()?;

        Some(Self {
            major,
            minor,
            patch,
        })
    }

    /// Get the current application version.
    ///
    /// # Returns
    ///
    /// Returns the current version from Cargo.toml.
    pub fn current() -> Option<Self> {
        Self::parse(CURRENT_VERSION)
    }
}

impl PartialOrd for SemanticVersion {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for SemanticVersion {
    fn cmp(&self, other: &Self) -> Ordering {
        // Compare major, then minor, then patch
        self.major
            .cmp(&other.major)
            .then_with(|| self.minor.cmp(&other.minor))
            .then_with(|| self.patch.cmp(&other.patch))
    }
}

/// Check for updates from GitHub releases.
///
/// Queries the GitHub API for the latest release and compares it with
/// the current version. Returns `Some(UpdateInfo)` if an update is available,
/// or `None` if already on latest version or if check fails.
///
/// # Returns
///
/// - `Ok(Some(UpdateInfo))` - Update available
/// - `Ok(None)` - Already on latest version
/// - `Err(_)` - Failed to check for updates (network error, API error, etc.)
///
/// # Examples
///
/// ```no_run
/// use classic_tui::handlers::update_handler::check_for_updates;
///
/// #[tokio::main]
/// async fn main() {
///     match check_for_updates().await {
///         Ok(Some(update)) => {
///             println!("Update available: {} -> {}",
///                 env!("CARGO_PKG_VERSION"),
///                 update.version
///             );
///         }
///         Ok(None) => println!("Already on latest version"),
///         Err(e) => eprintln!("Failed to check for updates: {}", e),
///     }
/// }
/// ```
pub async fn check_for_updates() -> Result<Option<UpdateInfo>> {
    // Build GitHub API URL for latest release
    let url = format!(
        "https://api.github.com/repos/{}/{}/releases/latest",
        REPO_OWNER, REPO_NAME
    );

    // Create HTTP client
    let client = reqwest::Client::builder()
        .user_agent(format!("CLASSIC-TUI/{}", CURRENT_VERSION))
        .build()
        .context("Failed to create HTTP client")?;

    // Fetch latest release info from GitHub
    let response = client
        .get(&url)
        .send()
        .await
        .context("Failed to send request to GitHub API")?;

    if !response.status().is_success() {
        anyhow::bail!("GitHub API returned status: {}", response.status());
    }

    let release: GitHubRelease = response
        .json()
        .await
        .context("Failed to parse GitHub API response")?;

    // Parse versions
    let current_version = SemanticVersion::current()
        .context("Failed to parse current version")?;

    let latest_version = SemanticVersion::parse(&release.tag_name)
        .context("Failed to parse latest version from GitHub")?;

    // Compare versions
    if latest_version > current_version {
        Ok(Some(UpdateInfo {
            version: release.tag_name,
            name: release.name,
            body: release.body,
            html_url: release.html_url,
            prerelease: release.prerelease,
        }))
    } else {
        Ok(None)
    }
}

/// Open the release page in the system's default browser.
///
/// # Arguments
///
/// * `url` - URL to open (typically from `UpdateInfo.html_url`)
///
/// # Returns
///
/// Returns `Ok(())` if browser was opened successfully, or an error if it failed.
///
/// # Examples
///
/// ```no_run
/// use classic_tui::handlers::update_handler::open_release_page;
///
/// # #[tokio::main]
/// # async fn main() -> anyhow::Result<()> {
/// open_release_page("https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest")?;
/// # Ok(())
/// # }
/// ```
pub fn open_release_page(url: &str) -> Result<()> {
    open::that(url).context("Failed to open URL in browser")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_semantic_version_parse() {
        let v1 = SemanticVersion::parse("1.2.3").unwrap();
        assert_eq!(v1.major, 1);
        assert_eq!(v1.minor, 2);
        assert_eq!(v1.patch, 3);

        let v2 = SemanticVersion::parse("v1.2.3").unwrap();
        assert_eq!(v1, v2);

        // Invalid versions
        assert!(SemanticVersion::parse("1.2").is_none());
        assert!(SemanticVersion::parse("1.2.3.4").is_none());
        assert!(SemanticVersion::parse("abc").is_none());
    }

    #[test]
    fn test_semantic_version_comparison() {
        let v1_0_0 = SemanticVersion::parse("1.0.0").unwrap();
        let v1_1_0 = SemanticVersion::parse("1.1.0").unwrap();
        let v1_1_1 = SemanticVersion::parse("1.1.1").unwrap();
        let v2_0_0 = SemanticVersion::parse("2.0.0").unwrap();

        assert!(v1_0_0 < v1_1_0);
        assert!(v1_1_0 < v1_1_1);
        assert!(v1_1_1 < v2_0_0);
        assert!(v2_0_0 > v1_0_0);

        assert_eq!(v1_0_0, SemanticVersion::parse("1.0.0").unwrap());
    }

    #[test]
    fn test_semantic_version_ordering() {
        let mut versions = vec![
            SemanticVersion::parse("2.0.0").unwrap(),
            SemanticVersion::parse("1.0.0").unwrap(),
            SemanticVersion::parse("1.2.0").unwrap(),
            SemanticVersion::parse("1.1.5").unwrap(),
        ];

        versions.sort();

        assert_eq!(versions[0], SemanticVersion::parse("1.0.0").unwrap());
        assert_eq!(versions[1], SemanticVersion::parse("1.1.5").unwrap());
        assert_eq!(versions[2], SemanticVersion::parse("1.2.0").unwrap());
        assert_eq!(versions[3], SemanticVersion::parse("2.0.0").unwrap());
    }

    #[test]
    fn test_current_version() {
        // Should be able to parse the current version from Cargo.toml
        let current = SemanticVersion::current();
        assert!(current.is_some(), "Failed to parse current version");
    }
}
