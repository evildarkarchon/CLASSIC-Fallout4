use super::*;

#[test]
fn test_version_registry_get_all_count_at_least_four() {
    assert!(version_registry_get_all_count() >= 4);
}

#[test]
fn test_version_registry_get_all_ids_nonempty() {
    let ids = version_registry_get_all_ids();
    assert!(!ids.is_empty());
}

#[test]
fn test_version_registry_get_by_id_unknown_returns_not_found() {
    let result = version_registry_get_by_id("DEFINITELY_NOT_REAL_VERSION_ID");
    assert!(!result.found);
}

#[test]
fn test_version_registry_get_all_for_game_fallout4_non_vr() {
    let entries = version_registry_get_all_for_game("Fallout4", false);
    assert!(
        !entries.is_empty(),
        "Fallout4 should have at least one non-VR variant"
    );
    for entry in &entries {
        assert!(!entry.is_vr);
        assert_eq!(entry.game, "Fallout4");
    }
}

#[test]
fn test_version_registry_get_all_for_game_fallout4_vr() {
    let entries = version_registry_get_all_for_game("Fallout4", true);
    for entry in &entries {
        assert!(entry.is_vr);
        assert_eq!(entry.game, "Fallout4");
    }
}

#[test]
fn test_parse_game_version_valid() {
    let v = parse_game_version("1.10.163.0");
    assert!(v.valid);
    assert_eq!(v.major, 1);
    assert_eq!(v.minor, 10);
    assert_eq!(v.patch, 163);
}

#[test]
fn test_parse_game_version_invalid() {
    assert!(!parse_game_version("garbage").valid);
}
