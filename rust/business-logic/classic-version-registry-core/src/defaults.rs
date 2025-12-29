//! Hardcoded default versions for Fallout 4.
//!
//! This module provides default version configurations when YAML loading
//! fails or the Version_Registry section is not present. It includes
//! the four standard Fallout 4 versions: OG, NG, AE (Anniversary Edition), and VR.

use std::collections::HashMap;

use crate::GameVersion;
use crate::models::{
    AddressLibFormat, AddressLibraryConfig, CompatibleRange, LogLevel, UnknownVersionHandling,
    UnknownVersionStrategy, VersionInfo, XseConfig,
};

/// Create default Fallout 4 OG (Original) version info.
pub fn create_fo4_og() -> VersionInfo {
    VersionInfo {
        id: "FO4_OG".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 10, 163, 0),
        display_name: "Fallout 4 Original".to_string(),
        short_name: "OG".to_string(),
        description: "Pre-Next-Gen Update version".to_string(),
        address_library: Some(AddressLibraryConfig::new(
            "version-1-10-163-0.bin",
            AddressLibFormat::Bin,
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )),
        xse: Some(XseConfig::new("F4SE", "0.6.23", "f4se_loader.exe")),
        compatible_range: None,
        priority: 100,
        deprecated: false,
    }
}

/// Create default Fallout 4 NG (Next-Gen) version info.
pub fn create_fo4_ng() -> VersionInfo {
    VersionInfo {
        id: "FO4_NG".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 10, 984, 0),
        display_name: "Fallout 4 Next-Gen".to_string(),
        short_name: "NG".to_string(),
        description: "Next-Gen Update version".to_string(),
        address_library: Some(AddressLibraryConfig::new(
            "version-1-10-984-0.bin",
            AddressLibFormat::Bin,
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )),
        xse: Some(XseConfig::new("F4SE", "0.7.2", "f4se_loader.exe")),
        compatible_range: None,
        priority: 200, // Higher priority - default for unknown versions
        deprecated: false,
    }
}

/// Create default Fallout 4 Anniversary Edition version info.
///
/// The Anniversary Edition covers game versions from 1.11.137/1.11.140 to 1.11.191
/// and beyond (as it's an active development branch). Uses a generous compatible
/// range to match future versions in this branch.
pub fn create_fo4_ae() -> VersionInfo {
    VersionInfo {
        id: "FO4_AE".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 11, 191, 0), // Current max version
        display_name: "Fallout 4 Anniversary Edition".to_string(),
        short_name: "AE".to_string(),
        description: "Anniversary Edition version (active development branch)".to_string(),
        address_library: Some(AddressLibraryConfig::new(
            "version-1-11-191-0.bin",
            AddressLibFormat::Bin,
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )),
        xse: Some(XseConfig::new("F4SE", "0.7.3", "f4se_loader.exe")),
        // Generous compatible range: 1.11.137.0 through 1.11.999.0 (future-proof for active branch)
        compatible_range: Some(CompatibleRange::new(
            GameVersion::new(1, 11, 137, 0),
            GameVersion::new(1, 11, 999, 0),
        )),
        priority: 300, // Highest priority - most recent version branch
        deprecated: false,
    }
}

/// Create default Fallout 4 VR version info.
pub fn create_fo4_vr() -> VersionInfo {
    VersionInfo {
        id: "FO4_VR".to_string(),
        game: "Fallout4".to_string(),
        is_vr: true,
        version: GameVersion::new(1, 2, 72, 0),
        display_name: "Fallout 4 VR".to_string(),
        short_name: "VR".to_string(),
        description: "Virtual Reality version".to_string(),
        address_library: Some(AddressLibraryConfig::new(
            "version-1-2-72-0.csv",
            AddressLibFormat::Csv,
            "https://www.nexusmods.com/fallout4/mods/64879?tab=files",
        )),
        xse: Some(XseConfig::new("F4SEVR", "0.6.20", "f4sevr_loader.exe")),
        compatible_range: None,
        priority: 100,
        deprecated: false,
    }
}

/// Get all default Fallout 4 versions.
///
/// Returns a HashMap mapping version IDs to their VersionInfo.
pub fn get_default_versions() -> HashMap<String, VersionInfo> {
    let mut versions = HashMap::new();

    let og = create_fo4_og();
    let ng = create_fo4_ng();
    let ae = create_fo4_ae();
    let vr = create_fo4_vr();

    versions.insert(og.id.clone(), og);
    versions.insert(ng.id.clone(), ng);
    versions.insert(ae.id.clone(), ae);
    versions.insert(vr.id.clone(), vr);

    versions
}

/// Get default unknown version handling configuration.
pub fn get_default_unknown_handling() -> UnknownVersionHandling {
    let mut defaults = HashMap::new();
    defaults.insert("Fallout4".to_string(), "FO4_NG".to_string());
    defaults.insert("Fallout4VR".to_string(), "FO4_VR".to_string());

    UnknownVersionHandling::new(
        UnknownVersionStrategy::NearestMatch,
        defaults,
        LogLevel::Warning,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_versions() {
        let versions = get_default_versions();

        assert_eq!(versions.len(), 4);
        assert!(versions.contains_key("FO4_OG"));
        assert!(versions.contains_key("FO4_NG"));
        assert!(versions.contains_key("FO4_AE"));
        assert!(versions.contains_key("FO4_VR"));
    }

    #[test]
    fn test_og_version() {
        let og = create_fo4_og();

        assert_eq!(og.id, "FO4_OG");
        assert_eq!(og.version, GameVersion::new(1, 10, 163, 0));
        assert_eq!(og.short_name, "OG");
        assert!(!og.is_vr);
        assert!(og.address_library.is_some());
        assert_eq!(
            og.address_library.as_ref().unwrap().format,
            AddressLibFormat::Bin
        );
    }

    #[test]
    fn test_ng_version() {
        let ng = create_fo4_ng();

        assert_eq!(ng.id, "FO4_NG");
        assert_eq!(ng.version, GameVersion::new(1, 10, 984, 0));
        assert_eq!(ng.short_name, "NG");
        assert!(!ng.is_vr);
        assert_eq!(ng.priority, 200); // Higher priority than OG
    }

    #[test]
    fn test_ae_version() {
        let ae = create_fo4_ae();

        assert_eq!(ae.id, "FO4_AE");
        assert_eq!(ae.version, GameVersion::new(1, 11, 191, 0));
        assert_eq!(ae.short_name, "AE");
        assert!(!ae.is_vr);
        assert_eq!(ae.priority, 300); // Highest priority - most recent version branch
        assert!(ae.compatible_range.is_some());

        // Test compatible range includes expected versions
        let range = ae.compatible_range.as_ref().unwrap();
        assert!(range.contains(&GameVersion::new(1, 11, 137, 0))); // Min version
        assert!(range.contains(&GameVersion::new(1, 11, 140, 0))); // Early AE version
        assert!(range.contains(&GameVersion::new(1, 11, 191, 0))); // Current max
        assert!(range.contains(&GameVersion::new(1, 11, 200, 0))); // Future version
        assert!(!range.contains(&GameVersion::new(1, 10, 984, 0))); // NG version
        assert!(!range.contains(&GameVersion::new(1, 12, 0, 0))); // Outside range
    }

    #[test]
    fn test_vr_version() {
        let vr = create_fo4_vr();

        assert_eq!(vr.id, "FO4_VR");
        assert_eq!(vr.version, GameVersion::new(1, 2, 72, 0));
        assert_eq!(vr.short_name, "VR");
        assert!(vr.is_vr);
        assert!(vr.address_library.is_some());
        assert_eq!(
            vr.address_library.as_ref().unwrap().format,
            AddressLibFormat::Csv
        );
    }

    #[test]
    fn test_default_unknown_handling() {
        let handling = get_default_unknown_handling();

        assert_eq!(handling.strategy, UnknownVersionStrategy::NearestMatch);
        assert_eq!(handling.get_default("Fallout4"), Some("FO4_NG"));
        assert_eq!(handling.get_default("Fallout4VR"), Some("FO4_VR"));
    }
}
