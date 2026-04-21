use super::*;
use crate::defaults;
use std::collections::HashMap;

// Helper to create a test registry
fn create_test_registry() -> VersionRegistry {
    let versions = defaults::get_default_versions();
    let unknown_handling = defaults::get_default_unknown_handling();

    let mut by_version = HashMap::new();
    for version in versions.values() {
        by_version.insert(version.version_string(), version.clone());
    }

    VersionRegistry::new_for_testing(versions, by_version, unknown_handling)
}

#[test]
fn test_exact_match() {
    let registry = create_test_registry();
    let matcher = VersionMatcher::new(&registry);

    let detected = GameVersion::new(1, 10, 163, 0);
    let result = matcher.match_version(&detected, "Fallout4", false);

    assert_eq!(result.confidence, MatchConfidence::Exact);
    assert!(result.is_exact());
    assert!(!result.should_warn());
    assert!(result.is_valid());
    assert_eq!(result.version_info.as_ref().unwrap().id, "FO4_OG");
}

#[test]
fn test_exact_match_ng() {
    let registry = create_test_registry();
    let matcher = VersionMatcher::new(&registry);

    let detected = GameVersion::new(1, 10, 984, 0);
    let result = matcher.match_version(&detected, "Fallout4", false);

    assert_eq!(result.confidence, MatchConfidence::Exact);
    assert_eq!(result.version_info.as_ref().unwrap().id, "FO4_NG");
}

#[test]
fn test_exact_match_vr() {
    let registry = create_test_registry();
    let matcher = VersionMatcher::new(&registry);

    let detected = GameVersion::new(1, 2, 72, 0);
    let result = matcher.match_version(&detected, "Fallout4", true);

    assert_eq!(result.confidence, MatchConfidence::Exact);
    assert_eq!(result.version_info.as_ref().unwrap().id, "FO4_VR");
}

#[test]
fn test_nearest_match() {
    let registry = create_test_registry();
    let matcher = VersionMatcher::new(&registry);

    // Version between OG and NG
    let detected = GameVersion::new(1, 10, 500, 0);
    let result = matcher.match_version(&detected, "Fallout4", false);

    assert_eq!(result.confidence, MatchConfidence::Nearest);
    assert!(result.should_warn());
    assert!(result.is_valid());
    // Should match OG (closer: 337) over NG (484)
    assert_eq!(result.version_info.as_ref().unwrap().id, "FO4_OG");
}

#[test]
fn test_nearest_match_prefers_higher_priority() {
    let registry = create_test_registry();
    let matcher = VersionMatcher::new(&registry);

    // Version close to NG - should prefer NG due to higher priority
    let detected = GameVersion::new(1, 10, 800, 0);
    let result = matcher.match_version(&detected, "Fallout4", false);

    assert_eq!(result.confidence, MatchConfidence::Nearest);
    // NG is closer (184) than OG (637)
    assert_eq!(result.version_info.as_ref().unwrap().id, "FO4_NG");
}

#[test]
fn test_vr_mode_filtering() {
    let registry = create_test_registry();
    let matcher = VersionMatcher::new(&registry);

    // OG version number but VR mode - should not match
    let detected = GameVersion::new(1, 10, 163, 0);
    let result = matcher.match_version(&detected, "Fallout4", true);

    // Should fall back to nearest or default
    assert_ne!(result.confidence, MatchConfidence::Exact);
    if let Some(info) = &result.version_info {
        assert!(info.is_vr);
    }
}

#[test]
fn test_match_result_properties() {
    let result = MatchResult::new(
        None,
        MatchConfidence::Unknown,
        GameVersion::new(0, 0, 0, 0),
        "test",
    );

    assert!(!result.is_exact());
    assert!(result.is_fallback());
    assert!(!result.should_warn()); // Unknown doesn't warn
    assert!(!result.is_valid());
}
