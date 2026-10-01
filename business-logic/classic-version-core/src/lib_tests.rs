use super::*;

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

/// Until this crate retires (#258), its loose-parsing and PE paths are a
/// facade over `classic_shared_core::version`. Binding facade results to the
/// owner's types proves they are the same items, not drifting copies.
#[test]
fn test_facade_reexports_shared_core_owner() {
    use classic_shared_core::version as owner;

    let parsed: owner::VersionResult<Version> = parse_version("");
    assert!(matches!(parsed, Err(owner::VersionError::EmptyVersion)));

    let pe: owner::pe_version::PeVersionResult<(u16, u16, u16, u16)> =
        pe_version::extract_pe_version(std::path::Path::new("nonexistent.exe"));
    assert!(matches!(
        pe,
        Err(owner::pe_version::PeVersionError::InvalidPath(_))
    ));

    assert_eq!(
        format_version(&Version::new(1, 10, 163), Some("v")),
        owner::format_version(&Version::new(1, 10, 163), Some("v"))
    );
}
