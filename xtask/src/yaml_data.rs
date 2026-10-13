//! `cargo xtask yaml-data <step>`: the YAML Data (`yaml-data-v*`) publish
//! tooling, run by `.github/workflows/publish-yaml-data.yml` and by the
//! `xtask-linux` CI job.
//!
//! Steps, in workflow order:
//!
//! - `validate`: every `*.yaml` under the databases directory parses, carries
//!   a quoted `MAJOR.MINOR` root `schema_version`, keeps `placement`/`bucket`
//!   in agreement, and is listed in `client-schema-ranges.yaml`, whose
//!   entries must satisfy the mirrored client rules (see `client_rules`).
//! - `manifest`: stages each listed file plus a `<hex>\n` `.sha256` sidecar
//!   and writes `manifest.json` (byte-compatible with the retired Python tool).
//! - `verify-assets`: polls the release's `manifest.json` asset and every
//!   `files[].download_url` anonymously until each serves the staged bytes.
//! - `smoke-pages`: polls the GitHub Pages manifest until it serves the staged
//!   `manifest.json` bytes.
//!
//! YAML is parsed with `yaml-rust2`'s `YamlLoader`, which keeps no node
//! positions: findings point at the line a simple text search can locate
//! (a root `schema_version:` line, a ranges entry's `name:` line, a parse
//! error's line) and otherwise at line 1.
//!
//! Path flags are resolved against the current directory, as the workflow
//! passes them; findings show paths relative to the repository root when they
//! are inside it.

pub(crate) mod client_rules;
pub mod manifest;
pub mod smoke_pages;
pub mod validate;
pub mod verify_assets;

use std::path::Path;

use anyhow::Result;
use clap::Subcommand;
use yaml_rust2::{Yaml, YamlLoader};

use crate::{Finding, Outcome, RepoRoot};

/// File name of the ranges metadata inside the databases directory.
const RANGES_FILE_NAME: &str = "client-schema-ranges.yaml";

/// `cargo xtask yaml-data` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// The publish step to run.
    #[command(subcommand)]
    pub step: Step,
}

/// One YAML Data publish step.
#[derive(Debug, Clone, Subcommand)]
pub enum Step {
    /// Validate every shippable YAML file and client-schema-ranges.yaml.
    Validate(validate::Args),
    /// Stage the release assets: each file, its .sha256 sidecar, and manifest.json.
    Manifest(manifest::Args),
    /// Poll until every release asset serves the staged bytes anonymously.
    VerifyAssets(verify_assets::Args),
    /// Poll until the GitHub Pages manifest serves the staged manifest.json bytes.
    SmokePages(smoke_pages::Args),
}

/// Runs one step and discards its progress lines; see [`run_with_progress`].
///
/// # Errors
///
/// An operational failure (missing directory or file, unreadable or
/// malformed manifest, unwritable staging directory).
pub fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    run_with_progress(root, args, &mut |_| {})
}

/// Runs one step. The polling steps report each retry (and `smoke-pages` its
/// expected digest) through `progress`, one line per call, so a long wait is
/// visible in CI logs; this module never prints.
///
/// # Errors
///
/// An operational failure (missing directory or file, unreadable or
/// malformed manifest, unwritable staging directory).
pub fn run_with_progress(
    root: &RepoRoot,
    args: Args,
    progress: &mut dyn FnMut(&str),
) -> Result<Outcome> {
    match args.step {
        Step::Validate(args) => validate::run(root, args),
        Step::Manifest(args) => manifest::run(root, args),
        Step::VerifyAssets(args) => verify_assets::run(root, args, progress),
        Step::SmokePages(args) => smoke_pages::run(root, args, progress),
    }
}

/// A YAML file's text and its single document, or the finding that stops it.
enum Loaded {
    /// The file parsed to exactly one document (an empty file loads as null).
    Document {
        /// The file's text, for locating lines.
        text: String,
        /// The parsed document.
        document: Yaml,
    },
    /// The file could not be read or parsed.
    Unparseable(Finding),
}

/// Reads and parses the YAML file at `path`, reporting a read or parse
/// failure as an `unparseable-yaml` finding.
fn load_yaml(root: &RepoRoot, path: &Path) -> Loaded {
    let unparseable = |line, message: String| {
        Loaded::Unparseable(Finding::new(
            root.relative(path),
            line,
            "unparseable-yaml",
            format!("unparseable YAML: {message}"),
        ))
    };
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(error) => return unparseable(1, error.to_string()),
    };
    let mut documents = match YamlLoader::load_from_str(&text) {
        Ok(documents) => documents,
        Err(error) => return unparseable(error.marker().line().max(1), error.to_string()),
    };
    let document = match documents.len() {
        0 => Yaml::Null,
        1 => documents.remove(0),
        count => return unparseable(1, format!("expected one YAML document, found {count}")),
    };
    Loaded::Document { text, document }
}

/// The ranges file's entries, plus a finding for every ranges problem.
struct CheckedRanges {
    /// Entries that passed every rule, in file order.
    entries: Vec<client_rules::RangeEntry>,
    /// Every string `name` listed, valid or not.
    listed_names: Vec<String>,
    /// Findings against the ranges file.
    findings: Vec<Finding>,
}

/// Loads and checks the ranges file at `path`.
fn check_ranges_file(root: &RepoRoot, path: &Path) -> CheckedRanges {
    let (text, document) = match load_yaml(root, path) {
        Loaded::Document { text, document } => (text, document),
        Loaded::Unparseable(finding) => {
            return CheckedRanges {
                entries: Vec::new(),
                listed_names: Vec::new(),
                findings: vec![finding],
            };
        }
    };
    let ranges = client_rules::check_ranges(&document);
    let findings = ranges
        .problems
        .into_iter()
        .map(|problem| {
            Finding::new(
                root.relative(path),
                problem
                    .entry_name
                    .as_deref()
                    .map_or(1, |name| entry_line(&text, name)),
                problem.rule,
                problem.message,
            )
        })
        .collect();
    CheckedRanges {
        entries: ranges.entries,
        listed_names: ranges.listed_names,
        findings,
    }
}

/// The 1-based line of the ranges entry whose `name:` is `name` (quoted or
/// not), or 1 when no such line is found.
fn entry_line(text: &str, name: &str) -> usize {
    text.lines()
        .position(|line| {
            let line = line.trim_start();
            let line = line.strip_prefix('-').unwrap_or(line).trim_start();
            line.strip_prefix("name:").is_some_and(|value| {
                let value = value.trim();
                value == name
                    || value.strip_prefix('"').and_then(|v| v.strip_suffix('"')) == Some(name)
                    || value.strip_prefix('\'').and_then(|v| v.strip_suffix('\'')) == Some(name)
            })
        })
        .map_or(1, |index| index + 1)
}

#[cfg(test)]
#[path = "yaml_data_tests.rs"]
mod tests;
