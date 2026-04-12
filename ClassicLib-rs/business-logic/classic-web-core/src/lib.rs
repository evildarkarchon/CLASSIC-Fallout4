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

use classic_shared_core::GameId;
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
    /// use classic_shared_core::GameId;
    ///
    /// let url = ModSite::NexusMods.game_url(GameId::Fallout4);
    /// assert_eq!(url, "https://www.nexusmods.com/fallout4");
    /// ```
    #[must_use]
    pub fn game_url(self, game_id: GameId) -> String {
        let game_slug = match game_id {
            GameId::Fallout4 => "fallout4",
            GameId::Fallout4VR => "fallout4vr",
            GameId::Skyrim => "skyrimspecialedition",
            GameId::Starfield => "starfield",
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
        use classic_shared_core::GameId;

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

    // ========================================================================
    // Additional Tests for Improved Coverage
    // ========================================================================

    // Compile-time assertions for version string validity
    const _: () = assert!(!CLASSIC_VERSION.is_empty());
    const _: () =
        assert!(CLASSIC_VERSION.as_bytes()[1] == b'.' || CLASSIC_VERSION.as_bytes()[3] == b'.');

    #[test]
    fn test_user_agent_constants() {
        assert_eq!(USER_AGENT_PREFIX, "CLASSIC");
    }

    #[test]
    fn test_get_user_agent_with_various_suffixes() {
        let cases = [
            ("Windows", "CLASSIC/8.0.0 (Windows)"),
            ("Linux", "CLASSIC/8.0.0 (Linux)"),
            ("macOS", "CLASSIC/8.0.0 (macOS)"),
            ("", "CLASSIC/8.0.0 ()"),
            ("Test Suite", "CLASSIC/8.0.0 (Test Suite)"),
        ];

        for (suffix, expected) in cases {
            assert_eq!(get_user_agent_with_suffix(suffix), expected);
        }
    }

    #[test]
    fn test_validate_url_edge_cases() {
        // Valid URLs with various components
        assert!(validate_url("https://example.com").is_ok());
        assert!(validate_url("http://example.com:8080").is_ok());
        assert!(validate_url("https://example.com/path").is_ok());
        assert!(validate_url("https://example.com/path?query=1").is_ok());
        assert!(validate_url("https://example.com/path#anchor").is_ok());
        assert!(validate_url("https://user:pass@example.com").is_ok());

        // URLs with IP addresses
        assert!(validate_url("http://192.168.1.1").is_ok());
        assert!(validate_url("http://127.0.0.1:8080").is_ok());

        // Invalid schemes
        assert!(validate_url("ftp://example.com").is_err());
        assert!(validate_url("file:///path/to/file").is_err());
        assert!(validate_url("mailto:test@example.com").is_err());
        assert!(validate_url("data:text/plain,hello").is_err());

        // Malformed URLs
        assert!(validate_url("").is_err());
        assert!(validate_url("   ").is_err());
        assert!(validate_url("://missing-scheme.com").is_err());
    }

    #[test]
    fn test_is_valid_url_edge_cases() {
        // Various valid HTTP/HTTPS URLs
        assert!(is_valid_url("https://www.google.com"));
        assert!(is_valid_url("http://localhost"));
        assert!(is_valid_url("http://localhost:3000"));
        assert!(is_valid_url("https://api.example.com/v1/users?page=1"));

        // Invalid URLs
        assert!(!is_valid_url(""));
        assert!(!is_valid_url("just text"));
        assert!(!is_valid_url("www.example.com")); // No scheme
        assert!(!is_valid_url("javascript:alert(1)"));
    }

    #[test]
    fn test_extract_domain_edge_cases() {
        // Standard domains
        assert_eq!(
            extract_domain("https://example.com").unwrap(),
            "example.com"
        );
        assert_eq!(
            extract_domain("http://subdomain.example.com").unwrap(),
            "subdomain.example.com"
        );

        // With port
        assert_eq!(
            extract_domain("https://example.com:443").unwrap(),
            "example.com"
        );

        // With path and query
        assert_eq!(
            extract_domain("https://api.example.com/v1/users?id=123").unwrap(),
            "api.example.com"
        );

        // IP addresses
        assert_eq!(
            extract_domain("http://192.168.1.1/path").unwrap(),
            "192.168.1.1"
        );
        assert_eq!(
            extract_domain("http://127.0.0.1:8080").unwrap(),
            "127.0.0.1"
        );
    }

    #[test]
    fn test_extract_domain_errors() {
        // Invalid URL
        let result = extract_domain("not a url");
        assert!(result.is_err());

        // Invalid scheme
        let result = extract_domain("ftp://example.com");
        assert!(result.is_err());
    }

    #[test]
    fn test_mod_site_all_game_urls() {
        use classic_shared_core::GameId;

        // Nexus Mods
        assert_eq!(
            ModSite::NexusMods.game_url(GameId::Fallout4),
            "https://www.nexusmods.com/fallout4"
        );
        assert_eq!(
            ModSite::NexusMods.game_url(GameId::Fallout4VR),
            "https://www.nexusmods.com/fallout4vr"
        );
        assert_eq!(
            ModSite::NexusMods.game_url(GameId::Skyrim),
            "https://www.nexusmods.com/skyrimspecialedition"
        );
        assert_eq!(
            ModSite::NexusMods.game_url(GameId::Starfield),
            "https://www.nexusmods.com/starfield"
        );

        // Bethesda.net (same URL for all games)
        assert_eq!(
            ModSite::BethesdaNet.game_url(GameId::Fallout4),
            "https://bethesda.net/mods"
        );
        assert_eq!(
            ModSite::BethesdaNet.game_url(GameId::Skyrim),
            "https://bethesda.net/mods"
        );

        // ModDB (same URL for all games)
        assert_eq!(
            ModSite::ModDB.game_url(GameId::Fallout4),
            "https://www.moddb.com/games"
        );
        assert_eq!(
            ModSite::ModDB.game_url(GameId::Starfield),
            "https://www.moddb.com/games"
        );
    }

    #[test]
    fn test_mod_site_clone_copy() {
        let site = ModSite::NexusMods;
        let cloned = site;
        let copied = site;

        assert_eq!(site, cloned);
        assert_eq!(site, copied);
    }

    #[test]
    fn test_mod_site_eq_hash() {
        use std::collections::HashSet;

        let mut set = HashSet::new();
        set.insert(ModSite::NexusMods);
        set.insert(ModSite::BethesdaNet);
        set.insert(ModSite::ModDB);

        assert_eq!(set.len(), 3);
        assert!(set.contains(&ModSite::NexusMods));
        assert!(set.contains(&ModSite::BethesdaNet));
        assert!(set.contains(&ModSite::ModDB));

        // Inserting duplicate
        set.insert(ModSite::NexusMods);
        assert_eq!(set.len(), 3);
    }

    #[test]
    fn test_mod_site_serialization() {
        let site = ModSite::NexusMods;

        let json = serde_json::to_string(&site).unwrap();
        let parsed: ModSite = serde_json::from_str(&json).unwrap();

        assert_eq!(site, parsed);
    }

    #[test]
    fn test_mod_site_debug() {
        let site = ModSite::NexusMods;
        let debug = format!("{:?}", site);
        assert!(debug.contains("NexusMods"));
    }

    #[test]
    fn test_join_url_edge_cases() {
        // Trailing slash on base
        let url = join_url("https://example.com/", "path").unwrap();
        assert!(url.contains("path"));

        // Leading slash on path
        let url = join_url("https://example.com", "/path").unwrap();
        assert!(url.contains("path"));

        // Complex path
        let url = join_url("https://example.com/api/v1", "users/123").unwrap();
        assert!(url.contains("users/123"));

        // Empty path - should return base
        let url = join_url("https://example.com/base", "").unwrap();
        assert!(url.contains("example.com"));
    }

    #[test]
    fn test_join_url_errors() {
        // Invalid base URL
        let result = join_url("not a url", "path");
        assert!(result.is_err());

        // Invalid scheme
        let result = join_url("ftp://example.com", "path");
        assert!(result.is_err());
    }

    #[test]
    fn test_build_url_with_query_edge_cases() {
        // Empty params - URL library may add trailing ? which is still valid
        let url = build_url_with_query("https://example.com/search", &[]).unwrap();
        // Just verify it's still a valid URL and has the base
        assert!(url.starts_with("https://example.com/search"));

        // Single param
        let url = build_url_with_query("https://example.com/search", &[("q", "test")]).unwrap();
        assert_eq!(url, "https://example.com/search?q=test");

        // Multiple params
        let params = vec![("a", "1"), ("b", "2"), ("c", "3")];
        let url = build_url_with_query("https://example.com", &params).unwrap();
        assert!(url.contains("a=1"));
        assert!(url.contains("b=2"));
        assert!(url.contains("c=3"));

        // Params with special characters
        let params = vec![("q", "hello world"), ("tag", "c++")];
        let url = build_url_with_query("https://example.com/search", &params).unwrap();
        assert!(url.contains("q=hello"));
        assert!(url.contains("tag=c"));
    }

    #[test]
    fn test_build_url_with_query_errors() {
        // Invalid base URL
        let result = build_url_with_query("not a url", &[("q", "test")]);
        assert!(result.is_err());

        // Invalid scheme
        let result = build_url_with_query("ftp://example.com", &[("q", "test")]);
        assert!(result.is_err());
    }

    #[test]
    fn test_web_error_display() {
        let err = WebError::InvalidUrl("test url".to_string());
        let display = format!("{}", err);
        assert!(display.contains("Invalid URL"));
        assert!(display.contains("test url"));

        let err = WebError::InvalidScheme("ftp".to_string());
        let display = format!("{}", err);
        assert!(display.contains("Invalid URL scheme"));
        assert!(display.contains("ftp"));
    }

    #[test]
    fn test_web_error_debug() {
        let err = WebError::InvalidUrl("test".to_string());
        let debug = format!("{:?}", err);
        assert!(debug.contains("InvalidUrl"));
    }

    #[test]
    fn test_web_error_from_url_parse_error() {
        let url_err = url::Url::parse(":::").unwrap_err();
        let err: WebError = url_err.into();

        let display = format!("{}", err);
        assert!(display.contains("URL parse error"));
    }

    #[test]
    fn test_web_result_type() {
        fn returns_ok() -> WebResult<String> {
            Ok("success".to_string())
        }

        fn returns_err() -> WebResult<String> {
            Err(WebError::InvalidUrl("test".to_string()))
        }

        assert!(returns_ok().is_ok());
        assert!(returns_err().is_err());
    }

    #[test]
    fn test_validate_url_returns_parsed_url() {
        let url = validate_url("https://www.nexusmods.com/fallout4").unwrap();

        assert_eq!(url.scheme(), "https");
        assert_eq!(url.host_str(), Some("www.nexusmods.com"));
        assert_eq!(url.path(), "/fallout4");
    }

    #[test]
    fn test_unicode_in_urls() {
        // Unicode in path should work
        let url = validate_url("https://example.com/path/файл");
        assert!(url.is_ok());

        // Unicode domain (punycode)
        // Note: This might or might not work depending on URL parsing
        let url = validate_url("https://example.com/中文路径");
        assert!(url.is_ok());
    }

    #[test]
    fn test_url_with_fragments() {
        let url = validate_url("https://example.com/page#section").unwrap();
        assert_eq!(url.fragment(), Some("section"));
    }

    #[test]
    fn test_url_with_username_password() {
        let url = validate_url("https://user:password@example.com").unwrap();
        assert_eq!(url.username(), "user");
        assert_eq!(url.password(), Some("password"));
    }

    #[test]
    fn test_long_url() {
        let long_path = "a".repeat(1000);
        let url_str = format!("https://example.com/{}", long_path);
        let result = validate_url(&url_str);
        assert!(result.is_ok());
    }

    #[test]
    fn test_mod_site_all_variants_covered() {
        // Ensure all variants are tested
        let sites = [ModSite::NexusMods, ModSite::BethesdaNet, ModSite::ModDB];

        for site in sites {
            // Each should have a base_url
            assert!(!site.base_url().is_empty());
            assert!(site.base_url().starts_with("https://"));

            // Each should have a name
            assert!(!site.name().is_empty());
        }
    }
}
