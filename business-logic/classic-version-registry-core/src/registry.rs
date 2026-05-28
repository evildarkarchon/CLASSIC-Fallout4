//! Version registry singleton.
//!
//! This module provides the main `VersionRegistry` type that manages game version
//! metadata. It implements a thread-safe singleton pattern using `OnceLock` and
//! supports loading from YAML with fallback to hardcoded defaults.

use std::collections::HashMap;
use std::path::Path;
use std::sync::OnceLock;

use classic_settings_core::YamlOperations;

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
                        .unwrap_or_default(),
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

            XseConfig::with_script_hashes(
                acronym,
                full_name,
                compatible_version,
                loader,
                file_count,
                script_hashes,
            )
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
            .unwrap_or_default();

        let log_level: LogLevel = yaml_ops
            .get_string_value(yaml, "log_level", "warning")
            .parse()
            .unwrap_or_default();

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
        versions.sort_by_key(|version| std::cmp::Reverse(version.priority));
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
        versions.sort_by_key(|version| std::cmp::Reverse(version.priority));
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
#[path = "registry_tests.rs"]
mod tests;
