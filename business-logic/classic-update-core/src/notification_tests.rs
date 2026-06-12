use super::*;

// ---------------------------------------------------------------------------
// Manifest deserialization + validation
// ---------------------------------------------------------------------------

fn minimal_manifest_json() -> &'static str {
    r#"{
        "manifest_version": "1.0",
        "release_tag": "v9.2.0",
        "latest_version": "9.2.0",
        "published_at": "2026-05-01T12:00:00Z"
    }"#
}

#[test]
fn manifest_deserializes_without_display_block() {
    let m = parse_notification_manifest(minimal_manifest_json().as_bytes()).unwrap();
    assert_eq!(m.manifest_version, "1.0");
    assert_eq!(m.release_tag, "v9.2.0");
    assert_eq!(m.latest_version, "9.2.0");
    assert_eq!(m.published_at, "2026-05-01T12:00:00Z");
    assert!(m.min_supported_version.is_none());
    assert!(m.display.is_none());
}

#[test]
fn manifest_deserializes_with_full_display_block() {
    let body = r#"{
        "manifest_version": "1.0",
        "release_tag": "v9.2.0",
        "latest_version": "9.2.0",
        "published_at": "2026-05-01T12:00:00Z",
        "min_supported_version": "9.0.0",
        "display": {
            "title": "New release",
            "body": "Bug fixes and improvements.",
            "cta_url": "https://example.invalid/changelog"
        }
    }"#;
    let m = parse_notification_manifest(body.as_bytes()).unwrap();
    assert_eq!(m.min_supported_version.as_deref(), Some("9.0.0"));
    let d = m.display.expect("display populated");
    assert_eq!(d.title, "New release");
    assert_eq!(d.body, "Bug fixes and improvements.");
    assert_eq!(
        d.cta_url.as_deref(),
        Some("https://example.invalid/changelog")
    );
}

#[test]
fn manifest_deserialization_tolerates_unknown_fields() {
    let body = r#"{
        "manifest_version": "1.0",
        "release_tag": "v9.2.0",
        "latest_version": "9.2.0",
        "published_at": "2026-05-01T12:00:00Z",
        "unknown_future_field": {"nested": "data"},
        "another_new_key": 42
    }"#;
    let m = parse_notification_manifest(body.as_bytes())
        .expect("unknown fields must not break deserialization");
    assert_eq!(m.release_tag, "v9.2.0");
}

#[test]
fn manifest_deserialize_missing_required_field_errors() {
    // Missing `latest_version` field — serde's missing-field error should
    // be projected into `NotificationDecode { field: "latest_version" }`.
    let body = r#"{
        "manifest_version": "1.0",
        "release_tag": "v9.2.0",
        "published_at": "2026-05-01T12:00:00Z"
    }"#;
    let err = parse_notification_manifest(body.as_bytes()).unwrap_err();
    match err {
        UpdateError::NotificationDecode { field } => {
            assert_eq!(field, "latest_version");
        }
        other => panic!("expected NotificationDecode, got {other:?}"),
    }
}

#[test]
fn validate_manifest_accepts_valid() {
    let m = AppNotificationManifest {
        manifest_version: "1.0".into(),
        release_tag: "v9.2.0".into(),
        latest_version: "9.2.0".into(),
        published_at: "2026-05-01T12:00:00Z".into(),
        min_supported_version: None,
        display: None,
    };
    validate_notification_manifest(&m).expect("baseline manifest must validate");
}

#[test]
fn validate_manifest_rejects_bad_manifest_version_shapes() {
    let bad_versions = [
        "1",        // single component
        "1.0-beta", // pre-release tag
        "1.0.0",    // three components
        "1.",       // trailing dot
        ".0",       // leading dot
        "v1.0",     // unexpected prefix
        "one.zero", // non-numeric
        "",         // empty
    ];
    for v in bad_versions {
        let m = AppNotificationManifest {
            manifest_version: v.into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: None,
            display: None,
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(err, UpdateError::NotificationDecode { ref field } if field == "manifest_version"),
            "expected manifest_version decode failure for {v:?}, got {err:?}"
        );
    }
}

#[test]
fn validate_manifest_rejects_major_above_client_max() {
    // The client declares `MAX_NOTIFICATION_MANIFEST_MAJOR = 1`, so any
    // manifest advertising a higher MAJOR must be refused with the typed
    // `ManifestUnsupportedVersion` variant (NOT a generic `NotificationDecode`).
    // This is the variant `manifest_fetch::PagesError::UnsupportedVersion`
    // routes past the Releases fallback.
    let higher_majors = ["2.0", "2.15", "10.0", "99.99"];
    for v in higher_majors {
        let m = AppNotificationManifest {
            manifest_version: v.into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: None,
            display: None,
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(
                err,
                UpdateError::ManifestUnsupportedVersion { max_supported, .. }
                    if max_supported == MAX_NOTIFICATION_MANIFEST_MAJOR
            ),
            "expected ManifestUnsupportedVersion for {v:?}, got {err:?}"
        );
    }
}

#[test]
fn validate_manifest_accepts_supported_major_any_minor() {
    // Serde tolerates unknown fields and MINOR bumps SHOULD not break
    // older clients — validate must accept any MINOR within the supported
    // MAJOR. `1.0` through `1.999` all pass.
    for v in ["1.0", "1.1", "1.99", "1.999"] {
        let m = AppNotificationManifest {
            manifest_version: v.into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: None,
            display: None,
        };
        validate_notification_manifest(&m)
            .unwrap_or_else(|e| panic!("expected {v:?} to validate, got {e:?}"));
    }
}

#[test]
fn validate_manifest_rejects_empty_required_fields() {
    let baseline = AppNotificationManifest {
        manifest_version: "1.0".into(),
        release_tag: "v9.2.0".into(),
        latest_version: "9.2.0".into(),
        published_at: "2026-05-01T12:00:00Z".into(),
        min_supported_version: None,
        display: None,
    };

    for field in ["latest_version", "published_at", "release_tag"] {
        let mut m = baseline.clone();
        match field {
            "latest_version" => m.latest_version.clear(),
            "published_at" => m.published_at.clear(),
            "release_tag" => m.release_tag.clear(),
            _ => unreachable!(),
        }
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(err, UpdateError::NotificationDecode { field: ref f } if f == field),
            "expected NotificationDecode for empty `{field}`, got {err:?}"
        );
    }
}

#[test]
fn validate_manifest_rejects_bad_semver_in_latest_version() {
    // A future "9.x" / "9-rc" in `latest_version` must be rejected at
    // validate time so the cache cannot be poisoned with a body that a
    // later 304 path would return verbatim. Classify's defensive
    // `Unknown` branch is the second line of defense, not the first.
    for v in ["9.x", "9-rc", "nine", "9.2", "9.2.3.4", ""] {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.2.0".into(),
            latest_version: v.into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: None,
            display: None,
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(err, UpdateError::NotificationDecode { ref field } if field == "latest_version"),
            "expected latest_version decode failure for {v:?}, got {err:?}"
        );
    }
}

#[test]
fn validate_manifest_rejects_bad_semver_in_min_supported_version() {
    // A mistyped `min_supported_version` would otherwise let deprecated
    // clients keep running without the warning — `classify` silently
    // skips the min-version branch on parse failure. Reject at validate.
    for v in ["9.x", "nine", "9.0-", "9"] {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: Some(v.into()),
            display: None,
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(
                err,
                UpdateError::NotificationDecode { ref field } if field == "min_supported_version"
            ),
            "expected min_supported_version decode failure for {v:?}, got {err:?}"
        );
    }
}

#[test]
fn validate_manifest_rejects_min_supported_above_latest() {
    // Regression: Codex adversarial-review finding. Each field parses
    // individually, but the invariant `min_supported_version <=
    // latest_version` is load-bearing — `classify` gives
    // `min_supported_version` precedence, so a mistyped pair would
    // falsely mark the advertised latest build as DeprecatedClient.
    let cases = [
        ("9.1.0", "9.2.0"),
        ("9.1.0", "10.0.0"),
        ("9.1.0", "9.1.1"),
        // Leading `v` on either side is tolerated individually; the
        // cross-field check must be prefix-agnostic too.
        ("9.1.0", "v9.2.0"),
        ("v9.1.0", "9.2.0"),
    ];
    for (latest, min) in cases {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.1.0".into(),
            latest_version: latest.into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: Some(min.into()),
            display: None,
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        match err {
            UpdateError::ManifestInvalid { reason } => {
                assert!(
                    reason.contains("min_supported_version"),
                    "reason must name the offending field: {reason}"
                );
                assert!(
                    reason.contains(latest),
                    "reason must cite latest_version {latest:?}: {reason}"
                );
                assert!(
                    reason.contains(min),
                    "reason must cite min_supported_version {min:?}: {reason}"
                );
            }
            other => {
                panic!("expected ManifestInvalid for min={min:?}, latest={latest:?}, got {other:?}")
            }
        }
    }
}

#[test]
fn validate_manifest_accepts_min_supported_at_or_below_latest() {
    // Boundary case: min == latest must pass (the publisher is explicit
    // about "only the latest release is supported"). And the common
    // case min < latest stays valid. Leading-`v` tolerated on both.
    for (latest, min) in [
        ("9.2.0", "9.2.0"),
        ("9.2.0", "9.1.0"),
        ("10.0.0", "9.0.0"),
        ("9.2.0", "v9.2.0"),
        ("v9.2.0", "9.1.0"),
        // Prerelease precedence: 9.2.0 > 9.2.0-rc.1 per SemVer rule 11,
        // so min=9.2.0-rc.1 with latest=9.2.0 is a valid pair.
        ("9.2.0", "9.2.0-rc.1"),
    ] {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.2.0".into(),
            latest_version: latest.into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: Some(min.into()),
            display: None,
        };
        validate_notification_manifest(&m)
            .unwrap_or_else(|e| panic!("expected valid (min={min}, latest={latest}), got {e:?}"));
    }
}

#[test]
fn validate_manifest_rejects_bad_release_tag() {
    // The publish workflow emits `v<SEMVER>` — bare semver or arbitrary
    // strings must be rejected so `release_tag` stays tied to the live
    // git tag namespace.
    for v in ["9.2.0", "V9.2.0", "release-9.2.0", "v9.x", "v"] {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: v.into(),
            latest_version: "9.2.0".into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: None,
            display: None,
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(err, UpdateError::NotificationDecode { ref field } if field == "release_tag"),
            "expected release_tag decode failure for {v:?}, got {err:?}"
        );
    }
}

#[test]
fn validate_manifest_rejects_non_rfc3339_published_at() {
    // The publisher sources this from git's iso-strict output. A bad
    // published_at must fail fast at validate time so clients can't
    // display garbage timestamps.
    let bad = [
        "2026-05-01",             // date only
        "2026-05-01 12:00:00Z",   // space instead of T
        "2026/05/01T12:00:00Z",   // slashes
        "2026-5-1T12:00:00Z",     // single-digit month/day
        "2026-05-01T12:00:00",    // missing timezone
        "2026-05-01T12:00:00+00", // incomplete offset
        "2026-05-01T12:00:00.Z",  // empty fractional
        "totally not a date",
        "",
    ];
    for ts in bad {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: ts.into(),
            min_supported_version: None,
            display: None,
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(err, UpdateError::NotificationDecode { ref field } if field == "published_at"),
            "expected published_at decode failure for {ts:?}, got {err:?}"
        );
    }
}

#[test]
fn validate_manifest_accepts_rfc3339_variations() {
    // Timezone offsets, fractional seconds, and the `t` separator are all
    // RFC3339-valid; must not be rejected.
    for ts in [
        "2026-05-01T12:00:00Z",
        "2026-05-01t12:00:00Z",
        "2026-05-01T12:00:00+00:00",
        "2026-05-01T12:00:00-04:30",
        "2026-05-01T12:00:00.123Z",
        "2026-05-01T12:00:00.123456789+00:00",
    ] {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: ts.into(),
            min_supported_version: None,
            display: None,
        };
        validate_notification_manifest(&m)
            .unwrap_or_else(|e| panic!("expected {ts:?} to validate, got {e:?}"));
    }
}

#[test]
fn validate_manifest_rejects_non_https_cta_url() {
    // Regression: Codex adversarial-review finding #3. The GUI opens
    // `display.cta_url` from an update prompt, so a typo'd or
    // compromised manifest could downgrade users onto an
    // unauthenticated destination at the exact moment they are being
    // asked to fetch an update. Runtime rejection backs up the
    // publish-side validator: a tampered Pages or Releases asset that
    // bypassed the publish workflow still gets refused.
    let bad_ctas = [
        "http://example.invalid/changelog",
        "ftp://example.invalid/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "//example.invalid/changelog", // protocol-relative, no scheme
        "example.invalid/changelog",   // no scheme
        "",                            // empty (parse fails)
    ];
    // Note: `url::Url::parse` follows WHATWG and trims leading C0 /
    // whitespace, so `"  https://example.invalid"` normalizes to a
    // valid HTTPS URL. That is correct behavior — the trimmed form is
    // what would actually be opened — so we do not list it as a
    // rejection case.
    for cta in bad_ctas {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: None,
            display: Some(AppNotificationDisplay {
                title: "Update".into(),
                body: "Notes".into(),
                cta_url: Some(cta.into()),
            }),
        };
        let err = validate_notification_manifest(&m).unwrap_err();
        assert!(
            matches!(err, UpdateError::NotificationDecode { ref field } if field == "display.cta_url"),
            "expected display.cta_url decode failure for {cta:?}, got {err:?}",
        );
    }
}

#[test]
fn validate_manifest_accepts_https_cta_url() {
    // HTTPS URLs must pass — including ones with paths, queries, and
    // fragments. The check is scheme-only; the publisher is responsible
    // for the destination.
    for cta in [
        "https://example.invalid/changelog",
        "https://example.invalid/path?query=1#fragment",
        "https://example.invalid:8443/",
        "HTTPS://example.invalid/cased", // url crate normalizes scheme
    ] {
        let m = AppNotificationManifest {
            manifest_version: "1.0".into(),
            release_tag: "v9.2.0".into(),
            latest_version: "9.2.0".into(),
            published_at: "2026-05-01T12:00:00Z".into(),
            min_supported_version: None,
            display: Some(AppNotificationDisplay {
                title: "Update".into(),
                body: "Notes".into(),
                cta_url: Some(cta.into()),
            }),
        };
        validate_notification_manifest(&m)
            .unwrap_or_else(|e| panic!("expected {cta:?} to validate, got {e:?}"));
    }
}

#[test]
fn validate_manifest_accepts_absent_cta_url() {
    // The display block without a cta_url at all must still validate —
    // the field is optional, the new check only fires when present.
    let m = AppNotificationManifest {
        manifest_version: "1.0".into(),
        release_tag: "v9.2.0".into(),
        latest_version: "9.2.0".into(),
        published_at: "2026-05-01T12:00:00Z".into(),
        min_supported_version: None,
        display: Some(AppNotificationDisplay {
            title: "Update".into(),
            body: "Notes".into(),
            cta_url: None,
        }),
    };
    validate_notification_manifest(&m).expect("missing cta_url is allowed");
}

// ---------------------------------------------------------------------------
// parse_major_minor
// ---------------------------------------------------------------------------

#[test]
fn parse_major_minor_accepts_expected_shapes() {
    assert_eq!(parse_major_minor("1.0"), Some((1, 0)));
    assert_eq!(parse_major_minor("2.15"), Some((2, 15)));
    assert_eq!(parse_major_minor("10.99"), Some((10, 99)));
}

#[test]
fn parse_major_minor_rejects_malformed() {
    for s in ["1", "1.", ".0", "1.0.0", "1a.0", "1.0b", "", "1.0-beta"] {
        assert!(parse_major_minor(s).is_none(), "must reject {s:?}");
    }
}

// ---------------------------------------------------------------------------
// parse_notification_tag (Releases-fallback ordering)
// ---------------------------------------------------------------------------

#[test]
fn parse_notification_tag_accepts_semver() {
    let v = parse_notification_tag("app-notification-v9.2.0").unwrap();
    assert_eq!(v, semver::Version::parse("9.2.0").unwrap());
}

#[test]
fn parse_notification_tag_accepts_prerelease_and_build_metadata() {
    // semver::Version accepts pre-release and build metadata. The
    // publish workflow itself disallows prereleases, but the parser
    // stays permissive so a future policy change doesn't require a
    // parallel parser update.
    assert!(parse_notification_tag("app-notification-v9.2.0-rc.1").is_some());
    assert!(parse_notification_tag("app-notification-v9.2.0+build.7").is_some());
}

#[test]
fn parse_notification_tag_rejects_wrong_prefix() {
    assert!(parse_notification_tag("v9.2.0").is_none());
    assert!(parse_notification_tag("yaml-data-v2026.04.17").is_none());
    assert!(parse_notification_tag("app-notification-9.2.0").is_none()); // missing `v`
}

#[test]
fn parse_notification_tag_orders_numerically() {
    // Regression-style: raw string comparison would pick .9 over .10.
    let ten = parse_notification_tag("app-notification-v9.10.0").unwrap();
    let nine = parse_notification_tag("app-notification-v9.9.0").unwrap();
    assert!(ten > nine, "9.10.0 must sort above 9.9.0");
}

// ---------------------------------------------------------------------------
// classify
// ---------------------------------------------------------------------------

fn manifest(latest: &str, min_supported: Option<&str>) -> AppNotificationManifest {
    AppNotificationManifest {
        manifest_version: "1.0".into(),
        release_tag: format!("v{latest}"),
        latest_version: latest.into(),
        published_at: "2026-05-01T12:00:00Z".into(),
        min_supported_version: min_supported.map(String::from),
        display: Some(AppNotificationDisplay {
            title: "Update".into(),
            body: "Release notes.".into(),
            cta_url: None,
        }),
    }
}

#[test]
fn classify_up_to_date_when_installed_equals_latest() {
    let status = classify("9.2.0", &manifest("9.2.0", None));
    assert_eq!(status.classification, Classification::UpToDate);
    assert_eq!(status.latest_version, "9.2.0");
    assert!(status.parse_error.is_none());
}

#[test]
fn classify_update_available_when_installed_below_latest() {
    let status = classify("9.1.0", &manifest("9.2.0", None));
    assert_eq!(status.classification, Classification::UpdateAvailable);
    // Result includes the display payload so frontends can render it.
    assert!(status.display.is_some());
}

#[test]
fn classify_deprecated_when_below_min_supported() {
    let status = classify("8.5.0", &manifest("9.2.0", Some("9.0.0")));
    assert_eq!(status.classification, Classification::DeprecatedClient);
    assert_eq!(status.min_supported_version.as_deref(), Some("9.0.0"));
}

#[test]
fn classify_deprecated_wins_over_up_to_date() {
    // Edge case: installed happens to equal latest, but is below the
    // min_supported_version the publisher advertised for backward-compat.
    // DeprecatedClient should win — it's the more severe signal.
    let status = classify("8.0.0", &manifest("8.0.0", Some("9.0.0")));
    assert_eq!(status.classification, Classification::DeprecatedClient);
}

#[test]
fn classify_unknown_when_installed_version_unparseable() {
    let status = classify("not-a-version", &manifest("9.2.0", None));
    assert_eq!(status.classification, Classification::Unknown);
    assert!(
        status.parse_error.is_some(),
        "parse_error must be populated"
    );
    assert!(
        status
            .parse_error
            .as_deref()
            .unwrap()
            .contains("not-a-version"),
        "parse_error must name the offending input",
    );
}

#[test]
fn classify_strips_leading_v_and_big_v() {
    let manifest = manifest("9.2.0", None);
    assert_eq!(
        classify("v9.2.0", &manifest).classification,
        Classification::UpToDate,
    );
    assert_eq!(
        classify("V9.2.0", &manifest).classification,
        Classification::UpToDate,
    );
    assert_eq!(
        classify("v9.1.0", &manifest).classification,
        Classification::UpdateAvailable,
    );
}

#[test]
fn classify_installed_ahead_of_latest_is_up_to_date() {
    // Per design D-04: CI / pre-release builds "ahead of latest" must
    // not flash UpdateAvailable.
    let status = classify("9.3.0-rc.1", &manifest("9.2.0", None));
    assert_eq!(status.classification, Classification::UpToDate);
}

#[test]
fn classify_unknown_when_manifest_latest_unparseable() {
    // Defensive: manifest might carry an invalid latest_version past the
    // structural validator (e.g. "9.x"). Classification should degrade
    // to Unknown rather than silently treating installed as UpToDate.
    let status = classify("9.2.0", &manifest("9.x", None));
    assert_eq!(status.classification, Classification::Unknown);
    assert!(
        status
            .parse_error
            .as_deref()
            .unwrap()
            .contains("latest_version"),
        "parse_error must point at manifest latest_version",
    );
}

// ---------------------------------------------------------------------------
// Fallback cache seed + reuse (persist_fallback_manifest_body /
// try_fallback_cache / clear_fallback_marker)
// ---------------------------------------------------------------------------

mod fallback_cache {
    use super::*;
    use crate::manifest_fetch::{CACHED_MANIFEST_FILENAME, ETAG_FILENAME};
    use std::time::{Duration, SystemTime};
    use tempfile::TempDir;

    fn minimal_manifest_bytes() -> &'static [u8] {
        br#"{
            "manifest_version": "1.0",
            "release_tag": "v9.2.0",
            "latest_version": "9.2.0",
            "published_at": "2026-05-01T12:00:00Z"
        }"#
    }

    #[test]
    fn persist_writes_body_and_marker_and_clears_stale_etag() {
        let tmp = TempDir::new().unwrap();
        // Pretend a prior Pages leg left an ETag behind. The fallback must
        // clear it so a subsequent `If-None-Match` does not carry a
        // non-Pages ETag into a real Pages probe.
        std::fs::write(tmp.path().join(ETAG_FILENAME), b"\"W/prior\"").unwrap();

        persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());

        let body_path = tmp.path().join(CACHED_MANIFEST_FILENAME);
        assert!(body_path.exists(), "body must be written");
        let body = std::fs::read(&body_path).unwrap();
        assert_eq!(body, minimal_manifest_bytes());

        assert!(
            !tmp.path().join(ETAG_FILENAME).exists(),
            "stale Pages ETag must be removed after fallback seed",
        );
        assert!(
            tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "fallback marker must be written so a future outage can reuse the body",
        );
    }

    #[test]
    fn persist_ignores_occupied_legacy_fixed_tmp_path() {
        let tmp = TempDir::new().unwrap();
        let legacy_staging = tmp.path().join(format!("{}.tmp", CACHED_MANIFEST_FILENAME));

        // Regression for the fixed-temp race: the old helper always staged
        // through `manifest-latest.json.tmp`, so any competing writer or
        // stranded directory at that legacy path jammed fallback seeding.
        // The shared atomic helper uses a unique temp sibling instead, so
        // this occupied legacy path must no longer block persistence.
        std::fs::create_dir(&legacy_staging).unwrap();

        persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());

        assert!(
            tmp.path().join(CACHED_MANIFEST_FILENAME).exists(),
            "body must still be written when the legacy fixed tmp path is occupied",
        );
        assert!(
            tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "marker must still be written when the legacy fixed tmp path is occupied",
        );
    }

    #[test]
    fn persist_is_noop_when_cache_dir_is_none() {
        // Simply must not panic. No files to inspect — the side-effect
        // surface is empty when caching is disabled.
        persist_fallback_manifest_body(None, minimal_manifest_bytes());
    }

    #[test]
    fn try_fallback_cache_returns_none_when_cache_dir_is_none() {
        assert!(try_fallback_cache_at(None, SystemTime::now()).is_none());
    }

    #[test]
    fn try_fallback_cache_returns_none_when_marker_missing() {
        let tmp = TempDir::new().unwrap();
        // Body is present but no marker — cache is NOT from a fallback,
        // so we must not reuse it.
        std::fs::write(
            tmp.path().join(CACHED_MANIFEST_FILENAME),
            minimal_manifest_bytes(),
        )
        .unwrap();
        assert!(try_fallback_cache_at(Some(tmp.path()), SystemTime::now()).is_none());
    }

    #[test]
    fn try_fallback_cache_returns_manifest_when_marker_is_fresh() {
        let tmp = TempDir::new().unwrap();
        persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());

        let m = try_fallback_cache_at(Some(tmp.path()), SystemTime::now())
            .expect("fresh marker + valid body must reuse the cache");
        assert_eq!(m.release_tag, "v9.2.0");
        assert_eq!(m.latest_version, "9.2.0");
    }

    #[test]
    fn try_fallback_cache_returns_none_when_marker_older_than_ttl() {
        let tmp = TempDir::new().unwrap();
        persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());

        // Simulate a marker aged past TTL by shifting `now` forward.
        let future = SystemTime::now() + FALLBACK_CACHE_TTL + Duration::from_secs(1);
        assert!(
            try_fallback_cache_at(Some(tmp.path()), future).is_none(),
            "stale marker must not be reused — caller should re-hit Releases",
        );
    }

    #[test]
    fn try_fallback_cache_returns_none_when_body_missing() {
        let tmp = TempDir::new().unwrap();
        // Marker present but body deleted — corrupted cache state.
        std::fs::write(tmp.path().join(FALLBACK_MARKER_FILENAME), b"").unwrap();
        assert!(try_fallback_cache_at(Some(tmp.path()), SystemTime::now()).is_none());
    }

    #[test]
    fn try_fallback_cache_returns_none_when_body_fails_validation() {
        let tmp = TempDir::new().unwrap();
        std::fs::write(tmp.path().join(FALLBACK_MARKER_FILENAME), b"").unwrap();
        // Body lacks a required field (no latest_version).
        std::fs::write(
            tmp.path().join(CACHED_MANIFEST_FILENAME),
            br#"{"manifest_version":"1.0","release_tag":"v9.2.0","published_at":"2026-05-01T12:00:00Z"}"#,
        )
        .unwrap();
        assert!(
            try_fallback_cache_at(Some(tmp.path()), SystemTime::now()).is_none(),
            "invalid cached body must not be reused",
        );
    }

    #[test]
    fn body_write_failure_clears_existing_marker_to_prevent_stale_reuse() {
        // Regression: Codex adversarial-review finding #1. A failed
        // fallback body refresh (e.g. Windows AV holding the body file
        // open during the rename) must NOT leave the previous body
        // bytes paired with a still-fresh marker — `try_fallback_cache`
        // would otherwise serve the stale `latest_version` /
        // `min_supported_version` for up to FALLBACK_CACHE_TTL exactly
        // when the fallback path is supposed to be the source of truth.
        let tmp = TempDir::new().unwrap();

        // Pre-seed: a previous fallback succeeded. Fresh marker, valid
        // body — `try_fallback_cache_at` would currently reuse this.
        persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());
        assert!(tmp.path().join(FALLBACK_MARKER_FILENAME).exists());
        assert!(tmp.path().join(CACHED_MANIFEST_FILENAME).exists());
        assert!(
            try_fallback_cache_at(Some(tmp.path()), SystemTime::now()).is_some(),
            "precondition: fresh fallback cache must initially reuse",
        );

        // Sabotage the next body replacement by turning the target into
        // a directory. The shared atomic writer can still stage its temp
        // file, but the final rename must fail cross-platform when the
        // destination is a directory, exercising the body_ok=false path
        // without relying on a fixed temp filename.
        let body_path = tmp.path().join(CACHED_MANIFEST_FILENAME);
        std::fs::remove_file(&body_path).unwrap();
        std::fs::create_dir(&body_path).unwrap();

        let newer_bytes = br#"{
            "manifest_version": "1.0",
            "release_tag": "v9.3.0",
            "latest_version": "9.3.0",
            "published_at": "2026-06-01T12:00:00Z"
        }"#;
        persist_fallback_manifest_body(Some(tmp.path()), newer_bytes);

        // Marker must be gone — the load-bearing assertion. Without
        // the fix, the marker from the pre-seed call would remain
        // fresh and `try_fallback_cache_at` would return the stale
        // 9.2.0 body for the next 6 hours.
        assert!(
            !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "marker must be cleared on body-write failure to prevent stale reuse",
        );
        assert!(
            try_fallback_cache_at(Some(tmp.path()), SystemTime::now()).is_none(),
            "stale body must not be served after the marker is cleared",
        );

        // The body file itself is untouched (rename never landed),
        // which is exactly why the marker has to go: the cache pair
        // (body + marker) is split into a state where the marker
        // alone can no longer authorize reuse.
    }

    #[test]
    fn body_write_failure_with_no_prior_marker_stays_marker_free() {
        // Counterpart: when no prior fallback ran, a failed body write
        // must NOT introduce a new marker. The stale-reuse window is
        // already closed; we just need to confirm the failure path
        // doesn't open it.
        let tmp = TempDir::new().unwrap();
        std::fs::create_dir(tmp.path().join(CACHED_MANIFEST_FILENAME)).unwrap();

        persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());

        assert!(
            !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "no marker must be written when the body write fails",
        );
    }

    #[test]
    fn clear_fallback_marker_removes_existing_marker() {
        let tmp = TempDir::new().unwrap();
        persist_fallback_manifest_body(Some(tmp.path()), minimal_manifest_bytes());
        assert!(tmp.path().join(FALLBACK_MARKER_FILENAME).exists());

        clear_fallback_marker(Some(tmp.path()));
        assert!(
            !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "marker must be gone after clear",
        );
        // Body stays — next Pages success will rewrite it via `try_pages`.
        assert!(tmp.path().join(CACHED_MANIFEST_FILENAME).exists());
    }

    #[test]
    fn clear_fallback_marker_is_noop_when_marker_absent() {
        let tmp = TempDir::new().unwrap();
        // Must not error or panic.
        clear_fallback_marker(Some(tmp.path()));
        clear_fallback_marker(None);
    }
}

// ---------------------------------------------------------------------------
// check_app_notification_with: UnsupportedVersion short-circuit +
// fallback cache reuse on Pages outage
// ---------------------------------------------------------------------------

mod orchestrator {
    use super::*;
    use crate::github::GithubClient;
    use crate::manifest_fetch::{CACHED_MANIFEST_FILENAME, ETAG_FILENAME};
    use tempfile::TempDir;

    fn tokenless_client(base_url: &str) -> GithubClient {
        GithubClient::with_base_url("owner", "repo", base_url, None).unwrap()
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn pages_returns_unsupported_version_short_circuits_past_fallback() {
        // Pages returns a manifest whose MAJOR exceeds MAX. The caller
        // must surface `ManifestUnsupportedVersion` directly, NOT fall
        // through to the Releases API — that would waste a request for
        // the same-schema asset and collapse a hard error into the
        // ambiguous `NotificationFetchFailed`.
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        let unsupported = r#"{
            "manifest_version": "99.0",
            "release_tag": "v9.2.0",
            "latest_version": "9.2.0",
            "published_at": "2026-05-01T12:00:00Z"
        }"#;
        let pages_mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .with_status(200)
            .with_header("etag", "\"W/future\"")
            .with_body(unsupported)
            .create_async()
            .await;
        // The Releases-listing endpoint must NOT be hit for an
        // unsupported-version rejection. We assert this with `expect(0)`.
        let releases_mock = server
            .mock(
                "GET",
                mockito::Matcher::Regex(r"^/repos/.*/releases.*".into()),
            )
            .expect(0)
            .create_async()
            .await;

        let tmp = TempDir::new().unwrap();
        let client = tokenless_client(&server.url());
        let err = check_app_notification_with(&client, &pages_url, Some(tmp.path()), "9.2.0")
            .await
            .expect_err("unsupported MAJOR must fail the check");

        assert!(
            matches!(
                err,
                UpdateError::ManifestUnsupportedVersion { max_supported, .. }
                    if max_supported == MAX_NOTIFICATION_MANIFEST_MAJOR
            ),
            "expected ManifestUnsupportedVersion, got {err:?}",
        );
        pages_mock.assert_async().await;
        releases_mock.assert_async().await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn pages_success_clears_stale_fallback_marker() {
        // Simulate a recovered Pages leg after an outage: the cache still
        // holds a fallback marker from a previous check. A successful
        // Pages fetch must remove the marker so the body becomes
        // Pages-authoritative again.
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        let tmp = TempDir::new().unwrap();
        // Pre-seed as if we fell back earlier.
        persist_fallback_manifest_body(
            Some(tmp.path()),
            br#"{"manifest_version":"1.0","release_tag":"v9.1.0","latest_version":"9.1.0","published_at":"2026-04-01T12:00:00Z"}"#,
        );
        assert!(tmp.path().join(FALLBACK_MARKER_FILENAME).exists());

        let fresh = r#"{
            "manifest_version": "1.0",
            "release_tag": "v9.2.0",
            "latest_version": "9.2.0",
            "published_at": "2026-05-01T12:00:00Z"
        }"#;
        let _mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .with_status(200)
            .with_header("etag", "\"W/fresh\"")
            .with_body(fresh)
            .create_async()
            .await;

        let client = tokenless_client(&server.url());
        let status = check_app_notification_with(&client, &pages_url, Some(tmp.path()), "9.2.0")
            .await
            .expect("Pages success must succeed");
        assert_eq!(status.latest_version, "9.2.0");
        assert!(
            !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "marker must be cleared on Pages success",
        );
        // `try_pages` wrote the fresh body + ETag, so a future 304 path
        // returns Pages-authoritative bytes, not the old fallback body.
        assert!(tmp.path().join(CACHED_MANIFEST_FILENAME).exists());
        assert!(tmp.path().join(ETAG_FILENAME).exists());
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn fallback_leg_unsupported_version_surfaces_structural_error() {
        // Counterpart to `pages_returns_unsupported_version_short_circuits_past_fallback`:
        // here the Pages leg is DOWN (no cached body to short-circuit on),
        // the Releases API fallback succeeds in fetching an asset, but the
        // asset body advertises a `manifest_version` this client cannot
        // parse. The outcome must be `ManifestUnsupportedVersion`, NOT
        // `NotificationFetchFailed` — the latter would misreport a
        // deterministic 'client too old for this manifest' condition as a
        // transient transport failure on every binding exactly when Pages
        // is unreachable.
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        // Pages leg: unreachable. Must not be cached from a previous run
        // (TempDir is fresh), so the orchestrator proceeds to Releases.
        let pages_mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .with_status(503)
            .create_async()
            .await;

        // Releases API: return a single release whose asset download URL
        // points back at the mock server so the next GET lands on the
        // asset mock below. `draft = false`, `prerelease = false` so the
        // `get_all_releases(false, false)` filter keeps it.
        let asset_url = format!("{}/assets/manifest.json", server.url());
        let releases_body = format!(
            r#"[{{
                "tag_name": "app-notification-v9.2.0",
                "name": "Notification v9.2.0",
                "body": "",
                "prerelease": false,
                "draft": false,
                "html_url": "https://example.com/release",
                "assets": [
                    {{
                        "name": "manifest.json",
                        "size": 256,
                        "browser_download_url": "{asset_url}",
                        "content_type": "application/json",
                        "download_count": 0
                    }}
                ],
                "created_at": "2026-05-01T12:00:00Z",
                "published_at": "2026-05-01T12:00:00Z"
            }}]"#,
        );
        let releases_mock = server
            .mock(
                "GET",
                mockito::Matcher::Regex(r"^/repos/.*/releases.*".into()),
            )
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(releases_body)
            .create_async()
            .await;

        // Asset download: unsupported MAJOR `99.0` — the same shape that
        // triggers `ManifestUnsupportedVersion` on the Pages leg.
        let unsupported_asset = r#"{
            "manifest_version": "99.0",
            "release_tag": "v9.2.0",
            "latest_version": "9.2.0",
            "published_at": "2026-05-01T12:00:00Z"
        }"#;
        let asset_mock = server
            .mock("GET", "/assets/manifest.json")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(unsupported_asset)
            .create_async()
            .await;

        let tmp = TempDir::new().unwrap();
        let client = tokenless_client(&server.url());
        let err = check_app_notification_with(&client, &pages_url, Some(tmp.path()), "9.2.0")
            .await
            .expect_err("unsupported fallback MAJOR must fail the check");

        assert!(
            matches!(
                err,
                UpdateError::ManifestUnsupportedVersion { max_supported, .. }
                    if max_supported == MAX_NOTIFICATION_MANIFEST_MAJOR
            ),
            "expected ManifestUnsupportedVersion from fallback leg, got {err:?}",
        );

        // A structural rejection MUST NOT seed the fallback cache — the
        // body is explicitly "this client cannot parse the schema". Seeding
        // would force every subsequent check within TTL to replay the same
        // unparseable body from disk without ever re-consulting Pages.
        assert!(
            !tmp.path().join(CACHED_MANIFEST_FILENAME).exists(),
            "structural rejection must not seed the fallback cache",
        );
        assert!(
            !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "structural rejection must not create a fallback marker",
        );

        pages_mock.assert_async().await;
        releases_mock.assert_async().await;
        asset_mock.assert_async().await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn fallback_leg_decode_failure_surfaces_decode_error() {
        // Pages is down, but Releases successfully returns an app-notification
        // asset whose body is structurally invalid. That is a manifest decode
        // failure, not a transport failure, so bindings must keep their
        // DECODE / typed-exception discriminator instead of seeing
        // `NotificationFetchFailed`.
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        let pages_mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .with_status(503)
            .create_async()
            .await;

        let asset_url = format!("{}/assets/manifest.json", server.url());
        let releases_body = format!(
            r#"[{{
                "tag_name": "app-notification-v9.2.0",
                "name": "Notification v9.2.0",
                "body": "",
                "prerelease": false,
                "draft": false,
                "html_url": "https://example.com/release",
                "assets": [
                    {{
                        "name": "manifest.json",
                        "size": 256,
                        "browser_download_url": "{asset_url}",
                        "content_type": "application/json",
                        "download_count": 0
                    }}
                ],
                "created_at": "2026-05-01T12:00:00Z",
                "published_at": "2026-05-01T12:00:00Z"
            }}]"#,
        );
        let releases_mock = server
            .mock(
                "GET",
                mockito::Matcher::Regex(r"^/repos/.*/releases.*".into()),
            )
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(releases_body)
            .create_async()
            .await;

        let malformed_asset = r#"{
            "manifest_version": "1.0",
            "release_tag": "v9.2.0",
            "published_at": "2026-05-01T12:00:00Z"
        }"#;
        let asset_mock = server
            .mock("GET", "/assets/manifest.json")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(malformed_asset)
            .create_async()
            .await;

        let tmp = TempDir::new().unwrap();
        let client = tokenless_client(&server.url());
        let err = check_app_notification_with(&client, &pages_url, Some(tmp.path()), "9.2.0")
            .await
            .expect_err("malformed fallback manifest must fail the check");

        match err {
            UpdateError::NotificationDecode { field } => {
                assert_eq!(field, "latest_version");
            }
            other => panic!("expected NotificationDecode from fallback leg, got {other:?}"),
        }

        assert!(
            !tmp.path().join(CACHED_MANIFEST_FILENAME).exists(),
            "decode failure must not seed the fallback cache",
        );
        assert!(
            !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "decode failure must not create a fallback marker",
        );

        pages_mock.assert_async().await;
        releases_mock.assert_async().await;
        asset_mock.assert_async().await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn fallback_leg_manifest_invalid_surfaces_schema_error() {
        // Pages is down, but Releases successfully returns an
        // app-notification asset whose fields parse individually while
        // failing the cross-field invariant. That deterministic publisher
        // data error must stay `ManifestInvalid`, not be wrapped as a
        // transient `NotificationFetchFailed`.
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        let pages_mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .with_status(503)
            .create_async()
            .await;

        let asset_url = format!("{}/assets/manifest.json", server.url());
        let releases_body = format!(
            r#"[{{
                "tag_name": "app-notification-v9.2.0",
                "name": "Notification v9.2.0",
                "body": "",
                "prerelease": false,
                "draft": false,
                "html_url": "https://example.com/release",
                "assets": [
                    {{
                        "name": "manifest.json",
                        "size": 256,
                        "browser_download_url": "{asset_url}",
                        "content_type": "application/json",
                        "download_count": 0
                    }}
                ],
                "created_at": "2026-05-01T12:00:00Z",
                "published_at": "2026-05-01T12:00:00Z"
            }}]"#,
        );
        let releases_mock = server
            .mock(
                "GET",
                mockito::Matcher::Regex(r"^/repos/.*/releases.*".into()),
            )
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(releases_body)
            .create_async()
            .await;

        let invalid_asset = r#"{
            "manifest_version": "1.0",
            "release_tag": "v9.2.0",
            "latest_version": "9.2.0",
            "min_supported_version": "9.3.0",
            "published_at": "2026-05-01T12:00:00Z"
        }"#;
        let asset_mock = server
            .mock("GET", "/assets/manifest.json")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(invalid_asset)
            .create_async()
            .await;

        let tmp = TempDir::new().unwrap();
        let client = tokenless_client(&server.url());
        let err = check_app_notification_with(&client, &pages_url, Some(tmp.path()), "9.2.0")
            .await
            .expect_err("invalid fallback manifest must fail the check");

        match err {
            UpdateError::ManifestInvalid { reason } => {
                assert!(
                    reason.contains("min_supported_version") && reason.contains("latest_version"),
                    "reason must cite the invalid cross-field pair: {reason}",
                );
            }
            other => panic!("expected ManifestInvalid from fallback leg, got {other:?}"),
        }

        assert!(
            !tmp.path().join(CACHED_MANIFEST_FILENAME).exists(),
            "invalid manifest must not seed the fallback cache",
        );
        assert!(
            !tmp.path().join(FALLBACK_MARKER_FILENAME).exists(),
            "invalid manifest must not create a fallback marker",
        );

        pages_mock.assert_async().await;
        releases_mock.assert_async().await;
        asset_mock.assert_async().await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn pages_outage_with_fresh_fallback_cache_reuses_body_and_skips_releases() {
        // The core reuse test: Pages is 5xx, fallback cache is fresh
        // (marker within TTL, body valid). The check MUST classify from
        // cache and MUST NOT hit the Releases-listing endpoint. This is
        // what stops repeated-outage rate-limit thrashing.
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        let tmp = TempDir::new().unwrap();
        persist_fallback_manifest_body(
            Some(tmp.path()),
            br#"{"manifest_version":"1.0","release_tag":"v9.2.0","latest_version":"9.2.0","published_at":"2026-05-01T12:00:00Z"}"#,
        );

        let pages_mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .with_status(503)
            .create_async()
            .await;
        let releases_mock = server
            .mock(
                "GET",
                mockito::Matcher::Regex(r"^/repos/.*/releases.*".into()),
            )
            .expect(0)
            .create_async()
            .await;

        let client = tokenless_client(&server.url());
        let status = check_app_notification_with(&client, &pages_url, Some(tmp.path()), "9.1.0")
            .await
            .expect("fallback cache must classify from cache");
        assert_eq!(status.classification, Classification::UpdateAvailable);
        assert_eq!(status.latest_version, "9.2.0");

        pages_mock.assert_async().await;
        releases_mock.assert_async().await;
    }

    // -----------------------------------------------------------------
    // Eager installed-version validation — finding #1 of the adversarial
    // review. The orchestrator MUST surface
    // `NotificationInstalledVersionParse` instead of degrading to a
    // successful `Classification::Unknown`, and it MUST do so before
    // any network or cache I/O runs so bindings see the variant
    // deterministically.
    // -----------------------------------------------------------------

    #[tokio::test(flavor = "multi_thread")]
    async fn unparseable_installed_version_surfaces_typed_error_before_network() {
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        // Load-bearing expectation: `expect(0)` on both legs — the eager
        // validator MUST short-circuit before any HTTP call leaves the
        // process. Without the validator, classify would wrap the bad
        // input in `Ok(Classification::Unknown)` and the mocks would
        // fire at least once.
        let pages_mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .expect(0)
            .create_async()
            .await;
        let releases_mock = server
            .mock(
                "GET",
                mockito::Matcher::Regex(r"^/repos/.*/releases.*".into()),
            )
            .expect(0)
            .create_async()
            .await;

        let tmp = TempDir::new().unwrap();
        let client = tokenless_client(&server.url());
        let err =
            check_app_notification_with(&client, &pages_url, Some(tmp.path()), "not-a-version")
                .await
                .expect_err("unparseable installed_version must be a hard error");

        match err {
            UpdateError::NotificationInstalledVersionParse { input, .. } => {
                assert_eq!(input, "not-a-version");
            }
            other => panic!("expected NotificationInstalledVersionParse, got {other:?}"),
        }

        pages_mock.assert_async().await;
        releases_mock.assert_async().await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn valid_installed_version_still_reaches_pages_leg() {
        // Counterpart to the previous test: a well-formed installed
        // version must NOT short-circuit, it must flow through to the
        // Pages fetch. Uses the minimal-manifest happy path.
        let mut server = mockito::Server::new_async().await;
        let pages_url = format!("{}/app-notification/manifest-latest.json", server.url());

        let body = r#"{
            "manifest_version": "1.0",
            "release_tag": "v9.2.0",
            "latest_version": "9.2.0",
            "published_at": "2026-05-01T12:00:00Z"
        }"#;
        let pages_mock = server
            .mock("GET", "/app-notification/manifest-latest.json")
            .with_status(200)
            .with_header("etag", "\"W/ok\"")
            .with_body(body)
            .create_async()
            .await;

        let tmp = TempDir::new().unwrap();
        let client = tokenless_client(&server.url());

        // Leading `v` is tolerated, mirroring `classify`.
        let status = check_app_notification_with(&client, &pages_url, Some(tmp.path()), "v9.2.0")
            .await
            .expect("well-formed installed_version must flow through");
        assert_eq!(status.classification, Classification::UpToDate);
        pages_mock.assert_async().await;
    }
}

// ---------------------------------------------------------------------------
// map_ensure_cache_result: PathError projection onto the notification error
// contract (finding #2 of the adversarial review).
// ---------------------------------------------------------------------------

mod cache_result_mapping {
    use super::*;
    use classic_path_core::PathError;
    use std::path::{Path, PathBuf};

    #[test]
    fn ok_dir_surfaces_as_some() {
        let dir = PathBuf::from("/tmp/classic-cache");
        let mapped = map_ensure_cache_result(Ok(dir.clone())).expect("Ok input must stay Ok");
        assert_eq!(mapped.as_deref(), Some(Path::new("/tmp/classic-cache")));
    }

    #[test]
    fn io_error_surfaces_as_notification_cache_io() {
        // Finding #2: `create_dir_all`-class failures must not be
        // silently downgraded to `cache_dir = None`. They must reach
        // binding consumers as the typed `CACHE_IO` variant so the
        // advertised error shape is actually reachable.
        let offending = PathBuf::from(r"C:\nope\cache");
        let source = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "simulated EACCES");
        let err = map_ensure_cache_result(Err(PathError::IoError {
            path: offending.clone(),
            source,
        }))
        .expect_err("IoError must propagate as NotificationCacheIo");
        match err {
            UpdateError::NotificationCacheIo { path, source } => {
                assert_eq!(path, offending);
                assert_eq!(source.kind(), std::io::ErrorKind::PermissionDenied);
            }
            other => panic!("expected NotificationCacheIo, got {other:?}"),
        }
    }

    #[test]
    fn invalid_path_degrades_to_no_cache() {
        // Env-resolution failures (`LOCALAPPDATA`/`HOME` unset, invalid
        // owner/repo segment) remain best-effort per design D-06. The
        // `NotificationCacheIo` docstring explicitly reserves that
        // variant for I/O-class failures only, so this branch returns
        // `Ok(None)` and the caller runs uncached.
        let mapped = map_ensure_cache_result(Err(PathError::InvalidPath(
            "neither LOCALAPPDATA nor APPDATA is set".into(),
        )))
        .expect("InvalidPath must degrade rather than error");
        assert!(mapped.is_none(), "env-resolution failure must yield None");
    }

    #[test]
    fn future_pathcore_variant_stays_typed_as_cache_io() {
        // Forward-compat: `ensure_notification_cache_dir` does not emit
        // these variants today, but if path-core grows a new I/O-flavored
        // variant, the notification check MUST surface it as
        // `NotificationCacheIo` rather than silently degrading. This
        // test locks the catch-all arm so a quiet classification drift
        // would require an explicit code change in the mapping helper.
        let err = map_ensure_cache_result(Err(PathError::PermissionDenied(
            "simulated permission denied".into(),
        )))
        .expect_err("forward-compat PathError variant must still error");
        assert!(
            matches!(err, UpdateError::NotificationCacheIo { .. }),
            "expected NotificationCacheIo, got {err:?}",
        );
    }
}
