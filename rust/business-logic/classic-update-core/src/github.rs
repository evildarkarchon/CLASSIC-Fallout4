//! GitHub API integration for checking releases and updates.
//!
//! This module provides functionality to interact with the GitHub API
//! to check for new releases, download updates, and manage version information.
//!
//! # Authentication
//!
//! The client automatically loads environment variables from a `.env` file
//! (if present in the current directory) and uses the `GITHUB_TOKEN` variable.
//! This increases the API rate limit from 60 requests/hour (unauthenticated)
//! to 5,000 requests/hour (authenticated).
//!
//! Create a `.env` file with:
//! ```text
//! GITHUB_TOKEN=ghp_your_token_here
//! ```
//!
//! # Examples
//!
//! ```rust,no_run
//! use classic_update_core::github::GithubClient;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4");
//!
//! // Check latest release
//! let latest = client.get_latest_release().await?;
//! println!("Latest version: {}", latest.tag_name);
//! println!("Release notes: {}", latest.body);
//!
//! // Compare versions
//! if client.has_update("v8.0.0", &latest.tag_name)? {
//!     println!("Update available!");
//! }
//! # Ok(())
//! # }
//! ```

use crate::error::{Result, UpdateError};
use reqwest::Client;
use semver::Version;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// GitHub release information.
///
/// This struct contains all relevant information about a GitHub release,
/// including version, release notes, and download URLs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GithubRelease {
    /// Release tag name (e.g., "v8.0.0")
    pub tag_name: String,

    /// Release name/title
    pub name: String,

    /// Release notes in Markdown format
    pub body: String,

    /// Whether this is a pre-release
    pub prerelease: bool,

    /// Whether this is a draft release
    pub draft: bool,

    /// URL to the release page
    pub html_url: String,

    /// Release assets (downloadable files)
    pub assets: Vec<GithubAsset>,

    /// Release creation timestamp
    pub created_at: String,

    /// Release publication timestamp
    pub published_at: Option<String>,
}

/// GitHub release asset (downloadable file).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GithubAsset {
    /// Asset name
    pub name: String,

    /// Asset size in bytes
    pub size: u64,

    /// Download URL
    pub browser_download_url: String,

    /// MIME type
    pub content_type: String,

    /// Download count
    pub download_count: u64,
}

/// Client for interacting with the GitHub API.
///
/// This client handles API requests, rate limiting, and version comparison
/// for GitHub repositories.
///
/// # Authentication
///
/// The client automatically uses the `GITHUB_TOKEN` environment variable if set.
/// This increases the rate limit from 60 requests/hour (unauthenticated) to
/// 5,000 requests/hour (authenticated).
///
/// # Thread Safety
///
/// The client is thread-safe and can be cloned cheaply for use across threads.
#[derive(Debug, Clone)]
pub struct GithubClient {
    owner: String,
    repo: String,
    client: Client,
    base_url: String,
    /// Optional authentication token for increased rate limits.
    token: Option<String>,
}

impl GithubClient {
    /// API timeout duration (30 seconds).
    const API_TIMEOUT: Duration = Duration::from_secs(30);

    /// GitHub API base URL.
    const GITHUB_API_BASE: &'static str = "https://api.github.com";

    /// Environment variable name for GitHub token.
    const GITHUB_TOKEN_ENV: &'static str = "GITHUB_TOKEN";

    /// Creates a new GitHub client for the specified repository.
    ///
    /// Automatically loads environment variables from a `.env` file if present,
    /// then uses the `GITHUB_TOKEN` environment variable if set.
    /// This increases the rate limit from 60 requests/hour to 5,000 requests/hour.
    ///
    /// # .env File Support
    ///
    /// Create a `.env` file in the current directory with:
    /// ```text
    /// GITHUB_TOKEN=ghp_your_token_here
    /// ```
    ///
    /// # Arguments
    ///
    /// * `owner` - Repository owner (e.g., "evildarkarchon")
    /// * `repo` - Repository name (e.g., "CLASSIC-Fallout4")
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_update_core::github::GithubClient;
    ///
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4");
    /// ```
    pub fn new(owner: impl Into<String>, repo: impl Into<String>) -> Self {
        // Load .env file if present (silently ignores if not found)
        let _ = dotenvy::dotenv();

        let token = std::env::var(Self::GITHUB_TOKEN_ENV)
            .ok()
            .filter(|t| !t.is_empty());

        let client = Client::builder()
            .timeout(Self::API_TIMEOUT)
            .user_agent(format!("CLASSIC-Update/{}", env!("CARGO_PKG_VERSION")))
            .build()
            .expect("Failed to create HTTP client");

        Self {
            owner: owner.into(),
            repo: repo.into(),
            client,
            base_url: Self::GITHUB_API_BASE.to_string(),
            token,
        }
    }

    /// Creates a new GitHub client with an explicit token.
    ///
    /// Use this when you want to provide a token explicitly rather than
    /// relying on the `GITHUB_TOKEN` environment variable.
    ///
    /// # Arguments
    ///
    /// * `owner` - Repository owner (e.g., "evildarkarchon")
    /// * `repo` - Repository name (e.g., "CLASSIC-Fallout4")
    /// * `token` - GitHub personal access token or None for unauthenticated requests
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_update_core::github::GithubClient;
    ///
    /// let client = GithubClient::with_token("evildarkarchon", "CLASSIC-Fallout4", Some("ghp_xxx".to_string()));
    /// ```
    pub fn with_token(
        owner: impl Into<String>,
        repo: impl Into<String>,
        token: Option<String>,
    ) -> Self {
        let client = Client::builder()
            .timeout(Self::API_TIMEOUT)
            .user_agent(format!("CLASSIC-Update/{}", env!("CARGO_PKG_VERSION")))
            .build()
            .expect("Failed to create HTTP client");

        Self {
            owner: owner.into(),
            repo: repo.into(),
            client,
            base_url: Self::GITHUB_API_BASE.to_string(),
            token: token.filter(|t| !t.is_empty()),
        }
    }

    /// Builds a request with optional authentication headers.
    fn build_request(&self, url: &str) -> reqwest::RequestBuilder {
        let mut request = self.client.get(url);
        if let Some(ref token) = self.token {
            request = request.header("Authorization", format!("Bearer {}", token));
        }
        request
    }

    /// Gets the latest release for the repository.
    ///
    /// # Returns
    ///
    /// Returns the latest non-draft, non-prerelease release.
    ///
    /// # Errors
    ///
    /// - `UpdateError::HttpError` if the HTTP request fails
    /// - `UpdateError::JsonError` if the response cannot be parsed
    /// - `UpdateError::GithubError` if the API returns an error
    /// - `UpdateError::NotFound` if no releases exist
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_update_core::github::GithubClient;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4");
    /// let latest = client.get_latest_release().await?;
    /// println!("Latest version: {}", latest.tag_name);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn get_latest_release(&self) -> Result<GithubRelease> {
        let url = format!(
            "{}/repos/{}/{}/releases/latest",
            self.base_url, self.owner, self.repo
        );

        let response = self.build_request(&url).send().await?;

        match response.status() {
            reqwest::StatusCode::OK => {
                let release: GithubRelease = response.json().await?;
                Ok(release)
            }
            reqwest::StatusCode::NOT_FOUND => {
                Err(UpdateError::NotFound("No releases found".to_string()))
            }
            reqwest::StatusCode::FORBIDDEN => Err(UpdateError::RateLimitExceeded(None)),
            status => Err(UpdateError::GithubError(format!(
                "API returned status {}",
                status
            ))),
        }
    }

    /// Gets all releases for the repository.
    ///
    /// # Arguments
    ///
    /// * `include_prereleases` - Whether to include pre-releases
    /// * `include_drafts` - Whether to include draft releases
    ///
    /// # Returns
    ///
    /// Returns a vector of releases, sorted by publication date (newest first).
    ///
    /// # Errors
    ///
    /// - `UpdateError::HttpError` if the HTTP request fails
    /// - `UpdateError::JsonError` if the response cannot be parsed
    /// - `UpdateError::GithubError` if the API returns an error
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_update_core::github::GithubClient;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4");
    /// let releases = client.get_all_releases(false, false).await?;
    /// for release in releases {
    ///     println!("{}: {}", release.tag_name, release.name);
    /// }
    /// # Ok(())
    /// # }
    /// ```
    pub async fn get_all_releases(
        &self,
        include_prereleases: bool,
        include_drafts: bool,
    ) -> Result<Vec<GithubRelease>> {
        let url = format!(
            "{}/repos/{}/{}/releases",
            self.base_url, self.owner, self.repo
        );

        let response = self.build_request(&url).send().await?;

        match response.status() {
            reqwest::StatusCode::OK => {
                let mut releases: Vec<GithubRelease> = response.json().await?;

                // Filter based on preferences
                releases.retain(|r| {
                    (include_prereleases || !r.prerelease) && (include_drafts || !r.draft)
                });

                Ok(releases)
            }
            reqwest::StatusCode::FORBIDDEN => Err(UpdateError::RateLimitExceeded(None)),
            status => Err(UpdateError::GithubError(format!(
                "API returned status {}",
                status
            ))),
        }
    }

    /// Checks if a newer version is available compared to the current version.
    ///
    /// # Arguments
    ///
    /// * `current_version` - Current version string (e.g., "v8.0.0" or "8.0.0")
    /// * `latest_version` - Latest version string to compare against
    ///
    /// # Returns
    ///
    /// Returns `true` if `latest_version` is newer than `current_version`.
    ///
    /// # Errors
    ///
    /// Returns `UpdateError::VersionError` if either version string cannot be parsed.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_update_core::github::GithubClient;
    ///
    /// # fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4");
    ///
    /// assert!(client.has_update("v8.0.0", "v8.1.0")?);
    /// assert!(!client.has_update("v8.1.0", "v8.0.0")?);
    /// assert!(!client.has_update("v8.0.0", "v8.0.0")?);
    /// # Ok(())
    /// # }
    /// ```
    pub fn has_update(&self, current_version: &str, latest_version: &str) -> Result<bool> {
        let current = Self::parse_version(current_version)?;
        let latest = Self::parse_version(latest_version)?;

        Ok(latest > current)
    }

    /// Parses a version string into a strict semantic version.
    ///
    /// This function uses strict semver parsing (via `semver::Version::parse`)
    /// rather than the lenient `classic_version_core::parse_version` because
    /// GitHub releases use proper semver including pre-release versions
    /// like `8.0.0-beta.1` or `1.2.3-alpha`.
    ///
    /// # Arguments
    ///
    /// * `version` - Version string to parse (e.g., "v8.0.0" or "8.0.0")
    ///
    /// # Returns
    ///
    /// Returns a parsed `Version` object.
    ///
    /// # Errors
    ///
    /// Returns `UpdateError::VersionError` if the version string is invalid.
    fn parse_version(version: &str) -> Result<Version> {
        let version = version.trim_start_matches('v');
        Version::parse(version).map_err(UpdateError::from)
    }

    /// Gets the repository owner.
    ///
    /// # Returns
    ///
    /// Returns the repository owner string.
    pub fn owner(&self) -> &str {
        &self.owner
    }

    /// Gets the repository name.
    ///
    /// # Returns
    ///
    /// Returns the repository name string.
    pub fn repo(&self) -> &str {
        &self.repo
    }

    /// Constructs the full repository URL.
    ///
    /// # Returns
    ///
    /// Returns the full GitHub repository URL.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_update_core::github::GithubClient;
    ///
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4");
    /// assert_eq!(client.repo_url(), "https://github.com/evildarkarchon/CLASSIC-Fallout4");
    /// ```
    pub fn repo_url(&self) -> String {
        format!("https://github.com/{}/{}", self.owner, self.repo)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_client_creation() {
        let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4");
        assert_eq!(client.owner(), "evildarkarchon");
        assert_eq!(client.repo(), "CLASSIC-Fallout4");
        assert_eq!(
            client.repo_url(),
            "https://github.com/evildarkarchon/CLASSIC-Fallout4"
        );
    }

    #[test]
    fn test_version_parsing() {
        // Valid versions
        assert!(GithubClient::parse_version("8.0.0").is_ok());
        assert!(GithubClient::parse_version("v8.0.0").is_ok());
        assert!(GithubClient::parse_version("1.2.3-alpha").is_ok());

        // Invalid versions
        assert!(GithubClient::parse_version("invalid").is_err());
        assert!(GithubClient::parse_version("v.8.0.0").is_err());
    }

    #[test]
    fn test_has_update() {
        let client = GithubClient::new("test", "repo");

        // Newer version available
        assert!(client.has_update("8.0.0", "8.1.0").unwrap());
        assert!(client.has_update("v8.0.0", "v8.1.0").unwrap());
        assert!(client.has_update("8.0.0", "9.0.0").unwrap());

        // Same version
        assert!(!client.has_update("8.0.0", "8.0.0").unwrap());
        assert!(!client.has_update("v8.0.0", "v8.0.0").unwrap());

        // Older version
        assert!(!client.has_update("8.1.0", "8.0.0").unwrap());
        assert!(!client.has_update("v9.0.0", "v8.0.0").unwrap());
    }

    #[test]
    fn test_client_clone() {
        let client1 = GithubClient::new("owner", "repo");
        let client2 = client1.clone();

        assert_eq!(client1.owner(), client2.owner());
        assert_eq!(client1.repo(), client2.repo());
    }

    #[test]
    fn test_client_with_token() {
        let client = GithubClient::with_token("owner", "repo", Some("test_token".to_string()));
        assert_eq!(client.owner(), "owner");
        assert_eq!(client.repo(), "repo");
        assert!(client.token.is_some());
        assert_eq!(client.token.as_deref(), Some("test_token"));
    }

    #[test]
    fn test_client_with_empty_token() {
        let client = GithubClient::with_token("owner", "repo", Some("".to_string()));
        assert!(client.token.is_none()); // Empty tokens should be filtered out
    }

    #[test]
    fn test_client_without_token() {
        let client = GithubClient::with_token("owner", "repo", None);
        assert!(client.token.is_none());
    }
}
