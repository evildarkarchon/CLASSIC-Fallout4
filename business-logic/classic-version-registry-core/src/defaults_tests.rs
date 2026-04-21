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
    assert_eq!(og.docs_name, "Fallout4");
    assert_eq!(og.steam_id, 377160);
    assert!(og.address_library.is_some());
    assert_eq!(
        og.address_library.as_ref().unwrap().format,
        AddressLibFormat::Bin
    );

    // XSE config
    let xse = og.xse.as_ref().expect("OG should have XSE");
    assert_eq!(xse.full_name, "Fallout 4 Script Extender (F4SE)");
    assert_eq!(xse.file_count, 29);
    assert_eq!(xse.script_hashes.len(), 29);

    // Crashgen config
    assert_eq!(og.crashgen_versions[0].acronym, "BO4");
    assert_eq!(og.crashgen_versions[0].dll_file, "buffout4.dll");
    assert_eq!(og.crashgen_versions[1].acronym, "BO4 NG");
    assert_eq!(og.crashgen_versions[1].dll_file, "buffout4.dll");

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
    assert_eq!(ng.docs_name, "Fallout4");
    assert_eq!(ng.steam_id, 377160);
    assert_eq!(ng.priority, 200); // Higher priority than OG

    // XSE config
    let xse = ng.xse.as_ref().expect("NG should have XSE");
    assert_eq!(xse.full_name, "Fallout 4 Script Extender (F4SE)");
    assert_eq!(xse.file_count, 29);
    assert_eq!(xse.script_hashes.len(), 29);

    // Crashgen config
    assert_eq!(ng.crashgen_versions[0].acronym, "BO4 NG");
    assert_eq!(ng.crashgen_versions[0].dll_file, "buffout4.dll");

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
    assert_eq!(ae.docs_name, "Fallout4");
    assert_eq!(ae.steam_id, 377160);
    assert_eq!(ae.priority, 300); // Highest priority - most recent version branch
    assert!(ae.compatible_range.is_some());

    // XSE config
    let xse = ae.xse.as_ref().expect("AE should have XSE");
    assert_eq!(xse.full_name, "Fallout 4 Script Extender (F4SE)");
    assert_eq!(xse.file_count, 29);

    // Crashgen configs
    assert_eq!(ae.crashgen_versions[0].acronym, "BO4");
    assert_eq!(ae.crashgen_versions[0].dll_file, "buffout4.dll");
    assert_eq!(ae.crashgen_versions[1].acronym, "Addictol");
    assert_eq!(ae.crashgen_versions[1].dll_file, "addictol.dll");

    // Test compatible range includes expected versions
    let range = ae.compatible_range.as_ref().unwrap();
    assert!(range.contains(&GameVersion::new(1, 11, 137, 0))); // Min version
    assert!(range.contains(&GameVersion::new(1, 11, 140, 0))); // Early AE version
    assert!(range.contains(&GameVersion::new(1, 11, 191, 0))); // Current max
    assert!(range.contains(&GameVersion::new(1, 11, 200, 0))); // Future version
    assert!(!range.contains(&GameVersion::new(1, 10, 984, 0))); // NG version
    assert!(!range.contains(&GameVersion::new(1, 12, 0, 0))); // Outside range

    // AE supports both Buffout 4 and Addictol
    assert_eq!(ae.crashgen_versions.len(), 2);
    assert_eq!(ae.crashgen_versions[0].version, "1.7.1");
    assert_eq!(ae.crashgen_versions[0].name, "Buffout 4");
    assert_eq!(ae.crashgen_versions[1].version, "1.0.0");
    assert_eq!(ae.crashgen_versions[1].name, "Addictol");

    // Both AE crashgen configs have compatible_range matching AE's version-level range
    let ae_cg_range_0 = ae.crashgen_versions[0].compatible_range.as_ref().unwrap();
    assert_eq!(ae_cg_range_0.min_version, GameVersion::new(1, 11, 137, 0));
    assert_eq!(ae_cg_range_0.max_version, GameVersion::new(1, 11, 999, 999));
    assert!(ae.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 11, 191, 0)));
    assert!(!ae.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));

    let ae_cg_range_1 = ae.crashgen_versions[1].compatible_range.as_ref().unwrap();
    assert_eq!(ae_cg_range_1.min_version, GameVersion::new(1, 11, 137, 0));
    assert_eq!(ae_cg_range_1.max_version, GameVersion::new(1, 11, 999, 999));
    assert!(ae.crashgen_versions[1].is_compatible_with(&GameVersion::new(1, 11, 191, 0)));
    assert!(!ae.crashgen_versions[1].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));
}

#[test]
fn test_vr_version() {
    let vr = create_fo4_vr();

    assert_eq!(vr.id, "FO4_VR");
    assert_eq!(vr.version, GameVersion::new(1, 2, 72, 0));
    assert_eq!(vr.short_name, "VR");
    assert!(vr.is_vr);
    assert_eq!(vr.docs_name, "Fallout4VR");
    assert_eq!(vr.steam_id, 611660);
    assert!(vr.address_library.is_some());
    assert_eq!(
        vr.address_library.as_ref().unwrap().format,
        AddressLibFormat::Csv
    );

    // XSE config
    let xse = vr.xse.as_ref().expect("VR should have XSE");
    assert_eq!(xse.full_name, "Fallout 4 Script Extender VR (F4SEVR)");
    assert_eq!(xse.file_count, 29);
    assert_eq!(xse.script_hashes.len(), 29);

    // Crashgen config
    assert_eq!(vr.crashgen_versions[0].acronym, "BO4 NG");
    assert_eq!(vr.crashgen_versions[0].dll_file, "buffout4.dll");

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
    assert_eq!(handling.get_default("Fallout4"), Some("FO4_AE"));
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

    // AE game version (1.11.191.0) — both Buffout 4 and Addictol should be compatible
    let compatible = ae.get_compatible_crashgens(None);
    assert_eq!(compatible.len(), 2);
    assert_eq!(compatible[0].version, "1.7.1");
    assert_eq!(compatible[1].version, "1.0.0");

    // NG game version — neither AE crashgen should be compatible
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
