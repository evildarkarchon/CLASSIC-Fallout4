//! Web utilities for CLASSIC.
//!
//! This crate provides web-related utilities including URL validation,
//! user agent strings, and mod site constants.
//!
//! # Features
//!
//! - **URL Validation**: Validate and parse URLs
//! - **User Agent Strings**: Generate appropriate user agent strings for CLASSIC
//! - **Mod Site Constants**: URLs for common modding sites (Nexus Mods, etc.)
//! - **URL Building**: Build URLs for common operations
//!
//! # Examples
//!
//! ```rust
//! use classic_web_core::{validate_url, get_user_agent, ModSite};
//!
//! // Validate a URL
//! assert!(validate_url("https://www.nexusmods.com").is_ok());
//!
//! // Get user agent string
//! let ua = get_user_agent();
//! println!("User agent: {}", ua);
//!
//! // Get Nexus Mods URL
//! let nexus_url = ModSite::NexusMods.base_url();
//! assert_eq!(nexus_url, "https://www.nexusmods.com");
//! ```

use serde::{Deserialize, Serialize};
use thiserror::Error;
use url::Url;

/// Web utilities errors.
#[derive(Error, Debug)]
pub enum WebError {
    /// Invalid URL.
    #[error("Invalid URL: {0}")]
    InvalidUrl(String),

    /// URL parse error.
    #[error("URL parse error: {0}")]
    UrlParseError(#[from] url::ParseError),

    /// Invalid scheme.
    #[error("Invalid URL scheme: {0} (expected http or https)")]
    InvalidScheme(String),
}

/// Result type for web operations.
pub type WebResult<T> = Result<T, WebError>;

// ============================================================================
// User Agent
// ============================================================================

/// CLASSIC version for user agent string.
pub const CLASSIC_VERSION: &str = "8.0.0";

/// CLASSIC user agent prefix.
pub const USER_AGENT_PREFIX: &str = "CLASSIC";

/// Get the user agent string for CLASSIC.
///
/// # Returns
///
/// A user agent string like "CLASSIC/8.0.0".
///
/// # Examples
///
/// ```rust
/// use classic_web_core::get_user_agent;
///
/// let ua = get_user_agent();
/// assert!(ua.starts_with("CLASSIC/"));
/// ```
#[must_use]
pub fn get_user_agent() -> String {
    format!("{}/{}", USER_AGENT_PREFIX, CLASSIC_VERSION)
}

/// Get a custom user agent string with additional info.
///
/// # Arguments
///
/// * `suffix` - Additional information to append
///
/// # Returns
///
/// A user agent string like "CLASSIC/8.0.0 (Windows)".
///
/// # Examples
///
/// ```rust
/// use classic_web_core::get_user_agent_with_suffix;
///
/// let ua = get_user_agent_with_suffix("Windows");
/// assert_eq!(ua, "CLASSIC/8.0.0 (Windows)");
/// ```
#[must_use]
pub fn get_user_agent_with_suffix(suffix: &str) -> String {
    format!("{}/{} ({})", USER_AGENT_PREFIX, CLASSIC_VERSION, suffix)
}

// ============================================================================
// URL Validation
// ============================================================================

/// Validate a URL string.
///
/// Checks if the URL is well-formed and uses http or https scheme.
///
/// # Arguments
///
/// * `url_str` - The URL string to validate
///
/// # Returns
///
/// Ok with the parsed URL if valid.
///
/// # Errors
///
/// Returns `WebError::UrlParseError` if the URL cannot be parsed,
/// or `WebError::InvalidScheme` if the scheme is not http/https.
///
/// # Examples
///
/// ```rust
/// use classic_web_core::validate_url;
///
/// assert!(validate_url("https://www.nexusmods.com").is_ok());
/// assert!(validate_url("http://example.com").is_ok());
/// assert!(validate_url("ftp://example.com").is_err());
/// assert!(validate_url("not a url").is_err());
/// ```
pub fn validate_url(url_str: &str) -> WebResult<Url> {
    let url = Url::parse(url_str)?;

    // Check scheme
    let scheme = url.scheme();
    if scheme != "http" && scheme != "https" {
        return Err(WebError::InvalidScheme(scheme.to_string()));
    }

    Ok(url)
}

/// Check if a URL string is valid.
///
/// # Arguments
///
/// * `url_str` - The URL string to check
///
/// # Returns
///
/// True if the URL is valid and uses http/https.
///
/// # Examples
///
/// ```rust
/// use classic_web_core::is_valid_url;
///
/// assert!(is_valid_url("https://www.nexusmods.com"));
/// assert!(is_valid_url("http://example.com"));
/// assert!(!is_valid_url("ftp://example.com"));
/// assert!(!is_valid_url("not a url"));
/// ```
#[must_use]
pub fn is_valid_url(url_str: &str) -> bool {
    validate_url(url_str).is_ok()
}

/// Extract the domain from a URL.
///
/// # Arguments
///
/// * `url_str` - The URL string
///
/// # Returns
///
/// The domain name if the URL is valid.
///
/// # Errors
///
/// Returns `WebError` if the URL is invalid or has no host.
///
/// # Examples
///
/// ```rust
/// use classic_web_core::extract_domain;
///
/// assert_eq!(extract_domain("https://www.nexusmods.com/fallout4").unwrap(), "www.nexusmods.com");
/// assert_eq!(extract_domain("http://example.com:8080/path").unwrap(), "example.com");
/// ```
pub fn extract_domain(url_str: &str) -> WebResult<String> {
    let url = validate_url(url_str)?;

    url.host_str()
        .map(String::from)
        .ok_or_else(|| WebError::InvalidUrl("URL has no host".to_string()))
}

// ============================================================================
// Mod Sites
// ============================================================================

/// Mod site enumeration.
///
/// Represents popular modding sites.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ModSite {
    /// Nexus Mods
    NexusMods,
    /// Bethesda.net
    BethesdaNet,
    /// ModDB
    ModDB,
}

impl ModSite {
    /// Get the base URL for this mod site.
    ///
    /// # Returns
    ///
    /// The base URL as a string.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_web_core::ModSite;
    ///
    /// assert_eq!(ModSite::NexusMods.base_url(), "https://www.nexusmods.com");
    /// assert_eq!(ModSite::BethesdaNet.base_url(), "https://bethesda.net");
    /// assert_eq!(ModSite::ModDB.base_url(), "https://www.moddb.com");
    /// ```
    #[must_use]
    pub fn base_url(self) -> &'static str {
        match self {
            Self::NexusMods => "https://www.nexusmods.com",
            Self::BethesdaNet => "https://bethesda.net",
            Self::ModDB => "https://www.moddb.com",
        }
    }

    /// Get the site name as a string.
    ///
    /// # Returns
    ///
    /// The site name.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_web_core::ModSite;
    ///
    /// assert_eq!(ModSite::NexusMods.name(), "Nexus Mods");
    /// assert_eq!(ModSite::BethesdaNet.name(), "Bethesda.net");
    /// assert_eq!(ModSite::ModDB.name(), "ModDB");
    /// ```
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::NexusMods => "Nexus Mods",
            Self::BethesdaNet => "Bethesda.net",
            Self::ModDB => "ModDB",
        }
    }

    /// Build a URL for a specific game on this mod site.
    ///
    /// # Arguments
    ///
    /// * `game_id` - The game identifier
    ///
    /// # Returns
    ///
    /// The full URL for the game's mod page.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_web_core::ModSite;
    /// use classic_constants_core::GameId;
    ///
    /// let url = ModSite::NexusMods.game_url(GameId::Fallout4);
    /// assert_eq!(url, "https://www.nexusmods.com/fallout4");
    /// ```
    #[must_use]
    pub fn game_url(self, game_id: classic_constants_core::GameId) -> String {
        let game_slug = match game_id {
            classic_constants_core::GameId::Fallout4 => "fallout4",
            classic_constants_core::GameId::Fallout4VR => "fallout4vr",
            classic_constants_core::GameId::Skyrim => "skyrimspecialedition",
            classic_constants_core::GameId::Starfield => "starfield",
        };

        match self {
            Self::NexusMods => format!("{}/{}", self.base_url(), game_slug),
            Self::BethesdaNet => format!("{}/mods", self.base_url()),
            Self::ModDB => format!("{}/games", self.base_url()),
        }
    }
}

// ============================================================================
// URL Building
// ============================================================================

/// Build a URL by joining a base URL with a path.
///
/// # Arguments
///
/// * `base` - The base URL
/// * `path` - The path to append
///
/// # Returns
///
/// The joined URL.
///
/// # Errors
///
/// Returns `WebError` if the base URL or path is invalid.
///
/// # Examples
///
/// ```rust
/// use classic_web_core::join_url;
///
/// let url = join_url("https://example.com", "path/to/resource").unwrap();
/// assert_eq!(url, "https://example.com/path/to/resource");
/// ```
pub fn join_url(base: &str, path: &str) -> WebResult<String> {
    let mut base_url = validate_url(base)?;

    // Join the path
    base_url = base_url
        .join(path)
        .map_err(|e| WebError::InvalidUrl(format!("Failed to join URL: {}", e)))?;

    Ok(base_url.to_string())
}

/// Build a URL with query parameters.
///
/// # Arguments
///
/// * `base` - The base URL
/// * `params` - Query parameters as key-value pairs
///
/// # Returns
///
/// The URL with query parameters appended.
///
/// # Errors
///
/// Returns `WebError` if the base URL is invalid.
///
/// # Examples
///
/// ```rust
/// use classic_web_core::build_url_with_query;
///
/// let params = vec![("page", "1"), ("sort", "popular")];
/// let url = build_url_with_query("https://example.com/search", &params).unwrap();
/// assert_eq!(url, "https://example.com/search?page=1&sort=popular");
/// ```
pub fn build_url_with_query(base: &str, params: &[(&str, &str)]) -> WebResult<String> {
    let mut url = validate_url(base)?;

    // Add query parameters
    {
        let mut query_pairs = url.query_pairs_mut();
        for (key, value) in params {
            query_pairs.append_pair(key, value);
        }
    }

    Ok(url.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_user_agent() {
        let ua = get_user_agent();
        assert!(ua.starts_with("CLASSIC/"));
        assert!(ua.contains("8.0.0"));
    }

    #[test]
    fn test_get_user_agent_with_suffix() {
        let ua = get_user_agent_with_suffix("Windows");
        assert_eq!(ua, "CLASSIC/8.0.0 (Windows)");
    }

    #[test]
    fn test_validate_url() {
        assert!(validate_url("https://www.nexusmods.com").is_ok());
        assert!(validate_url("http://example.com").is_ok());
        assert!(validate_url("ftp://example.com").is_err());
        assert!(validate_url("not a url").is_err());
    }

    #[test]
    fn test_is_valid_url() {
        assert!(is_valid_url("https://www.nexusmods.com"));
        assert!(is_valid_url("http://example.com"));
        assert!(!is_valid_url("ftp://example.com"));
        assert!(!is_valid_url("not a url"));
    }

    #[test]
    fn test_extract_domain() {
        assert_eq!(
            extract_domain("https://www.nexusmods.com/fallout4").unwrap(),
            "www.nexusmods.com"
        );
        assert_eq!(
            extract_domain("http://example.com:8080/path").unwrap(),
            "example.com"
        );
    }

    #[test]
    fn test_mod_site_base_url() {
        assert_eq!(ModSite::NexusMods.base_url(), "https://www.nexusmods.com");
        assert_eq!(ModSite::BethesdaNet.base_url(), "https://bethesda.net");
        assert_eq!(ModSite::ModDB.base_url(), "https://www.moddb.com");
    }

    #[test]
    fn test_mod_site_name() {
        assert_eq!(ModSite::NexusMods.name(), "Nexus Mods");
        assert_eq!(ModSite::BethesdaNet.name(), "Bethesda.net");
        assert_eq!(ModSite::ModDB.name(), "ModDB");
    }

    #[test]
    fn test_mod_site_game_url() {
        use classic_constants_core::GameId;

        let url = ModSite::NexusMods.game_url(GameId::Fallout4);
        assert_eq!(url, "https://www.nexusmods.com/fallout4");

        let url = ModSite::NexusMods.game_url(GameId::Skyrim);
        assert_eq!(url, "https://www.nexusmods.com/skyrimspecialedition");
    }

    #[test]
    fn test_join_url() {
        let url = join_url("https://example.com", "path/to/resource").unwrap();
        assert_eq!(url, "https://example.com/path/to/resource");
    }

    #[test]
    fn test_build_url_with_query() {
        let params = vec![("page", "1"), ("sort", "popular")];
        let url = build_url_with_query("https://example.com/search", &params).unwrap();
        assert_eq!(url, "https://example.com/search?page=1&sort=popular");
    }
}
