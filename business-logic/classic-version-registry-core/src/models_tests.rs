use super::*;

#[test]
fn test_address_lib_format() {
    assert_eq!(
        "bin".parse::<AddressLibFormat>().unwrap(),
        AddressLibFormat::Bin
    );
    assert_eq!(
        "csv".parse::<AddressLibFormat>().unwrap(),
        AddressLibFormat::Csv
    );
    assert_eq!(
        "CSV".parse::<AddressLibFormat>().unwrap(),
        AddressLibFormat::Csv
    );
    assert_eq!(
        "unknown".parse::<AddressLibFormat>().unwrap(),
        AddressLibFormat::Bin
    );
}

#[test]
fn test_compatible_range() {
    let range = CompatibleRange::from_strings("1.10.163.0", "1.10.163.999").unwrap();

    assert!(range.contains(&GameVersion::parse("1.10.163.0").unwrap()));
    assert!(range.contains(&GameVersion::parse("1.10.163.500").unwrap()));
    assert!(range.contains(&GameVersion::parse("1.10.163.999").unwrap()));
    assert!(!range.contains(&GameVersion::parse("1.10.164.0").unwrap()));
    assert!(!range.contains(&GameVersion::parse("1.10.162.0").unwrap()));
}

#[test]
fn test_unknown_version_strategy() {
    assert_eq!(
        "nearest_match".parse::<UnknownVersionStrategy>().unwrap(),
        UnknownVersionStrategy::NearestMatch
    );
    assert_eq!(
        "strict".parse::<UnknownVersionStrategy>().unwrap(),
        UnknownVersionStrategy::Strict
    );
    assert_eq!(
        "default_only".parse::<UnknownVersionStrategy>().unwrap(),
        UnknownVersionStrategy::DefaultOnly
    );
}

#[test]
fn test_crashgen_config_new() {
    let config = CrashgenConfig::new(
        "1.28.6",
        "Buffout 4",
        "BO4",
        "buffout4.dll",
        "Legacy version for OG",
        "https://www.nexusmods.com/fallout4/mods/47359",
    );

    assert_eq!(config.version, "1.28.6");
    assert_eq!(config.name, "Buffout 4");
    assert_eq!(config.acronym, "BO4");
    assert_eq!(config.dll_file, "buffout4.dll");
    assert_eq!(config.description, "Legacy version for OG");
    assert_eq!(
        config.download_url,
        "https://www.nexusmods.com/fallout4/mods/47359"
    );
    assert!(config.compatible_range.is_none());
}

#[test]
fn test_crashgen_config_from_version_string() {
    let config = CrashgenConfig::from_version_string("1.37.0");

    assert_eq!(config.version, "1.37.0");
    assert!(config.name.is_empty());
    assert!(config.acronym.is_empty());
    assert!(config.dll_file.is_empty());
    assert!(config.description.is_empty());
    assert!(config.download_url.is_empty());
    assert!(config.compatible_range.is_none());
}

#[test]
fn test_crashgen_config_with_range() {
    let range = CompatibleRange::from_strings("1.10.163.0", "1.10.163.999").unwrap();
    let config = CrashgenConfig::with_range(
        "1.28.6",
        "Buffout 4",
        "BO4",
        "buffout4.dll",
        "Legacy version for OG",
        "https://www.nexusmods.com/fallout4/mods/47359",
        range,
    );

    assert_eq!(config.version, "1.28.6");
    assert_eq!(config.acronym, "BO4");
    assert_eq!(config.dll_file, "buffout4.dll");
    assert!(config.compatible_range.is_some());
}

#[test]
fn test_crashgen_config_is_compatible_with_no_range() {
    let config = CrashgenConfig::from_version_string("1.37.0");

    // Without a range, all versions are compatible
    assert!(config.is_compatible_with(&GameVersion::parse("1.10.163.0").unwrap()));
    assert!(config.is_compatible_with(&GameVersion::parse("1.10.984.0").unwrap()));
    assert!(config.is_compatible_with(&GameVersion::parse("99.99.99.99").unwrap()));
}

#[test]
fn test_crashgen_config_is_compatible_with_range() {
    let range = CompatibleRange::from_strings("1.10.163.0", "1.10.163.999").unwrap();
    let config = CrashgenConfig::with_range(
        "1.28.6",
        "Buffout 4",
        "BO4",
        "buffout4.dll",
        "Legacy version for OG",
        "https://www.nexusmods.com/fallout4/mods/47359",
        range,
    );

    // Within range
    assert!(config.is_compatible_with(&GameVersion::parse("1.10.163.0").unwrap()));
    assert!(config.is_compatible_with(&GameVersion::parse("1.10.163.500").unwrap()));
    assert!(config.is_compatible_with(&GameVersion::parse("1.10.163.999").unwrap()));

    // Outside range
    assert!(!config.is_compatible_with(&GameVersion::parse("1.10.984.0").unwrap()));
    assert!(!config.is_compatible_with(&GameVersion::parse("1.10.162.0").unwrap()));
}

// === VersionInfo crashgen helper method tests ===

fn create_test_version_info_with_crashgens() -> VersionInfo {
    let og_range = CompatibleRange::from_strings("1.10.163.0", "1.10.163.999").unwrap();

    let mut legacy_buffout = CrashgenConfig::with_range(
        "1.28.6",
        "Buffout 4",
        "BO4",
        "buffout4.dll",
        "Legacy version for OG",
        "https://www.nexusmods.com/fallout4/mods/47359",
        og_range,
    );
    legacy_buffout.exact_match = true;

    VersionInfo {
        id: "TEST_VERSION".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 10, 163, 0),
        display_name: "Test Version".to_string(),
        short_name: "TEST".to_string(),
        description: "Test version for unit tests".to_string(),
        docs_name: "Fallout4".to_string(),
        steam_id: 377160,
        address_library: None,
        xse: None,
        compatible_range: None,
        priority: 100,
        deprecated: false,
        exe_hash: None,
        crashgen_versions: vec![
            legacy_buffout,
            CrashgenConfig::new(
                "1.37.0",
                "Buffout 4", // Name matches what appears in log output
                "BO4 NG",
                "buffout4.dll",
                "Buffout 4 NG",
                "https://www.nexusmods.com/fallout4/mods/64880",
            ),
        ],
    }
}

#[test]
fn test_version_info_get_crashgen_version_strings() {
    let version_info = create_test_version_info_with_crashgens();

    let version_strings = version_info.get_crashgen_version_strings();

    assert_eq!(version_strings, vec!["1.37.0"]);
}

#[test]
fn test_version_info_get_crashgen_version_strings_empty() {
    let mut version_info = create_test_version_info_with_crashgens();
    version_info.crashgen_versions = vec![];

    let version_strings = version_info.get_crashgen_version_strings();

    assert!(version_strings.is_empty());
}

#[test]
fn test_version_info_get_crashgen_for_version_found() {
    let version_info = create_test_version_info_with_crashgens();

    // Find first crashgen
    let config = version_info.get_crashgen_for_version("1.28.6");
    assert!(config.is_some());
    let config = config.unwrap();
    assert_eq!(config.version, "1.28.6");
    assert_eq!(config.name, "Buffout 4");
    assert!(config.compatible_range.is_some());

    // Find second crashgen
    let config = version_info.get_crashgen_for_version("1.37.0");
    assert!(config.is_some());
    let config = config.unwrap();
    assert_eq!(config.version, "1.37.0");
    assert_eq!(config.name, "Buffout 4"); // Name matches log output
    assert!(config.compatible_range.is_none());
}

#[test]
fn test_version_info_get_crashgen_for_version_not_found() {
    let version_info = create_test_version_info_with_crashgens();

    let config = version_info.get_crashgen_for_version("9.99.99");
    assert!(config.is_none());
}

#[test]
fn test_version_info_get_compatible_crashgens_with_own_version() {
    let version_info = create_test_version_info_with_crashgens();

    // Use the version_info's own version (1.10.163.0)
    // Both crashgens should be compatible:
    // - Buffout 4 (1.28.6) has range 1.10.163.0 - 1.10.163.999, which includes 1.10.163.0
    // - Buffout 4 NG (1.37.0) has no range, so it's compatible with all versions
    let compatible = version_info.get_compatible_crashgens(None);

    assert_eq!(compatible.len(), 2);
    assert_eq!(compatible[0].version, "1.28.6");
    assert_eq!(compatible[1].version, "1.37.0");
}

#[test]
fn test_version_info_get_compatible_crashgens_with_og_version() {
    let version_info = create_test_version_info_with_crashgens();

    // Use OG version 1.10.163.0 - both crashgens should be compatible
    let og_version = GameVersion::parse("1.10.163.0").unwrap();
    let compatible = version_info.get_compatible_crashgens(Some(&og_version));

    assert_eq!(compatible.len(), 2);
}

#[test]
fn test_version_info_get_compatible_crashgens_with_ng_version() {
    let version_info = create_test_version_info_with_crashgens();

    // Use NG version 1.10.984.0 - only Buffout 4 NG should be compatible
    // (Buffout 4 1.28.6 has a range that excludes this version)
    let ng_version = GameVersion::parse("1.10.984.0").unwrap();
    let compatible = version_info.get_compatible_crashgens(Some(&ng_version));

    assert_eq!(compatible.len(), 1);
    assert_eq!(compatible[0].version, "1.37.0");
    assert_eq!(compatible[0].name, "Buffout 4"); // Name matches log output
}

#[test]
fn test_version_info_get_compatible_crashgens_with_future_version() {
    let version_info = create_test_version_info_with_crashgens();

    // Use a future version outside the OG range - only Buffout 4 NG should be compatible
    let future_version = GameVersion::parse("1.11.200.0").unwrap();
    let compatible = version_info.get_compatible_crashgens(Some(&future_version));

    assert_eq!(compatible.len(), 1);
    assert_eq!(compatible[0].version, "1.37.0");
}

#[test]
fn test_version_info_get_compatible_crashgens_empty() {
    let mut version_info = create_test_version_info_with_crashgens();
    version_info.crashgen_versions = vec![];

    let compatible = version_info.get_compatible_crashgens(None);

    assert!(compatible.is_empty());
}

#[test]
fn test_version_info_crashgen_with_all_restricted_ranges() {
    // Test when all crashgens have ranges and none match the version
    let range1 = CompatibleRange::from_strings("1.10.100.0", "1.10.150.0").unwrap();
    let range2 = CompatibleRange::from_strings("1.10.200.0", "1.10.250.0").unwrap();

    let version_info = VersionInfo {
        id: "TEST_VERSION".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 10, 163, 0), // Outside both ranges
        display_name: "Test Version".to_string(),
        short_name: "TEST".to_string(),
        description: "Test version".to_string(),
        docs_name: "Fallout4".to_string(),
        steam_id: 377160,
        address_library: None,
        xse: None,
        compatible_range: None,
        priority: 100,
        deprecated: false,
        exe_hash: None,
        crashgen_versions: vec![
            CrashgenConfig::with_range("1.0.0", "Config 1", "", "", "", "", range1),
            CrashgenConfig::with_range("2.0.0", "Config 2", "", "", "", "", range2),
        ],
    };

    // Version 1.10.163.0 is outside both ranges
    let compatible = version_info.get_compatible_crashgens(None);
    assert!(compatible.is_empty());

    // Version 1.10.120.0 is inside range1
    let in_range1 = GameVersion::parse("1.10.120.0").unwrap();
    let compatible = version_info.get_compatible_crashgens(Some(&in_range1));
    assert_eq!(compatible.len(), 1);
    assert_eq!(compatible[0].version, "1.0.0");

    // Version 1.10.220.0 is inside range2
    let in_range2 = GameVersion::parse("1.10.220.0").unwrap();
    let compatible = version_info.get_compatible_crashgens(Some(&in_range2));
    assert_eq!(compatible.len(), 1);
    assert_eq!(compatible[0].version, "2.0.0");
}

fn ae_style_xse_config() -> XseConfig {
    XseConfig::new("F4SE", "F4SE", "0.7.8", "f4se_loader.exe", 29).with_runtime_versions(vec![
        // Deliberately out of order: the builder sorts by runtime.
        (GameVersion::parse("1.11.240").unwrap(), "0.7.9".to_string()),
        (GameVersion::parse("1.11.221").unwrap(), "0.7.8".to_string()),
    ])
}

#[test]
fn xse_expected_version_selects_the_release_for_the_installed_runtime() {
    let xse = ae_style_xse_config();

    // The build component never affects the match.
    let runtime = GameVersion::parse("1.11.240.0").unwrap();
    assert_eq!(xse.expected_version_for(Some(&runtime)), Some("0.7.9"));
    let runtime = GameVersion::parse("1.11.221.7").unwrap();
    assert_eq!(xse.expected_version_for(Some(&runtime)), Some("0.7.8"));

    let runtimes: Vec<String> = xse
        .runtime_versions
        .iter()
        .map(|(runtime, _)| runtime.to_string())
        .collect();
    assert_eq!(runtimes, ["1.11.221.0", "1.11.240.0"]);
}

#[test]
fn xse_expected_version_has_no_answer_for_an_unlisted_runtime() {
    // A newer runtime the registry has not recorded yet must not be compared
    // against an older runtime's release.
    let runtime = GameVersion::parse("1.11.250.0").unwrap();
    assert_eq!(
        ae_style_xse_config().expected_version_for(Some(&runtime)),
        None
    );
}

#[test]
fn xse_expected_version_falls_back_to_compatible_version() {
    // Unknown runtime (unreadable executable) on a multi-runtime entry.
    assert_eq!(
        ae_style_xse_config().expected_version_for(None),
        Some("0.7.8")
    );

    // Single-runtime entries list no runtimes and always use compatible_version.
    let og = XseConfig::new("F4SE", "F4SE", "0.6.23", "f4se_loader.exe", 29);
    let runtime = GameVersion::parse("1.10.163.0").unwrap();
    assert_eq!(og.expected_version_for(Some(&runtime)), Some("0.6.23"));
    assert_eq!(og.expected_version_for(None), Some("0.6.23"));
}
