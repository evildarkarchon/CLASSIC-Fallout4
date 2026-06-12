//! GitHub API integration for checking releases and updates.
//!
//! # Compat-only surface
//!
//! User-facing update checks SHOULD go through
//! [`crate::notification::check_app_notification`] (the manifest-driven,
//! Pages-first, rate-limit-resilient path). This module is retained for
//! diagnostic tooling and a gradual binding migration (see design decision
//! D-08 in `openspec/changes/app-update-manifest-notification/design.md`).
//! [`GithubClient::get_latest_release`] is annotated `#[deprecated]` to
//! flag accidental new use sites — existing in-tree callers keep working
//! until their owning crate migrates to the notification API.
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
//! let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")?;
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

    /// Page size for `/releases` pagination. GitHub caps this at 100; we
    /// pick the max so the common case (a handful of `yaml-data-v*` tags
    /// interleaved with binary releases) finishes in a single request.
    const RELEASES_PER_PAGE: u32 = 100;

    /// Upper bound on pages walked by `get_all_releases`. With
    /// `RELEASES_PER_PAGE = 100`, this caps the fetch at 1,000 releases —
    /// well beyond this repo's actual history — while keeping a
    /// pathological or malicious response from looping indefinitely.
    const MAX_RELEASES_PAGES: u32 = 10;

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
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4").unwrap();
    /// ```
    pub fn new(owner: impl Into<String>, repo: impl Into<String>) -> Result<Self> {
        // Load .env file if present (silently ignores if not found)
        let _ = dotenvy::dotenv();

        let token = std::env::var(Self::GITHUB_TOKEN_ENV)
            .ok()
            .filter(|t| !t.is_empty());

        let client = Client::builder()
            .timeout(Self::API_TIMEOUT)
            .user_agent(format!("CLASSIC-Update/{}", env!("CARGO_PKG_VERSION")))
            .build()?;

        Ok(Self {
            owner: owner.into(),
            repo: repo.into(),
            client,
            base_url: Self::GITHUB_API_BASE.to_string(),
            token,
        })
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
    /// let client = GithubClient::with_token("evildarkarchon", "CLASSIC-Fallout4", Some("ghp_xxx".to_string())).unwrap();
    /// ```
    pub fn with_token(
        owner: impl Into<String>,
        repo: impl Into<String>,
        token: Option<String>,
    ) -> Result<Self> {
        let client = Client::builder()
            .timeout(Self::API_TIMEOUT)
            .user_agent(format!("CLASSIC-Update/{}", env!("CARGO_PKG_VERSION")))
            .build()?;

        Ok(Self {
            owner: owner.into(),
            repo: repo.into(),
            client,
            base_url: Self::GITHUB_API_BASE.to_string(),
            token: token.filter(|t| !t.is_empty()),
        })
    }

    /// Creates a client with an explicit API base URL and token, intended for
    /// unit tests that mock the GitHub API (e.g. via `mockito::Server`).
    ///
    /// Production code should prefer [`GithubClient::new`] or
    /// [`GithubClient::with_token`]; this constructor exists only so tests can
    /// redirect the API-fallback leg of `fetch_yaml_manifest` without
    /// otherwise reimplementing the client.
    pub fn with_base_url(
        owner: impl Into<String>,
        repo: impl Into<String>,
        base_url: impl Into<String>,
        token: Option<String>,
    ) -> Result<Self> {
        let client = Client::builder()
            .timeout(Self::API_TIMEOUT)
            .user_agent(format!("CLASSIC-Update/{}", env!("CARGO_PKG_VERSION")))
            .build()?;

        Ok(Self {
            owner: owner.into(),
            repo: repo.into(),
            client,
            base_url: base_url.into(),
            token: token.filter(|t| !t.is_empty()),
        })
    }

    /// Returns the underlying `reqwest::Client` so sibling modules (namely
    /// `yaml_update`) can issue GETs against arbitrary URLs (e.g. GitHub
    /// Pages or release-asset CDN URLs) through the same connection-pooled
    /// client with the same user agent and timeout.
    pub(crate) fn http_client(&self) -> &Client {
        &self.client
    }

    /// Returns the (optional) authentication token the client was built with.
    /// Used by the YAML-update fetch path to reuse the same opportunistic
    /// `Authorization: Bearer` header applied by [`build_request`] — without
    /// ever synthesizing a token that wasn't already present in the process
    /// environment.
    pub(crate) fn token(&self) -> Option<&str> {
        self.token.as_deref()
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
    /// - `UpdateError::HttpError` if the HTTP request or JSON deserialization fails
    ///   (note: `reqwest`'s `.json()` wraps serde errors in `reqwest::Error`)
    /// - `UpdateError::GithubError` if the API returns an error
    /// - `UpdateError::NotFound` if no releases exist
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_update_core::github::GithubClient;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")?;
    /// let latest = client.get_latest_release().await?;
    /// println!("Latest version: {}", latest.tag_name);
    /// # Ok(())
    /// # }
    /// ```
    #[deprecated(note = "Use classic_update_core::notification::check_app_notification instead")]
    pub async fn get_latest_release(&self) -> Result<GithubRelease> {
        let url = format!(
            "{}/repos/{}/{}/releases/latest",
            self.base_url, self.owner, self.repo
        );

        let response = self
            .build_request(&url)
            .send()
            .await
            .map_err(UpdateError::HttpError)?;

        match response.status() {
            reqwest::StatusCode::OK => {
                let release: GithubRelease =
                    response.json().await.map_err(UpdateError::HttpError)?;
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
    /// # Pagination
    ///
    /// GitHub's `/releases` endpoint paginates at 30 items per page by
    /// default (configurable up to 100). This method requests
    /// `per_page = RELEASES_PER_PAGE` and walks pages until the API returns
    /// a short page (fewer items than requested) or until
    /// `MAX_RELEASES_PAGES` have been fetched, whichever comes first. The
    /// cap exists so a pathological or malicious response can't turn this
    /// into an unbounded request loop.
    ///
    /// This matters for the YAML-data fallback path
    /// (`fetch_from_releases_api`), which filters for `yaml-data-v*` tags
    /// that are interleaved with binary releases. Without pagination, the
    /// newest YAML release can fall off the first page as history grows
    /// and a Pages-blocked client would spuriously report `NotFound`.
    ///
    /// # Errors
    ///
    /// - `UpdateError::HttpError` if the HTTP request or JSON deserialization fails
    ///   (note: `reqwest`'s `.json()` wraps serde errors in `reqwest::Error`)
    /// - `UpdateError::GithubError` if the API returns an error
    ///
    /// # Examples
    ///
    /// ```rust,no_run
    /// use classic_update_core::github::GithubClient;
    ///
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")?;
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
        let base_path = format!(
            "{}/repos/{}/{}/releases",
            self.base_url, self.owner, self.repo
        );

        let mut all: Vec<GithubRelease> = Vec::new();
        for page in 1..=Self::MAX_RELEASES_PAGES {
            let url = format!(
                "{}?per_page={}&page={}",
                base_path,
                Self::RELEASES_PER_PAGE,
                page
            );

            let response = self
                .build_request(&url)
                .send()
                .await
                .map_err(UpdateError::HttpError)?;

            let page_releases: Vec<GithubRelease> = match response.status() {
                reqwest::StatusCode::OK => response.json().await.map_err(UpdateError::HttpError)?,
                reqwest::StatusCode::FORBIDDEN => {
                    return Err(UpdateError::RateLimitExceeded(None));
                }
                status => {
                    return Err(UpdateError::GithubError(format!(
                        "API returned status {}",
                        status
                    )));
                }
            };

            let page_len = page_releases.len();
            all.extend(page_releases);

            // A short page (or an empty page) means we've seen the tail;
            // no need to ask for another one. This correctly handles both
            // the "fewer than per_page on the last page" case and the
            // "page beyond the last has zero items" case.
            if page_len < Self::RELEASES_PER_PAGE as usize {
                break;
            }
        }

        // Filter based on preferences
        all.retain(|r| (include_prereleases || !r.prerelease) && (include_drafts || !r.draft));

        Ok(all)
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
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")?;
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
    /// let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4").unwrap();
    /// assert_eq!(client.repo_url(), "https://github.com/evildarkarchon/CLASSIC-Fallout4");
    /// ```
    pub fn repo_url(&self) -> String {
        format!("https://github.com/{}/{}", self.owner, self.repo)
    }
}

#[cfg(test)]
#[path = "github_tests.rs"]
mod tests;
