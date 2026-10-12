//! Fixture-tree tests for `cargo xtask yaml-data`, driven through
//! `yaml_data::run_with_progress` (the subcommand seam). They port the
//! retired Python suites under `tools/publish_yaml_data/tests/`.

mod common;

use std::path::{Path, PathBuf};

use common::FixtureRepo;
use common::http::TestServer;
use xtask::yaml_data::{self, Step, manifest, smoke_pages, validate, verify_assets};
use xtask::{Outcome, RepoRoot};

const DB: &str = "CLASSIC Data/databases";

/// Runs one step over `repo`, returning the outcome and the progress lines.
fn run(repo: &RepoRoot, step: Step) -> (anyhow::Result<Outcome>, Vec<String>) {
    let mut lines = Vec::new();
    let outcome =
        yaml_data::run_with_progress(repo, yaml_data::Args { step }, &mut |line: &str| {
            lines.push(line.to_owned())
        });
    (outcome, lines)
}

/// The rendered findings of a failed outcome (empty on a pass).
fn findings(outcome: &Outcome) -> Vec<String> {
    match outcome {
        Outcome::Pass { .. } => Vec::new(),
        Outcome::Fail { findings, .. } => findings.iter().map(ToString::to_string).collect(),
    }
}

/// A ranges document listing `names`, each with the range 1.0–1.0.
fn ranges(names: &[&str]) -> String {
    let mut text = String::from("files:\n");
    for name in names {
        text.push_str(&format!(
            "  - name: \"{name}\"\n    min_client_schema: \"1.0\"\n    max_client_schema: \"1.0\"\n"
        ));
    }
    text
}

/// A registry-shaped YAML file with one preflight action whose body is
/// `action_body` (already indented), as in the Python suite.
fn registry_yaml(action_body: &str) -> String {
    format!(
        "schema_version: \"1.1\"\nCrashgen_Registry:\n  Buffout4:\n    settings_rules:\n      preflight:\n        \
         - id: sample\n          when:\n            plugin_any: [buffout4.dll]\n          action:\n{action_body}"
    )
}

fn validate_step(repo: &FixtureRepo) -> Step {
    Step::Validate(validate::Args {
        databases_dir: repo.path().join(DB),
        schema_ranges: None,
    })
}

fn validate_findings(repo: &FixtureRepo) -> Vec<String> {
    findings(
        &run(&repo.root(), validate_step(repo))
            .0
            .expect("validate runs"),
    )
}

// ---------------------------------------------------------------- validate

#[test]
fn the_live_yaml_data_validates() {
    let root = RepoRoot::discover(None).expect("repository root");
    let step = Step::Validate(validate::Args {
        databases_dir: root.join(DB),
        schema_ranges: None,
    });

    let (outcome, _) = run(&root, step);

    assert_eq!(
        outcome.expect("validate runs"),
        Outcome::Pass {
            summary: "validated 2 shippable YAML files".into()
        }
    );
}

#[test]
fn a_clean_tree_passes_and_names_with_spaces_are_kept_as_authored() {
    let repo = FixtureRepo::empty()
        .file(
            &format!("{DB}/client-schema-ranges.yaml"),
            &ranges(&["CLASSIC Main.yaml", "CLASSIC Fallout4 Local.yaml"]),
        )
        .file(
            &format!("{DB}/CLASSIC Main.yaml"),
            "schema_version: \"2.0\"\n",
        )
        .file(
            &format!("{DB}/CLASSIC Fallout4 Local.yaml"),
            "schema_version: \"1.0\"\n",
        )
        // Not *.yaml, so not shippable and not checked.
        .file(&format!("{DB}/notes.txt"), "free text");

    assert_eq!(
        run(&repo.root(), validate_step(&repo))
            .0
            .expect("validate runs"),
        Outcome::Pass {
            summary: "validated 2 shippable YAML files".into()
        }
    );
}

#[test]
fn placement_and_bucket_must_agree() {
    let repo = FixtureRepo::empty()
        .file(&format!("{DB}/client-schema-ranges.yaml"), &ranges(&["CLASSIC Fallout4.yaml"]))
        .file(
            &format!("{DB}/CLASSIC Fallout4.yaml"),
            &registry_yaml(
                "            kind: notice\n            placement: error_information\n            \
                 bucket: settings\n            severity: error\n            message: \"disagreement\"\n",
            ),
        );

    assert_eq!(
        validate_findings(&repo),
        [format!(
            "{DB}/CLASSIC Fallout4.yaml:1: placement-bucket-mismatch: action declares \
             placement='error_information' and bucket='settings'; both keys must resolve to the same value"
        )]
    );
}

#[test]
fn agreeing_or_single_placement_keys_pass() {
    for action in [
        "            placement: \"error_information\"\n            bucket: \"error_information\"\n",
        "            placement: \"Error_Information\"\n            bucket: \"error_information \"\n",
        "            placement: error_information\n",
    ] {
        let repo = FixtureRepo::empty()
            .file(
                &format!("{DB}/client-schema-ranges.yaml"),
                &ranges(&["CLASSIC Fallout4.yaml"]),
            )
            .file(
                &format!("{DB}/CLASSIC Fallout4.yaml"),
                &registry_yaml(action),
            );

        assert_eq!(validate_findings(&repo), Vec::<String>::new(), "{action}");
    }
}

#[test]
fn schema_version_must_be_present_quoted_and_major_minor() {
    let repo = FixtureRepo::empty()
        .file(
            &format!("{DB}/client-schema-ranges.yaml"),
            &ranges(&["a.yaml", "b.yaml", "c.yaml", "d.yaml", "e.yaml"]),
        )
        .file(&format!("{DB}/a.yaml"), "other: 1\n")
        .file(&format!("{DB}/b.yaml"), "# header\nschema_version: 1.0\n")
        .file(&format!("{DB}/c.yaml"), "schema_version: \"1.x\"\n")
        .file(&format!("{DB}/d.yaml"), "- a\n- b\n")
        .file(&format!("{DB}/e.yaml"), "key: [unclosed\n");

    let found = validate_findings(&repo);

    assert_eq!(found.len(), 5, "{found:#?}");
    assert_eq!(
        found[0],
        format!("{DB}/a.yaml:1: missing-schema-version: missing root-level schema_version")
    );
    assert_eq!(
        found[1],
        format!(
            "{DB}/b.yaml:2: schema-version-not-string: schema_version must be a quoted string, got float (1.0)"
        )
    );
    assert_eq!(
        found[2],
        format!(
            "{DB}/c.yaml:1: malformed-schema-version: schema_version '1.x' is not a MAJOR.MINOR schema version"
        )
    );
    assert_eq!(
        found[3],
        format!("{DB}/d.yaml:1: root-not-mapping: root document is not a mapping")
    );
    assert!(
        found[4].starts_with(&format!(
            "{DB}/e.yaml:2: unparseable-yaml: unparseable YAML: "
        )),
        "{}",
        found[4]
    );
}

#[test]
fn unlisted_and_missing_shippable_files_are_reported() {
    let repo = FixtureRepo::empty()
        .file(
            &format!("{DB}/client-schema-ranges.yaml"),
            &ranges(&["listed.yaml", "gone.yaml"]),
        )
        .file(&format!("{DB}/listed.yaml"), "schema_version: \"1.0\"\n")
        .file(&format!("{DB}/extra.yaml"), "schema_version: \"1.0\"\n");

    assert_eq!(
        validate_findings(&repo),
        [
            format!(
                "{DB}/client-schema-ranges.yaml:5: missing-shippable-yaml: gone.yaml listed in \
                     client-schema-ranges.yaml but not found in {}",
                repo.path().join(DB).display()
            ),
            format!(
                "{DB}/extra.yaml:1: unlisted-shippable-yaml: shippable YAML not listed in client-schema-ranges.yaml"
            ),
        ]
    );
}

#[test]
fn ranges_rules_report_invalid_names_and_windows_duplicates() {
    for (names, expected) in [
        (
            vec!["NUL.yaml"],
            "invalid-cache-file-name: entry 'NUL.yaml': file name is not a valid cache/install basename",
        ),
        (
            vec!["CLASSIC Main.yaml", "CLASSIC Main.yaml"],
            "duplicate-cache-file-name: contains duplicate entry for 'CLASSIC Main.yaml'",
        ),
        (
            vec!["CLASSIC Main.yaml", "classic main.yaml"],
            "duplicate-cache-file-name: contains duplicate entry for 'classic main.yaml'",
        ),
    ] {
        let repo = FixtureRepo::empty()
            .file(&format!("{DB}/client-schema-ranges.yaml"), &ranges(&names))
            .file(
                &format!("{DB}/CLASSIC Main.yaml"),
                "schema_version: \"1.0\"\n",
            );

        let found = validate_findings(&repo);

        assert!(
            found.iter().any(|line| line.contains(expected)),
            "{names:?}: {found:#?}"
        );
    }
}

#[test]
fn every_finding_across_ranges_and_files_is_collected() {
    let repo = FixtureRepo::empty()
        .file(
            &format!("{DB}/client-schema-ranges.yaml"),
            "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"2.0\"\n    max_client_schema: \"1.0\"\n",
        )
        .file(&format!("{DB}/a.yaml"), "schema_version: 1\n");

    let rules: Vec<String> = validate_findings(&repo)
        .iter()
        .map(|line| line.split(": ").next().unwrap_or_default().to_owned())
        .collect();

    assert_eq!(
        rules,
        [
            format!("{DB}/a.yaml:1"),
            format!("{DB}/client-schema-ranges.yaml:2")
        ]
    );
}

#[test]
fn operational_failures_are_errors() {
    let missing_dir = FixtureRepo::empty();
    let error = run(&missing_dir.root(), validate_step(&missing_dir))
        .0
        .expect_err("missing dir");
    assert!(error.to_string().ends_with("is not a directory"), "{error}");

    let no_ranges = FixtureRepo::empty().file(&format!("{DB}/a.yaml"), "schema_version: \"1.0\"\n");
    let error = run(&no_ranges.root(), validate_step(&no_ranges))
        .0
        .expect_err("missing ranges");
    assert!(
        error.to_string().contains("client-schema-ranges file"),
        "{error}"
    );

    // The ranges file lives elsewhere and the directory holds no *.yaml.
    let no_yaml = FixtureRepo::empty()
        .file("ranges.yaml", &ranges(&["a.yaml"]))
        .file(&format!("{DB}/a.txt"), "");
    let error = run(
        &no_yaml.root(),
        Step::Validate(validate::Args {
            databases_dir: no_yaml.path().join(DB),
            schema_ranges: Some(no_yaml.path().join("ranges.yaml")),
        }),
    )
    .0
    .expect_err("no yaml files");
    assert!(
        error.to_string().ends_with("contains no *.yaml files"),
        "{error}"
    );
}

// ---------------------------------------------------------------- manifest

/// The golden fixture: one ASCII name, one non-ASCII name with a space.
fn golden_repo() -> FixtureRepo {
    FixtureRepo::empty()
        .file(
            &format!("{DB}/client-schema-ranges.yaml"),
            "files:\n  - name: \"CLASSIC Main.yaml\"\n    client_schemas_const: \"MAIN_YAML\"\n    \
             min_client_schema: \"2.0\"\n    max_client_schema: \"2.999\"\n  - name: \"Caf\u{e9} Data.yaml\"\n    \
             min_client_schema: \"1.0\"\n    max_client_schema: \"1.999\"\n",
        )
        .file(&format!("{DB}/CLASSIC Main.yaml"), "schema_version: \"2.2\"\nkey: value\n")
        .file(
            &format!("{DB}/Caf\u{e9} Data.yaml"),
            "schema_version: \"1.0\"\nnote: \"\u{fc}n\u{ef}code\"\n",
        )
}

fn manifest_step(repo: &FixtureRepo, staging: &Path) -> Step {
    Step::Manifest(manifest::Args {
        tag: "yaml-data-v2026.10.11".into(),
        repo: "evildarkarchon/CLASSIC-Fallout4".into(),
        databases_dir: repo.path().join(DB),
        schema_ranges: None,
        staging: staging.to_path_buf(),
        published_at: Some("2026-10-12T04:01:31Z".into()),
    })
}

/// Byte-exact output of the retired `generate_manifest.py` (CPython 3.14,
/// ruamel.yaml 0.18) on `golden_repo()`, with its Windows CRLF line endings
/// folded to the LF that the Linux publish runner writes and its
/// `published_at` as fixed above.
const GOLDEN_MANIFEST: &str = r#"{
  "manifest_version": 1,
  "release_tag": "yaml-data-v2026.10.11",
  "published_at": "2026-10-12T04:01:31Z",
  "files": [
    {
      "name": "CLASSIC Main.yaml",
      "schema_version": "2.2",
      "sha256": "3b08732094062f8d29447f0906d251e6576b24645a1403794e729981dd7cce2d",
      "size_bytes": 33,
      "min_client_schema": "2.0",
      "max_client_schema": "2.999",
      "download_url": "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.10.11/CLASSIC%20Main.yaml"
    },
    {
      "name": "Caf\u00e9 Data.yaml",
      "schema_version": "1.0",
      "sha256": "69058351d2729587aaab8e55d84c1a2a9f726df2af5459b26003e959b4946791",
      "size_bytes": 40,
      "min_client_schema": "1.0",
      "max_client_schema": "1.999",
      "download_url": "https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/download/yaml-data-v2026.10.11/Caf%C3%A9%20Data.yaml"
    }
  ],
  "signatures": []
}
"#;

#[test]
fn manifest_and_sidecars_are_byte_exact() {
    let repo = golden_repo();
    let staging = repo.path().join("staging");

    let (outcome, _) = run(&repo.root(), manifest_step(&repo, &staging));

    assert!(matches!(
        outcome.expect("manifest runs"),
        Outcome::Pass { .. }
    ));
    assert_eq!(
        String::from_utf8(std::fs::read(staging.join("manifest.json")).expect("manifest written"))
            .expect("ASCII manifest"),
        GOLDEN_MANIFEST
    );
    assert_eq!(
        std::fs::read(staging.join("CLASSIC Main.yaml.sha256")).expect("sidecar"),
        b"3b08732094062f8d29447f0906d251e6576b24645a1403794e729981dd7cce2d\n"
    );
    assert_eq!(
        std::fs::read(staging.join("Caf\u{e9} Data.yaml.sha256")).expect("sidecar"),
        b"69058351d2729587aaab8e55d84c1a2a9f726df2af5459b26003e959b4946791\n"
    );
    assert_eq!(
        std::fs::read(staging.join("CLASSIC Main.yaml")).expect("staged copy"),
        b"schema_version: \"2.2\"\nkey: value\n"
    );
}

#[test]
fn the_generated_manifest_passes_the_real_client_validation() {
    let repo = golden_repo();
    let staging = repo.path().join("staging");
    run(&repo.root(), manifest_step(&repo, &staging))
        .0
        .expect("manifest runs");

    let manifest: classic_update_core::YamlManifest = serde_json::from_slice(
        &std::fs::read(staging.join("manifest.json")).expect("manifest written"),
    )
    .expect("client parses the manifest");

    classic_update_core::validate_manifest(&manifest, "evildarkarchon", "CLASSIC-Fallout4")
        .expect("client accepts the manifest");
}

#[test]
fn published_at_defaults_to_the_current_utc_second() {
    let repo = golden_repo();
    let staging = repo.path().join("staging");
    let Step::Manifest(mut args) = manifest_step(&repo, &staging) else {
        unreachable!()
    };
    args.published_at = None;

    run(&repo.root(), Step::Manifest(args))
        .0
        .expect("manifest runs");

    let manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(staging.join("manifest.json")).expect("written"))
            .expect("JSON");
    let stamp = manifest["published_at"].as_str().expect("string");
    assert_eq!(stamp.len(), 20, "{stamp}");
    assert!(
        stamp.starts_with("20") && stamp.ends_with('Z') && &stamp[10..11] == "T",
        "{stamp}"
    );
}

#[test]
fn a_missing_source_or_bad_ranges_writes_no_manifest() {
    let missing = FixtureRepo::empty().file(
        &format!("{DB}/client-schema-ranges.yaml"),
        &ranges(&["gone.yaml"]),
    );
    let staging = missing.path().join("staging");
    let outcome = run(&missing.root(), manifest_step(&missing, &staging))
        .0
        .expect("runs");
    let found = findings(&outcome);
    assert_eq!(found.len(), 1);
    assert!(
        found[0].starts_with(&format!(
            "{DB}/client-schema-ranges.yaml:2: missing-shippable-source: shippable source missing: "
        )),
        "{}",
        found[0]
    );
    assert!(!staging.join("manifest.json").exists());

    let inverted = FixtureRepo::empty()
        .file(
            &format!("{DB}/client-schema-ranges.yaml"),
            "files:\n  - name: \"a.yaml\"\n    min_client_schema: \"1.10\"\n    max_client_schema: \"1.9\"\n",
        )
        .file(&format!("{DB}/a.yaml"), "schema_version: \"1.0\"\n");
    let staging = inverted.path().join("staging");
    let outcome = run(&inverted.root(), manifest_step(&inverted, &staging))
        .0
        .expect("runs");
    assert!(findings(&outcome)[0].contains("empty-schema-range"));
    assert!(
        !staging.exists(),
        "nothing is staged when the ranges are refused"
    );
}

#[test]
fn a_staged_file_without_a_string_schema_version_is_refused() {
    let repo = FixtureRepo::empty()
        .file(
            &format!("{DB}/client-schema-ranges.yaml"),
            &ranges(&["a.yaml"]),
        )
        .file(&format!("{DB}/a.yaml"), "schema_version: 1.0\n");
    let staging = repo.path().join("staging");

    let outcome = run(&repo.root(), manifest_step(&repo, &staging))
        .0
        .expect("runs");

    assert_eq!(
        findings(&outcome),
        [
            "staging/a.yaml:1: missing-schema-version: has no string schema_version \
          (run `cargo xtask yaml-data validate` first)"
        ]
    );
    assert!(!staging.join("manifest.json").exists());
}

// ---------------------------------------------------------------- verify-assets

/// Writes a manifest whose single file and release `manifest.json` live on
/// `server`, returning the manifest path and its bytes.
fn served_manifest(
    repo: &FixtureRepo,
    server: &TestServer,
    file_body: &[u8],
) -> (PathBuf, Vec<u8>) {
    let digest = sha256(file_body);
    let manifest = serde_json::to_vec_pretty(&serde_json::json!({
        "files": [{
            "name": "CLASSIC Fallout4.yaml",
            "download_url": server.url("/download/CLASSIC%20Fallout4.yaml"),
            "sha256": digest,
        }]
    }))
    .expect("serialize");
    let path = repo.path().join("staging/manifest.json");
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(&path, &manifest).expect("write manifest");
    (path, manifest)
}

fn sha256(bytes: &[u8]) -> String {
    use sha2::Digest as _;
    sha2::Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn verify_step(manifest: PathBuf, timeout_seconds: u64) -> Step {
    Step::VerifyAssets(verify_assets::Args {
        manifest,
        timeout_seconds,
        poll_interval_seconds: 0,
        socket_timeout_seconds: 5,
    })
}

const STAGED: &[u8] = b"schema_version: \"1.0\"\nfoo: bar\n";
const STALE: &[u8] = b"schema_version: \"0.9\"\nfoo: old\n";

#[test]
fn verify_assets_passes_when_every_asset_serves_the_staged_bytes() {
    let repo = FixtureRepo::empty();
    let server = TestServer::start();
    let (path, manifest) = served_manifest(&repo, &server, STAGED);
    server.route(
        "/download/CLASSIC%20Fallout4.yaml",
        vec![(200, STAGED.to_vec())],
    );
    server.route("/download/manifest.json", vec![(200, manifest)]);

    let (outcome, lines) = run(&repo.root(), verify_step(path, 0));

    assert_eq!(
        outcome.expect("runs"),
        Outcome::Pass {
            summary: "all 2 asset URL(s) serve manifest bytes anonymously (attempt 1)".into()
        }
    );
    assert!(lines.is_empty(), "{lines:?}");
}

#[test]
fn verify_assets_retries_a_stale_cdn_copy_until_the_staged_bytes_arrive() {
    let repo = FixtureRepo::empty();
    let server = TestServer::start();
    let (path, manifest) = served_manifest(&repo, &server, STAGED);
    server.route(
        "/download/CLASSIC%20Fallout4.yaml",
        vec![
            (200, STALE.to_vec()),
            (404, Vec::new()),
            (200, STAGED.to_vec()),
        ],
    );
    server.route("/download/manifest.json", vec![(200, manifest)]);

    let (outcome, lines) = run(&repo.root(), verify_step(path, 60));

    assert_eq!(
        outcome.expect("runs"),
        Outcome::Pass {
            summary: "all 2 asset URL(s) serve manifest bytes anonymously (attempt 3)".into()
        }
    );
    // Each sweep re-probes every asset, not just the failing one.
    assert_eq!(server.hits("/download/manifest.json"), 3);
    assert_eq!(lines.len(), 4, "{lines:#?}");
    assert!(lines[0].starts_with("retrying: attempt 1, 1/2 asset(s) not ready, "));
    assert!(
        lines[1].starts_with(&format!(
            "  - CLASSIC Fallout4.yaml: SHA-256 mismatch: expected {}, got {} \
             (CDN likely still serving the previous same-tag asset)",
            sha256(STAGED),
            sha256(STALE)
        )),
        "{}",
        lines[1]
    );
    assert!(
        lines[3].starts_with("  - CLASSIC Fallout4.yaml: HTTP 404 ("),
        "{}",
        lines[3]
    );
}

#[test]
fn verify_assets_fails_naming_each_asset_still_wrong_at_the_deadline() {
    let repo = FixtureRepo::empty();
    let server = TestServer::start();
    let (path, _) = served_manifest(&repo, &server, STAGED);
    server.route(
        "/download/CLASSIC%20Fallout4.yaml",
        vec![(200, STALE.to_vec())],
    );
    // No route for manifest.json: 404.

    let outcome = run(&repo.root(), verify_step(path, 0)).0.expect("runs");

    let Outcome::Fail { findings, summary } = outcome else {
        panic!("expected a failure");
    };
    assert_eq!(
        summary,
        "2 of 2 asset URL(s) still not serving expected bytes after 0s"
    );
    let rendered: Vec<String> = findings.iter().map(ToString::to_string).collect();
    assert!(rendered[0].starts_with(
        "staging/manifest.json:1: asset-not-serving: CLASSIC Fallout4.yaml: SHA-256 mismatch: "
    ));
    assert_eq!(
        rendered[1],
        format!(
            "staging/manifest.json:1: asset-not-serving: manifest.json: HTTP 404 ({})",
            server.url("/download/manifest.json")
        )
    );
}

#[test]
fn verify_assets_reports_a_network_error() {
    let repo = FixtureRepo::empty();
    let server = TestServer::start();
    let (path, _) = served_manifest(&repo, &server, STAGED);
    drop(server);

    let outcome = run(&repo.root(), verify_step(path, 0)).0.expect("runs");

    assert!(
        findings(&outcome)
            .iter()
            .all(|line| line.contains(": network error: ")),
        "{outcome:?}"
    );
}

#[test]
fn verify_assets_refuses_a_malformed_manifest() {
    let repo = FixtureRepo::empty().file("manifest.json", r#"{"files": []}"#);

    let error = run(
        &repo.root(),
        verify_step(repo.path().join("manifest.json"), 0),
    )
    .0
    .expect_err("malformed manifest");

    assert!(
        error.to_string().contains("has no non-empty 'files' array"),
        "{error}"
    );
}

// ---------------------------------------------------------------- smoke-pages

fn smoke_step(server: &TestServer, expected: PathBuf, timeout_seconds: u64) -> Step {
    Step::SmokePages(smoke_pages::Args {
        owner: None,
        repo: None,
        expected_body_path: expected,
        timeout_seconds,
        poll_interval_seconds: 0,
        pages_path: "yaml-data/manifest-latest.json".into(),
        base_url: Some(format!("{}/gh-pages/", server.base())),
    })
}

#[test]
fn smoke_pages_passes_once_pages_serves_the_staged_manifest() {
    let repo = FixtureRepo::empty().file("staging/manifest.json", "{\"new\": true}\n");
    let server = TestServer::start();
    server.route(
        "/gh-pages/yaml-data/manifest-latest.json",
        vec![
            (200, b"{\"old\": true}\n".to_vec()),
            (200, b"{\"new\": true}\n".to_vec()),
        ],
    );
    let expected = sha256(b"{\"new\": true}\n");

    let (outcome, lines) = run(
        &repo.root(),
        smoke_step(&server, repo.path().join("staging/manifest.json"), 60),
    );

    assert_eq!(
        outcome.expect("runs"),
        Outcome::Pass {
            summary: format!(
                "{} serves staged manifest (sha256={expected}, attempt 2)",
                server.url("/gh-pages/yaml-data/manifest-latest.json")
            )
        }
    );
    assert!(lines[0].starts_with(&format!(
        "strict-body smoke test: expecting sha256={expected} (14 bytes from "
    )));
    assert!(
        lines[1].starts_with(&format!(
            "retrying: attempt 1, remote sha256={}, expected sha256={expected}, ",
            sha256(b"{\"old\": true}\n")
        )),
        "{}",
        lines[1]
    );
}

#[test]
fn smoke_pages_fails_after_the_deadline_with_the_last_body_seen() {
    let repo = FixtureRepo::empty().file("staging/manifest.json", "{}\n");
    let server = TestServer::start();

    let outcome = run(
        &repo.root(),
        smoke_step(&server, repo.path().join("staging/manifest.json"), 0),
    )
    .0
    .expect("runs");

    assert_eq!(
        findings(&outcome),
        [format!(
            "staging/manifest.json:1: pages-not-serving: {} did not serve expected bytes (sha256={}) \
             within 0s (last saw fetch-failed)",
            server.url("/gh-pages/yaml-data/manifest-latest.json"),
            sha256(b"{}\n")
        )]
    );
}

// ---------------------------------------------------------------- workflow pin

#[test]
fn the_publish_workflow_keeps_its_step_order_and_tool_lines() {
    let root = RepoRoot::discover(None).expect("repository root");
    let text = std::fs::read_to_string(root.join(".github/workflows/publish-yaml-data.yml"))
        .expect("read workflow");
    let workflow = &yaml_rust2::YamlLoader::load_from_str(&text).expect("workflow parses")[0];
    let steps = workflow["jobs"]["publish"]["steps"]
        .as_vec()
        .expect("publish steps");
    let names: Vec<&str> = steps
        .iter()
        .map(|step| step["name"].as_str().expect("every step is named"))
        .collect();

    // Verify -> Clear prerelease -> Deploy gh-pages -> Smoke: the release is
    // fallback-discoverable before the Pages pointer can advance.
    assert_eq!(
        names,
        [
            "Checkout source (tag)",
            "Install Rust toolchain",
            "Build xtask",
            "Validate shippable YAML schema headers",
            "Generate checksums and manifest",
            "Show manifest preview",
            "Reset stale draft (idempotent re-run)",
            "Create draft GitHub release with assets",
            "Promote release (draft -> live prerelease)",
            "Verify assets reachable anonymously",
            "Clear prerelease flag (make client-discoverable)",
            "Deploy manifest to gh-pages",
            "Smoke-test Pages manifest",
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
        run_of("Validate shippable YAML schema headers").contains("cargo xtask yaml-data validate")
    );
    assert!(run_of("Generate checksums and manifest").contains("cargo xtask yaml-data manifest"));
    assert!(
        run_of("Verify assets reachable anonymously")
            .contains("cargo xtask yaml-data verify-assets")
    );
    let smoke = run_of("Smoke-test Pages manifest");
    assert!(smoke.contains("cargo xtask yaml-data smoke-pages"));
    assert!(smoke.contains("--expected-body-path \"$RUNNER_TEMP/staging/manifest.json\""));
    assert!(!smoke.contains("--tag"));
    assert!(!text.contains("python"), "no Python left in the workflow");
}
