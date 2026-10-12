//! `cargo xtask app-notification manifest`: project the validated source into
//! the `manifest.json` the workflow uploads as a release asset and mirrors to
//! GitHub Pages.
//!
//! The required fields are re-checked here, so a source change is caught
//! even when `validate` was skipped locally. When the source leaves
//! `published_at` null, `--published-at` (the tag's publication time in the
//! workflow) fills it, so every client sees a stable, workflow-provided
//! timestamp rather than "now".
//!
//! Output is byte-compatible with the retired Python tool's
//! `json.dumps(indent=2, ensure_ascii=False) + "\n"`: keys in the client's
//! field order (`manifest_version, release_tag, latest_version, published_at,
//! [min_supported_version], [display {title, body, [cta_url]}]`), two-space
//! indent, `,` and `: ` separators, non-ASCII written as UTF-8 (no BOM),
//! control characters escaped as lowercase `\u00XX`, LF line endings and a
//! trailing newline.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::Serialize;
use yaml_rust2::Yaml;

use super::{as_str, display_line, field, load_source, top_level_line};
use crate::{Finding, Outcome, RepoRoot};

/// `cargo xtask app-notification manifest` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// Path to the app-notification.yaml source artifact.
    #[arg(long, value_name = "FILE")]
    pub source: PathBuf,
    /// Path to write the generated manifest.json.
    #[arg(long, value_name = "FILE")]
    pub output: PathBuf,
    /// RFC 3339 timestamp to substitute when the source sets published_at to
    /// null (e.g. the tag's UTC publication time). Not re-validated.
    #[arg(long)]
    pub published_at: Option<String>,
}

/// `manifest.json`, with fields in output order.
#[derive(Debug, Serialize)]
struct Manifest {
    manifest_version: String,
    release_tag: String,
    latest_version: String,
    published_at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    min_supported_version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    display: Option<Display>,
}

/// The `display` object, with fields in output order.
#[derive(Debug, Serialize)]
struct Display {
    title: String,
    body: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    cta_url: Option<String>,
}

/// Generates `args.output` (creating its parent directories) from the
/// source. Every source problem is a finding, all collected, and then nothing
/// is written.
///
/// # Errors
///
/// When the output cannot be written.
pub(crate) fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    let manifest = match build(root, &args.source, args.published_at.as_deref()) {
        Ok(manifest) => manifest,
        Err(findings) => {
            let count = findings.len();
            return Ok(Outcome::from_findings(
                findings,
                String::new(),
                format!("app-notification manifest: {count} finding(s); nothing written"),
            ));
        }
    };
    if let Some(parent) = args
        .output
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
    {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("creating {}", parent.display()))?;
    }
    std::fs::write(&args.output, manifest_bytes(&manifest)?)
        .with_context(|| format!("writing {}", args.output.display()))?;
    Ok(Outcome::Pass {
        summary: format!("wrote {}", args.output.display()),
    })
}

/// Projects the source at `path` into a [`Manifest`], or every finding that
/// stops it.
fn build(root: &RepoRoot, path: &Path, fallback: Option<&str>) -> Result<Manifest, Vec<Finding>> {
    let source = match load_source(root, path) {
        Ok(source) => source,
        Err(finding) => return Err(vec![finding]),
    };
    let doc = &source.document;
    let text = &source.text;
    let relative = root.relative(path);
    let mut findings = Vec::new();
    let mut report = |line: usize, rule: &'static str, message: String| {
        findings.push(Finding {
            path: relative.clone(),
            line,
            rule,
            message,
        });
    };
    if !matches!(doc, Yaml::Hash(_)) {
        report(
            1,
            "not-a-mapping",
            format!("{} top-level document must be a mapping", path.display()),
        );
        drop(report);
        return Err(findings);
    }
    let line_of = |key: &str| top_level_line(text, key).unwrap_or(1);

    let mut required = |key: &str| {
        let value = as_str(field(doc, key)).filter(|value| !value.trim().is_empty());
        if value.is_none() {
            report(
                line_of(key),
                "missing-required-field",
                format!("source missing required string field `{key}`"),
            );
        }
        value.map(str::to_owned)
    };
    let manifest_version = required("manifest_version");
    let release_tag = required("release_tag");
    let latest_version = required("latest_version");

    let published_at = match field(doc, "published_at") {
        Yaml::Null => match fallback.filter(|fallback| !fallback.is_empty()) {
            Some(fallback) => Some(fallback.to_owned()),
            None => {
                report(
                    line_of("published_at"),
                    "missing-published-at",
                    "source `published_at` is null and no --published-at fallback was supplied"
                        .to_owned(),
                );
                None
            }
        },
        Yaml::String(value) if !value.trim().is_empty() => Some(value.clone()),
        _ => {
            report(
                line_of("published_at"),
                "invalid-published-at",
                "source `published_at` must be a non-empty string or null".to_owned(),
            );
            None
        }
    };

    let min_supported_version = match field(doc, "min_supported_version") {
        Yaml::Null => None,
        Yaml::String(value) if !value.trim().is_empty() => Some(value.clone()),
        _ => {
            report(
                line_of("min_supported_version"),
                "invalid-min-supported-version",
                "source `min_supported_version` must be null or a non-empty string".to_owned(),
            );
            None
        }
    };

    let display = field(doc, "display");
    let display = match display {
        Yaml::Null => None,
        Yaml::Hash(_) => {
            let mut string = |key: &str| {
                let value = as_str(field(display, key)).map(str::to_owned);
                if value.is_none() {
                    report(
                        display_line(text, key),
                        "invalid-display",
                        format!("source `display.{key}` must be a string when display is set"),
                    );
                }
                value
            };
            let title = string("title");
            let body = string("body");
            let cta_url = match field(display, "cta_url") {
                Yaml::Null => None,
                Yaml::String(value) if !value.trim().is_empty() => Some(value.clone()),
                _ => {
                    report(
                        display_line(text, "cta_url"),
                        "invalid-cta-url",
                        "source `display.cta_url` must be null/omitted or a non-empty string"
                            .to_owned(),
                    );
                    None
                }
            };
            title.zip(body).map(|(title, body)| Display {
                title,
                body,
                cta_url,
            })
        }
        _ => {
            report(
                line_of("display"),
                "invalid-display",
                "source `display` must be a mapping or null".to_owned(),
            );
            None
        }
    };

    // A missing required field has always been reported, so the `else` only
    // runs with findings to return.
    let (Some(manifest_version), Some(release_tag), Some(latest_version), Some(published_at)) =
        (manifest_version, release_tag, latest_version, published_at)
    else {
        return Err(findings);
    };
    if !findings.is_empty() {
        return Err(findings);
    }
    Ok(Manifest {
        manifest_version,
        release_tag,
        latest_version,
        published_at,
        min_supported_version,
        display,
    })
}

/// Serializes `manifest` exactly as Python's `json.dumps(indent=2,
/// ensure_ascii=False)` followed by `"\n"` does. `serde_json`'s pretty
/// printer uses the same indent, separators and string escapes (lowercase
/// `\u00XX` for control characters, everything else as-is).
fn manifest_bytes(manifest: &Manifest) -> Result<Vec<u8>> {
    let mut text = serde_json::to_string_pretty(manifest).context("serializing manifest.json")?;
    text.push('\n');
    Ok(text.into_bytes())
}
