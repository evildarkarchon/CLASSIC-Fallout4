//! Fixture-tree tests for `cargo xtask app-notification`, driven through
//! `app_notification::run_with_progress` (the subcommand seam). They port the
//! retired Python suites under `tools/publish_app_notification/tests/`.

mod common;

use std::path::PathBuf;

use common::FixtureRepo;
use common::http::TestServer;
use xtask::app_notification::{self, Step, dry_run, manifest, smoke_pages, validate, verify_asset};
use xtask::{Outcome, RepoRoot};

/// Runs one step over `repo`, returning the outcome and the progress lines.
fn run(repo: &RepoRoot, step: Step) -> (anyhow::Result<Outcome>, Vec<String>) {
    let mut lines = Vec::new();
    let outcome = app_notification::run_with_progress(
        repo,
        app_notification::Args { step },
        &mut |line: &str| lines.push(line.to_owned()),
    );
    (outcome, lines)
}

/// The rendered findings of a failed outcome (empty on a pass).
fn findings(outcome: &Outcome) -> Vec<String> {
    match outcome {
        Outcome::Pass { .. } => Vec::new(),
        Outcome::Fail { findings, .. } => findings.iter().map(ToString::to_string).collect(),
    }
}

// ---------------------------------------------------------------- validate

const SOURCE: &str = "app-notification.yaml";

const BASE_VALID_MANIFEST: &str = "manifest_version: \"1.0\"\n\
release_tag: \"v9.1.0\"\n\
latest_version: \"9.1.0\"\n\
published_at: \"2026-04-22T12:00:00Z\"\n";

fn validate_source(body: &str) -> Vec<String> {
    let repo = FixtureRepo::empty().file(SOURCE, body);
    let step = Step::Validate(validate::Args {
        source: Some(repo.path().join(SOURCE)),
        workflow_tag: None,
    });
    findings(&run(&repo.root(), step).0.expect("validate runs"))
}

fn validate_tag(tag: &str) -> Vec<String> {
    let repo = FixtureRepo::empty();
    let step = Step::Validate(validate::Args {
        source: None,
        workflow_tag: Some(tag.to_owned()),
    });
    findings(&run(&repo.root(), step).0.expect("validate runs"))
}

fn with_field(old: &str, new: &str) -> String {
    assert!(BASE_VALID_MANIFEST.contains(old), "{old}");
    BASE_VALID_MANIFEST.replace(old, new)
}

fn assert_any(errors: &[String], needles: &[&str]) {
    assert!(
        errors
            .iter()
            .any(|error| needles.iter().all(|needle| error.contains(needle))),
        "no finding contains {needles:?}: {errors:#?}"
    );
}

#[test]
fn happy_path_passes() {
    assert_eq!(validate_source(BASE_VALID_MANIFEST), Vec::<String>::new());
}

#[test]
fn a_pass_names_the_tag_and_the_source() {
    let repo = FixtureRepo::empty().file(SOURCE, BASE_VALID_MANIFEST);
    let step = Step::Validate(validate::Args {
        source: Some(repo.path().join(SOURCE)),
        workflow_tag: Some("app-notification-v9.2.0".into()),
    });
    let outcome = run(&repo.root(), step).0.expect("validate runs");
    assert_eq!(
        outcome,
        Outcome::Pass {
            summary: format!(
                "app-notification-v9.2.0 passes app-notification tag validation; {} passes \
                 app-notification validation",
                repo.path().join(SOURCE).display()
            ),
            report: None,
        }
    );
}

#[test]
fn release_tag_without_v_prefix_is_rejected() {
    let errors = validate_source(&with_field(
        "release_tag: \"v9.1.0\"",
        "release_tag: \"9.1.0\"",
    ));
    assert_eq!(
        errors,
        [
            "app-notification.yaml:2: invalid-release-tag: release_tag must be a `v<SEMVER>` string \
          (got '9.1.0')"
        ]
    );
}

#[test]
fn latest_version_with_leading_zero_is_rejected() {
    let errors = validate_source(&with_field(
        "latest_version: \"9.1.0\"",
        "latest_version: \"01.2.3\"",
    ));
    assert_eq!(
        errors,
        [
            "app-notification.yaml:3: invalid-latest-version: latest_version must be a SemVer \
          string (got '01.2.3')"
        ]
    );
}

#[test]
fn published_at_without_offset_is_rejected() {
    let errors = validate_source(&with_field(
        "published_at: \"2026-04-22T12:00:00Z\"",
        "published_at: \"2026-05-01T12:00:00\"",
    ));
    assert_eq!(
        errors,
        [
            "app-notification.yaml:4: invalid-published-at: published_at is not RFC 3339 with an \
          explicit Z or ±HH:MM offset: '2026-05-01T12:00:00'"
        ]
    );
}

#[test]
fn published_at_with_explicit_offset_is_accepted() {
    let body = with_field(
        "published_at: \"2026-04-22T12:00:00Z\"",
        "published_at: \"2026-04-22T12:00:00+00:00\"",
    );
    assert_eq!(validate_source(&body), Vec::<String>::new());
}

#[test]
fn published_at_may_be_null_but_not_another_type() {
    let null = with_field(
        "published_at: \"2026-04-22T12:00:00Z\"",
        "published_at: null",
    );
    assert_eq!(validate_source(&null), Vec::<String>::new());
    let number = with_field("published_at: \"2026-04-22T12:00:00Z\"", "published_at: 5");
    assert_any(
        &validate_source(&number),
        &["published_at must be null or an RFC 3339 string"],
    );
}

#[test]
fn release_tag_with_leading_zero_semver_is_rejected() {
    let errors = validate_source(&with_field(
        "release_tag: \"v9.1.0\"",
        "release_tag: \"v01.2.3\"",
    ));
    assert_any(&errors, &["release_tag"]);
}

#[test]
fn min_supported_version_with_leading_zero_is_rejected() {
    let errors = validate_source(&format!(
        "{BASE_VALID_MANIFEST}min_supported_version: \"01.0.0\"\n"
    ));
    assert_eq!(
        errors,
        [
            "app-notification.yaml:5: invalid-min-supported-version: min_supported_version must be \
          a SemVer string or null (got '01.0.0')"
        ]
    );
}

#[test]
fn min_supported_version_strict_semver_is_accepted() {
    let body = format!("{BASE_VALID_MANIFEST}min_supported_version: \"9.0.0\"\n");
    assert_eq!(validate_source(&body), Vec::<String>::new());
}

#[test]
fn prerelease_semver_is_accepted() {
    let body = with_field(
        "latest_version: \"9.1.0\"",
        "latest_version: \"9.1.0-rc.1\"",
    )
    .replace("release_tag: \"v9.1.0\"", "release_tag: \"v9.1.0-rc.1\"");
    assert_eq!(validate_source(&body), Vec::<String>::new());
}

#[test]
fn workflow_tag_with_strict_semver_is_accepted() {
    assert_eq!(
        validate_tag("app-notification-v9.2.0"),
        Vec::<String>::new()
    );
}

#[test]
fn workflow_tag_with_prerelease_and_build_is_accepted() {
    assert_eq!(
        validate_tag("app-notification-v9.2.0-rc.1+build.5"),
        Vec::<String>::new()
    );
}

#[test]
fn workflow_tag_with_unparseable_suffix_is_rejected() {
    assert_eq!(
        validate_tag("app-notification-vnext"),
        [
            "--workflow-tag:1: invalid-workflow-tag: workflow tag must match \
          app-notification-v<SEMVER> (for example app-notification-v9.2.0; got \
          'app-notification-vnext')"
        ]
    );
}

#[test]
fn workflow_tag_with_leading_zero_semver_is_rejected() {
    assert_any(
        &validate_tag("app-notification-v01.2.3"),
        &["app-notification-v<SEMVER>"],
    );
}

#[test]
fn workflow_tag_requires_notification_prefix() {
    assert_any(&validate_tag("v9.2.0"), &["app-notification-v<SEMVER>"]);
}

#[test]
fn min_supported_above_latest_is_rejected() {
    // latest_version is 9.1.0, so min 9.2.0 would deprecate even the
    // advertised latest build.
    let errors = validate_source(&format!(
        "{BASE_VALID_MANIFEST}min_supported_version: \"9.2.0\"\n"
    ));
    assert_eq!(
        errors,
        [
            "app-notification.yaml:5: min-supported-exceeds-latest: min_supported_version \
          ('9.2.0') must not exceed latest_version ('9.1.0')"
        ]
    );
}

#[test]
fn min_supported_equal_to_latest_is_accepted() {
    let body = format!("{BASE_VALID_MANIFEST}min_supported_version: \"9.1.0\"\n");
    assert_eq!(validate_source(&body), Vec::<String>::new());
}

#[test]
fn min_supported_prerelease_above_latest_core_is_rejected() {
    // SemVer rule 11: 9.2.0 > 9.2.0-rc.1.
    let body = with_field(
        "latest_version: \"9.1.0\"",
        "latest_version: \"9.2.0-rc.1\"",
    )
    .replace("release_tag: \"v9.1.0\"", "release_tag: \"v9.2.0-rc.1\"")
        + "min_supported_version: \"9.2.0\"\n";
    assert_any(
        &validate_source(&body),
        &["min_supported_version", "latest_version"],
    );
}

#[test]
fn min_supported_prerelease_at_latest_core_is_accepted() {
    // SemVer rule 11: 9.2.0-rc.1 < 9.2.0.
    let body = with_field("latest_version: \"9.1.0\"", "latest_version: \"9.2.0\"")
        .replace("release_tag: \"v9.1.0\"", "release_tag: \"v9.2.0\"")
        + "min_supported_version: \"9.2.0-rc.1\"\n";
    assert_eq!(validate_source(&body), Vec::<String>::new());
}

#[test]
fn prerelease_precedence_follows_semver_rule_11() {
    // Numeric identifiers sort below alphanumeric ones and compare
    // numerically; a shorter identifier list sorts first; build metadata is
    // ignored.
    let ordered = [
        ("9.2.0-alpha", "9.2.0-alpha.1"),
        ("9.2.0-alpha.1", "9.2.0-alpha.beta"),
        ("9.2.0-beta.2", "9.2.0-beta.11"),
        ("9.2.0-rc.1", "9.2.0"),
        ("9.9.0", "9.10.0"),
    ];
    for (lower, higher) in ordered {
        let ok = format!(
            "manifest_version: \"1.0\"\nrelease_tag: \"v{higher}\"\nlatest_version: \"{higher}\"\n\
             published_at: null\nmin_supported_version: \"{lower}\"\n"
        );
        assert_eq!(
            validate_source(&ok),
            Vec::<String>::new(),
            "{lower} < {higher}"
        );
        let bad = format!(
            "manifest_version: \"1.0\"\nrelease_tag: \"v{lower}\"\nlatest_version: \"{lower}\"\n\
             published_at: null\nmin_supported_version: \"{higher}\"\n"
        );
        assert_any(&validate_source(&bad), &["must not exceed"]);
    }
    let build = "manifest_version: \"1.0\"\nrelease_tag: \"v9.2.0\"\nlatest_version: \
                 \"9.2.0+build.1\"\npublished_at: null\nmin_supported_version: \"9.2.0+build.9\"\n";
    assert_eq!(validate_source(build), Vec::<String>::new());
}

fn with_display(cta: &str) -> String {
    format!(
        "{BASE_VALID_MANIFEST}display:\n  title: \"Update available\"\n  body: \"Bug fixes and \
         improvements.\"\n  cta_url: {cta}\n"
    )
}

#[test]
fn display_cta_url_https_is_accepted() {
    assert_eq!(
        validate_source(&with_display("\"https://example.invalid/changelog\"")),
        Vec::<String>::new()
    );
}

#[test]
fn display_cta_url_must_parse_as_https_url() {
    for cta in ["https://", "https://example.com bad"] {
        assert_eq!(
            validate_source(&with_display(&format!("\"{cta}\""))),
            [format!(
                "app-notification.yaml:8: invalid-cta-url: display.cta_url must be an HTTPS URL \
                 (got '{cta}')"
            )],
            "{cta}"
        );
    }
}

#[test]
fn display_cta_url_http_is_rejected() {
    assert_any(
        &validate_source(&with_display("\"http://example.invalid/changelog\"")),
        &["cta_url", "HTTPS"],
    );
}

#[test]
fn display_cta_url_other_schemes_are_rejected() {
    for cta in [
        "ftp://example.invalid/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
    ] {
        assert_any(
            &validate_source(&with_display(&format!("\"{cta}\""))),
            &["cta_url", "HTTPS"],
        );
    }
}

#[test]
fn display_cta_url_omitted_is_accepted() {
    let body = format!(
        "{BASE_VALID_MANIFEST}display:\n  title: \"Update available\"\n  body: \"Notes\"\n"
    );
    assert_eq!(validate_source(&body), Vec::<String>::new());
}

#[test]
fn display_cta_url_https_case_insensitive() {
    assert_eq!(
        validate_source(&with_display("\"HTTPS://example.invalid/cased\"")),
        Vec::<String>::new()
    );
}

#[test]
fn display_cta_url_follows_urlsplit_authority_rules() {
    let accepted = [
        "https://example.invalid:443/x",
        "https://user@example.invalid/x",
        "https://[::1]:8443/x",
        "  https://example.invalid/leading-space",
        "https://exa\\tmple.invalid/tab-removed",
    ];
    for cta in accepted {
        assert_eq!(
            validate_source(&with_display(&format!("\"{cta}\""))),
            Vec::<String>::new(),
            "{cta}"
        );
    }
    let rejected = [
        "https://example.invalid:99999/x",
        "https://example.invalid:port/x",
        "https://[::1/x",
        "https://[1.2.3.4]/x",
        "https://@/x",
        "https:example.invalid",
    ];
    for cta in rejected {
        assert_any(
            &validate_source(&with_display(&format!("\"{cta}\""))),
            &["cta_url", "HTTPS"],
        );
    }
}

#[test]
fn display_fields_and_unknown_keys_are_all_reported() {
    let body = format!(
        "{BASE_VALID_MANIFEST}display:\n  title: \"  \"\n  body: 3\n  tilte: \"x\"\nextra: 1\nanother: true\n"
    );
    assert_eq!(
        validate_source(&body),
        [
            "app-notification.yaml:6: invalid-display: display.title must be a non-empty string",
            "app-notification.yaml:7: invalid-display: display.body must be a string",
            "app-notification.yaml:8: unexpected-keys: display has unexpected keys: ['tilte']",
            "app-notification.yaml:10: unexpected-keys: top-level document has unexpected keys: \
             ['another', 'extra']",
        ]
    );
}

#[test]
fn display_must_be_a_mapping_or_null() {
    let null = format!("{BASE_VALID_MANIFEST}display: null\n");
    assert_eq!(validate_source(&null), Vec::<String>::new());
    let list = format!("{BASE_VALID_MANIFEST}display: [1]\n");
    assert_eq!(
        validate_source(&list),
        ["app-notification.yaml:5: invalid-display: display must be a mapping or null"]
    );
}

#[test]
fn unquoted_values_are_reported_with_their_python_repr() {
    let body = "manifest_version: 1.10\nrelease_tag: null\nlatest_version: 9\n\
                published_at: null\nmin_supported_version: [1, 'x']\n";
    assert_eq!(
        validate_source(body),
        [
            "app-notification.yaml:1: invalid-manifest-version: manifest_version must be a quoted \
             MAJOR.MINOR string (got 1.1)",
            "app-notification.yaml:2: invalid-release-tag: release_tag must be a `v<SEMVER>` \
             string (got None)",
            "app-notification.yaml:3: invalid-latest-version: latest_version must be a SemVer \
             string (got 9)",
            "app-notification.yaml:5: invalid-min-supported-version: min_supported_version must \
             be a SemVer string or null (got [1, 'x'])",
        ]
    );
}

#[test]
fn an_unreadable_unparseable_or_non_mapping_source_is_a_finding() {
    let repo = FixtureRepo::empty();
    let missing = repo.path().join("missing.yaml");
    let step = Step::Validate(validate::Args {
        source: Some(missing.clone()),
        workflow_tag: None,
    });
    let errors = findings(&run(&repo.root(), step).0.expect("validate runs"));
    assert_eq!(errors.len(), 1, "{errors:?}");
    assert!(
        errors[0].starts_with(&format!(
            "missing.yaml:1: unreadable-source: cannot read {}: ",
            missing.display()
        )),
        "{errors:?}"
    );

    let errors = validate_source("a: [1\n");
    assert_eq!(errors.len(), 1, "{errors:?}");
    assert!(
        errors[0].contains(": unparseable-yaml: ") && errors[0].contains("does not parse as YAML"),
        "{errors:?}"
    );

    assert_any(
        &validate_source("a: 1\na: 2\n"),
        &["does not parse as YAML"],
    );
    assert_eq!(
        validate_source("- 1\n"),
        ["app-notification.yaml:1: not-a-mapping: top-level document must be a YAML mapping"]
    );
}

#[test]
fn the_live_source_validates() {
    let root = RepoRoot::discover(None).expect("repository root");
    let step = Step::Validate(validate::Args {
        source: Some(root.join("CLASSIC Data/app-notification.yaml")),
        workflow_tag: Some("app-notification-v0.0.0".into()),
    });
    let outcome = run(&root, step).0.expect("validate runs");
    assert!(matches!(outcome, Outcome::Pass { .. }), "{outcome:?}");
}

// ---------------------------------------------------------------- manifest

/// A source exercising every optional field, non-ASCII, escapes, U+0001 and
/// U+007F.
const FULL_SOURCE: &str = r#"manifest_version: "1.0"
release_tag: "v9.2.0-rc.1"
latest_version: "9.2.0-rc.1"
published_at: null
min_supported_version: "9.0.0"
display:
  title: "Café update ✨"
  body: "Line one\nLine two \"quoted\" \\ tab\there \u0001 \u007f 😀"
  cta_url: "https://example.invalid/changelog"
"#;

/// The retired Python tool's output for `FULL_SOURCE` with
/// `--published-at 2026-06-02T12:34:56Z` (CRLF folded to LF; `<DEL>` stands
/// for the raw U+007F byte it wrote).
const FULL_GOLDEN: &str = r#"{
  "manifest_version": "1.0",
  "release_tag": "v9.2.0-rc.1",
  "latest_version": "9.2.0-rc.1",
  "published_at": "2026-06-02T12:34:56Z",
  "min_supported_version": "9.0.0",
  "display": {
    "title": "Café update ✨",
    "body": "Line one\nLine two \"quoted\" \\ tab\there \u0001 <DEL> 😀",
    "cta_url": "https://example.invalid/changelog"
  }
}
"#;

const MINIMAL_SOURCE: &str = "manifest_version: \"1.0\"\nrelease_tag: \"v9.1.0\"\n\
latest_version: \"9.1.0\"\npublished_at: \"2026-04-22T12:00:00+02:00\"\n\
min_supported_version: null\ndisplay: null\n";

/// The retired Python tool's output for `MINIMAL_SOURCE` with no
/// `--published-at`.
const MINIMAL_GOLDEN: &str = "{\n  \"manifest_version\": \"1.0\",\n  \"release_tag\": \"v9.1.0\",\n  \
\"latest_version\": \"9.1.0\",\n  \"published_at\": \"2026-04-22T12:00:00+02:00\"\n}\n";

fn manifest_step(repo: &FixtureRepo, published_at: Option<&str>) -> Step {
    Step::Manifest(manifest::Args {
        source: repo.path().join(SOURCE),
        output: repo.path().join("staging/nested/manifest.json"),
        published_at: published_at.map(str::to_owned),
    })
}

fn generate(source: &str, published_at: Option<&str>) -> (Outcome, FixtureRepo) {
    let repo = FixtureRepo::empty().file(SOURCE, source);
    let outcome = run(&repo.root(), manifest_step(&repo, published_at))
        .0
        .expect("manifest runs");
    (outcome, repo)
}

#[test]
fn manifest_json_is_byte_exact() {
    let (outcome, repo) = generate(FULL_SOURCE, Some("2026-06-02T12:34:56Z"));
    let output = repo.path().join("staging/nested/manifest.json");
    assert_eq!(
        outcome,
        Outcome::Pass {
            summary: format!("wrote {}", output.display()),
            report: None,
        }
    );
    assert_eq!(
        std::fs::read(&output).expect("manifest written"),
        FULL_GOLDEN.replace("<DEL>", "\u{7f}").into_bytes()
    );

    let (_, repo) = generate(MINIMAL_SOURCE, None);
    assert_eq!(
        std::fs::read(repo.path().join("staging/nested/manifest.json")).expect("written"),
        MINIMAL_GOLDEN.as_bytes()
    );
}

#[test]
fn the_generated_manifest_deserializes_in_the_client() {
    let (_, repo) = generate(FULL_SOURCE, Some("2026-06-02T12:34:56Z"));
    let bytes = std::fs::read(repo.path().join("staging/nested/manifest.json")).expect("written");
    let manifest: classic_update_core::notification::AppNotificationManifest =
        serde_json::from_slice(&bytes).expect("the client's manifest type deserializes it");
    assert_eq!(manifest.release_tag, "v9.2.0-rc.1");
    assert_eq!(manifest.published_at, "2026-06-02T12:34:56Z");
    assert_eq!(manifest.min_supported_version.as_deref(), Some("9.0.0"));
    assert_eq!(
        manifest.display.expect("display").cta_url.as_deref(),
        Some("https://example.invalid/changelog")
    );
}

#[test]
fn a_source_published_at_wins_over_the_fallback() {
    let (_, repo) = generate(MINIMAL_SOURCE, Some("2030-01-01T00:00:00Z"));
    let text =
        std::fs::read_to_string(repo.path().join("staging/nested/manifest.json")).expect("written");
    assert!(
        text.contains("\"published_at\": \"2026-04-22T12:00:00+02:00\""),
        "{text}"
    );
}

#[test]
fn a_null_published_at_needs_a_fallback() {
    let source = MINIMAL_SOURCE.replace("\"2026-04-22T12:00:00+02:00\"", "null");
    for fallback in [None, Some("")] {
        let (outcome, repo) = generate(&source, fallback);
        assert_eq!(
            findings(&outcome),
            [
                "app-notification.yaml:4: missing-published-at: source `published_at` is null and \
              no --published-at fallback was supplied"
            ]
        );
        assert!(!repo.path().join("staging").exists());
    }
}

#[test]
fn every_manifest_field_problem_is_collected_and_nothing_is_written() {
    let source = "manifest_version: \"1.0\"\nrelease_tag: \" \"\npublished_at: 5\n\
                  min_supported_version: \"\"\ndisplay:\n  title: 1\n  cta_url: \"\"\n";
    let (outcome, repo) = generate(source, Some("2026-06-02T12:34:56Z"));
    assert_eq!(
        findings(&outcome),
        [
            "app-notification.yaml:1: missing-required-field: source missing required string \
             field `latest_version`",
            "app-notification.yaml:2: missing-required-field: source missing required string \
             field `release_tag`",
            "app-notification.yaml:3: invalid-published-at: source `published_at` must be a \
             non-empty string or null",
            "app-notification.yaml:4: invalid-min-supported-version: source \
             `min_supported_version` must be null or a non-empty string",
            // No `body:` line, so the finding points at `display:`.
            "app-notification.yaml:5: invalid-display: source `display.body` must be a string \
             when display is set",
            "app-notification.yaml:6: invalid-display: source `display.title` must be a string \
             when display is set",
            "app-notification.yaml:7: invalid-cta-url: source `display.cta_url` must be \
             null/omitted or a non-empty string",
        ]
    );
    assert!(!repo.path().join("staging").exists());
}

#[test]
fn an_unreadable_or_non_mapping_source_writes_nothing() {
    let (outcome, repo) = generate("- 1\n", Some("2026-06-02T12:34:56Z"));
    assert_eq!(
        findings(&outcome),
        [format!(
            "app-notification.yaml:1: not-a-mapping: {} top-level document must be a mapping",
            repo.path().join(SOURCE).display()
        )]
    );
    assert!(!repo.path().join("staging").exists());
}

// ---------------------------------------------------------------- verify-asset

/// A compact staged manifest, as in the retired Python suite.
const STAGED: &[u8] = br#"{"manifest_version":"1.0","release_tag":"v9.1.0","latest_version":"9.1.0","published_at":"2026-04-22T12:00:00Z"}"#;
const STALE: &[u8] = br#"{"manifest_version":"1.0","release_tag":"v9.0.0","latest_version":"9.0.0","published_at":"2026-01-01T00:00:00Z"}"#;
const ASSET: &str = "/releases/download/app-notification-v9.1.0/manifest.json";

fn sha256(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn verify_step(url: String, expected: Option<PathBuf>, timeout_seconds: u64) -> Step {
    Step::VerifyAsset(verify_asset::Args {
        url,
        expected_body_path: expected,
        timeout_seconds,
        poll_interval_seconds: 0,
    })
}

fn staged_repo() -> FixtureRepo {
    FixtureRepo::empty().file(
        "staging/manifest.json",
        std::str::from_utf8(STAGED).expect("utf-8"),
    )
}

#[test]
fn verify_asset_accepts_a_matching_body() {
    let repo = staged_repo();
    let server = TestServer::start();
    server.route(ASSET, vec![(200, STAGED.to_vec())]);
    let expected = repo.path().join("staging/manifest.json");

    let (outcome, lines) = run(
        &repo.root(),
        verify_step(server.url(ASSET), Some(expected.clone()), 60),
    );

    assert_eq!(
        outcome.expect("runs"),
        Outcome::Pass {
            summary: format!(
                "{} is anonymously reachable (attempt 1) (body matches staged manifest)",
                server.url(ASSET)
            ),
            report: None,
        }
    );
    assert_eq!(
        lines,
        [format!(
            "expecting body SHA-256 {} (computed from {})",
            sha256(STAGED),
            expected.display()
        )]
    );
}

#[test]
fn verify_asset_retries_a_stale_cdn_copy_until_the_staged_bytes_arrive() {
    let repo = staged_repo();
    let server = TestServer::start();
    server.route(ASSET, vec![(200, STALE.to_vec()), (200, STAGED.to_vec())]);

    let (outcome, lines) = run(
        &repo.root(),
        verify_step(
            server.url(ASSET),
            Some(repo.path().join("staging/manifest.json")),
            60,
        ),
    );

    assert!(
        matches!(outcome.expect("runs"), Outcome::Pass { summary, .. } if summary.contains("(attempt 2)"))
    );
    assert!(
        lines[1].starts_with(&format!(
            "retrying: attempt 1: body SHA-256 mismatch: expected {}, got {} (CDN likely still \
             serving the previous same-tag asset); ",
            sha256(STAGED),
            sha256(STALE)
        )),
        "{lines:?}"
    );
    assert_eq!(server.hits(ASSET), 2);
}

#[test]
fn verify_asset_rejects_a_mismatched_body_at_the_deadline() {
    let repo = staged_repo();
    let server = TestServer::start();
    server.route(ASSET, vec![(200, STALE.to_vec())]);

    let outcome = run(
        &repo.root(),
        verify_step(
            server.url(ASSET),
            Some(repo.path().join("staging/manifest.json")),
            0,
        ),
    )
    .0
    .expect("runs");

    assert_eq!(
        findings(&outcome),
        [format!(
            "staging/manifest.json:1: asset-not-reachable: {} did not become reachable within 0s \
             (last error: body SHA-256 mismatch: expected {}, got {} (CDN likely still serving \
             the previous same-tag asset))",
            server.url(ASSET),
            sha256(STAGED),
            sha256(STALE)
        )]
    );
}

#[test]
fn verify_asset_without_an_expected_body_accepts_any_reachable_manifest() {
    let repo = FixtureRepo::empty();
    let server = TestServer::start();
    server.route(ASSET, vec![(200, STALE.to_vec())]);

    let outcome = run(&repo.root(), verify_step(server.url(ASSET), None, 0))
        .0
        .expect("runs");

    assert_eq!(
        outcome,
        Outcome::Pass {
            summary: format!("{} is anonymously reachable (attempt 1)", server.url(ASSET)),
            report: None,
        }
    );
}

#[test]
fn verify_asset_reports_each_probe_failure() {
    let cases: [(u16, &[u8], &str); 3] = [
        (
            200,
            br#"{"manifest_version":"1.0"}"#,
            "manifest is missing a non-empty release_tag",
        ),
        (
            200,
            br#"{"release_tag":"  "}"#,
            "manifest is missing a non-empty release_tag",
        ),
        (404, b"", "unexpected status 404"),
    ];
    for (status, body, expected) in cases {
        let repo = FixtureRepo::empty();
        let server = TestServer::start();
        server.route(ASSET, vec![(status, body.to_vec())]);
        let outcome = run(&repo.root(), verify_step(server.url(ASSET), None, 0))
            .0
            .expect("runs");
        let found = findings(&outcome);
        assert!(
            found.len() == 1 && found[0].ends_with(&format!("(last error: {expected})")),
            "{found:?}"
        );
        // Without an expected body, the finding is reported against the URL.
        assert!(found[0].starts_with(&server.url(ASSET)), "{found:?}");
    }

    let repo = FixtureRepo::empty();
    let server = TestServer::start();
    server.route(ASSET, vec![(200, b"not json".to_vec())]);
    let found = findings(
        &run(&repo.root(), verify_step(server.url(ASSET), None, 0))
            .0
            .expect("runs"),
    );
    assert!(
        found[0].contains("(last error: body is not JSON: "),
        "{found:?}"
    );

    // Nothing listens on port 9 of the loopback address.
    let found = findings(
        &run(
            &repo.root(),
            verify_step("http://127.0.0.1:9/manifest.json".into(), None, 0),
        )
        .0
        .expect("runs"),
    );
    assert!(
        found[0].contains("(last error: transport error: "),
        "{found:?}"
    );
}

#[test]
fn verify_asset_refuses_a_missing_expected_body() {
    let repo = FixtureRepo::empty();
    let missing = repo.path().join("nope.json");
    let error = run(
        &repo.root(),
        verify_step("http://127.0.0.1:9/x".into(), Some(missing.clone()), 0),
    )
    .0
    .expect_err("an operational failure");
    assert_eq!(
        error.to_string(),
        format!(
            "--expected-body-path `{}` does not exist or is not a regular file",
            missing.display()
        )
    );
}

// ---------------------------------------------------------------- smoke-pages

const PAGES: &str = "/gh-pages/app-notification/manifest-latest.json";

#[test]
fn smoke_pages_passes_once_pages_serves_the_staged_manifest() {
    let repo = staged_repo();
    let server = TestServer::start();
    server.route(PAGES, vec![(200, STALE.to_vec()), (200, STAGED.to_vec())]);

    let (outcome, lines) = run(
        &repo.root(),
        Step::SmokePages(smoke_pages::Args {
            owner: None,
            repo: None,
            expected_body_path: repo.path().join("staging/manifest.json"),
            timeout_seconds: 60,
            poll_interval_seconds: 0,
            pages_path: "app-notification/manifest-latest.json".into(),
            base_url: Some(format!("{}/gh-pages", server.base())),
        }),
    );

    assert_eq!(
        outcome.expect("runs"),
        Outcome::Pass {
            summary: format!(
                "{} serves staged manifest (sha256={}, attempt 2)",
                server.url(PAGES),
                sha256(STAGED)
            ),
            report: None,
        }
    );
    assert!(
        lines[1].starts_with(&format!(
            "retrying: attempt 1, remote sha256={}, expected sha256={}, ",
            sha256(STALE),
            sha256(STAGED)
        )),
        "{lines:?}"
    );
}

#[test]
fn smoke_pages_fails_after_the_deadline_naming_the_family() {
    let repo = staged_repo();
    let server = TestServer::start();

    let outcome = run(
        &repo.root(),
        Step::SmokePages(smoke_pages::Args {
            owner: None,
            repo: None,
            expected_body_path: repo.path().join("staging/manifest.json"),
            timeout_seconds: 0,
            poll_interval_seconds: 0,
            pages_path: "app-notification/manifest-latest.json".into(),
            base_url: Some(format!("{}/gh-pages", server.base())),
        }),
    )
    .0
    .expect("runs");

    let Outcome::Fail { findings, summary } = outcome else {
        panic!("expected a failure");
    };
    assert_eq!(
        findings[0].to_string(),
        format!(
            "staging/manifest.json:1: pages-not-serving: {} did not serve expected bytes \
             (sha256={}) within 0s (last saw fetch-failed)",
            server.url(PAGES),
            sha256(STAGED)
        )
    );
    assert_eq!(
        summary,
        "app-notification smoke-pages: the Pages manifest does not match the staged manifest"
    );
}

#[test]
fn smoke_pages_defaults_to_the_app_notification_pages_path() {
    let repo = staged_repo();
    let server = TestServer::start();
    server.route(PAGES, vec![(200, STAGED.to_vec())]);
    let expected = repo.path().join("staging/manifest.json");

    let output = std::process::Command::new(env!("CARGO_BIN_EXE_xtask"))
        .args([
            "app-notification",
            "smoke-pages",
            "--base-url",
            &format!("{}/gh-pages/", server.base()),
            "--expected-body-path",
            expected.to_str().expect("utf-8 path"),
            "--timeout-seconds",
            "0",
        ])
        .output()
        .expect("run the xtask binary");

    assert_eq!(
        output.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(server.hits(PAGES), 1);
}

// ---------------------------------------------------------------- dry-run

const DRY_RUN_SOURCE: &str = "manifest_version: \"1.0\"\nrelease_tag: \"v9.2.0\"\n\
latest_version: \"9.2.0\"\npublished_at: null\nmin_supported_version: null\ndisplay: null\n";

fn dry_run_args(repo: &FixtureRepo, tag: &str) -> dry_run::Args {
    dry_run::Args {
        workflow_tag: tag.to_owned(),
        source: Some(repo.path().join(SOURCE)),
        published_at: Some("2026-06-02T12:34:56Z".into()),
        require_existing_tag: false,
        work_dir: Some(repo.path().join("work")),
        timeout_seconds: 0,
        simulate_release_asset_mismatch: false,
        simulate_pages_mismatch: false,
    }
}

fn dry_run(repo: &FixtureRepo, args: dry_run::Args) -> (anyhow::Result<Outcome>, Vec<String>) {
    run(&repo.root(), Step::DryRun(args))
}

#[test]
fn dry_run_rejects_an_invalid_tag_before_reading_the_source() {
    let repo = FixtureRepo::empty();
    let mut args = dry_run_args(&repo, "app-notification-vnext");
    args.source = Some(repo.path().join("missing.yaml"));

    let (outcome, lines) = dry_run(&repo, args);

    let outcome = outcome.expect("runs");
    let found = findings(&outcome);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(
        found[0].contains("workflow tag must match app-notification-v<SEMVER>"),
        "{found:?}"
    );
    assert!(
        !found
            .iter()
            .chain(&lines)
            .any(|line| line.contains("cannot read")),
        "{lines:?}"
    );
    assert!(!repo.path().join("work").exists());
}

#[test]
fn dry_run_rejects_an_invalid_source_before_staging() {
    let repo = FixtureRepo::empty().file(SOURCE, "manifest_version: \"1.0\"\n");

    let (outcome, _) = dry_run(&repo, dry_run_args(&repo, "app-notification-v9.2.0"));

    assert!(matches!(outcome.expect("runs"), Outcome::Fail { .. }));
    assert!(!repo.path().join("work").exists());
}

#[test]
fn dry_run_generates_and_stages_the_manifest() {
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);

    let (outcome, lines) = dry_run(&repo, dry_run_args(&repo, "app-notification-v9.2.0"));

    let work = repo.path().join("work");
    let work_display = dunce_display(&work);
    assert_eq!(
        outcome.expect("runs"),
        Outcome::Pass {
            summary: format!("dry run complete; outputs preserved under: {work_display}"),
            report: None,
        }
    );
    let manifest = std::fs::read(work.join(dry_run::STAGED_MANIFEST)).expect("staged manifest");
    let text = String::from_utf8(manifest.clone()).expect("utf-8");
    assert!(
        text.contains("\"published_at\": \"2026-06-02T12:34:56Z\""),
        "{text}"
    );
    for staged in [
        dry_run::PAGES_LATEST.to_owned(),
        "gh-pages/app-notification/manifest-app-notification-v9.2.0.json".to_owned(),
        format!(
            "{}/app-notification-v9.2.0/manifest.json",
            dry_run::RELEASE_ASSETS
        ),
    ] {
        assert_eq!(
            std::fs::read(work.join(&staged)).expect("staged"),
            manifest,
            "{staged}"
        );
    }

    let stages: Vec<&str> = lines
        .iter()
        .filter(|line| line.starts_with('['))
        .map(String::as_str)
        .collect();
    assert_eq!(
        stages,
        [
            "[1/9] Validate app-notification workflow tag",
            "[2/9] Validate app-notification source",
            "[3/9] Resolve tag publication timestamp",
            "[4/9] Generate manifest.json",
            "[5/9] Stage local release asset",
            "[6/9] Verify local release asset with existing probe",
            "[7/9] Stage local gh-pages manifests",
            "[8/9] Smoke-test local Pages manifest with reused helper",
            "[9/9] Dry run complete; live workflow would clear prerelease flag now",
        ]
    );
    assert!(
        lines.contains(&"published_at=2026-06-02T12:34:56Z (--published-at argument)".to_owned()),
        "{lines:?}"
    );
}

/// `work`, canonicalized the way the dry run reports it (without Windows'
/// `\\?\` verbatim prefix).
fn dunce_display(work: &std::path::Path) -> String {
    let canonical = work.canonicalize().expect("work dir exists");
    let text = canonical.display().to_string();
    text.strip_prefix(r"\\?\")
        .map_or(text.clone(), str::to_owned)
}

#[test]
fn dry_run_quotes_the_tag_in_the_release_asset_url() {
    // `+` must be percent-encoded in the URL and decoded by the local server.
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);

    let (outcome, lines) = dry_run(
        &repo,
        dry_run_args(&repo, "app-notification-v9.2.0-rc.1+build.5"),
    );

    assert!(
        matches!(outcome.expect("runs"), Outcome::Pass { .. }),
        "{lines:#?}"
    );
    assert!(
        lines
            .iter()
            .any(|line| line.contains("/releases/download/app-notification-v9.2.0-rc.1%2Bbuild.5/manifest.json is anonymously reachable")),
        "{lines:#?}"
    );
}

#[test]
fn dry_run_release_asset_mismatch_fails_before_pages_staging() {
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);
    let mut args = dry_run_args(&repo, "app-notification-v9.2.0");
    args.simulate_release_asset_mismatch = true;

    let (outcome, _) = dry_run(&repo, args);

    let found = findings(&outcome.expect("runs"));
    assert!(found[0].contains(": asset-not-reachable: "), "{found:?}");
    let work = repo.path().join("work");
    assert!(work.join(dry_run::STAGED_MANIFEST).is_file());
    assert!(!work.join(dry_run::PAGES_LATEST).exists());
}

#[test]
fn dry_run_pages_mismatch_fails_after_pages_staging() {
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);
    let mut args = dry_run_args(&repo, "app-notification-v9.2.0");
    args.simulate_pages_mismatch = true;

    let (outcome, _) = dry_run(&repo, args);

    let found = findings(&outcome.expect("runs"));
    assert!(found[0].contains(": pages-not-serving: "), "{found:?}");
    let work = repo.path().join("work");
    let latest = std::fs::read(work.join(dry_run::PAGES_LATEST)).expect("staged");
    assert_ne!(
        latest,
        std::fs::read(work.join(dry_run::STAGED_MANIFEST)).expect("staged")
    );
    assert!(
        latest.starts_with(b"{\n  \"manifest_version\": \"1.0\",\n  \"release_tag\": \"v0.0.0\"")
    );
}

#[test]
fn dry_run_falls_back_to_now_when_the_tag_does_not_exist() {
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);
    let mut args = dry_run_args(&repo, "app-notification-v0.0.0");
    args.published_at = None;

    let (outcome, lines) = dry_run(&repo, args);

    assert!(matches!(outcome.expect("runs"), Outcome::Pass { .. }));
    let resolved = lines
        .iter()
        .find(|line| line.starts_with("published_at="))
        .expect("timestamp line");
    assert!(
        resolved.ends_with("Z (current UTC time (tag does not exist locally))"),
        "{resolved}"
    );
}

#[test]
fn dry_run_can_require_an_existing_tag() {
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);
    let mut args = dry_run_args(&repo, "app-notification-v0.0.0");
    args.published_at = None;
    args.require_existing_tag = true;

    let error = dry_run(&repo, args).0.expect_err("operational failure");

    assert_eq!(
        error.to_string(),
        "workflow tag does not exist locally, so no workflow timestamp could be resolved. Pass \
         --published-at or omit --require-existing-tag."
    );
    assert!(!repo.path().join("work").exists());
}

/// Runs `git` in `dir` with a fixed identity, no signing, and the given
/// committer (and so tagger) date.
fn git(dir: &std::path::Path, date: &str, args: &[&str]) {
    let status = std::process::Command::new("git")
        .current_dir(dir)
        .args([
            "-c",
            "user.name=xtask test",
            "-c",
            "user.email=xtask@example.invalid",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "tag.gpgSign=false",
            "-c",
            "core.hooksPath=",
        ])
        .args(args)
        .env("GIT_AUTHOR_DATE", date)
        .env("GIT_COMMITTER_DATE", date)
        .status()
        .expect("run git");
    assert!(status.success(), "git {args:?}");
}

#[test]
fn dry_run_reads_annotated_and_lightweight_tag_times_from_git() {
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);
    git(repo.path(), "2026-06-02T12:34:56+00:00", &["init", "-q"]);
    git(
        repo.path(),
        "2026-06-02T12:34:56+00:00",
        &["commit", "-q", "--allow-empty", "-m", "init"],
    );
    git(
        repo.path(),
        "2026-06-02T12:34:56+00:00",
        &["tag", "app-notification-v9.2.0"],
    );
    git(
        repo.path(),
        "2026-07-01T08:00:00+02:00",
        &["tag", "-a", "-m", "notification", "app-notification-v9.3.0"],
    );

    let cases = [
        (
            "app-notification-v9.2.0",
            // Git's strict ISO format writes a zero offset as `Z`.
            "published_at=2026-06-02T12:34:56Z (local lightweight tag/commit \
             app-notification-v9.2.0)",
        ),
        (
            "app-notification-v9.3.0",
            "published_at=2026-07-01T08:00:00+02:00 (local annotated tag \
             app-notification-v9.3.0)",
        ),
    ];
    for (tag, expected) in cases {
        let mut args = dry_run_args(&repo, tag);
        args.published_at = None;
        args.require_existing_tag = true;
        let (outcome, lines) = dry_run(&repo, args);
        assert!(matches!(outcome.expect("runs"), Outcome::Pass { .. }));
        assert!(lines.contains(&expected.to_owned()), "{lines:#?}");
    }
}

#[test]
fn dry_run_defaults_to_a_preserved_temp_work_dir() {
    let repo = FixtureRepo::empty().file(SOURCE, DRY_RUN_SOURCE);
    let mut args = dry_run_args(&repo, "app-notification-v9.2.0");
    args.work_dir = None;

    let outcome = dry_run(&repo, args).0.expect("runs");

    let Outcome::Pass { summary, .. } = outcome else {
        panic!("expected a pass");
    };
    let work = PathBuf::from(
        summary
            .strip_prefix("dry run complete; outputs preserved under: ")
            .expect("summary names the work dir"),
    );
    let name = work
        .file_name()
        .expect("named")
        .to_string_lossy()
        .into_owned();
    assert!(
        name.starts_with("classic-app-notification-dry-run-"),
        "{name}"
    );
    assert!(work.join(dry_run::STAGED_MANIFEST).is_file());
    std::fs::remove_dir_all(&work).expect("clean up the preserved work dir");
}

// ---------------------------------------------------------------- binary

fn xtask(args: &[&str]) -> std::process::Output {
    std::process::Command::new(env!("CARGO_BIN_EXE_xtask"))
        .args(args)
        .output()
        .expect("run the xtask binary")
}

#[test]
fn validate_without_a_source_or_tag_is_a_usage_error() {
    assert_eq!(
        xtask(&["app-notification", "validate"]).status.code(),
        Some(2)
    );
}

#[test]
fn the_xtask_linux_commands_pass_on_the_live_source() {
    // The same commands the `xtask-linux` CI job runs.
    let output = xtask(&[
        "app-notification",
        "validate",
        "--source",
        concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../CLASSIC Data/app-notification.yaml"
        ),
    ]);
    assert_eq!(
        output.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );

    let work = tempfile::tempdir().expect("temp dir");
    let output = xtask(&[
        "app-notification",
        "dry-run",
        "--workflow-tag",
        "app-notification-v0.0.0",
        "--work-dir",
        work.path().to_str().expect("utf-8 path"),
    ]);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert_eq!(output.status.code(), Some(0), "{stderr}");
    assert!(
        String::from_utf8_lossy(&output.stdout)
            .starts_with("OK: dry run complete; outputs preserved under: "),
        "{stderr}"
    );
    assert!(stderr.contains("[9/9] Dry run complete"), "{stderr}");
}

// ---------------------------------------------------------------- workflow pin

#[test]
fn the_publish_workflow_keeps_its_step_order_and_tool_lines() {
    let root = RepoRoot::discover(None).expect("repository root");
    let text = std::fs::read_to_string(root.join(".github/workflows/publish-app-notification.yml"))
        .expect("read workflow");
    let workflow = &yaml_rust2::YamlLoader::load_from_str(&text).expect("workflow parses")[0];
    let steps = workflow["jobs"]["publish"]["steps"]
        .as_vec()
        .expect("publish steps");
    let names: Vec<&str> = steps
        .iter()
        .map(|step| step["name"].as_str().expect("every step is named"))
        .collect();

    // Verify -> Deploy gh-pages -> Smoke -> Clear prerelease (last): the
    // release stays invisible to the Releases fallback until Pages serves the
    // new payload, so the two discovery channels advance together. (The
    // yaml-data workflow clears the prerelease flag before the Pages deploy;
    // the difference is deliberate.)
    assert_eq!(
        names,
        [
            "Checkout source (tag)",
            "Install Rust toolchain",
            "Build xtask",
            "Validate app-notification workflow tag",
            "Validate app-notification source",
            "Resolve tag publication timestamp",
            "Generate manifest.json",
            "Show manifest preview",
            "Reset stale draft (idempotent re-run)",
            "Create draft GitHub release with manifest asset",
            "Promote release (draft -> live prerelease)",
            "Verify manifest asset reachable anonymously",
            "Deploy manifest to gh-pages",
            "Smoke-test Pages manifest",
            "Clear prerelease flag (make client-discoverable)",
        ]
    );

    let run_of = |name: &str| {
        steps
            .iter()
            .find(|step| step["name"].as_str() == Some(name))
            .and_then(|step| step["run"].as_str())
            .unwrap_or_default()
            .to_owned()
    };
    assert!(run_of("Build xtask").contains("cargo build -p xtask --locked"));
    assert!(
        run_of("Validate app-notification workflow tag")
            .contains("cargo xtask app-notification validate \\\n  --workflow-tag \"$TAG\"")
    );
    assert!(
        run_of("Validate app-notification source")
            .contains("cargo xtask app-notification validate \\\n  --source \"$SOURCE_ARTIFACT\"")
    );
    let generate = run_of("Generate manifest.json");
    assert!(generate.contains("cargo xtask app-notification manifest"));
    assert!(generate.contains("--published-at \"${{ steps.tag_ts.outputs.published_at }}\""));
    let verify = run_of("Verify manifest asset reachable anonymously");
    assert!(verify.contains("cargo xtask app-notification verify-asset"));
    assert!(verify.contains("--expected-body-path \"$RUNNER_TEMP/staging/manifest.json\""));
    let smoke = run_of("Smoke-test Pages manifest");
    assert!(smoke.contains("cargo xtask app-notification smoke-pages"));
    assert!(smoke.contains("--expected-body-path \"$RUNNER_TEMP/staging/manifest.json\""));
    assert!(smoke.contains("--pages-path \"app-notification/manifest-latest.json\""));

    // A notification publish must never move "latest release" off a binary
    // release: every release create/edit keeps `--latest=false`.
    for name in [
        "Create draft GitHub release with manifest asset",
        "Promote release (draft -> live prerelease)",
        "Clear prerelease flag (make client-discoverable)",
    ] {
        assert!(run_of(name).contains("--latest=false"), "{name}");
    }
    assert!(!text.contains("python"), "no Python left in the workflow");
}
