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

/// The move to shared core must keep each typed error variant and its message,
/// because bindings surface `VersionError::to_string()` to callers verbatim.
#[test]
fn test_parse_version_typed_errors_and_messages() {
    let empty = parse_version("").unwrap_err();
    assert!(matches!(empty, VersionError::EmptyVersion));
    assert_eq!(empty.to_string(), "Version string is empty");

    let short = parse_version("1").unwrap_err();
    assert!(matches!(short, VersionError::InvalidFormat(_)));
    assert_eq!(
        short.to_string(),
        "Invalid version format: Version must have at least major.minor: 1"
    );

    let bad_major = parse_version("x.1").unwrap_err();
    assert!(matches!(bad_major, VersionError::ParseError(_)));
    assert_eq!(
        bad_major.to_string(),
        "Invalid version string: Invalid major version: x"
    );

    let bad_patch = parse_version("1.2.z").unwrap_err();
    assert_eq!(
        bad_patch.to_string(),
        "Invalid version string: Invalid patch version: z"
    );
}

/// Loose parsing trims whitespace and leading `v` then `V` prefix characters and drops
/// the fourth (build) component; these are the observations callers rely on.
#[test]
fn test_parse_version_loose_normalization() {
    assert_eq!(parse_version("  V1.2  ").unwrap(), Version::new(1, 2, 0));
    assert_eq!(
        parse_version("1.10.163.99").unwrap(),
        Version::new(1, 10, 163)
    );
}

/// The PE helpers are re-exported at the `version` root for convenience; both
/// paths must name the same items.
#[test]
fn test_pe_helpers_reexported_at_version_root() {
    let missing = std::path::Path::new("nonexistent_file.exe");
    // Binding the root result to the module's error type proves both paths
    // name one `PeVersionError`, not two look-alike types.
    let via_root: pe_version::PeVersionResult<(u16, u16, u16, u16)> = extract_pe_version(missing);
    assert!(matches!(via_root, Err(PeVersionError::InvalidPath(_))));
    assert!(!is_valid_executable_path(missing));
    assert!(!pe_version::is_valid_executable_path(missing));
}
