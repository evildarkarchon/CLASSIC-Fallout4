//! Script Extender (XSE) bindings (classic-xse-core)
//!
//! Exposes XSE detection and version checking functions
//! to JavaScript/TypeScript.

use crate::constants::JsGameId;
use classic_constants_core::GameId;
use classic_xse_core::XseType;
use napi::bindgen_prelude::*;
use std::path::PathBuf;

/// Convert any Display error to a napi::Error.
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

// ============================================================================
// Internal Conversion Helpers
// ============================================================================

/// Convert a JsGameId to the core GameId.
fn js_game_id_to_core(id: &JsGameId) -> GameId {
    match id {
        JsGameId::Fallout4 => GameId::Fallout4,
        JsGameId::Fallout4Vr => GameId::Fallout4VR,
        JsGameId::Skyrim => GameId::Skyrim,
        JsGameId::Starfield => GameId::Starfield,
    }
}

/// Convert a core XseType to a JsXseType.
fn core_to_js_xse_type(xse_type: XseType) -> JsXseType {
    match xse_type {
        XseType::F4SE => JsXseType::F4se,
        XseType::F4SEVR => JsXseType::F4sevr,
        XseType::SKSE => JsXseType::Skse,
        XseType::SKSE64 => JsXseType::Skse64,
        XseType::SKSEVR => JsXseType::Sksevr,
        XseType::SFSE => JsXseType::Sfse,
    }
}

/// Convert a JsXseType to the core XseType.
fn js_to_core_xse_type(js_type: &JsXseType) -> XseType {
    match js_type {
        JsXseType::F4se => XseType::F4SE,
        JsXseType::F4sevr => XseType::F4SEVR,
        JsXseType::Skse => XseType::SKSE,
        JsXseType::Skse64 => XseType::SKSE64,
        JsXseType::Sksevr => XseType::SKSEVR,
        JsXseType::Sfse => XseType::SFSE,
    }
}

// ============================================================================
// XSE Type Enumeration
// ============================================================================

/// Script Extender type identifiers exposed to JavaScript as string literals.
#[napi(string_enum)]
pub enum JsXseType {
    /// Fallout 4 Script Extender
    #[napi(value = "F4SE")]
    F4se,
    /// Fallout 4 VR Script Extender
    #[napi(value = "F4SEVR")]
    F4sevr,
    /// Skyrim Script Extender (Classic)
    #[napi(value = "SKSE")]
    Skse,
    /// Skyrim Special Edition Script Extender
    #[napi(value = "SKSE64")]
    Skse64,
    /// Skyrim VR Script Extender
    #[napi(value = "SKSEVR")]
    Sksevr,
    /// Starfield Script Extender
    #[napi(value = "SFSE")]
    Sfse,
}

// ============================================================================
// XSE Info DTO
// ============================================================================

/// XSE installation information returned from `getXseInfo`.
#[napi(object)]
pub struct JsXseInfo {
    /// The XSE type identifier (e.g., "F4SE", "SKSE64").
    pub xse_type: String,
    /// The installation path.
    pub path: String,
    /// The detected version string (e.g., "0.6.23"), or undefined if not detected.
    pub version: Option<String>,
    /// Whether the XSE loader executable was found.
    pub installed: bool,
    /// The full path to the loader executable.
    pub loader_path: String,
}

// ============================================================================
// XSE Type Functions
// ============================================================================

/// Parse an XSE type from a string (case-insensitive).
///
/// @param typeName - The XSE type name (e.g., "f4se", "SKSE64", "sfse").
/// @returns The corresponding XSE type string literal.
/// @throws If the type name is not recognized.
#[napi]
pub fn parse_xse_type(type_name: String) -> Result<JsXseType> {
    type_name
        .parse::<XseType>()
        .map(core_to_js_xse_type)
        .map_err(to_napi_err)
}

/// Get the XSE type for a given game identifier.
///
/// @param gameId - The game identifier.
/// @returns The corresponding XSE type string literal.
#[napi]
pub fn xse_type_for_game(game_id: JsGameId) -> JsXseType {
    let core_game = js_game_id_to_core(&game_id);
    core_to_js_xse_type(XseType::from_game_id(core_game))
}

/// Get the display name of an XSE type (e.g., "F4SE", "SKSE64").
///
/// @param xseType - The XSE type identifier.
/// @returns The XSE type name string.
#[napi]
pub fn xse_type_name(xse_type: JsXseType) -> String {
    js_to_core_xse_type(&xse_type).as_str().to_string()
}

/// Get the loader executable name for an XSE type.
///
/// @param xseType - The XSE type identifier.
/// @returns The loader filename (e.g., "f4se_loader.exe").
#[napi]
pub fn xse_loader_name(xse_type: JsXseType) -> String {
    js_to_core_xse_type(&xse_type).loader_name().to_string()
}

/// Get the DLL prefix for an XSE type.
///
/// @param xseType - The XSE type identifier.
/// @returns The DLL prefix string (e.g., "f4se_").
#[napi]
pub fn xse_dll_prefix(xse_type: JsXseType) -> String {
    js_to_core_xse_type(&xse_type).dll_prefix().to_string()
}

// ============================================================================
// XSE Detection Functions
// ============================================================================

/// Check if a Script Extender is installed in a game directory.
///
/// Checks for the presence of the XSE loader executable.
///
/// @param gamePath - The game installation directory.
/// @param xseType - The XSE type to check for.
/// @returns True if the XSE loader exists.
#[napi]
pub fn is_xse_installed(game_path: String, xse_type: JsXseType) -> bool {
    classic_xse_core::is_xse_installed(&PathBuf::from(game_path), js_to_core_xse_type(&xse_type))
}

/// Detect the XSE version from a loader executable path.
///
/// Scans the directory for version-specific DLL files to determine the version.
///
/// @param loaderPath - Path to the XSE loader executable.
/// @param xseType - The XSE type to detect.
/// @returns The detected version string (e.g., "0.6.23"), or null if detection fails.
#[napi]
pub fn detect_xse_version(loader_path: String, xse_type: JsXseType) -> Option<String> {
    classic_xse_core::detect_xse_version(
        &PathBuf::from(loader_path),
        js_to_core_xse_type(&xse_type),
    )
    .ok()
    .map(|v| v.to_string())
}

/// Get comprehensive XSE information for a game directory.
///
/// Checks installation status, detects version, and returns full info.
///
/// @param gamePath - The game installation directory.
/// @param xseType - The XSE type to check.
/// @returns An object with xseType, path, version, installed, and loaderPath fields.
#[napi]
pub fn get_xse_info(game_path: String, xse_type: JsXseType) -> JsXseInfo {
    let core_type = js_to_core_xse_type(&xse_type);
    let info = classic_xse_core::get_xse_info(&PathBuf::from(&game_path), core_type);

    JsXseInfo {
        xse_type: info.xse_type.as_str().to_string(),
        path: info.path.to_string_lossy().to_string(),
        version: info.version.as_ref().map(|v| v.to_string()),
        installed: info.installed,
        loader_path: info.loader_path().to_string_lossy().to_string(),
    }
}
