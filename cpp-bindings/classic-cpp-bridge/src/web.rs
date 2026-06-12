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
//! `classic::shared::GameId` but is a separate CXX type. C++ callers
//! that have a `classic::shared::GameId` value translate via the value
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

use classic_shared_core::GameId as CoreGameId;
use classic_web_core::{
    ModSite as CoreModSite, build_url_with_query as core_build_url_with_query,
    extract_domain as core_extract_domain, get_user_agent as core_get_user_agent,
    get_user_agent_with_suffix as core_get_user_agent_with_suffix,
    is_valid_url as core_is_valid_url, join_url as core_join_url,
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
    /// Mirrors `classic_shared_core::GameId` exactly (same repr(u8) discriminants).
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
#[path = "web_tests.rs"]
mod tests;
