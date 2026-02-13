//! Hardcoded default versions for Fallout 4.
//!
//! This module provides default version configurations when YAML loading
//! fails or the Version_Registry section is not present. It includes
//! the four standard Fallout 4 versions: OG, NG, AE (Anniversary Edition), and VR.

use std::collections::HashMap;

use crate::GameVersion;
use crate::models::{
    AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel,
    UnknownVersionHandling, UnknownVersionStrategy, VersionInfo, XseConfig,
};

/// Create default Fallout 4 OG (Original) version info.
pub fn create_fo4_og() -> VersionInfo {
    let og_script_hashes = vec![
        (
            "Actor.pex".to_string(),
            "9333aa9b33d6009933afc3a1234a89ca93b5522ea186b44bc6c78846ed5a82c4".to_string(),
        ),
        (
            "ActorBase.pex".to_string(),
            "cb5d29fead7df77eca8674101abdc57349a8cf345f18c3ddd6ef8d94ad254da7".to_string(),
        ),
        (
            "Form.pex".to_string(),
            "3ac9cd7ecb22d377800ca316413eb1d8f4def3ff3721a14b4c6fa61500f9f568".to_string(),
        ),
        (
            "Game.pex".to_string(),
            "19c858908f1a2054755b602121e5944dbbfb1ee0be38a24a532e6ab2f9390f4d".to_string(),
        ),
        (
            "ObjectReference.pex".to_string(),
            "97cfd2749b70545c9378955b09a898631fa03a0e235623b76f2c5631f2801be5".to_string(),
        ),
    ];
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
        xse: Some(XseConfig::with_script_hashes(
            "F4SE",
            "0.6.23",
            "f4se_loader.exe",
            og_script_hashes,
        )),
        compatible_range: None,
        priority: 100,
        deprecated: false,
        exe_hash: Some(
            "55f57947db9e05575122fae1088f0b0247442f11e566b56036caa0ac93329c36".to_string(),
        ),
        crashgen_versions: vec![
            CrashgenConfig::with_range(
                "1.28.6",
                "Buffout 4",
                "Legacy version for OG",
                "https://www.nexusmods.com/fallout4/mods/47359",
                CompatibleRange::new(
                    GameVersion::new(1, 10, 163, 0),
                    GameVersion::new(1, 10, 163, 999),
                ),
            ),
            CrashgenConfig::new(
                "1.37.0",
                "Buffout 4",
                "Buffout 4 NG",
                "https://www.nexusmods.com/fallout4/mods/64880",
            ),
        ],
    }
}

/// Create default Fallout 4 NG (Next-Gen) version info.
pub fn create_fo4_ng() -> VersionInfo {
    let ng_script_hashes = vec![
        (
            "Actor.pex".to_string(),
            "12175169977977bf382631272ae6dfda03f002c268434144eedf8653000b2b90".to_string(),
        ),
        (
            "ActorBase.pex".to_string(),
            "6c7f6b82306ef541673ebb31142c5f69d32f574d81f932d957e3e7f3b649863f".to_string(),
        ),
        (
            "Form.pex".to_string(),
            "7afbf5bdf3e454dbf968c784807c6bef79fa88893083f1160bc4bb4e980228b3".to_string(),
        ),
        (
            "Game.pex".to_string(),
            "c0bba25948ddb5574d84d995ee71886f6aacab10f25d979145e684d9625d6cda".to_string(),
        ),
        (
            "ObjectReference.pex".to_string(),
            "c166855a4b2b34a1f07cb1bc928aed34a323b3a7da5fc90d6b6d9cfb6f7c22da".to_string(),
        ),
    ];
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
        xse: Some(XseConfig::with_script_hashes(
            "F4SE",
            "0.7.2",
            "f4se_loader.exe",
            ng_script_hashes,
        )),
        compatible_range: None,
        priority: 200, // Higher priority - default for unknown versions
        deprecated: false,
        exe_hash: Some(
            "bcb8f9fe660ef4c33712b873fdc24e5ecbd6a77e629d6419f803c2c09c63eaf2".to_string(),
        ),
        crashgen_versions: vec![CrashgenConfig::with_range(
            "1.37.0",
            "Buffout 4",
            "Buffout 4 NG",
            "https://www.nexusmods.com/fallout4/mods/64880",
            CompatibleRange::new(
                GameVersion::new(1, 10, 984, 0),
                GameVersion::new(1, 10, 999, 999),
            ),
        )],
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
        exe_hash: None, // AE exe hash not yet available
        crashgen_versions: vec![CrashgenConfig::with_range(
            "1.4.0",
            "MiniBuff AE Crash Logger",
            "AE-compatible Crash Logger",
            "https://www.nexusmods.com/fallout4/mods/99911",
            CompatibleRange::new(
                GameVersion::new(1, 11, 137, 0),
                GameVersion::new(1, 11, 999, 999),
            ),
        )],
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
        exe_hash: None, // VR exe hash not yet available
        crashgen_versions: vec![CrashgenConfig::new(
            "1.37.0",
            "Buffout 4",
            "NG-compatible version for VR",
            "https://www.nexusmods.com/fallout4/mods/64880",
        )],
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

        // OG supports both Buffout 4 legacy and Buffout 4 NG
        assert_eq!(og.crashgen_versions.len(), 2);
        assert_eq!(og.crashgen_versions[0].version, "1.28.6");
        assert_eq!(og.crashgen_versions[0].name, "Buffout 4");
        // Buffout 4 legacy has OG-specific compatible_range
        let og_range = og.crashgen_versions[0].compatible_range.as_ref().unwrap();
        assert_eq!(og_range.min_version, GameVersion::new(1, 10, 163, 0));
        assert_eq!(og_range.max_version, GameVersion::new(1, 10, 163, 999));
        assert!(og.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 163, 0)));
        assert!(!og.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));

        assert_eq!(og.crashgen_versions[1].version, "1.37.0");
        assert_eq!(og.crashgen_versions[1].name, "Buffout 4"); // Name matches log output
        // Buffout 4 NG has no range restriction (universal within OG)
        assert!(og.crashgen_versions[1].compatible_range.is_none());
    }

    #[test]
    fn test_ng_version() {
        let ng = create_fo4_ng();

        assert_eq!(ng.id, "FO4_NG");
        assert_eq!(ng.version, GameVersion::new(1, 10, 984, 0));
        assert_eq!(ng.short_name, "NG");
        assert!(!ng.is_vr);
        assert_eq!(ng.priority, 200); // Higher priority than OG

        // NG only supports Buffout 4 NG (name matches log output, description identifies as NG)
        assert_eq!(ng.crashgen_versions.len(), 1);
        assert_eq!(ng.crashgen_versions[0].version, "1.37.0");
        assert_eq!(ng.crashgen_versions[0].name, "Buffout 4");
        // NG crashgen has compatible_range for NG game versions
        let ng_range = ng.crashgen_versions[0].compatible_range.as_ref().unwrap();
        assert_eq!(ng_range.min_version, GameVersion::new(1, 10, 984, 0));
        assert_eq!(ng_range.max_version, GameVersion::new(1, 10, 999, 999));
        assert!(ng.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));
        assert!(!ng.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 163, 0)));
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

        // AE supports MiniBuff AE Crash Logger
        assert_eq!(ae.crashgen_versions.len(), 1);
        assert_eq!(ae.crashgen_versions[0].version, "1.4.0");
        assert_eq!(ae.crashgen_versions[0].name, "MiniBuff AE Crash Logger");
        // AE crashgen has compatible_range matching AE's version-level range
        let ae_cg_range = ae.crashgen_versions[0].compatible_range.as_ref().unwrap();
        assert_eq!(ae_cg_range.min_version, GameVersion::new(1, 11, 137, 0));
        assert_eq!(ae_cg_range.max_version, GameVersion::new(1, 11, 999, 999));
        assert!(ae.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 11, 191, 0)));
        assert!(!ae.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));
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

        // VR supports Buffout 4 NG (name matches log output)
        assert_eq!(vr.crashgen_versions.len(), 1);
        assert_eq!(vr.crashgen_versions[0].version, "1.37.0");
        assert_eq!(vr.crashgen_versions[0].name, "Buffout 4");
        // VR crashgen has no compatible_range (universal within VR)
        assert!(vr.crashgen_versions[0].compatible_range.is_none());
    }

    #[test]
    fn test_default_unknown_handling() {
        let handling = get_default_unknown_handling();

        assert_eq!(handling.strategy, UnknownVersionStrategy::NearestMatch);
        assert_eq!(handling.get_default("Fallout4"), Some("FO4_NG"));
        assert_eq!(handling.get_default("Fallout4VR"), Some("FO4_VR"));
    }

    #[test]
    fn test_og_get_compatible_crashgens_filters_by_range() {
        let og = create_fo4_og();

        // OG game version (1.10.163.0) — both crashgens should be compatible:
        // - 1.28.6 has range 1.10.163.0–1.10.163.999 (contains 1.10.163.0)
        // - 1.37.0 has no range (universal)
        let compatible = og.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 2);

        // NG game version (1.10.984.0) — only 1.37.0 should be compatible:
        // - 1.28.6 range excludes NG versions
        // - 1.37.0 has no range (universal)
        let ng_version = GameVersion::new(1, 10, 984, 0);
        let compatible = og.get_compatible_crashgens(Some(&ng_version));
        assert_eq!(compatible.len(), 1);
        assert_eq!(compatible[0].version, "1.37.0");
    }

    #[test]
    fn test_ng_get_compatible_crashgens_filters_by_range() {
        let ng = create_fo4_ng();

        // NG game version (1.10.984.0) — 1.37.0 should be compatible (within range)
        let compatible = ng.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 1);
        assert_eq!(compatible[0].version, "1.37.0");

        // OG game version (1.10.163.0) — 1.37.0 should NOT be compatible (outside range)
        let og_version = GameVersion::new(1, 10, 163, 0);
        let compatible = ng.get_compatible_crashgens(Some(&og_version));
        assert!(compatible.is_empty());
    }

    #[test]
    fn test_ae_get_compatible_crashgens_filters_by_range() {
        let ae = create_fo4_ae();

        // AE game version (1.11.191.0) — MiniBuff should be compatible
        let compatible = ae.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 1);
        assert_eq!(compatible[0].version, "1.4.0");

        // NG game version — MiniBuff should NOT be compatible
        let ng_version = GameVersion::new(1, 10, 984, 0);
        let compatible = ae.get_compatible_crashgens(Some(&ng_version));
        assert!(compatible.is_empty());
    }

    #[test]
    fn test_vr_get_compatible_crashgens_no_range() {
        let vr = create_fo4_vr();

        // VR crashgen has no range — compatible with any version
        let compatible = vr.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 1);
        assert_eq!(compatible[0].version, "1.37.0");

        // Even with a random version, still compatible
        let random_version = GameVersion::new(99, 99, 99, 99);
        let compatible = vr.get_compatible_crashgens(Some(&random_version));
        assert_eq!(compatible.len(), 1);
    }
}
