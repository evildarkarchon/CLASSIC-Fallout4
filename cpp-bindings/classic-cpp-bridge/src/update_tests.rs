use super::*;

#[test]
fn test_has_update_older() {
    assert!(github_has_update("1.0.0", "2.0.0"));
}

#[test]
fn test_has_update_same() {
    assert!(!github_has_update("1.0.0", "1.0.0"));
}

#[test]
fn test_has_update_newer() {
    assert!(!github_has_update("2.0.0", "1.0.0"));
}

#[test]
fn test_has_update_prerelease() {
    assert!(github_has_update("1.0.0-alpha", "1.0.0"));
}

#[test]
fn test_has_update_invalid_version() {
    // Invalid versions should return false (no update)
    assert!(!github_has_update("not_a_version", "1.0.0"));
}

#[test]
#[ignore] // Requires network access
fn test_check_for_updates_network() {
    let result = github_check_for_updates("evildarkarchon", "CLASSIC-Fallout4", "0.0.1");
    assert!(result.error_message.is_empty());
    assert!(!result.latest_version.is_empty());
}

#[test]
fn yaml_check_update_disabled_short_circuits() {
    let entries = vec![ffi::YamlClientSchemaEntryDto {
        name: "CLASSIC Main.yaml".into(),
        accepted_major: 1,
        accepted_minimum_minor: 0,
        has_installed: false,
        installed_major: 0,
        installed_minor: 0,
    }];
    // Pass a deliberately-unreachable Pages URL. If Disabled short-
    // circuit is broken, this would hang or produce a non-Disabled tag.
    let dto = yaml_check_update(
        "http://127.0.0.1:1/manifest-latest.json",
        "yaml-data-v",
        &entries,
        false,
        "",
    );
    assert_eq!(dto.tag, TAG_DISABLED);
    assert!(dto.error_message.is_empty());
}

#[test]
fn yaml_rollback_update_returns_no_prev_for_unknown_file() {
    let dto = yaml_rollback_update("__cpp_bridge_definitely_nonexistent_file_xyzzy__.yaml");
    // Either the rollback ran and found nothing to roll back, or the
    // cache dir itself was unresolvable — either is a valid
    // non-panic outcome for a machine without the cache populated.
    if dto.error_message.is_empty() {
        assert!(!dto.rolled_back);
    }
}
