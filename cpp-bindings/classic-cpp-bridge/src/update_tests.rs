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

// ---------------------------------------------------------------------------
// Notification DTO mapping (task 3.7)
// ---------------------------------------------------------------------------
//
// These tests drive `notification_status_to_dto` and
// `notification_error_dto` directly so they don't need network; the flatten
// rules (optional display, optional min_supported_version, empty-string
// sentinels) and the error classification string are pure functions.

use classic_update_core::{
    AppNotificationDisplay, Classification, NotificationStatus, UpdateError,
};

fn status_fixture(
    classification: Classification,
    min_supported_version: Option<&str>,
    display: Option<AppNotificationDisplay>,
    parse_error: Option<&str>,
) -> NotificationStatus {
    NotificationStatus {
        classification,
        latest_version: "9.2.0".into(),
        published_at: "2026-05-01T12:00:00Z".into(),
        min_supported_version: min_supported_version.map(String::from),
        display,
        parse_error: parse_error.map(String::from),
    }
}

#[test]
fn notification_dto_up_to_date_maps_classification_and_keeps_empty_display() {
    let status = status_fixture(Classification::UpToDate, None, None, None);
    let dto = notification_status_to_dto(&status);
    assert_eq!(dto.classification, "up_to_date");
    assert_eq!(dto.latest_version, "9.2.0");
    assert_eq!(dto.published_at, "2026-05-01T12:00:00Z");
    assert!(dto.min_supported_version.is_empty());
    assert!(dto.display_title.is_empty());
    assert!(dto.display_body.is_empty());
    assert!(dto.display_cta_url.is_empty());
    assert!(dto.parse_error.is_empty());
    assert!(dto.error_message.is_empty());
}

#[test]
fn notification_dto_update_available_flattens_display() {
    let display = AppNotificationDisplay {
        title: "New release".into(),
        body: "Bug fixes.".into(),
        cta_url: Some("https://example.invalid/changelog".into()),
    };
    let status = status_fixture(Classification::UpdateAvailable, None, Some(display), None);
    let dto = notification_status_to_dto(&status);
    assert_eq!(dto.classification, "update_available");
    assert_eq!(dto.display_title, "New release");
    assert_eq!(dto.display_body, "Bug fixes.");
    assert_eq!(dto.display_cta_url, "https://example.invalid/changelog");
    assert!(dto.error_message.is_empty());
}

#[test]
fn notification_dto_deprecated_client_populates_min_supported_version() {
    let status = status_fixture(Classification::DeprecatedClient, Some("9.0.0"), None, None);
    let dto = notification_status_to_dto(&status);
    assert_eq!(dto.classification, "deprecated_client");
    assert_eq!(dto.min_supported_version, "9.0.0");
}

#[test]
fn notification_dto_unknown_carries_parse_error() {
    let status = status_fixture(
        Classification::Unknown,
        None,
        None,
        Some("installed version `bogus` is not a valid semver"),
    );
    let dto = notification_status_to_dto(&status);
    assert_eq!(dto.classification, "unknown");
    assert!(dto.parse_error.contains("bogus"));
    assert!(dto.error_message.is_empty());
}

#[test]
fn notification_dto_not_published_uses_dedicated_classification_and_no_error() {
    assert_eq!(
        classification_label(Classification::NotPublished),
        "not_published"
    );

    let status = NotificationStatus {
        classification: Classification::NotPublished,
        latest_version: String::new(),
        published_at: String::new(),
        min_supported_version: None,
        display: None,
        parse_error: None,
    };

    let dto = notification_status_to_dto(&status);
    assert_eq!(dto.classification, "not_published");
    assert!(dto.latest_version.is_empty());
    assert!(dto.published_at.is_empty());
    assert!(dto.min_supported_version.is_empty());
    assert!(dto.display_title.is_empty());
    assert!(dto.display_body.is_empty());
    assert!(dto.display_cta_url.is_empty());
    assert!(dto.parse_error.is_empty());
    assert!(dto.error_message.is_empty());
}

#[test]
fn notification_dto_display_without_cta_url_has_empty_sentinel() {
    // When `display.cta_url` is None, the flattened DTO field is the
    // empty string — not a missing field — so C++ can reason with a
    // single branch: "empty == absent".
    let display = AppNotificationDisplay {
        title: "Heads up".into(),
        body: "Read more in the release notes.".into(),
        cta_url: None,
    };
    let status = status_fixture(Classification::UpdateAvailable, None, Some(display), None);
    let dto = notification_status_to_dto(&status);
    assert_eq!(dto.display_title, "Heads up");
    assert!(
        dto.display_cta_url.is_empty(),
        "missing cta_url must flatten to empty-string sentinel",
    );
}

#[test]
fn notification_error_dto_uses_error_classification_and_empty_sentinels() {
    // Mirrors the spec's "CXX DTO on error" scenario: classification =
    // "error", error_message populated with Display rendering, every
    // other string field empty per docs/api/error-contract.md.
    let err = UpdateError::NotificationFetchFailed {
        pages_error: "pages 500".into(),
        releases_error: "releases timeout".into(),
    };
    let dto = notification_error_dto(&err);
    assert_eq!(dto.classification, "error");
    assert!(dto.error_message.contains("pages 500"));
    assert!(dto.error_message.contains("releases timeout"));
    assert!(dto.latest_version.is_empty());
    assert!(dto.published_at.is_empty());
    assert!(dto.min_supported_version.is_empty());
    assert!(dto.display_title.is_empty());
    assert!(dto.display_body.is_empty());
    assert!(dto.display_cta_url.is_empty());
    assert!(dto.parse_error.is_empty());
}

#[test]
fn notification_error_dto_preserves_variant_specific_display() {
    // Different UpdateError variants render to distinct Display strings;
    // the DTO must forward the Display output verbatim so C++ can
    // surface the operator-meaningful text (missing field name, etc.).
    let err = UpdateError::NotificationDecode {
        field: "latest_version".into(),
    };
    let dto = notification_error_dto(&err);
    assert_eq!(dto.classification, "error");
    assert!(dto.error_message.contains("latest_version"));
}

#[test]
fn yaml_apply_update_accepts_structured_request_and_short_circuits_when_disabled() {
    let request = ffi::YamlApplyRequestDto {
        pages_url: "http://127.0.0.1:1/manifest-latest.json".into(),
        tag_prefix: "yaml-data-v".into(),
        entries: vec![ffi::YamlClientSchemaEntryDto {
            name: "CLASSIC Main.yaml".into(),
            accepted_major: 1,
            accepted_minimum_minor: 0,
            has_installed: false,
            installed_major: 0,
            installed_minor: 0,
        }],
        enabled: false,
        approved: ffi::ApprovedUpdateDto {
            release_tag: "yaml-data-v-test".into(),
            file_names: vec!["CLASSIC Main.yaml".into()],
            file_sha256: vec!["deadbeef".into()],
        },
        bundled_yaml_dir: String::new(),
    };

    let dto = yaml_apply_update(&request);
    assert!(dto.installed.is_empty());
    assert!(dto.failed.is_empty());
    assert!(dto.error_message.starts_with("update check disabled:"));
}
