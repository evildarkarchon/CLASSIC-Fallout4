//! Update system error types.

use thiserror::Error;

/// Errors that can occur during update operations.
#[derive(Debug, Error)]
pub enum UpdateError {
    /// HTTP request error occurred
    #[error("HTTP error: {0}")]
    HttpError(#[from] reqwest::Error),

    /// Failed to parse JSON response
    #[error("JSON parsing error: {0}")]
    JsonError(#[from] serde_json::Error),

    /// HTML scraping error
    #[error("Scraping error: {0}")]
    ScrapingError(String),

    /// Version comparison error
    #[error("Version error: {0}")]
    VersionError(#[from] semver::Error),

    /// URL parsing error
    #[error("URL parsing error: {0}")]
    UrlError(#[from] url::ParseError),

    /// GitHub API error
    #[error("GitHub API error: {0}")]
    GithubError(String),

    /// Nexus Mods error
    #[error("Nexus Mods error: {0}")]
    NexusError(String),

    /// Rate limit exceeded
    #[error("Rate limit exceeded. Retry after: {0:?}")]
    RateLimitExceeded(Option<std::time::Duration>),

    /// Resource not found (404)
    #[error("Resource not found: {0}")]
    NotFound(String),

    /// Network timeout
    #[error("Network timeout")]
    Timeout,

    /// Generic update error
    #[error("Update error: {0}")]
    Generic(String),
}

/// Result type alias for update operations.
pub type Result<T> = std::result::Result<T, UpdateError>;
