//! Web/URL utility bindings (classic-web-core)
//!
//! Exposes URL validation, user agent generation, mod site constants,
//! and URL building utilities to JavaScript/TypeScript.

use crate::shared::JsGameId;
use classic_shared_core::GameId;
use classic_web_core::ModSite;
use napi::bindgen_prelude::*;

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Convert a JsGameId to the core GameId.
fn js_game_id_to_core(id: &JsGameId) -> GameId {
    match id {
        JsGameId::Fallout4 => GameId::Fallout4,
        JsGameId::Fallout4Vr => GameId::Fallout4VR,
        JsGameId::Skyrim => GameId::Skyrim,
        JsGameId::Starfield => GameId::Starfield,
    }
}

// ============================================================================
// Mod Site Enumeration
// ============================================================================

/// Mod site identifiers exposed to JavaScript as string literals.
#[napi(string_enum)]
pub enum JsModSite {
    /// Nexus Mods
    NexusMods,
    /// Bethesda.net
    BethesdaNet,
    /// ModDB
    #[napi(value = "ModDB")]
    ModDb,
}

/// Convert a JsModSite to the core ModSite.
fn js_mod_site_to_core(site: &JsModSite) -> ModSite {
    match site {
        JsModSite::NexusMods => ModSite::NexusMods,
        JsModSite::BethesdaNet => ModSite::BethesdaNet,
        JsModSite::ModDb => ModSite::ModDB,
    }
}

// ============================================================================
// Mod Site Functions
// ============================================================================

/// Get the base URL for a mod site.
///
/// @param site - The mod site identifier.
/// @returns The base URL string (e.g., "https://www.nexusmods.com").
#[napi]
pub fn get_mod_site_url(site: JsModSite) -> String {
    js_mod_site_to_core(&site).base_url().to_string()
}

/// Get the human-readable name of a mod site.
///
/// @param site - The mod site identifier.
/// @returns The display name (e.g., "Nexus Mods").
#[napi]
pub fn get_mod_site_name(site: JsModSite) -> String {
    js_mod_site_to_core(&site).name().to_string()
}

/// Get the mod page URL for a specific game on a mod site.
///
/// @param site - The mod site identifier.
/// @param gameId - The game identifier.
/// @returns The full URL for the game's mod page.
#[napi]
pub fn get_mod_site_game_url(site: JsModSite, game_id: JsGameId) -> String {
    let core_site = js_mod_site_to_core(&site);
    let core_game = js_game_id_to_core(&game_id);
    core_site.game_url(core_game)
}

// ============================================================================
// User Agent
// ============================================================================

/// Get the default CLASSIC user agent string.
///
/// @returns A user agent string like "CLASSIC/8.0.0".
#[napi]
pub fn get_user_agent() -> String {
    classic_web_core::get_user_agent()
}

/// Get a CLASSIC user agent string with a custom suffix.
///
/// @param suffix - Additional information to append (e.g., "Windows").
/// @returns A user agent string like "CLASSIC/8.0.0 (Windows)".
#[napi]
pub fn get_user_agent_with_suffix(suffix: String) -> String {
    classic_web_core::get_user_agent_with_suffix(&suffix)
}

// ============================================================================
// URL Validation
// ============================================================================

/// Validate and parse a URL string.
///
/// Checks that the URL is well-formed and uses http or https scheme.
///
/// @param urlStr - The URL string to validate.
/// @returns The validated, normalized URL string.
/// @throws If the URL is invalid or uses a non-http(s) scheme.
#[napi]
pub fn validate_url(url_str: String) -> Result<String> {
    classic_web_core::validate_url(&url_str)
        .map(|url| url.to_string())
        .map_err(to_napi_err)
}

/// Check if a URL string is valid (non-throwing).
///
/// @param urlStr - The URL string to check.
/// @returns True if the URL is valid and uses http/https, false otherwise.
#[napi]
pub fn is_valid_url(url_str: String) -> bool {
    classic_web_core::is_valid_url(&url_str)
}

/// Extract the domain from a URL.
///
/// @param urlStr - The URL string to extract the domain from.
/// @returns The domain name (e.g., "www.nexusmods.com").
/// @throws If the URL is invalid or has no host.
#[napi]
pub fn extract_domain(url_str: String) -> Result<String> {
    classic_web_core::extract_domain(&url_str).map_err(to_napi_err)
}

// ============================================================================
// URL Building
// ============================================================================

/// Join a base URL with a path.
///
/// @param base - The base URL (must be valid http/https).
/// @param path - The path to append.
/// @returns The joined URL string.
/// @throws If the base URL is invalid or joining fails.
#[napi]
pub fn join_url(base: String, path: String) -> Result<String> {
    classic_web_core::join_url(&base, &path).map_err(to_napi_err)
}

/// Query parameter key-value pair for URL building.
#[napi(object)]
pub struct QueryParam {
    /// The parameter key.
    pub key: String,
    /// The parameter value.
    pub value: String,
}

/// Build a URL with query parameters.
///
/// @param base - The base URL (must be valid http/https).
/// @param params - Array of { key, value } objects for query parameters.
/// @returns The URL with query parameters appended.
/// @throws If the base URL is invalid.
#[napi]
pub fn build_url_with_query(base: String, params: Vec<QueryParam>) -> Result<String> {
    let param_refs: Vec<(&str, &str)> = params
        .iter()
        .map(|p| (p.key.as_str(), p.value.as_str()))
        .collect();

    classic_web_core::build_url_with_query(&base, &param_refs).map_err(to_napi_err)
}

// ============================================================================
// Constants
// ============================================================================

/// Get the CLASSIC version string used in user agent headers.
///
/// @returns The version string (e.g., "8.0.0").
#[napi]
pub fn get_classic_version() -> String {
    classic_web_core::CLASSIC_VERSION.to_string()
}

/// Get the user agent prefix string.
///
/// @returns The prefix string (e.g., "CLASSIC").
#[napi]
pub fn get_user_agent_prefix() -> String {
    classic_web_core::USER_AGENT_PREFIX.to_string()
}
