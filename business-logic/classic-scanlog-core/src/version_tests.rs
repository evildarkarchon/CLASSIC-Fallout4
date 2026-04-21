use super::*;

#[test]
fn test_parse_simple_version() {
    let v = CrashgenVersion::parse("1.28.0").unwrap();
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 28);
    assert_eq!(v.patch, 0);
}

#[test]
fn test_parse_version_with_v_prefix() {
    let v = CrashgenVersion::parse("v1.29.1").unwrap();
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 29);
    assert_eq!(v.patch, 1);
}

#[test]
fn test_parse_version_from_crashgen_string() {
    let v = CrashgenVersion::parse("Buffout 4 v1.30.2").unwrap();
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 30);
    assert_eq!(v.patch, 2);
}

#[test]
fn test_parse_version_without_patch() {
    let v = CrashgenVersion::parse("1.28").unwrap();
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 28);
    assert_eq!(v.patch, 0);
}

#[test]
fn test_version_comparison() {
    let v1 = CrashgenVersion::new(1, 26, 0);
    let v2 = CrashgenVersion::new(1, 28, 0);
    let v3 = CrashgenVersion::new(1, 28, 1);

    assert!(v1 < v2);
    assert!(v2 < v3);
    assert!(v1 < v3);
}

// Replacement tests for deprecated is_outdated method -- now exercise check_version_status directly

#[test]
fn test_check_version_status_non_vr_outdated_scenario() {
    // Replaces test_is_outdated_non_vr: version 1.26.0 is outdated against valid [1.28.0]
    let current = CrashgenVersion::new(1, 26, 0);
    let valid = vec![CrashgenVersion::new(1, 28, 0)];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Outdated);
}

#[test]
fn test_check_version_status_vr_outdated_scenario() {
    // Replaces test_is_outdated_vr: version 1.26.0 is outdated against VR valid [1.27.0]
    let current = CrashgenVersion::new(1, 26, 0);
    let valid = vec![CrashgenVersion::new(1, 27, 0)];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Outdated);
}

#[test]
fn test_check_version_status_vr_matches_valid() {
    // Replaces test_not_outdated_when_matches_latest: version 1.28.0 matches a VR valid entry
    let current = CrashgenVersion::new(1, 28, 0);
    let valid = vec![
        CrashgenVersion::new(1, 27, 0),
        CrashgenVersion::new(1, 28, 0),
    ];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Valid);
}

#[test]
fn test_check_version_status_vr_newer_than_known() {
    // VR version 1.30.0 is newer than all known VR valid versions [1.27.0, 1.28.0]
    let current = CrashgenVersion::new(1, 30, 0);
    let valid = vec![
        CrashgenVersion::new(1, 27, 0),
        CrashgenVersion::new(1, 28, 0),
    ];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::NewerThanKnown);
}

#[test]
fn test_check_version_status_vr_empty_valid_list() {
    // Any version checked against empty VR valid list returns NoSupportedVersion
    let current = CrashgenVersion::new(1, 27, 0);
    let valid: Vec<CrashgenVersion> = vec![];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::NoSupportedVersion);
}

#[test]
fn test_check_version_status_vr_single_valid() {
    // VR version exactly matching the single valid entry returns Valid
    let current = CrashgenVersion::new(1, 27, 0);
    let valid = vec![CrashgenVersion::new(1, 27, 0)];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Valid);
}

#[test]
fn test_check_version_status_vr_between_entries() {
    // VR version 1.27.5 between valid entries [1.27.0, 1.28.0] is not in list, below max
    let current = CrashgenVersion::new(1, 27, 5);
    let valid = vec![
        CrashgenVersion::new(1, 27, 0),
        CrashgenVersion::new(1, 28, 0),
    ];
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Outdated);
}

#[test]
fn test_crashgen_version_gen() {
    let v = crashgen_version_gen("v1.28.0");
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 28);

    // Invalid version defaults to 0.0.0
    let v_invalid = crashgen_version_gen("invalid");
    assert_eq!(v_invalid.major, 0);
}

// ========== List-based version checking tests ==========

#[test]
fn test_check_version_status_valid() {
    let current = CrashgenVersion::new(1, 28, 6);
    let valid = vec![
        CrashgenVersion::new(1, 28, 6),
        CrashgenVersion::new(1, 37, 0),
    ];

    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Valid);
}

#[test]
fn test_check_version_status_valid_second_option() {
    let current = CrashgenVersion::new(1, 37, 0);
    let valid = vec![
        CrashgenVersion::new(1, 28, 6),
        CrashgenVersion::new(1, 37, 0),
    ];

    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Valid);
}

#[test]
fn test_check_version_status_outdated() {
    let current = CrashgenVersion::new(1, 26, 0);
    let valid = vec![
        CrashgenVersion::new(1, 28, 6),
        CrashgenVersion::new(1, 37, 0),
    ];

    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Outdated);
}

#[test]
fn test_check_version_status_newer_than_known() {
    let current = CrashgenVersion::new(1, 40, 0);
    let valid = vec![
        CrashgenVersion::new(1, 28, 6),
        CrashgenVersion::new(1, 37, 0),
    ];

    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::NewerThanKnown);
}

#[test]
fn test_check_version_status_no_supported_version() {
    let current = CrashgenVersion::new(1, 28, 6);
    let valid: Vec<CrashgenVersion> = vec![];

    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::NoSupportedVersion);
}

#[test]
fn test_check_crashgen_version_status_convenience() {
    // Valid version
    let status = check_crashgen_version_status("1.28.6", &["1.28.6", "1.37.0"]);
    assert_eq!(status, CrashgenVersionStatus::Valid);

    // Outdated version
    let status = check_crashgen_version_status("1.26.0", &["1.28.6", "1.37.0"]);
    assert_eq!(status, CrashgenVersionStatus::Outdated);

    // Newer than known
    let status = check_crashgen_version_status("1.40.0", &["1.28.6", "1.37.0"]);
    assert_eq!(status, CrashgenVersionStatus::NewerThanKnown);

    // No supported version
    let status = check_crashgen_version_status("1.28.6", &[]);
    assert_eq!(status, CrashgenVersionStatus::NoSupportedVersion);
}

#[test]
fn test_check_version_status_between_valid_versions() {
    // Version 1.30.0 is between 1.28.6 and 1.37.0 but not in the list
    let current = CrashgenVersion::new(1, 30, 0);
    let valid = vec![
        CrashgenVersion::new(1, 28, 6),
        CrashgenVersion::new(1, 37, 0),
    ];

    // This should be outdated because it's not in the valid list
    // and is less than the max valid version
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Outdated);
}

#[test]
fn test_version_equality_ignores_original_string() {
    // Parse from different string formats that yield the same version
    let v1 = CrashgenVersion::parse("Buffout 4 v1.28.6").unwrap();
    let v2 = CrashgenVersion::parse("1.28.6").unwrap();
    let v3 = CrashgenVersion::parse("v1.28.6").unwrap();

    // Verify they have different original strings
    assert_ne!(v1.original, v2.original);
    assert_ne!(v1.original, v3.original);

    // But they should be equal because major/minor/patch are the same
    assert_eq!(v1, v2);
    assert_eq!(v1, v3);
    assert_eq!(v2, v3);
}

#[test]
fn test_check_version_status_with_different_original_strings() {
    // This is the real-world scenario: crash log contains "Buffout 4 v1.28.6"
    // but valid versions list contains "1.28.6"
    let current = CrashgenVersion::parse("Buffout 4 v1.28.6").unwrap();
    let valid = vec![
        CrashgenVersion::parse("1.28.6").unwrap(),
        CrashgenVersion::parse("1.37.0").unwrap(),
    ];

    // Should be Valid because version numbers match, regardless of original string
    let status = current.check_version_status(&valid);
    assert_eq!(status, CrashgenVersionStatus::Valid);
}

#[test]
fn test_check_crashgen_version_status_with_crashgen_prefix() {
    // Test the convenience function with real-world inputs
    let status = check_crashgen_version_status("Buffout 4 v1.28.6", &["1.28.6", "1.37.0"]);
    assert_eq!(status, CrashgenVersionStatus::Valid);

    let status = check_crashgen_version_status("Buffout 4 v1.37.0", &["1.28.6", "1.37.0"]);
    assert_eq!(status, CrashgenVersionStatus::Valid);

    let status = check_crashgen_version_status("Buffout 4 v1.26.0", &["1.28.6", "1.37.0"]);
    assert_eq!(status, CrashgenVersionStatus::Outdated);
}

#[test]
fn test_is_fake_bot_compatible_buffout_version_detects_low_fake_version() {
    assert!(is_fake_bot_compatible_buffout_version("Buffout 4 v1.1.0"));
    assert!(is_fake_bot_compatible_buffout_version("Buffout 4 v1.19.9"));
    assert!(!is_fake_bot_compatible_buffout_version("Buffout 4 v1.28.6"));
    assert!(!is_fake_bot_compatible_buffout_version(
        "Addictol v1.1.0 Feb 16 2026 08:02:06"
    ));
}
