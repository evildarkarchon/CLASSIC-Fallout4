//! Version registry singleton.
//!
//! This module provides the main `VersionRegistry` type that manages game version
//! metadata. It implements a thread-safe singleton pattern using `OnceLock` and
//! supports loading from YAML with fallback to hardcoded defaults.

use std::collections::HashMap;
use std::path::Path;
use std::sync::OnceLock;

use classic_yaml_core::YamlOperations;

use crate::defaults;
use crate::matching::{MatchResult, VersionMatcher};
use crate::models::{
    AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel, UnknownVersionHandling,
    UnknownVersionStrategy, VersionInfo, XseConfig,
};
use crate::{GameVersion, VersionRegistryError};

/// Global singleton registry instance.
static REGISTRY: OnceLock<VersionRegistry> = OnceLock::new();

/// Thread-safe version registry for game version metadata.
///
/// The registry is implemented as a singleton that is automatically
/// initialized on first access. It loads version data from YAML
/// configuration, falling back to hardcoded defaults if loading fails.
///
/// # Usage
///
/// ```rust,no_run
/// use classic_version_registry_core::get_version_registry;
///
/// let registry = get_version_registry();
/// if let Some(og) = registry.get_by_id("FO4_OG") {
///     println!("OG version: {}", og.version);
/// }
/// ```
pub struct VersionRegistry {
    /// Version info indexed by ID.
    versions: HashMap<String, VersionInfo>,
    /// Version info indexed by version string.
    by_version: HashMap<String, VersionInfo>,
    /// Configuration for handling unknown versions.
    unknown_handling: UnknownVersionHandling,
}

impl VersionRegistry {
    /// Get the singleton registry instance.
    ///
    /// The registry is automatically initialized on first access.
    /// This is thread-safe and guaranteed to return the same instance.
    ///
    /// # Panics
    ///
    /// This function should not panic under normal circumstances.
    /// If initialization fails, it falls back to hardcoded defaults.
    #[must_use]
    pub fn get_instance() -> &'static Self {
        REGISTRY.get_or_init(Self::initialize)
    }

    /// Initialize the registry, loading from YAML or using defaults.
    fn initialize() -> Self {
        // Try to find and load YAML configuration
        if let Ok(registry) = Self::try_load_from_yaml() {
            return registry;
        }

        // Fall back to hardcoded defaults
        Self::load_defaults()
    }

    /// Try to load the registry from YAML configuration.
    fn try_load_from_yaml() -> Result<Self, VersionRegistryError> {
        // Try common locations for CLASSIC Main.yaml
        let possible_paths = [
            "CLASSIC Data/databases/CLASSIC Main.yaml",
            "databases/CLASSIC Main.yaml",
            "CLASSIC Main.yaml",
        ];

        for path_str in &possible_paths {
            let path = Path::new(path_str);
            if path.exists() {
                if let Ok(registry) = Self::load_from_yaml(path) {
                    return Ok(registry);
                }
            }
        }

        Err(VersionRegistryError::NotFound(
            "CLASSIC Main.yaml not found".to_string(),
        ))
    }

    /// Load the registry from a YAML file.
    fn load_from_yaml(yaml_path: &Path) -> Result<Self, VersionRegistryError> {
        let yaml_ops = YamlOperations::new();
        let yaml = yaml_ops.load_yaml_file(yaml_path)?;

        // Try to get Version_Registry.versions
        let versions_yaml = yaml_ops
            .get_setting(&yaml, "Version_Registry.versions")
            .ok_or_else(|| {
                VersionRegistryError::NotFound("Version_Registry.versions not found".to_string())
            })?;

        // Parse versions array
        let versions_array = match &versions_yaml {
            yaml_rust2::Yaml::Array(arr) => arr,
            _ => {
                return Err(VersionRegistryError::InvalidConfig(
                    "Version_Registry.versions is not an array".to_string(),
                ));
            }
        };

        if versions_array.is_empty() {
            return Err(VersionRegistryError::NotFound(
                "Version_Registry.versions is empty".to_string(),
            ));
        }

        let mut versions = HashMap::new();
        let mut by_version = HashMap::new();

        for v_yaml in versions_array {
            if let Ok(version_info) = Self::parse_version_yaml(v_yaml) {
                by_version.insert(version_info.version_string(), version_info.clone());
                versions.insert(version_info.id.clone(), version_info);
            }
        }

        if versions.is_empty() {
            return Err(VersionRegistryError::NotFound(
                "No valid versions parsed from YAML".to_string(),
            ));
        }

        // Load unknown version handling
        let unknown_handling = if let Some(handling_yaml) =
            yaml_ops.get_setting(&yaml, "Version_Registry.unknown_version_handling")
        {
            Self::parse_unknown_handling_yaml(&handling_yaml)
        } else {
            defaults::get_default_unknown_handling()
        };

        Ok(Self {
            versions,
            by_version,
            unknown_handling,
        })
    }

    /// Parse a single version entry from YAML.
    fn parse_version_yaml(yaml: &yaml_rust2::Yaml) -> Result<VersionInfo, VersionRegistryError> {
        let yaml_ops = YamlOperations::new();

        let id = yaml_ops.get_string_value(yaml, "id", "");
        if id.is_empty() {
            return Err(VersionRegistryError::InvalidConfig(
                "Version entry missing 'id' field".to_string(),
            ));
        }

        let version_str = yaml_ops.get_string_value(yaml, "version", "");
        let version = GameVersion::parse(&version_str)?;

        // Parse address library config
        let address_library = yaml_ops
            .get_setting(yaml, "address_library")
            .map(|al_yaml| {
                AddressLibraryConfig::new(
                    yaml_ops.get_string_value(&al_yaml, "filename", ""),
                    yaml_ops
                        .get_string_value(&al_yaml, "format", "bin")
                        .parse()
                        .unwrap(),
                    yaml_ops.get_string_value(&al_yaml, "nexus_url", ""),
                )
            });

        // Parse XSE config
        let xse = yaml_ops.get_setting(yaml, "xse").map(|xse_yaml| {
            let acronym = yaml_ops.get_string_value(&xse_yaml, "acronym", "");
            let compatible_version = yaml_ops.get_string_value(&xse_yaml, "compatible_version", "");
            let loader = yaml_ops.get_string_value(&xse_yaml, "loader", "");

            // Parse script_hashes as a map of filename -> hash
            let script_hashes: Vec<(String, String)> = yaml_ops
                .get_hashmap_value(&xse_yaml, "script_hashes")
                .into_iter()
                .filter(|(_, v)| !v.is_empty())
                .collect();

            let full_name = yaml_ops.get_string_value(&xse_yaml, "full_name", "");
            let file_count = yaml_ops
                .get_setting(&xse_yaml, "file_count")
                .and_then(|v| v.as_i64())
                .map(|v| v as u32)
                .unwrap_or(0);

            XseConfig::with_script_hashes(acronym, full_name, compatible_version, loader, file_count, script_hashes)
        });

        // Parse compatible range
        let compatible_range = if let Some(cr_yaml) = yaml_ops.get_setting(yaml, "compatible_range")
        {
            let min_str = yaml_ops.get_string_value(&cr_yaml, "min", "");
            let max_str = yaml_ops.get_string_value(&cr_yaml, "max", "");
            CompatibleRange::from_strings(&min_str, &max_str).ok()
        } else {
            None
        };

        // Parse priority (with default of 100)
        let priority = yaml_ops
            .get_setting(yaml, "priority")
            .and_then(|p| p.as_i64())
            .map(|p| p as i32)
            .unwrap_or(100);

        // Parse is_vr boolean
        let is_vr = yaml_ops
            .get_setting(yaml, "is_vr")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        // Parse deprecated boolean
        let deprecated = yaml_ops
            .get_setting(yaml, "deprecated")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        // Parse exe_hash
        let exe_hash = yaml_ops
            .get_setting(yaml, "exe_hash")
            .and_then(|v| v.as_str().map(String::from))
            .filter(|s| !s.is_empty());

        // Parse crashgen_versions (supports both simple strings and structured format)
        let crashgen_versions = Self::parse_crashgen_versions_yaml(yaml, &yaml_ops);

        Ok(VersionInfo {
            id,
            game: yaml_ops.get_string_value(yaml, "game", "Fallout4"),
            is_vr,
            version,
            display_name: yaml_ops.get_string_value(yaml, "display_name", ""),
            short_name: yaml_ops.get_string_value(yaml, "short_name", ""),
            description: yaml_ops.get_string_value(yaml, "description", ""),
            docs_name: yaml_ops.get_string_value(yaml, "docs_name", ""),
            steam_id: yaml_ops
                .get_setting(yaml, "steam_id")
                .and_then(|v| v.as_i64())
                .map(|v| v as u32)
                .unwrap_or(0),
            address_library,
            xse,
            compatible_range,
            priority,
            deprecated,
            exe_hash,
            crashgen_versions,
        })
    }

    /// Parse crashgen_versions from YAML.
    ///
    /// Supports two formats:
    /// 1. Simple string list: `["1.28.6", "1.37.0"]`
    /// 2. Structured format: `[{ version: "1.28.6", name: "Buffout 4", ... }]`
    fn parse_crashgen_versions_yaml(
        yaml: &yaml_rust2::Yaml,
        yaml_ops: &YamlOperations,
    ) -> Vec<CrashgenConfig> {
        let crashgen_yaml = match yaml_ops.get_setting(yaml, "crashgen_versions") {
            Some(v) => v,
            None => return Vec::new(),
        };

        let array = match &crashgen_yaml {
            yaml_rust2::Yaml::Array(arr) => arr,
            _ => return Vec::new(),
        };

        array
            .iter()
            .filter_map(|item| Self::parse_single_crashgen_yaml(item, yaml_ops))
            .collect()
    }

    /// Parse a single crashgen entry (either string or structured).
    fn parse_single_crashgen_yaml(
        yaml: &yaml_rust2::Yaml,
        yaml_ops: &YamlOperations,
    ) -> Option<CrashgenConfig> {
        match yaml {
            // Simple string format: "1.28.6"
            yaml_rust2::Yaml::String(version) => {
                Some(CrashgenConfig::from_version_string(version.clone()))
            }
            // Structured format: { version: "1.28.6", name: "Buffout 4", ... }
            yaml_rust2::Yaml::Hash(_) => {
                let version = yaml_ops.get_string_value(yaml, "version", "");
                if version.is_empty() {
                    return None;
                }

                let name = yaml_ops.get_string_value(yaml, "name", "");
                let acronym = yaml_ops.get_string_value(yaml, "acronym", "");
                let dll_file = yaml_ops.get_string_value(yaml, "dll_file", "");
                let description = yaml_ops.get_string_value(yaml, "description", "");
                let download_url = yaml_ops.get_string_value(yaml, "download_url", "");

                // Parse optional compatible_range
                let compatible_range =
                    if let Some(cr_yaml) = yaml_ops.get_setting(yaml, "compatible_range") {
                        let min_str = yaml_ops.get_string_value(&cr_yaml, "min", "");
                        let max_str = yaml_ops.get_string_value(&cr_yaml, "max", "");
                        CompatibleRange::from_strings(&min_str, &max_str).ok()
                    } else {
                        None
                    };

                Some(CrashgenConfig {
                    version,
                    name,
                    acronym,
                    dll_file,
                    description,
                    download_url,
                    compatible_range,
                })
            }
            _ => None,
        }
    }

    /// Parse unknown version handling from YAML.
    fn parse_unknown_handling_yaml(yaml: &yaml_rust2::Yaml) -> UnknownVersionHandling {
        let yaml_ops = YamlOperations::new();

        let strategy: UnknownVersionStrategy = yaml_ops
            .get_string_value(yaml, "strategy", "nearest_match")
            .parse()
            .unwrap();

        let log_level: LogLevel = yaml_ops
            .get_string_value(yaml, "log_level", "warning")
            .parse()
            .unwrap();

        // Parse defaults hashmap
        let defaults_map = yaml_ops.get_hashmap_value(yaml, "defaults");

        UnknownVersionHandling::new(strategy, defaults_map, log_level)
    }

    /// Load the registry with hardcoded defaults.
    fn load_defaults() -> Self {
        let versions = defaults::get_default_versions();
        let unknown_handling = defaults::get_default_unknown_handling();

        let mut by_version = HashMap::new();
        for version in versions.values() {
            by_version.insert(version.version_string(), version.clone());
        }

        Self {
            versions,
            by_version,
            unknown_handling,
        }
    }

    /// Create a registry for testing (bypasses singleton).
    #[cfg(test)]
    pub fn new_for_testing(
        versions: HashMap<String, VersionInfo>,
        by_version: HashMap<String, VersionInfo>,
        unknown_handling: UnknownVersionHandling,
    ) -> Self {
        Self {
            versions,
            by_version,
            unknown_handling,
        }
    }

    // === Public Lookup API ===

    /// Get version info by ID.
    ///
    /// # Arguments
    ///
    /// * `id` - The version ID (e.g., "FO4_OG", "FO4_NG", "FO4_VR")
    ///
    /// # Returns
    ///
    /// The `VersionInfo` for the specified ID, or `None` if not found.
    #[must_use]
    pub fn get_by_id(&self, id: &str) -> Option<&VersionInfo> {
        self.versions.get(id)
    }

    /// Get version info by exact version match.
    ///
    /// # Arguments
    ///
    /// * `version` - The exact game version to look up
    ///
    /// # Returns
    ///
    /// The `VersionInfo` for the specified version, or `None` if not found.
    #[must_use]
    pub fn get_by_version(&self, version: &GameVersion) -> Option<&VersionInfo> {
        self.by_version.get(&version.to_string())
    }

    /// Get version info by short name.
    ///
    /// # Arguments
    ///
    /// * `short_name` - The short name (e.g., "OG", "NG", "VR")
    ///
    /// # Returns
    ///
    /// The `VersionInfo` for the specified short name, or `None` if not found.
    #[must_use]
    pub fn get_by_short_name(&self, short_name: &str) -> Option<&VersionInfo> {
        self.versions.values().find(|v| v.short_name == short_name)
    }

    // === Public Filtering API ===

    /// Get all registered versions.
    ///
    /// Returns versions sorted by priority (descending).
    #[must_use]
    pub fn get_all(&self) -> Vec<&VersionInfo> {
        let mut versions: Vec<_> = self.versions.values().collect();
        versions.sort_by(|a, b| b.priority.cmp(&a.priority));
        versions
    }

    /// Get all versions for a specific game.
    ///
    /// # Arguments
    ///
    /// * `game` - Game identifier (e.g., "Fallout4")
    /// * `is_vr` - Optional VR filter. If `None`, returns all versions for the game.
    ///
    /// # Returns
    ///
    /// List of matching versions, sorted by priority (descending).
    #[must_use]
    pub fn get_all_for_game(&self, game: &str, is_vr: Option<bool>) -> Vec<&VersionInfo> {
        let mut versions: Vec<_> = self
            .versions
            .values()
            .filter(|v| v.game == game && is_vr.is_none_or(|vr| v.is_vr == vr))
            .collect();
        versions.sort_by(|a, b| b.priority.cmp(&a.priority));
        versions
    }

    /// Get correct versions for current mode (VR or non-VR).
    ///
    /// Returns versions that match the specified VR mode.
    ///
    /// # Arguments
    ///
    /// * `is_vr` - Whether VR mode is active
    #[must_use]
    pub fn get_correct_versions(&self, is_vr: bool) -> Vec<&VersionInfo> {
        self.versions
            .values()
            .filter(|v| v.is_vr == is_vr)
            .collect()
    }

    /// Get wrong versions for current mode (opposite of is_vr).
    ///
    /// Returns versions that do NOT match the specified VR mode.
    ///
    /// # Arguments
    ///
    /// * `is_vr` - Whether VR mode is active
    #[must_use]
    pub fn get_wrong_versions(&self, is_vr: bool) -> Vec<&VersionInfo> {
        self.versions
            .values()
            .filter(|v| v.is_vr != is_vr)
            .collect()
    }

    // === Public Matching API ===

    /// Match a detected version to the registry.
    ///
    /// Uses intelligent matching with fallback:
    /// 1. Exact match
    /// 2. Compatible range match
    /// 3. Nearest match (same major version)
    /// 4. Default fallback
    ///
    /// # Arguments
    ///
    /// * `detected` - The detected game version
    /// * `game` - Game identifier
    /// * `is_vr` - Whether VR mode is active
    ///
    /// # Returns
    ///
    /// A `MatchResult` with the matched version and confidence level.
    #[must_use]
    pub fn match_version(&self, detected: &GameVersion, game: &str, is_vr: bool) -> MatchResult {
        let matcher = VersionMatcher::new(self);
        matcher.match_version(detected, game, is_vr)
    }

    /// Get Address Library filename for a version.
    ///
    /// Convenience method to get just the Address Library filename.
    ///
    /// # Arguments
    ///
    /// * `version` - The game version
    /// * `is_vr` - Whether VR mode is active
    ///
    /// # Returns
    ///
    /// The Address Library filename, or `None` if not found.
    #[must_use]
    pub fn get_address_library_filename(
        &self,
        version: &GameVersion,
        is_vr: bool,
    ) -> Option<String> {
        let result = self.match_version(version, "Fallout4", is_vr);
        result
            .version_info
            .as_ref()
            .and_then(|v| v.address_library.as_ref())
            .map(|al| al.filename.clone())
    }

    // === Crashgen API ===

    /// Get all crash generator configurations for a version ID.
    ///
    /// # Arguments
    ///
    /// * `id` - The version ID (e.g., "FO4_OG", "FO4_NG")
    ///
    /// # Returns
    ///
    /// A vector of references to `CrashgenConfig` objects, or an empty vector if
    /// the version ID is not found.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use classic_version_registry_core::get_version_registry;
    ///
    /// let registry = get_version_registry();
    /// let configs = registry.get_crashgen_versions("FO4_OG");
    /// for config in configs {
    ///     println!("{}: {}", config.name, config.version);
    /// }
    /// ```
    #[must_use]
    pub fn get_crashgen_versions(&self, id: &str) -> Vec<&CrashgenConfig> {
        self.versions
            .get(id)
            .map(|v| v.crashgen_versions.iter().collect())
            .unwrap_or_default()
    }

    /// Get crash generator versions as simple version strings for a version ID.
    ///
    /// # Arguments
    ///
    /// * `id` - The version ID (e.g., "FO4_OG", "FO4_NG")
    ///
    /// # Returns
    ///
    /// A vector of version strings, or an empty vector if the version ID is not found.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use classic_version_registry_core::get_version_registry;
    ///
    /// let registry = get_version_registry();
    /// let versions = registry.get_crashgen_version_strings("FO4_OG");
    /// // Returns ["1.28.6", "1.37.0"]
    /// ```
    #[must_use]
    pub fn get_crashgen_version_strings(&self, id: &str) -> Vec<&str> {
        self.versions
            .get(id)
            .map(|v| v.get_crashgen_version_strings())
            .unwrap_or_default()
    }

    /// Get a specific crash generator configuration by version ID and crashgen version.
    ///
    /// # Arguments
    ///
    /// * `id` - The version ID (e.g., "FO4_OG", "FO4_NG")
    /// * `crashgen_version` - The crash generator version string (e.g., "1.28.6")
    ///
    /// # Returns
    ///
    /// The `CrashgenConfig` with the matching version, or `None` if not found.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use classic_version_registry_core::get_version_registry;
    ///
    /// let registry = get_version_registry();
    /// if let Some(config) = registry.get_crashgen_for_version("FO4_OG", "1.28.6") {
    ///     println!("Name: {}", config.name);
    ///     println!("Download: {}", config.download_url);
    /// }
    /// ```
    #[must_use]
    pub fn get_crashgen_for_version(
        &self,
        id: &str,
        crashgen_version: &str,
    ) -> Option<&CrashgenConfig> {
        self.versions
            .get(id)
            .and_then(|v| v.get_crashgen_for_version(crashgen_version))
    }

    /// Get the unknown version handling configuration.
    #[must_use]
    pub fn unknown_version_handling(&self) -> &UnknownVersionHandling {
        &self.unknown_handling
    }
}

/// Get the singleton version registry instance.
///
/// Convenience function for accessing the registry.
///
/// # Examples
///
/// ```rust,no_run
/// use classic_version_registry_core::get_version_registry;
///
/// let registry = get_version_registry();
/// let og = registry.get_by_id("FO4_OG");
/// ```
#[must_use]
pub fn get_version_registry() -> &'static VersionRegistry {
    VersionRegistry::get_instance()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_registry() -> VersionRegistry {
        VersionRegistry::load_defaults()
    }

    #[test]
    fn test_get_by_id() {
        let registry = create_test_registry();

        let og = registry.get_by_id("FO4_OG");
        assert!(og.is_some());
        assert_eq!(og.unwrap().short_name, "OG");

        let ng = registry.get_by_id("FO4_NG");
        assert!(ng.is_some());
        assert_eq!(ng.unwrap().short_name, "NG");

        let vr = registry.get_by_id("FO4_VR");
        assert!(vr.is_some());
        assert_eq!(vr.unwrap().short_name, "VR");

        let missing = registry.get_by_id("FO4_MISSING");
        assert!(missing.is_none());
    }

    #[test]
    fn test_get_by_version() {
        let registry = create_test_registry();

        let og = registry.get_by_version(&GameVersion::new(1, 10, 163, 0));
        assert!(og.is_some());
        assert_eq!(og.unwrap().id, "FO4_OG");

        let ng = registry.get_by_version(&GameVersion::new(1, 10, 984, 0));
        assert!(ng.is_some());
        assert_eq!(ng.unwrap().id, "FO4_NG");
    }

    #[test]
    fn test_get_by_short_name() {
        let registry = create_test_registry();

        let og = registry.get_by_short_name("OG");
        assert!(og.is_some());
        assert_eq!(og.unwrap().id, "FO4_OG");

        let missing = registry.get_by_short_name("MISSING");
        assert!(missing.is_none());
    }

    #[test]
    fn test_get_all() {
        let registry = create_test_registry();
        let all = registry.get_all();

        assert_eq!(all.len(), 4); // OG, NG, AE, VR
        // Should be sorted by priority (AE has highest priority at 300)
        assert_eq!(all[0].id, "FO4_AE");
    }

    #[test]
    fn test_get_all_for_game() {
        let registry = create_test_registry();

        let non_vr = registry.get_all_for_game("Fallout4", Some(false));
        assert_eq!(non_vr.len(), 3); // OG, NG, AE

        let vr = registry.get_all_for_game("Fallout4", Some(true));
        assert_eq!(vr.len(), 1);
        assert!(vr[0].is_vr);

        let all = registry.get_all_for_game("Fallout4", None);
        assert_eq!(all.len(), 4); // OG, NG, AE, VR
    }

    #[test]
    fn test_get_correct_wrong_versions() {
        let registry = create_test_registry();

        let correct_non_vr = registry.get_correct_versions(false);
        assert_eq!(correct_non_vr.len(), 3); // OG, NG, AE

        let wrong_for_non_vr = registry.get_wrong_versions(false);
        assert_eq!(wrong_for_non_vr.len(), 1);
        assert!(wrong_for_non_vr[0].is_vr);
    }

    #[test]
    fn test_match_version_exact() {
        let registry = create_test_registry();

        let result = registry.match_version(&GameVersion::new(1, 10, 163, 0), "Fallout4", false);

        assert!(result.is_exact());
        assert!(!result.should_warn());
        assert_eq!(result.version_info.as_ref().unwrap().id, "FO4_OG");
    }

    #[test]
    fn test_get_address_library_filename() {
        let registry = create_test_registry();

        let filename =
            registry.get_address_library_filename(&GameVersion::new(1, 10, 163, 0), false);

        assert_eq!(filename, Some("version-1-10-163-0.bin".to_string()));
    }

    #[test]
    fn test_get_crashgen_versions() {
        let registry = create_test_registry();

        // OG has two crashgen versions
        let og_configs = registry.get_crashgen_versions("FO4_OG");
        assert_eq!(og_configs.len(), 2);
        assert_eq!(og_configs[0].version, "1.28.6");
        assert_eq!(og_configs[1].version, "1.37.0");

        // NG has one crashgen version
        let ng_configs = registry.get_crashgen_versions("FO4_NG");
        assert_eq!(ng_configs.len(), 1);
        assert_eq!(ng_configs[0].version, "1.37.0");

        // AE has both Buffout 4 and Addictol
        let ae_configs = registry.get_crashgen_versions("FO4_AE");
        assert_eq!(ae_configs.len(), 2);
        assert_eq!(ae_configs[0].version, "1.7.1");
        assert_eq!(ae_configs[0].name, "Buffout 4");
        assert_eq!(ae_configs[1].version, "1.0.0");
        assert_eq!(ae_configs[1].name, "Addictol");

        // VR uses Buffout 4 (name matches log output)
        let vr_configs = registry.get_crashgen_versions("FO4_VR");
        assert_eq!(vr_configs.len(), 1);
        assert_eq!(vr_configs[0].version, "1.37.0");
        assert_eq!(vr_configs[0].name, "Buffout 4");

        // Missing version returns empty vector
        let missing = registry.get_crashgen_versions("FO4_MISSING");
        assert!(missing.is_empty());
    }

    #[test]
    fn test_get_crashgen_version_strings() {
        let registry = create_test_registry();

        let og_versions = registry.get_crashgen_version_strings("FO4_OG");
        assert_eq!(og_versions, vec!["1.28.6", "1.37.0"]);

        let ng_versions = registry.get_crashgen_version_strings("FO4_NG");
        assert_eq!(ng_versions, vec!["1.37.0"]);

        // AE has both Buffout 4 and Addictol
        let ae_versions = registry.get_crashgen_version_strings("FO4_AE");
        assert_eq!(ae_versions, vec!["1.7.1", "1.0.0"]);

        // VR uses Buffout 4 NG
        let vr_versions = registry.get_crashgen_version_strings("FO4_VR");
        assert_eq!(vr_versions, vec!["1.37.0"]);

        let missing = registry.get_crashgen_version_strings("FO4_MISSING");
        assert!(missing.is_empty());
    }

    #[test]
    fn test_get_crashgen_for_version() {
        let registry = create_test_registry();

        // Find existing crashgen
        let og_buffout4 = registry.get_crashgen_for_version("FO4_OG", "1.28.6");
        assert!(og_buffout4.is_some());
        assert_eq!(og_buffout4.unwrap().name, "Buffout 4");

        let og_buffout4ng = registry.get_crashgen_for_version("FO4_OG", "1.37.0");
        assert!(og_buffout4ng.is_some());
        assert_eq!(og_buffout4ng.unwrap().name, "Buffout 4"); // Name matches log output

        // Missing crashgen version returns None
        let missing_version = registry.get_crashgen_for_version("FO4_OG", "9.99.99");
        assert!(missing_version.is_none());

        // Missing version ID returns None
        let missing_id = registry.get_crashgen_for_version("FO4_MISSING", "1.28.6");
        assert!(missing_id.is_none());
    }

    // === YAML Parsing Tests for Crashgen ===

    #[test]
    fn test_parse_crashgen_versions_simple_string_list() {
        let yaml_ops = YamlOperations::new();

        // Create YAML with simple string list format
        let yaml_str = r#"
crashgen_versions:
  - "1.28.6"
  - "1.37.0"
  - "2.0.0"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert_eq!(parsed.len(), 3);

        // Check first version
        assert_eq!(parsed[0].version, "1.28.6");
        assert!(parsed[0].name.is_empty());
        assert!(parsed[0].description.is_empty());
        assert!(parsed[0].download_url.is_empty());
        assert!(parsed[0].compatible_range.is_none());

        // Check other versions
        assert_eq!(parsed[1].version, "1.37.0");
        assert_eq!(parsed[2].version, "2.0.0");
    }

    #[test]
    fn test_parse_crashgen_versions_structured_format() {
        let yaml_ops = YamlOperations::new();

        // Create YAML with structured format
        let yaml_str = r#"
crashgen_versions:
  - version: "1.28.6"
    name: "Buffout 4"
    description: "Legacy version for OG"
    download_url: "https://www.nexusmods.com/fallout4/mods/47359"
  - version: "1.37.0"
    name: "Buffout 4 NG"
    description: "NG-compatible version"
    download_url: "https://www.nexusmods.com/fallout4/mods/64880"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert_eq!(parsed.len(), 2);

        // Check first crashgen (Buffout 4)
        assert_eq!(parsed[0].version, "1.28.6");
        assert_eq!(parsed[0].name, "Buffout 4");
        assert_eq!(parsed[0].description, "Legacy version for OG");
        assert_eq!(
            parsed[0].download_url,
            "https://www.nexusmods.com/fallout4/mods/47359"
        );
        assert!(parsed[0].compatible_range.is_none());

        // Check second crashgen (Buffout 4 NG)
        assert_eq!(parsed[1].version, "1.37.0");
        assert_eq!(parsed[1].name, "Buffout 4 NG");
        assert_eq!(parsed[1].description, "NG-compatible version");
        assert_eq!(
            parsed[1].download_url,
            "https://www.nexusmods.com/fallout4/mods/64880"
        );
        assert!(parsed[1].compatible_range.is_none());
    }

    #[test]
    fn test_parse_crashgen_versions_structured_with_compatible_range() {
        let yaml_ops = YamlOperations::new();

        // Create YAML with structured format including compatible_range
        let yaml_str = r#"
crashgen_versions:
  - version: "1.28.6"
    name: "Buffout 4"
    description: "Legacy version for OG"
    download_url: "https://www.nexusmods.com/fallout4/mods/47359"
    compatible_range:
      min: "1.10.163.0"
      max: "1.10.163.999"
  - version: "1.37.0"
    name: "Buffout 4 NG"
    description: "NG-compatible version"
    download_url: "https://www.nexusmods.com/fallout4/mods/64880"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert_eq!(parsed.len(), 2);

        // Check first crashgen with compatible_range
        assert_eq!(parsed[0].version, "1.28.6");
        assert!(parsed[0].compatible_range.is_some());
        let range = parsed[0].compatible_range.as_ref().unwrap();
        assert_eq!(range.min_version, GameVersion::new(1, 10, 163, 0));
        assert_eq!(range.max_version, GameVersion::new(1, 10, 163, 999));

        // Check second crashgen without compatible_range
        assert!(parsed[1].compatible_range.is_none());
    }

    #[test]
    fn test_parse_crashgen_versions_empty_array() {
        let yaml_ops = YamlOperations::new();

        let yaml_str = r#"
crashgen_versions: []
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert!(parsed.is_empty());
    }

    #[test]
    fn test_parse_crashgen_versions_missing_field() {
        let yaml_ops = YamlOperations::new();

        // No crashgen_versions field at all
        let yaml_str = r#"
id: "TEST"
version: "1.0.0.0"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert!(parsed.is_empty());
    }

    #[test]
    fn test_parse_crashgen_versions_mixed_format() {
        let yaml_ops = YamlOperations::new();

        // Mixed format: some simple strings, some structured
        // Note: This tests backward compatibility when migrating from simple to structured
        let yaml_str = r#"
crashgen_versions:
  - "1.28.6"
  - version: "1.37.0"
    name: "Buffout 4 NG"
    description: "NG-compatible version"
    download_url: "https://www.nexusmods.com/fallout4/mods/64880"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert_eq!(parsed.len(), 2);

        // First is simple string
        assert_eq!(parsed[0].version, "1.28.6");
        assert!(parsed[0].name.is_empty());

        // Second is structured
        assert_eq!(parsed[1].version, "1.37.0");
        assert_eq!(parsed[1].name, "Buffout 4 NG");
    }

    #[test]
    fn test_parse_crashgen_versions_structured_missing_version_skipped() {
        let yaml_ops = YamlOperations::new();

        // Structured entry without version field should be skipped
        let yaml_str = r#"
crashgen_versions:
  - version: "1.28.6"
    name: "Buffout 4"
  - name: "Invalid Entry"
    description: "This has no version field"
  - version: "1.37.0"
    name: "Buffout 4 NG"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        // The entry without version should be skipped
        assert_eq!(parsed.len(), 2);
        assert_eq!(parsed[0].version, "1.28.6");
        assert_eq!(parsed[1].version, "1.37.0");
    }

    #[test]
    fn test_parse_crashgen_versions_structured_partial_fields() {
        let yaml_ops = YamlOperations::new();

        // Structured entry with only some optional fields
        let yaml_str = r#"
crashgen_versions:
  - version: "1.28.6"
    name: "Buffout 4"
  - version: "1.37.0"
    download_url: "https://example.com"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert_eq!(parsed.len(), 2);

        // First has only name
        assert_eq!(parsed[0].version, "1.28.6");
        assert_eq!(parsed[0].name, "Buffout 4");
        assert!(parsed[0].description.is_empty());
        assert!(parsed[0].download_url.is_empty());

        // Second has only download_url
        assert_eq!(parsed[1].version, "1.37.0");
        assert!(parsed[1].name.is_empty());
        assert_eq!(parsed[1].download_url, "https://example.com");
    }

    #[test]
    fn test_parse_crashgen_invalid_yaml_types() {
        let yaml_ops = YamlOperations::new();

        // crashgen_versions is not an array
        let yaml_str = r#"
crashgen_versions: "not an array"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        // Should return empty vec for invalid format
        assert!(parsed.is_empty());
    }

    #[test]
    fn test_parse_crashgen_versions_with_invalid_compatible_range() {
        let yaml_ops = YamlOperations::new();

        // compatible_range with invalid version strings
        let yaml_str = r#"
crashgen_versions:
  - version: "1.28.6"
    name: "Buffout 4"
    compatible_range:
      min: "invalid"
      max: "also_invalid"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let parsed = VersionRegistry::parse_crashgen_versions_yaml(&yaml, &yaml_ops);

        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].version, "1.28.6");
        // Invalid range parsing should result in None (using .ok())
        assert!(parsed[0].compatible_range.is_none());
    }

    // === Full Version YAML Parsing with Crashgen ===

    #[test]
    fn test_parse_version_yaml_with_crashgen() {
        let yaml_ops = YamlOperations::new();

        let yaml_str = r#"
id: "FO4_TEST"
game: "Fallout4"
version: "1.10.163.0"
display_name: "Test Version"
short_name: "TEST"
description: "Test version"
crashgen_versions:
  - version: "1.28.6"
    name: "Buffout 4"
    description: "Legacy version"
    download_url: "https://example.com/buffout4"
  - version: "1.37.0"
    name: "Buffout 4 NG"
    description: "NG version"
    download_url: "https://example.com/buffout4ng"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let version_info = VersionRegistry::parse_version_yaml(&yaml).unwrap();

        assert_eq!(version_info.id, "FO4_TEST");
        assert_eq!(version_info.crashgen_versions.len(), 2);
        assert_eq!(version_info.crashgen_versions[0].version, "1.28.6");
        assert_eq!(version_info.crashgen_versions[0].name, "Buffout 4");
        assert_eq!(version_info.crashgen_versions[1].version, "1.37.0");
        assert_eq!(version_info.crashgen_versions[1].name, "Buffout 4 NG");
    }

    #[test]
    fn test_parse_version_yaml_without_crashgen() {
        let yaml_ops = YamlOperations::new();

        let yaml_str = r#"
id: "FO4_TEST"
game: "Fallout4"
version: "1.10.163.0"
display_name: "Test Version"
short_name: "TEST"
description: "Test version"
"#;
        let yaml = yaml_ops.parse_yaml(yaml_str).unwrap();
        let version_info = VersionRegistry::parse_version_yaml(&yaml).unwrap();

        assert_eq!(version_info.id, "FO4_TEST");
        assert!(version_info.crashgen_versions.is_empty());
    }

    #[test]
    fn test_crashgen_config_metadata_from_defaults() {
        let registry = create_test_registry();

        // Verify OG crashgen configs have proper metadata
        if let Some(og) = registry.get_by_id("FO4_OG") {
            // Should have 2 crashgens
            assert_eq!(og.crashgen_versions.len(), 2);

            // Buffout 4 (legacy)
            let b4 = og.get_crashgen_for_version("1.28.6").unwrap();
            assert_eq!(b4.name, "Buffout 4");
            assert!(!b4.description.is_empty());
            assert!(!b4.download_url.is_empty());

            // Buffout 4 NG (name matches log output, description identifies as NG)
            let b4ng = og.get_crashgen_for_version("1.37.0").unwrap();
            assert_eq!(b4ng.name, "Buffout 4"); // Name matches what appears in crash log
            assert!(!b4ng.description.is_empty());
            assert!(!b4ng.download_url.is_empty());
        } else {
            panic!("FO4_OG not found in registry");
        }
    }

    #[test]
    fn test_crashgen_config_download_urls() {
        let registry = create_test_registry();

        // Verify download URLs are proper Nexus links
        if let Some(og) = registry.get_by_id("FO4_OG") {
            for config in &og.crashgen_versions {
                assert!(
                    config
                        .download_url
                        .starts_with("https://www.nexusmods.com/"),
                    "Download URL should be a Nexus link: {}",
                    config.download_url
                );
            }
        }

        if let Some(vr) = registry.get_by_id("FO4_VR") {
            for config in &vr.crashgen_versions {
                assert!(
                    config
                        .download_url
                        .starts_with("https://www.nexusmods.com/"),
                    "VR Download URL should be a Nexus link: {}",
                    config.download_url
                );
            }
        }
    }
}
