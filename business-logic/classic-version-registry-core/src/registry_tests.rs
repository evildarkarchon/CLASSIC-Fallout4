use super::*;

fn create_test_registry() -> VersionRegistry {
    VersionRegistry::load_embedded_defaults().expect("embedded CLASSIC Main.yaml should load")
}

fn classic_main_yaml_path() -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../CLASSIC Data/databases/CLASSIC Main.yaml")
}

fn version_entry<'a>(registry: &'a VersionRegistry, id: &str) -> &'a VersionInfo {
    registry
        .get_by_id(id)
        .unwrap_or_else(|| panic!("{id} should exist"))
}

fn crashgen_signature(configs: &[CrashgenConfig]) -> Vec<(&str, &str, &str, bool)> {
    configs
        .iter()
        .map(|config| {
            (
                config.version.as_str(),
                config.name.as_str(),
                config.acronym.as_str(),
                config.exact_match,
            )
        })
        .collect()
}

fn floor_crashgen_versions(info: &VersionInfo) -> Vec<&str> {
    info.crashgen_versions
        .iter()
        .filter(|config| !config.exact_match)
        .map(|config| config.version.as_str())
        .collect()
}

fn find_crashgen<'a>(
    info: &'a VersionInfo,
    description: &str,
    predicate: impl Fn(&CrashgenConfig) -> bool,
) -> &'a CrashgenConfig {
    info.crashgen_versions
        .iter()
        .find(|config| predicate(config))
        .unwrap_or_else(|| panic!("{description} should exist"))
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
fn test_embedded_yaml_metadata_fields_are_populated() {
    let registry = create_test_registry();

    for (id, docs_name, steam_id) in [
        ("FO4_OG", "Fallout4", 377160),
        ("FO4_NG", "Fallout4", 377160),
        ("FO4_AE", "Fallout4", 377160),
        ("FO4_VR", "Fallout4VR", 611660),
    ] {
        let info = registry.get_by_id(id).expect("version entry");
        assert_eq!(info.docs_name.as_str(), docs_name);
        assert_eq!(info.steam_id, steam_id);

        let xse = info.xse.as_ref().expect("XSE metadata");
        assert!(!xse.full_name.is_empty(), "{id} XSE full name is empty");
        assert_eq!(xse.file_count, 29, "{id} XSE file count changed");

        for crashgen in &info.crashgen_versions {
            assert!(
                !crashgen.acronym.is_empty(),
                "{id} crashgen {} acronym is empty",
                crashgen.version
            );
            assert!(
                !crashgen.dll_file.is_empty(),
                "{id} crashgen {} DLL file is empty",
                crashgen.version
            );
        }
    }

    assert_eq!(
        registry
            .get_by_id("FO4_OG")
            .unwrap()
            .xse
            .as_ref()
            .unwrap()
            .script_hashes
            .len(),
        29
    );
    assert_eq!(
        registry
            .get_by_id("FO4_NG")
            .unwrap()
            .xse
            .as_ref()
            .unwrap()
            .script_hashes
            .len(),
        29
    );
    assert_eq!(
        registry
            .get_by_id("FO4_AE")
            .unwrap()
            .xse
            .as_ref()
            .unwrap()
            .script_hashes
            .len(),
        0
    );
    assert_eq!(
        registry
            .get_by_id("FO4_VR")
            .unwrap()
            .xse
            .as_ref()
            .unwrap()
            .script_hashes
            .len(),
        29
    );

    let og_info = version_entry(&registry, "FO4_OG");
    let og_legacy_version = find_crashgen(og_info, "OG legacy crashgen", |config| {
        config.acronym == "BO4"
    })
    .version
    .as_str();
    let og_legacy = registry
        .get_crashgen_for_version("FO4_OG", og_legacy_version)
        .expect("OG legacy crashgen");
    assert_eq!(og_legacy.acronym.as_str(), "BO4");
    assert_eq!(og_legacy.dll_file.as_str(), "buffout4.dll");

    let vr_info = version_entry(&registry, "FO4_VR");
    let vr_crashgen_version =
        find_crashgen(vr_info, "VR crashgen", |config| config.acronym == "BO4 NG")
            .version
            .as_str();
    let vr_crashgen = registry
        .get_crashgen_for_version("FO4_VR", vr_crashgen_version)
        .expect("VR crashgen");
    assert_eq!(vr_crashgen.acronym.as_str(), "BO4 NG");
    assert_eq!(vr_crashgen.dll_file.as_str(), "buffout4.dll");
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

    let filename = registry.get_address_library_filename(&GameVersion::new(1, 10, 163, 0), false);

    assert_eq!(filename, Some("version-1-10-163-0.bin".to_string()));
}

#[test]
fn test_get_crashgen_versions() {
    let registry = create_test_registry();

    for id in ["FO4_OG", "FO4_NG", "FO4_AE", "FO4_VR"] {
        let info = version_entry(&registry, id);
        let expected = crashgen_signature(&info.crashgen_versions);
        let actual = registry
            .get_crashgen_versions(id)
            .iter()
            .map(|config| {
                (
                    config.version.as_str(),
                    config.name.as_str(),
                    config.acronym.as_str(),
                    config.exact_match,
                )
            })
            .collect::<Vec<_>>();

        assert_eq!(actual, expected, "{id} crashgen configs changed");
    }

    let ae_configs = registry.get_crashgen_versions("FO4_AE");
    assert!(ae_configs.iter().any(|config| config.name == "Buffout 4"));
    assert!(ae_configs.iter().any(|config| config.name == "Addictol"));

    let vr_configs = registry.get_crashgen_versions("FO4_VR");
    assert!(vr_configs.iter().any(|config| config.name == "Buffout 4"));

    // Missing version returns empty vector
    let missing = registry.get_crashgen_versions("FO4_MISSING");
    assert!(missing.is_empty());
}

#[test]
fn test_get_crashgen_version_strings() {
    let registry = create_test_registry();

    for id in ["FO4_OG", "FO4_NG", "FO4_AE", "FO4_VR"] {
        let info = version_entry(&registry, id);
        let expected = floor_crashgen_versions(info);
        let actual = registry.get_crashgen_version_strings(id);
        assert_eq!(actual, expected, "{id} floor crashgen versions changed");
    }

    let missing = registry.get_crashgen_version_strings("FO4_MISSING");
    assert!(missing.is_empty());
}

#[test]
fn test_get_crashgen_for_version() {
    let registry = create_test_registry();
    let og = version_entry(&registry, "FO4_OG");

    // Find existing crashgens by the versions loaded from the YAML registry.
    for expected in og
        .crashgen_versions
        .iter()
        .filter(|config| config.name == "Buffout 4")
    {
        let actual = registry
            .get_crashgen_for_version("FO4_OG", expected.version.as_str())
            .expect("OG Buffout crashgen should exist");
        assert_eq!(actual.name, expected.name); // Name matches log output
        assert_eq!(actual.acronym, expected.acronym);
    }

    // Missing crashgen version returns None
    let absent_version = format!("missing-{}", og.crashgen_versions.len());
    assert!(
        og.crashgen_versions
            .iter()
            .all(|config| config.version != absent_version)
    );
    let missing_version = registry.get_crashgen_for_version("FO4_OG", &absent_version);
    assert!(missing_version.is_none());

    // Missing version ID returns None
    let known_version = og
        .crashgen_versions
        .first()
        .expect("OG should have crashgen versions")
        .version
        .as_str();
    let missing_id = registry.get_crashgen_for_version("FO4_MISSING", known_version);
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
fn test_crashgen_config_metadata_from_embedded_yaml() {
    let registry = create_test_registry();

    // Verify OG crashgen configs have proper metadata
    let og = version_entry(&registry, "FO4_OG");
    assert!(!og.crashgen_versions.is_empty());

    // Buffout 4 (legacy)
    let b4 = find_crashgen(og, "OG exact-match Buffout", |config| {
        config.name == "Buffout 4" && config.exact_match
    });
    assert!(!b4.description.is_empty());
    assert!(!b4.download_url.is_empty());

    // Buffout 4 NG (name matches log output, description identifies as NG)
    let b4ng = find_crashgen(og, "OG floor Buffout", |config| {
        config.name == "Buffout 4" && !config.exact_match
    });
    assert!(!b4ng.description.is_empty());
    assert!(!b4ng.download_url.is_empty());
}

#[test]
fn test_og_legacy_buffout_exact_match_flag() {
    let registry = create_test_registry();
    let og = version_entry(&registry, "FO4_OG");

    let legacy = find_crashgen(og, "OG legacy Buffout", |config| config.acronym == "BO4");
    assert!(legacy.exact_match);

    let ng = find_crashgen(og, "OG NG Buffout", |config| config.acronym == "BO4 NG");
    assert!(!ng.exact_match);

    let floor_versions = registry.get_crashgen_version_strings("FO4_OG");
    for config in &og.crashgen_versions {
        if config.exact_match {
            assert!(!floor_versions.contains(&config.version.as_str()));
        } else {
            assert!(floor_versions.contains(&config.version.as_str()));
        }
    }
}

#[test]
fn test_embedded_yaml_fallback_tracks_main_yaml_versions() {
    let embedded_registry = create_test_registry();
    let file_registry = VersionRegistry::load_from_yaml(&classic_main_yaml_path())
        .expect("checked-in CLASSIC Main.yaml should load");

    for id in ["FO4_OG", "FO4_NG", "FO4_AE", "FO4_VR"] {
        let embedded = version_entry(&embedded_registry, id);
        let from_file = version_entry(&file_registry, id);

        assert_eq!(embedded.version_string(), from_file.version_string());
        assert_eq!(
            embedded
                .xse
                .as_ref()
                .map(|xse| xse.compatible_version.as_str()),
            from_file
                .xse
                .as_ref()
                .map(|xse| xse.compatible_version.as_str())
        );
        assert_eq!(
            crashgen_signature(&embedded.crashgen_versions),
            crashgen_signature(&from_file.crashgen_versions),
            "{id} embedded crashgen data should match CLASSIC Main.yaml"
        );
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
