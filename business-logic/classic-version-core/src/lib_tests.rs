use super::*;

#[test]
fn test_parse_version() {
    assert_eq!(parse_version("1.10.163").unwrap(), Version::new(1, 10, 163));
    assert_eq!(
        parse_version("1.10.163.0").unwrap(),
        Version::new(1, 10, 163)
    );
    assert_eq!(
        parse_version("v1.10.163").unwrap(),
        Version::new(1, 10, 163)
    );
    assert_eq!(parse_version("0.6.23").unwrap(), Version::new(0, 6, 23));
}

#[test]
fn test_parse_version_errors() {
    assert!(parse_version("").is_err());
    assert!(parse_version("invalid").is_err());
    assert!(parse_version("1").is_err());
}

#[test]
fn test_try_parse_version() {
    assert!(try_parse_version("1.10.163").is_some());
    assert!(try_parse_version("invalid").is_none());
}

#[test]
fn test_compare_versions() {
    let v1 = Version::new(1, 10, 163);
    let v2 = Version::new(1, 10, 984);
    assert_eq!(compare_versions(&v1, &v2), Ordering::Less);
    assert_eq!(compare_versions(&v2, &v1), Ordering::Greater);
    assert_eq!(compare_versions(&v1, &v1), Ordering::Equal);
}

#[test]
fn test_is_known_fallout4_version() {
    // Use VersionRegistry to get known versions
    let registry = get_version_registry();

    // Get OG version from registry
    if let Some(og_info) = registry.get_by_id("FO4_OG") {
        let og_version = Version::new(
            u64::from(og_info.version.major),
            u64::from(og_info.version.minor),
            u64::from(og_info.version.patch),
        );
        assert!(is_known_fallout4_version(&og_version));
    }

    // Get NG version from registry
    if let Some(ng_info) = registry.get_by_id("FO4_NG") {
        let ng_version = Version::new(
            u64::from(ng_info.version.major),
            u64::from(ng_info.version.minor),
            u64::from(ng_info.version.patch),
        );
        assert!(is_known_fallout4_version(&ng_version));
    }

    // Unknown version should not be known
    assert!(!is_known_fallout4_version(&Version::new(9, 9, 9)));
}

#[test]
fn test_is_known_f4se_version() {
    // Use VersionRegistry to get known F4SE versions
    let registry = get_version_registry();

    // Get OG F4SE version from registry
    if let Some(og_info) = registry.get_by_id("FO4_OG")
        && let Some(xse) = &og_info.xse
        && let Some(parsed) = try_parse_version(&xse.compatible_version)
    {
        assert!(is_known_f4se_version(&parsed));
    }

    // Get NG F4SE version from registry
    if let Some(ng_info) = registry.get_by_id("FO4_NG")
        && let Some(xse) = &ng_info.xse
        && let Some(parsed) = try_parse_version(&xse.compatible_version)
    {
        assert!(is_known_f4se_version(&parsed));
    }

    // Unknown version should not be known
    assert!(!is_known_f4se_version(&Version::new(9, 9, 9)));
}

#[test]
fn test_extract_version_from_filename() {
    assert_eq!(
        extract_version_from_filename("MyMod-v1.2.3.esp"),
        Some(Version::new(1, 2, 3))
    );
    assert_eq!(
        extract_version_from_filename("MyMod_1.2.3.esp"),
        Some(Version::new(1, 2, 3))
    );
    assert_eq!(
        extract_version_from_filename("MyMod-1.2.3.4-suffix.esp"),
        Some(Version::new(1, 2, 3))
    );
    assert!(extract_version_from_filename("NoVersion.esp").is_none());
}

#[test]
fn test_extract_version_from_log() {
    let log = "F4SE version: 0.6.23\nGame version: 1.10.163";
    let version = extract_version_from_log(log).unwrap();
    assert_eq!(version, Version::new(0, 6, 23));
}

#[test]
fn test_extract_all_versions() {
    let text = "Supports versions 1.10.163 and 1.10.984";
    let versions = extract_all_versions(text);
    assert_eq!(versions.len(), 2);
    assert!(versions.contains(&Version::new(1, 10, 163)));
    assert!(versions.contains(&Version::new(1, 10, 984)));
}

#[test]
fn test_format_version() {
    let v = Version::new(1, 10, 163);
    assert_eq!(format_version(&v, Some("v")), "v1.10.163");
    assert_eq!(format_version(&v, None), "1.10.163");
}
