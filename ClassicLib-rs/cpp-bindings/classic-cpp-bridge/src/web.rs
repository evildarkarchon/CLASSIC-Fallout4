//! Web bridge for CXX FFI.
//!
//! Bridges `classic-web-core` URL helpers, user-agent helpers, and the
//! `ModSite` enum so C++ frontends can build canonical mod-site URLs and
//! validate user-supplied URLs without hardcoding strings.
//!
//! Per D-04 and D-07, `ModSite` and `WebGameId` are CXX shared enums declared
//! INSIDE this bridge block. The Codex review (MEDIUM) corrected an earlier
//! string-dispatch design — bridge fns now take the typed enums directly.
//!
//! Note on cross-module shared enums: CXX shared enums don't share across
//! `#[cxx::bridge]` modules. `WebGameId` here mirrors the variant set of
//! `classic::constants::GameId` but is a separate CXX type. C++ callers
//! that have a `classic::constants::GameId` value translate via the value
//! (both enums use the same `#[repr(u8)]` discriminants).
//!
//! # CXXS-02 surface
//!
//! - Enums: `ModSite` (3 variants), `WebGameId` (4 variants — mirrors GameId)
//! - URL helpers: `is_valid_url`, `validate_url_string`, `extract_domain_string`,
//!   `web_join_url`, `web_build_url_with_query`
//! - User-agent helpers: `web_get_user_agent`, `web_get_user_agent_with_suffix`
//! - ModSite helpers: `mod_site_name`, `mod_site_base_url`, `mod_site_game_url`
//!
//! # Examples
//!
//! ```cpp
//! // C++ usage
//! auto ua = classic::web::web_get_user_agent();
//! // → "CLASSIC/8.0.0"
//!
//! auto url = classic::web::mod_site_base_url(classic::web::ModSite::NexusMods);
//! // → "https://www.nexusmods.com"
//! ```

use classic_constants_core::GameId as CoreGameId;
use classic_web_core::{
    ModSite as CoreModSite,
    build_url_with_query as core_build_url_with_query,
    extract_domain as core_extract_domain,
    get_user_agent as core_get_user_agent,
    get_user_agent_with_suffix as core_get_user_agent_with_suffix,
    is_valid_url as core_is_valid_url,
    join_url as core_join_url,
    validate_url as core_validate_url,
};

// ─────────────────────────────────────────────────────────────────────────────
// Enum mappers (Codex MEDIUM correction: typed enums, not string dispatch)
// ─────────────────────────────────────────────────────────────────────────────

fn from_bridge_mod_site(site: ffi::ModSite) -> CoreModSite {
    match site {
        ffi::ModSite::NexusMods => CoreModSite::NexusMods,
        ffi::ModSite::BethesdaNet => CoreModSite::BethesdaNet,
        ffi::ModSite::ModDB => CoreModSite::ModDB,
        _ => CoreModSite::NexusMods, // unreachable in safe usage
    }
}

fn from_bridge_web_game_id(g: ffi::WebGameId) -> CoreGameId {
    match g {
        ffi::WebGameId::Fallout4 => CoreGameId::Fallout4,
        ffi::WebGameId::Fallout4VR => CoreGameId::Fallout4VR,
        ffi::WebGameId::Skyrim => CoreGameId::Skyrim,
        ffi::WebGameId::Starfield => CoreGameId::Starfield,
        _ => CoreGameId::Fallout4, // unreachable in safe usage
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// URL helpers
// ─────────────────────────────────────────────────────────────────────────────

fn is_valid_url(url_str: &str) -> bool {
    core_is_valid_url(url_str)
}

/// Validate a URL and return the canonicalized URL string on success.
///
/// Codex MEDIUM correction: return the normalized URL (preserves Url::parse
/// canonicalization), not Result<()> which collapses the parsed value.
fn validate_url_string(url_str: &str) -> Result<String, String> {
    core_validate_url(url_str)
        .map(|url| url.to_string())
        .map_err(|e| e.to_string())
}

fn extract_domain_string(url_str: &str) -> Result<String, String> {
    core_extract_domain(url_str).map_err(|e| e.to_string())
}

fn web_join_url(base: &str, path: &str) -> Result<String, String> {
    core_join_url(base, path).map_err(|e| e.to_string())
}

/// Build a URL with query parameters from parallel key/value string slices.
///
/// `&[(&str, &str)]` slice-of-tuples is NOT CXX-bridgeable, so two parallel
/// `&[String]` vectors are accepted instead.  Returns Err if lengths differ.
fn web_build_url_with_query(
    base: &str,
    keys: &[String],
    values: &[String],
) -> Result<String, String> {
    if keys.len() != values.len() {
        return Err(format!(
            "build_url_with_query: keys.len() ({}) != values.len() ({})",
            keys.len(),
            values.len()
        ));
    }
    let params: Vec<(&str, &str)> = keys
        .iter()
        .zip(values.iter())
        .map(|(k, v)| (k.as_str(), v.as_str()))
        .collect();
    core_build_url_with_query(base, &params).map_err(|e| e.to_string())
}

// ─────────────────────────────────────────────────────────────────────────────
// User-agent helpers
// ─────────────────────────────────────────────────────────────────────────────

fn web_get_user_agent() -> String {
    core_get_user_agent()
}

fn web_get_user_agent_with_suffix(suffix: &str) -> String {
    core_get_user_agent_with_suffix(suffix)
}

// ─────────────────────────────────────────────────────────────────────────────
// ModSite helpers — TYPED ENUM dispatch (Codex MEDIUM correction)
// ─────────────────────────────────────────────────────────────────────────────

fn mod_site_name(site: ffi::ModSite) -> String {
    from_bridge_mod_site(site).name().to_string()
}

fn mod_site_base_url(site: ffi::ModSite) -> String {
    from_bridge_mod_site(site).base_url().to_string()
}

fn mod_site_game_url(site: ffi::ModSite, game: ffi::WebGameId) -> String {
    from_bridge_mod_site(site).game_url(from_bridge_web_game_id(game))
}

// ─────────────────────────────────────────────────────────────────────────────
// CXX bridge block — D-04 shared enums + extern "Rust" helper fns
// ─────────────────────────────────────────────────────────────────────────────

#[cxx::bridge(namespace = "classic::web")]
mod ffi {
    /// Popular mod hosting sites.
    ///
    /// Mirrors `classic_web_core::ModSite` exactly (3 variants).
    #[repr(u8)]
    enum ModSite {
        NexusMods = 0,
        BethesdaNet = 1,
        ModDB = 2,
    }

    /// Game identifier for mod-site URL construction.
    ///
    /// Mirrors `classic_constants_core::GameId` exactly (same repr(u8) discriminants).
    /// Declared here as a separate type because CXX shared enums cannot be reused
    /// across `#[cxx::bridge]` module boundaries.
    #[repr(u8)]
    enum WebGameId {
        Fallout4 = 0,
        Fallout4VR = 1,
        Skyrim = 2,
        Starfield = 3,
    }

    extern "Rust" {
        // ── URL helpers ──────────────────────────────────────────────────────

        /// Returns `true` if the URL is well-formed and uses http/https.
        fn is_valid_url(url_str: &str) -> bool;

        /// Validate a URL and return the canonicalized string on success.
        ///
        /// Returns `Err` if the URL is malformed or uses a non-http/https scheme.
        fn validate_url_string(url_str: &str) -> Result<String>;

        /// Extract the domain (host) portion of a URL.
        fn extract_domain_string(url_str: &str) -> Result<String>;

        /// Join a base URL with a relative path segment.
        fn web_join_url(base: &str, path: &str) -> Result<String>;

        /// Build a URL with query parameters from parallel key/value string slices.
        ///
        /// `keys` and `values` must have equal length; returns `Err` otherwise.
        fn web_build_url_with_query(
            base: &str,
            keys: &[String],
            values: &[String],
        ) -> Result<String>;

        // ── User-agent helpers ───────────────────────────────────────────────

        /// Get the CLASSIC user agent string (e.g. `"CLASSIC/8.0.0"`).
        fn web_get_user_agent() -> String;

        /// Get a CLASSIC user agent string with a parenthesised suffix
        /// (e.g. `"CLASSIC/8.0.0 (Windows)"`).
        fn web_get_user_agent_with_suffix(suffix: &str) -> String;

        // ── ModSite helpers — typed enum dispatch (D-04 / D-07) ─────────────

        /// Get the display name of a `ModSite` (e.g. `"Nexus Mods"`).
        fn mod_site_name(site: ModSite) -> String;

        /// Get the base URL for a `ModSite` (e.g. `"https://www.nexusmods.com"`).
        fn mod_site_base_url(site: ModSite) -> String;

        /// Get the game-specific URL on a `ModSite` given a `WebGameId`.
        fn mod_site_game_url(site: ModSite, game: WebGameId) -> String;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── URL helper tests ─────────────────────────────────────────────────────

    #[test]
    fn test_is_valid_url_true_for_https() {
        assert!(is_valid_url("https://nexusmods.com"));
    }

    #[test]
    fn test_is_valid_url_false_for_garbage() {
        assert!(!is_valid_url("not-a-url"));
    }

    #[test]
    fn test_validate_url_string_ok_returns_normalized_url() {
        let result = validate_url_string("https://nexusmods.com");
        assert!(result.is_ok(), "expected Ok, got {:?}", result);
        // url::Url::parse normalises to "https://nexusmods.com/" (trailing slash)
        let s = result.unwrap();
        assert!(
            s.starts_with("https://nexusmods.com"),
            "normalized URL should start with the input host, got: {s}"
        );
    }

    #[test]
    fn test_validate_url_string_err_for_garbage() {
        let result = validate_url_string("garbage");
        assert!(result.is_err());
        assert!(
            !result.unwrap_err().is_empty(),
            "error message should be non-empty"
        );
    }

    #[test]
    fn test_extract_domain_string_ok() {
        let result = extract_domain_string("https://nexusmods.com/games/fallout4");
        assert!(result.is_ok(), "expected Ok, got {:?}", result);
        assert_eq!(result.unwrap(), "nexusmods.com");
    }

    #[test]
    fn test_extract_domain_string_err_for_invalid() {
        let result = extract_domain_string("not a url");
        assert!(result.is_err());
    }

    #[test]
    fn test_web_get_user_agent_nonempty() {
        let ua = web_get_user_agent();
        assert!(!ua.is_empty());
        assert!(ua.starts_with("CLASSIC/"), "user agent should start with CLASSIC/, got: {ua}");
    }

    #[test]
    fn test_web_get_user_agent_with_suffix_contains_suffix() {
        let ua = web_get_user_agent_with_suffix("test-suffix");
        assert!(
            ua.contains("test-suffix"),
            "user agent should contain the suffix, got: {ua}"
        );
    }

    #[test]
    fn test_web_join_url_contains_path() {
        let result = web_join_url("https://example.com", "path");
        assert!(result.is_ok(), "expected Ok, got {:?}", result);
        assert!(result.unwrap().contains("/path"));
    }

    #[test]
    fn test_web_join_url_err_for_invalid_base() {
        let result = web_join_url("not a url", "path");
        assert!(result.is_err());
    }

    #[test]
    fn test_web_build_url_with_query_both_params() {
        let keys = vec!["a".to_string(), "b".to_string()];
        let values = vec!["1".to_string(), "2".to_string()];
        let result = web_build_url_with_query("https://example.com", &keys, &values);
        assert!(result.is_ok(), "expected Ok, got {:?}", result);
        let url = result.unwrap();
        assert!(url.contains("a=1"), "expected a=1 in {url}");
        assert!(url.contains("b=2"), "expected b=2 in {url}");
    }

    #[test]
    fn test_web_build_url_with_query_length_mismatch_returns_err() {
        let keys = vec!["only_one".to_string()];
        let values: Vec<String> = vec![];
        let result = web_build_url_with_query("https://example.com", &keys, &values);
        assert!(result.is_err(), "expected Err for mismatched vec lengths");
    }

    // ── ModSite helper tests ─────────────────────────────────────────────────

    #[test]
    fn test_mod_site_name_nexusmods() {
        let expected = CoreModSite::NexusMods.name();
        assert_eq!(mod_site_name(ffi::ModSite::NexusMods), expected);
    }

    #[test]
    fn test_mod_site_base_url_starts_with_https() {
        let url = mod_site_base_url(ffi::ModSite::NexusMods);
        assert!(url.starts_with("https://"), "expected https://, got: {url}");
    }

    #[test]
    fn test_mod_site_game_url_nexusmods_fallout4_nonempty() {
        let url = mod_site_game_url(ffi::ModSite::NexusMods, ffi::WebGameId::Fallout4);
        assert!(!url.is_empty());
    }

    #[test]
    fn test_mod_site_game_url_all_variants_matrix() {
        let sites = [
            ffi::ModSite::NexusMods,
            ffi::ModSite::BethesdaNet,
            ffi::ModSite::ModDB,
        ];
        let games = [
            ffi::WebGameId::Fallout4,
            ffi::WebGameId::Fallout4VR,
            ffi::WebGameId::Skyrim,
            ffi::WebGameId::Starfield,
        ];
        for site in sites {
            for game in games {
                let url = mod_site_game_url(site, game);
                assert!(
                    !url.is_empty(),
                    "mod_site_game_url returned empty string"
                );
            }
        }
    }

    #[test]
    fn test_mod_site_name_all_variants_nonempty() {
        for site in [
            ffi::ModSite::NexusMods,
            ffi::ModSite::BethesdaNet,
            ffi::ModSite::ModDB,
        ] {
            assert!(!mod_site_name(site).is_empty());
        }
    }

    #[test]
    fn test_mod_site_base_url_all_variants_nonempty_https() {
        for site in [
            ffi::ModSite::NexusMods,
            ffi::ModSite::BethesdaNet,
            ffi::ModSite::ModDB,
        ] {
            let url = mod_site_base_url(site);
            assert!(!url.is_empty());
            assert!(url.starts_with("https://"), "expected https://, got: {url}");
        }
    }
}
