//! Version registry bindings (classic-version-registry-core)
//!
//! Exposes game version lookup, matching, and registry enumeration
//! to JavaScript/TypeScript.

use napi::bindgen_prelude::*;
use std::collections::{BTreeSet, HashMap};

use classic_version_registry_core::{
    Fallout4Version, GameVersion, MatchConfidence,
    get_version_registry as core_get_version_registry,
};

/// Convert any Display error to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Fallout 4 version variants exposed to JavaScript as string literals.
#[napi(string_enum)]
pub enum JsFallout4Version {
    /// Original pre-Next-Gen version (1.10.163)
    Original,
    /// Next-Gen update version (1.10.984)
    NextGen,
    /// Anniversary Edition version (1.11.137+)
    AnniversaryEdition,
    /// Virtual Reality version (1.2.72)
    #[napi(value = "VR")]
    Vr,
}

/// Version metadata for a Fallout 4 variant.
#[napi(object)]
pub struct Fallout4VersionInfo {
    /// Human-readable display name
    pub name: String,
    /// Steam App ID
    pub steam_id: u32,
    /// Whether this is a VR variant
    pub is_vr: bool,
    /// Game executable filename
    pub exe_name: String,
}

fn js_to_core_fo4_version(v: &JsFallout4Version) -> Fallout4Version {
    match v {
        JsFallout4Version::Original => Fallout4Version::Original,
        JsFallout4Version::NextGen => Fallout4Version::NextGen,
        JsFallout4Version::AnniversaryEdition => Fallout4Version::AnniversaryEdition,
        JsFallout4Version::Vr => Fallout4Version::Vr,
    }
}

fn core_to_js_fo4_version(v: &Fallout4Version) -> JsFallout4Version {
    match v {
        Fallout4Version::Original => JsFallout4Version::Original,
        Fallout4Version::NextGen => JsFallout4Version::NextGen,
        Fallout4Version::AnniversaryEdition => JsFallout4Version::AnniversaryEdition,
        Fallout4Version::Vr => JsFallout4Version::Vr,
    }
}

// ============================================================================
// Data Transfer Objects
// ============================================================================

/// Address Library configuration for a game version.
#[napi(object)]
pub struct JsAddressLibraryConfig {
    /// Filename of the Address Library file (e.g., "version-1-10-163-0.bin")
    pub filename: String,
    /// File format ("bin" or "csv")
    pub format: String,
    /// Nexus Mods download URL
    pub nexus_url: String,
}

/// Script Extender (XSE) configuration for a game version.
#[napi(object)]
pub struct JsXseConfig {
    /// XSE acronym (e.g., "F4SE", "F4SEVR")
    pub acronym: String,
    /// Full display name (e.g., "Fallout 4 Script Extender (F4SE)")
    pub full_name: String,
    /// Compatible XSE version string (e.g., "0.6.23")
    pub compatible_version: String,
    /// Loader executable name (e.g., "f4se_loader.exe")
    pub loader: String,
    /// Expected number of script files (e.g., 29)
    pub file_count: u32,
    /// Expected script hashes as [filename, sha256] pairs.
    pub script_hashes: Vec<(String, String)>,
}

/// Version range for compatibility matching.
#[napi(object)]
pub struct JsCompatibleRange {
    /// Minimum version string (inclusive)
    pub min_version: String,
    /// Maximum version string (inclusive)
    pub max_version: String,
}

/// Crash generator configuration for a specific version.
#[napi(object)]
pub struct JsCrashgenConfig {
    /// Version string of the crash generator (e.g., "1.28.6")
    pub version: String,
    /// Display name (e.g., "Buffout 4", "Buffout 4 NG")
    pub name: String,
    /// Short identifier/acronym (e.g., "BO4", "BO4 NG")
    pub acronym: String,
    /// DLL filename (e.g., "buffout4.dll")
    pub dll_file: String,
    /// Description of this crash generator version
    pub description: String,
    /// Nexus Mods or other download URL
    pub download_url: String,
    /// Whether this crash generator has a compatible range restriction
    pub has_compatible_range: bool,
}

/// Complete version information for a game version entry.
#[napi(object)]
pub struct JsVersionInfo {
    /// Unique identifier (e.g., "FO4_OG", "FO4_NG", "FO4_VR")
    pub id: String,
    /// Game identifier (e.g., "Fallout4")
    pub game: String,
    /// Whether this is a VR version
    pub is_vr: bool,
    /// The game version string (e.g., "1.10.163.0")
    pub version: String,
    /// Human-readable display name (e.g., "Fallout 4 Original")
    pub display_name: String,
    /// Short name for quick reference (e.g., "OG", "NG", "VR")
    pub short_name: String,
    /// Description of this version
    pub description: String,
    /// My Documents subfolder name (e.g., "Fallout4", "Fallout4VR")
    pub docs_name: String,
    /// Steam application ID (e.g., 377160, 611660)
    pub steam_id: u32,
    /// Address Library configuration, if applicable
    pub address_library: Option<JsAddressLibraryConfig>,
    /// Script Extender configuration, if applicable
    pub xse: Option<JsXseConfig>,
    /// Compatible range for this version, if present
    pub compatible_range: Option<JsCompatibleRange>,
    /// Priority for matching (higher = preferred)
    pub priority: i32,
    /// Whether this version is deprecated
    pub deprecated: bool,
    /// Known executable SHA-256 hash for this version, if available
    pub exe_hash: Option<String>,
}

/// Result of version matching.
#[napi(object)]
pub struct JsMatchResult {
    /// The matched version info, if found
    pub version_info: Option<JsVersionInfo>,
    /// Confidence level: "exact", "range", "nearest", "default", or "unknown"
    pub confidence: String,
    /// The originally detected version string
    pub detected: String,
    /// Human-readable message about the match
    pub message: String,
    /// Whether this is an exact match
    pub is_exact: bool,
    /// Whether the user should be warned about this match
    pub should_warn: bool,
    /// Whether this is a valid match (version_info is present and not Unknown)
    pub is_valid: bool,
}

/// Unknown-version handling policy from the version registry.
#[napi(object)]
pub struct JsUnknownVersionHandling {
    /// Strategy: "nearest_match", "strict", or "default_only"
    pub strategy: String,
    /// Log level for unknown-version messaging.
    pub log_level: String,
    /// Per-game default version IDs.
    pub defaults: HashMap<String, String>,
}

/// Snapshot of the current version registry for a game/mode filter.
#[napi(object)]
pub struct JsVersionRegistrySnapshot {
    /// Game identifier used for filtering.
    pub game: String,
    /// Optional VR filter used for selecting versions.
    pub is_vr: Option<bool>,
    /// Matching versions sorted by priority (descending).
    pub versions: Vec<JsVersionInfo>,
    /// Unknown-version strategy configuration currently loaded.
    pub unknown_version_handling: JsUnknownVersionHandling,
}

// ============================================================================
// Internal Conversion Helpers
// ============================================================================

/// Convert a core VersionInfo to a JS DTO.
fn core_version_info_to_js(info: &classic_version_registry_core::VersionInfo) -> JsVersionInfo {
    JsVersionInfo {
        id: info.id.clone(),
        game: info.game.clone(),
        is_vr: info.is_vr,
        version: info.version.to_string(),
        display_name: info.display_name.clone(),
        short_name: info.short_name.clone(),
        description: info.description.clone(),
        docs_name: info.docs_name.clone(),
        steam_id: info.steam_id,
        address_library: info
            .address_library
            .as_ref()
            .map(|al| JsAddressLibraryConfig {
                filename: al.filename.clone(),
                format: al.format.extension().to_string(),
                nexus_url: al.nexus_url.clone(),
            }),
        xse: info.xse.as_ref().map(|x| JsXseConfig {
            acronym: x.acronym.clone(),
            full_name: x.full_name.clone(),
            compatible_version: x.compatible_version.clone(),
            loader: x.loader.clone(),
            file_count: x.file_count,
            script_hashes: x.script_hashes.clone(),
        }),
        compatible_range: info
            .compatible_range
            .as_ref()
            .map(|range| JsCompatibleRange {
                min_version: range.min_version.to_string(),
                max_version: range.max_version.to_string(),
            }),
        priority: info.priority,
        deprecated: info.deprecated,
        exe_hash: info.exe_hash.clone(),
    }
}

/// Convert a core CrashgenConfig to a JS DTO.
fn core_crashgen_to_js(config: &classic_version_registry_core::CrashgenConfig) -> JsCrashgenConfig {
    JsCrashgenConfig {
        version: config.version.clone(),
        name: config.name.clone(),
        acronym: config.acronym.clone(),
        dll_file: config.dll_file.clone(),
        description: config.description.clone(),
        download_url: config.download_url.clone(),
        has_compatible_range: config.compatible_range.is_some(),
    }
}

/// Convert a MatchConfidence to a string.
fn confidence_to_string(confidence: &MatchConfidence) -> String {
    match confidence {
        MatchConfidence::Exact => "exact".to_string(),
        MatchConfidence::Range => "range".to_string(),
        MatchConfidence::Nearest => "nearest".to_string(),
        MatchConfidence::Default => "default".to_string(),
        MatchConfidence::Unknown => "unknown".to_string(),
    }
}

fn unknown_strategy_to_string(
    strategy: &classic_version_registry_core::UnknownVersionStrategy,
) -> String {
    match strategy {
        classic_version_registry_core::UnknownVersionStrategy::NearestMatch => {
            "nearest_match".to_string()
        }
        classic_version_registry_core::UnknownVersionStrategy::Strict => "strict".to_string(),
        classic_version_registry_core::UnknownVersionStrategy::DefaultOnly => {
            "default_only".to_string()
        }
    }
}

fn log_level_to_string(log_level: &classic_version_registry_core::LogLevel) -> String {
    match log_level {
        classic_version_registry_core::LogLevel::Debug => "debug".to_string(),
        classic_version_registry_core::LogLevel::Warning => "warning".to_string(),
        classic_version_registry_core::LogLevel::Error => "error".to_string(),
    }
}

// ============================================================================
// Exported Functions — Lookup
// ============================================================================

/// Get version info by its unique ID.
///
/// @param id - The version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR", "FO4_AE")
/// @returns The version info object, or null if not found.
#[napi]
pub fn get_version_by_id(id: String) -> Option<JsVersionInfo> {
    let registry = core_get_version_registry();
    registry.get_by_id(&id).map(core_version_info_to_js)
}

/// Get version metadata for a Fallout 4 variant.
///
/// Returns an object with `name`, `steamId`, `isVr`, and `exeName` fields.
#[napi]
pub fn get_fallout4_version_info(version: JsFallout4Version) -> Fallout4VersionInfo {
    let core_version = js_to_core_fo4_version(&version);
    Fallout4VersionInfo {
        name: core_version.display_name().to_string(),
        steam_id: core_version.steam_app_id(),
        is_vr: core_version.is_vr(),
        exe_name: core_version.exe_name().to_string(),
    }
}

/// Get all Fallout 4 version variants.
#[napi]
pub fn get_all_fallout4_versions() -> Vec<JsFallout4Version> {
    Fallout4Version::all()
        .iter()
        .map(core_to_js_fo4_version)
        .collect()
}

/// Get version info by exact version string.
///
/// @param version - The exact game version string (e.g., "1.10.163.0")
/// @returns The version info object, or null if not found.
/// @throws if the version string cannot be parsed.
#[napi]
pub fn get_version_by_version_string(version: String) -> Result<Option<JsVersionInfo>> {
    let game_version = GameVersion::parse(&version).map_err(to_napi_err)?;
    let registry = core_get_version_registry();
    Ok(registry
        .get_by_version(&game_version)
        .map(core_version_info_to_js))
}

/// Get version info by short name.
///
/// @param short_name - The short name (e.g., "OG", "NG", "VR", "AE")
/// @returns The version info object, or null if not found.
#[napi]
pub fn get_version_by_short_name(short_name: String) -> Option<JsVersionInfo> {
    let registry = core_get_version_registry();
    registry
        .get_by_short_name(&short_name)
        .map(core_version_info_to_js)
}

// ============================================================================
// Exported Functions — Enumeration
// ============================================================================

/// Get all registered versions, sorted by priority (descending).
///
/// @returns Array of version info objects.
#[napi]
pub fn get_all_versions() -> Vec<JsVersionInfo> {
    let registry = core_get_version_registry();
    registry
        .get_all()
        .iter()
        .map(|v| core_version_info_to_js(v))
        .collect()
}

/// Get all versions for a specific game.
///
/// @param game - Game identifier (e.g., "Fallout4")
/// @param is_vr - Optional VR filter. If omitted, returns all versions for the game.
/// @returns Array of matching version info objects, sorted by priority (descending).
#[napi]
pub fn get_all_versions_for_game(game: String, is_vr: Option<bool>) -> Vec<JsVersionInfo> {
    let registry = core_get_version_registry();
    registry
        .get_all_for_game(&game, is_vr)
        .iter()
        .map(|v| core_version_info_to_js(v))
        .collect()
}

/// Get correct versions for a mode (VR or non-VR).
///
/// @param is_vr - Whether VR mode is active.
/// @returns Array of version info objects matching the specified mode.
#[napi]
pub fn get_correct_versions(is_vr: bool) -> Vec<JsVersionInfo> {
    let registry = core_get_version_registry();
    registry
        .get_correct_versions(is_vr)
        .iter()
        .map(|v| core_version_info_to_js(v))
        .collect()
}

/// Get wrong versions for a mode (opposite of is_vr).
///
/// @param is_vr - Whether VR mode is active.
/// @returns Array of version info objects that do NOT match the specified mode.
#[napi]
pub fn get_wrong_versions(is_vr: bool) -> Vec<JsVersionInfo> {
    let registry = core_get_version_registry();
    registry
        .get_wrong_versions(is_vr)
        .iter()
        .map(|v| core_version_info_to_js(v))
        .collect()
}

/// Get a filtered snapshot of the version registry.
///
/// @param game - Optional game identifier (defaults to "Fallout4")
/// @param is_vr - Optional VR filter. If omitted, includes all versions for the game.
/// @returns Snapshot with selected versions and unknown-version handling config.
#[napi]
pub fn get_version_registry(
    game: Option<String>,
    is_vr: Option<bool>,
) -> JsVersionRegistrySnapshot {
    let game = game.unwrap_or_else(|| "Fallout4".to_string());
    let registry = core_get_version_registry();
    let versions = registry
        .get_all_for_game(&game, is_vr)
        .iter()
        .map(|v| core_version_info_to_js(v))
        .collect();
    let unknown = registry.unknown_version_handling();

    JsVersionRegistrySnapshot {
        game,
        is_vr,
        versions,
        unknown_version_handling: JsUnknownVersionHandling {
            strategy: unknown_strategy_to_string(&unknown.strategy),
            log_level: log_level_to_string(&unknown.log_level),
            defaults: unknown.defaults.clone(),
        },
    }
}

// ============================================================================
// Exported Functions — Matching
// ============================================================================

/// Match a detected version to the nearest known version in the registry.
///
/// Uses intelligent matching with fallback:
/// 1. Exact match
/// 2. Compatible range match
/// 3. Nearest match (same major version)
/// 4. Default fallback
///
/// @param version - The detected game version string (e.g., "1.10.163.0")
/// @param game - Game identifier (e.g., "Fallout4")
/// @param is_vr - Whether VR mode is active
/// @returns A match result with version info, confidence, and message.
/// @throws if the version string cannot be parsed.
#[napi]
pub fn match_version(version: String, game: String, is_vr: bool) -> Result<JsMatchResult> {
    let detected = GameVersion::parse(&version).map_err(to_napi_err)?;
    let registry = core_get_version_registry();
    let result = registry.match_version(&detected, &game, is_vr);

    Ok(JsMatchResult {
        version_info: result.version_info.as_ref().map(core_version_info_to_js),
        confidence: confidence_to_string(&result.confidence),
        detected: result.detected.to_string(),
        message: result.message.clone(),
        is_exact: result.is_exact(),
        should_warn: result.should_warn(),
        is_valid: result.is_valid(),
    })
}

/// Get the Address Library filename for a game version.
///
/// @param version - The game version string (e.g., "1.10.163.0")
/// @param is_vr - Whether VR mode is active
/// @returns The Address Library filename, or null if not found.
/// @throws if the version string cannot be parsed.
#[napi]
pub fn get_address_library_filename(version: String, is_vr: bool) -> Result<Option<String>> {
    let game_version = GameVersion::parse(&version).map_err(to_napi_err)?;
    let registry = core_get_version_registry();
    Ok(registry.get_address_library_filename(&game_version, is_vr))
}

// ============================================================================
// Exported Functions — Crashgen
// ============================================================================

/// Get all crash generator configurations for a version ID.
///
/// @param id - The version ID (e.g., "FO4_OG", "FO4_NG")
/// @returns Array of crash generator config objects. Empty array if version ID not found.
#[napi]
pub fn get_crashgen_versions(id: String) -> Vec<JsCrashgenConfig> {
    let registry = core_get_version_registry();
    registry
        .get_crashgen_versions(&id)
        .iter()
        .map(|c| core_crashgen_to_js(c))
        .collect()
}

/// Get crash generator versions as simple version strings for a version ID.
///
/// @param id - The version ID (e.g., "FO4_OG", "FO4_NG")
/// @returns Array of version strings. Empty array if version ID not found.
#[napi]
pub fn get_crashgen_version_strings(id: String) -> Vec<String> {
    let registry = core_get_version_registry();
    registry
        .get_crashgen_version_strings(&id)
        .iter()
        .map(|s| s.to_string())
        .collect()
}

/// Get a specific crash generator configuration by version ID and crashgen version.
///
/// @param id - The version ID (e.g., "FO4_OG")
/// @param crashgen_version - The crash generator version string (e.g., "1.28.6")
/// @returns The crash generator config, or null if not found.
#[napi]
pub fn get_crashgen_for_version(id: String, crashgen_version: String) -> Option<JsCrashgenConfig> {
    let registry = core_get_version_registry();
    registry
        .get_crashgen_for_version(&id, &crashgen_version)
        .map(core_crashgen_to_js)
}

/// Get all known executable hashes for the selected game/mode.
///
/// @param game - Optional game identifier (defaults to "Fallout4")
/// @param is_vr - Optional VR filter (if omitted, includes all game modes)
/// @returns Unique executable SHA-256 hashes.
#[napi]
pub fn get_all_exe_hashes(game: Option<String>, is_vr: Option<bool>) -> Vec<String> {
    let game = game.unwrap_or_else(|| "Fallout4".to_string());
    let registry = core_get_version_registry();

    let mut hashes: BTreeSet<String> = BTreeSet::new();
    for version in registry.get_all_for_game(&game, is_vr) {
        if let Some(exe_hash) = &version.exe_hash {
            hashes.insert(exe_hash.clone());
        }
    }

    hashes.into_iter().collect()
}

/// Get all known script hashes grouped by script filename.
///
/// @param game - Optional game identifier (defaults to "Fallout4")
/// @param is_vr - Optional VR filter (if omitted, includes all game modes)
/// @returns Map of script filename to unique SHA-256 hashes.
#[napi]
pub fn get_all_script_hashes(
    game: Option<String>,
    is_vr: Option<bool>,
) -> HashMap<String, Vec<String>> {
    let game = game.unwrap_or_else(|| "Fallout4".to_string());
    let registry = core_get_version_registry();

    let mut aggregate: HashMap<String, BTreeSet<String>> = HashMap::new();
    for version in registry.get_all_for_game(&game, is_vr) {
        if let Some(xse) = &version.xse {
            for (script_name, hash_val) in &xse.script_hashes {
                aggregate
                    .entry(script_name.clone())
                    .or_default()
                    .insert(hash_val.clone());
            }
        }
    }

    aggregate
        .into_iter()
        .map(|(script_name, hashes)| (script_name, hashes.into_iter().collect()))
        .collect()
}

/// Get script hashes for a specific version ID.
///
/// @param id - The version ID (e.g., "FO4_OG")
/// @returns Map of script filename to SHA-256 hash for that version.
#[napi]
pub fn get_script_hashes_for_version(id: String) -> HashMap<String, String> {
    let registry = core_get_version_registry();
    registry
        .get_by_id(&id)
        .and_then(|version| version.xse.as_ref())
        .map(|xse| xse.script_hashes.iter().cloned().collect())
        .unwrap_or_default()
}

/// Get unknown-version handling configuration.
#[napi]
pub fn get_unknown_version_handling() -> JsUnknownVersionHandling {
    let registry = core_get_version_registry();
    let handling = registry.unknown_version_handling();
    JsUnknownVersionHandling {
        strategy: unknown_strategy_to_string(&handling.strategy),
        log_level: log_level_to_string(&handling.log_level),
        defaults: handling.defaults.clone(),
    }
}

/// Get the default version ID used for unknown versions for a game.
///
/// @param game - Game identifier (e.g., "Fallout4")
/// @returns Default version ID or null if not configured.
#[napi]
pub fn get_unknown_version_default(game: String) -> Option<String> {
    let registry = core_get_version_registry();
    registry
        .unknown_version_handling()
        .get_default(&game)
        .map(String::from)
}

// ============================================================================
// Exported Functions — Version Compatibility
// ============================================================================

/// Check if a detected version is compatible with a specific version entry.
///
/// Uses the compatible_range if defined, otherwise requires exact match.
///
/// @param id - The version ID to check against (e.g., "FO4_OG")
/// @param version - The detected version string to check
/// @returns True if compatible, false if not or if the version ID is not found.
/// @throws if the version string cannot be parsed.
#[napi]
pub fn is_version_compatible(id: String, version: String) -> Result<bool> {
    let detected = GameVersion::parse(&version).map_err(to_napi_err)?;
    let registry = core_get_version_registry();
    Ok(registry
        .get_by_id(&id)
        .is_some_and(|info| info.is_compatible_with(&detected)))
}

/// Parse a 4-component game version string and return it normalized.
///
/// Accepts 3-component ("1.10.163") or 4-component ("1.10.163.0") versions.
/// If only 3 components are provided, build defaults to 0.
///
/// @param version - The version string to parse
/// @returns The normalized version string (always 4 components)
/// @throws if the version string is invalid.
#[napi]
pub fn parse_game_version(version: String) -> Result<String> {
    let parsed = GameVersion::parse(&version).map_err(to_napi_err)?;
    Ok(parsed.to_string())
}

/// Calculate the semantic distance between two game version strings.
///
/// Uses a weighted formula: major x1,000,000 + minor x1,000 + patch x1.
/// Build differences are not included.
///
/// @param a - First version string
/// @param b - Second version string
/// @returns The semantic distance as a number.
/// @throws if either version string is invalid.
#[napi]
pub fn game_version_distance(a: String, b: String) -> Result<f64> {
    let va = GameVersion::parse(&a).map_err(to_napi_err)?;
    let vb = GameVersion::parse(&b).map_err(to_napi_err)?;
    Ok(va.semantic_distance(&vb) as f64)
}
