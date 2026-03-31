//! Constants and enumeration bindings (classic-constants-core)
//!
//! Exposes Fallout4Version, YamlFile, and GameId enums plus lookup functions
//! to JavaScript/TypeScript.

use classic_constants_core::{Fallout4Version, GameId, YamlFile};

// ============================================================================
// JS Enum Definitions
// ============================================================================

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

/// YAML configuration file identifiers exposed to JavaScript.
#[napi(string_enum)]
pub enum JsYamlFile {
    /// CLASSIC Data/databases/CLASSIC Main.yaml
    Main,
    /// CLASSIC Settings.yaml
    Settings,
    /// CLASSIC Ignore.yaml
    Ignore,
    /// CLASSIC Data/databases/CLASSIC {Game}.yaml
    Game,
    /// CLASSIC Data/CLASSIC {Game} Local.yaml
    GameLocal,
    /// tests/test_settings.yaml (for testing only)
    Test,
    /// User config dir/CLASSIC/cache.yaml
    Cache,
}

/// Supported game identifiers exposed to JavaScript.
#[napi(string_enum)]
pub enum JsGameId {
    /// Fallout 4 (base game)
    Fallout4,
    /// Fallout 4 VR
    #[napi(value = "Fallout4VR")]
    Fallout4Vr,
    /// Skyrim Special Edition
    Skyrim,
    /// Starfield
    Starfield,
}

// ============================================================================
// Data Transfer Objects
// ============================================================================

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

// ============================================================================
// Internal Conversion Helpers
// ============================================================================

fn js_to_core_game_id(id: &JsGameId) -> GameId {
    match id {
        JsGameId::Fallout4 => GameId::Fallout4,
        JsGameId::Fallout4Vr => GameId::Fallout4VR,
        JsGameId::Skyrim => GameId::Skyrim,
        JsGameId::Starfield => GameId::Starfield,
    }
}

fn js_to_core_yaml_file(file: &JsYamlFile) -> YamlFile {
    match file {
        JsYamlFile::Main => YamlFile::Main,
        JsYamlFile::Settings => YamlFile::Settings,
        JsYamlFile::Ignore => YamlFile::Ignore,
        JsYamlFile::Game => YamlFile::Game,
        JsYamlFile::GameLocal => YamlFile::GameLocal,
        JsYamlFile::Test => YamlFile::Test,
        JsYamlFile::Cache => YamlFile::Cache,
    }
}

fn js_to_core_fo4_version(v: &JsFallout4Version) -> Fallout4Version {
    match v {
        JsFallout4Version::Original => Fallout4Version::Original,
        JsFallout4Version::NextGen => Fallout4Version::NextGen,
        JsFallout4Version::AnniversaryEdition => Fallout4Version::AnniversaryEdition,
        JsFallout4Version::Vr => Fallout4Version::Vr,
    }
}

fn core_to_js_game_id(id: &GameId) -> JsGameId {
    match id {
        GameId::Fallout4 => JsGameId::Fallout4,
        GameId::Fallout4VR => JsGameId::Fallout4Vr,
        GameId::Skyrim => JsGameId::Skyrim,
        GameId::Starfield => JsGameId::Starfield,
    }
}

fn core_to_js_yaml_file(file: &YamlFile) -> JsYamlFile {
    match file {
        YamlFile::Main => JsYamlFile::Main,
        YamlFile::Settings => JsYamlFile::Settings,
        YamlFile::Ignore => JsYamlFile::Ignore,
        YamlFile::Game => JsYamlFile::Game,
        YamlFile::GameLocal => JsYamlFile::GameLocal,
        YamlFile::Test => JsYamlFile::Test,
        YamlFile::Cache => JsYamlFile::Cache,
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
// Exported Functions
// ============================================================================

/// Get a human-readable name for a game identifier.
///
/// Returns names like "Fallout 4", "Fallout 4 VR", "Skyrim", "Starfield".
#[napi]
pub fn get_game_name(id: JsGameId) -> String {
    let core_id = js_to_core_game_id(&id);
    match core_id {
        GameId::Fallout4 => "Fallout 4".to_string(),
        GameId::Fallout4VR => "Fallout 4 VR".to_string(),
        GameId::Skyrim => "Skyrim".to_string(),
        GameId::Starfield => "Starfield".to_string(),
    }
}

/// Get a human-readable description for a YAML file type.
#[napi]
pub fn get_yaml_file_description(file: JsYamlFile) -> String {
    let core_file = js_to_core_yaml_file(&file);
    core_file.description().to_string()
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

/// Get all supported game identifiers.
#[napi]
pub fn get_all_game_ids() -> Vec<JsGameId> {
    GameId::all().iter().map(core_to_js_game_id).collect()
}

/// Get all YAML file type identifiers.
#[napi]
pub fn get_all_yaml_files() -> Vec<JsYamlFile> {
    YamlFile::all().iter().map(core_to_js_yaml_file).collect()
}

/// Get all Fallout 4 version variants.
#[napi]
pub fn get_all_fallout4_versions() -> Vec<JsFallout4Version> {
    Fallout4Version::all()
        .iter()
        .map(core_to_js_fo4_version)
        .collect()
}
