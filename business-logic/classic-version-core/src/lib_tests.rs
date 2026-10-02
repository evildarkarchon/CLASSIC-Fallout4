use super::*;
use semver::Version;

/// Until this crate retires (#258), its known-version paths are a facade over
/// the Version Registry owner (#244); both answer from the same default
/// snapshot, for known and unknown inputs alike.
#[test]
fn test_facade_reexports_version_registry_known_queries() {
    use classic_version_registry_core as owner;

    for version in [
        Version::new(1, 10, 163),
        Version::new(1, 10, 984),
        Version::new(0, 6, 23),
        Version::new(9, 9, 9),
    ] {
        assert_eq!(
            is_known_fallout4_version(&version),
            owner::get_version_registry().is_known_fallout4_version(&version)
        );
        assert_eq!(
            is_known_f4se_version(&version),
            owner::get_version_registry().is_known_f4se_version(&version)
        );
    }
    assert!(is_known_fallout4_version(&Version::new(1, 10, 163)));
    assert!(is_known_f4se_version(&Version::new(0, 6, 23)));
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
