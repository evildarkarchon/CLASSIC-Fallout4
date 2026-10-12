//! `cargo xtask app-notification validate`: refuse a publish whose workflow
//! tag or source the client contract would reject.
//!
//! The rules match the Rust client (`classic_update_core::notification`) in
//! both directions: a laxer check would publish manifests every client then
//! refuses, a stricter one would block valid ones. Two deliberate source-side
//! strictnesses remain, as in the retired tool: unknown top-level and
//! `display` keys are refused (the client ignores them, but here they are
//! almost always typos).

use std::path::{Path, PathBuf};

use anyhow::Result;
use yaml_rust2::Yaml;

use super::rules::{
    is_https_cta_url, is_manifest_version, is_release_tag, is_rfc3339, is_semver, is_workflow_tag,
    semver_precedence,
};
use super::{as_str, display_line, field, load_source, py_repr, py_str_repr, top_level_line};
use crate::{Finding, Outcome, RepoRoot};

/// The path findings against `--workflow-tag` are reported under.
pub(crate) const WORKFLOW_TAG_PATH: &str = "--workflow-tag";

/// Keys the source's top level may carry.
const TOP_LEVEL_KEYS: [&str; 6] = [
    "manifest_version",
    "release_tag",
    "latest_version",
    "published_at",
    "min_supported_version",
    "display",
];

/// Keys a `display` mapping may carry.
const DISPLAY_KEYS: [&str; 3] = ["title", "body", "cta_url"];

/// `cargo xtask app-notification validate` arguments.
#[derive(Debug, Clone, clap::Args)]
#[group(id = "input", required = true, multiple = true)]
pub struct Args {
    /// Path to the app-notification.yaml source artifact.
    #[arg(long, value_name = "FILE", group = "input")]
    pub source: Option<PathBuf>,
    /// Git tag that triggered the app-notification publish workflow.
    #[arg(long, group = "input")]
    pub workflow_tag: Option<String>,
}

/// Validates the tag and/or the source (at least one is required; clap
/// enforces that for the CLI), collecting every finding.
///
/// # Errors
///
/// Never in practice; an unreadable source is a finding.
pub(crate) fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    let mut findings = Vec::new();
    let mut passed = Vec::new();
    if let Some(tag) = &args.workflow_tag {
        findings.extend(check_workflow_tag(tag));
        passed.push(format!("{tag} passes app-notification tag validation"));
    }
    if let Some(source) = &args.source {
        findings.extend(check_source(root, source));
        passed.push(format!(
            "{} passes app-notification validation",
            source.display()
        ));
    }
    let count = findings.len();
    Ok(Outcome::from_findings(
        findings,
        passed.join("; "),
        format!("app-notification validate: {count} finding(s)"),
    ))
}

/// Findings for a workflow tag that is not `app-notification-v<SEMVER>`.
pub(crate) fn check_workflow_tag(tag: &str) -> Vec<Finding> {
    if is_workflow_tag(tag) {
        return Vec::new();
    }
    vec![Finding {
        path: WORKFLOW_TAG_PATH.to_owned(),
        line: 1,
        rule: "invalid-workflow-tag",
        message: format!(
            "workflow tag must match app-notification-v<SEMVER> (for example \
             app-notification-v9.2.0; got {})",
            py_str_repr(tag)
        ),
    }]
}

/// Every finding for the source at `path`, including a read or parse failure.
pub(crate) fn check_source(root: &RepoRoot, path: &Path) -> Vec<Finding> {
    let source = match load_source(root, path) {
        Ok(source) => source,
        Err(finding) => return vec![finding],
    };
    let relative = root.relative(path);
    let text = &source.text;
    let mut findings = Vec::new();
    let mut report = |line: usize, rule: &'static str, message: String| {
        findings.push(Finding {
            path: relative.clone(),
            line,
            rule,
            message,
        });
    };
    let doc = &source.document;
    let Yaml::Hash(hash) = doc else {
        report(
            1,
            "not-a-mapping",
            "top-level document must be a YAML mapping".to_owned(),
        );
        return findings;
    };
    let line_of = |key: &str| top_level_line(text, key).unwrap_or(1);

    let manifest_version = field(doc, "manifest_version");
    if !as_str(manifest_version).is_some_and(is_manifest_version) {
        report(
            line_of("manifest_version"),
            "invalid-manifest-version",
            format!(
                "manifest_version must be a quoted MAJOR.MINOR string (got {})",
                py_repr(manifest_version)
            ),
        );
    }

    let release_tag = field(doc, "release_tag");
    if !as_str(release_tag).is_some_and(is_release_tag) {
        report(
            line_of("release_tag"),
            "invalid-release-tag",
            format!(
                "release_tag must be a `v<SEMVER>` string (got {})",
                py_repr(release_tag)
            ),
        );
    }

    let latest_version = field(doc, "latest_version");
    let latest = as_str(latest_version).filter(|text| is_semver(text));
    if latest.is_none() {
        report(
            line_of("latest_version"),
            "invalid-latest-version",
            format!(
                "latest_version must be a SemVer string (got {})",
                py_repr(latest_version)
            ),
        );
    }

    match field(doc, "published_at") {
        Yaml::Null => {}
        Yaml::String(text) if is_rfc3339(text) => {}
        Yaml::String(text) => report(
            line_of("published_at"),
            "invalid-published-at",
            format!(
                "published_at is not RFC 3339 with an explicit Z or ±HH:MM offset: {}",
                py_str_repr(text)
            ),
        ),
        _ => report(
            line_of("published_at"),
            "invalid-published-at",
            "published_at must be null or an RFC 3339 string".to_owned(),
        ),
    }

    let min_supported = field(doc, "min_supported_version");
    let minimum = as_str(min_supported).filter(|text| is_semver(text));
    if !matches!(min_supported, Yaml::Null) && minimum.is_none() {
        report(
            line_of("min_supported_version"),
            "invalid-min-supported-version",
            format!(
                "min_supported_version must be a SemVer string or null (got {})",
                py_repr(min_supported)
            ),
        );
    }

    // A minimum above the latest version would falsely deprecate even the
    // advertised latest build (the client's `classify` checks the minimum
    // first). Compared only once both fields have a valid shape.
    if let (Some(minimum), Some(latest)) = (minimum, latest)
        && semver_precedence(minimum, latest).is_gt()
    {
        report(
            line_of("min_supported_version"),
            "min-supported-exceeds-latest",
            format!(
                "min_supported_version ({}) must not exceed latest_version ({})",
                py_str_repr(minimum),
                py_str_repr(latest)
            ),
        );
    }

    check_display(text, field(doc, "display"), line_of("display"), &mut report);

    let unknown = unknown_keys(hash, &TOP_LEVEL_KEYS);
    if let Some((first, _)) = unknown.first() {
        report(
            top_level_line(text, first).unwrap_or(1),
            "unexpected-keys",
            format!(
                "top-level document has unexpected keys: {}",
                py_list(&unknown)
            ),
        );
    }
    findings
}

/// The `display` checks, in the retired tool's order: title, body, cta_url,
/// then unknown keys.
fn check_display(
    text: &str,
    display: &Yaml,
    display_at: usize,
    report: &mut impl FnMut(usize, &'static str, String),
) {
    let hash = match display {
        Yaml::Null => return,
        Yaml::Hash(hash) => hash,
        _ => {
            report(
                display_at,
                "invalid-display",
                "display must be a mapping or null".to_owned(),
            );
            return;
        }
    };
    if !as_str(field(display, "title")).is_some_and(|title| !title.trim().is_empty()) {
        report(
            display_line(text, "title"),
            "invalid-display",
            "display.title must be a non-empty string".to_owned(),
        );
    }
    if as_str(field(display, "body")).is_none() {
        report(
            display_line(text, "body"),
            "invalid-display",
            "display.body must be a string".to_owned(),
        );
    }
    match field(display, "cta_url") {
        Yaml::Null => {}
        // The GUI opens this URL from an update prompt, so a non-HTTPS value
        // could send users to an unauthenticated page at the moment they are
        // asked to fetch an update.
        Yaml::String(cta) if !is_https_cta_url(cta) => report(
            display_line(text, "cta_url"),
            "invalid-cta-url",
            format!(
                "display.cta_url must be an HTTPS URL (got {})",
                py_str_repr(cta)
            ),
        ),
        Yaml::String(_) => {}
        _ => report(
            display_line(text, "cta_url"),
            "invalid-cta-url",
            "display.cta_url must be a string or null/omitted".to_owned(),
        ),
    }
    let unknown = unknown_keys(hash, &DISPLAY_KEYS);
    if let Some((first, _)) = unknown.first() {
        report(
            display_line(text, first),
            "unexpected-keys",
            format!("display has unexpected keys: {}", py_list(&unknown)),
        );
    }
}

/// The keys of `hash` not in `known`, sorted (the retired tool printed
/// `sorted(unknown)`), each as `(name, repr)`. A non-string key's name is its
/// rendering, which is also what it sorts by.
fn unknown_keys(hash: &yaml_rust2::yaml::Hash, known: &[&str]) -> Vec<(String, String)> {
    let mut unknown: Vec<(String, String)> = hash
        .keys()
        .filter(|key| !as_str(key).is_some_and(|key| known.contains(&key)))
        .map(|key| {
            let name = as_str(key).map_or_else(|| py_repr(key), str::to_owned);
            (name, py_repr(key))
        })
        .collect();
    unknown.sort();
    unknown
}

/// Python's `repr` of the sorted unknown-key list.
fn py_list(keys: &[(String, String)]) -> String {
    let reprs: Vec<&str> = keys.iter().map(|(_, repr)| repr.as_str()).collect();
    format!("[{}]", reprs.join(", "))
}
