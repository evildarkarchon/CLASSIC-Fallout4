//! `pages_url` cases ported from the retired Python suites'
//! `build_pages_url` tests (yaml-data and app-notification).

use super::*;

#[test]
fn live_url_supports_the_app_notification_path() {
    assert_eq!(
        pages_url(
            Some("classic-owner"),
            Some("classic-repo"),
            "app-notification/manifest-latest.json",
            None
        )
        .as_deref(),
        Some("https://classic-owner.github.io/classic-repo/app-notification/manifest-latest.json")
    );
}

#[test]
fn live_url_is_built_from_owner_and_repo() {
    assert_eq!(
        pages_url(
            Some("owner"),
            Some("repo"),
            "/yaml-data/manifest-latest.json",
            None
        )
        .as_deref(),
        Some("https://owner.github.io/repo/yaml-data/manifest-latest.json")
    );
}

#[test]
fn base_url_overrides_owner_and_repo_and_collapses_the_join() {
    assert_eq!(
        pages_url(
            None,
            None,
            "/app-notification/manifest-latest.json",
            Some("http://127.0.0.1:9/gh-pages/")
        )
        .as_deref(),
        Some("http://127.0.0.1:9/gh-pages/app-notification/manifest-latest.json")
    );
}

#[test]
fn without_a_base_url_owner_and_repo_are_required() {
    assert_eq!(pages_url(Some("owner"), None, "x.json", None), None);
    assert_eq!(pages_url(None, Some("repo"), "x.json", Some("")), None);
}
