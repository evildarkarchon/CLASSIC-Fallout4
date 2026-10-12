//! `cargo xtask yaml-data validate`: refuse a YAML Data publish whose files a
//! client could not load or that the ranges metadata does not list.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use yaml_rust2::Yaml;

use super::client_rules::{describe, parse_schema_version, quoted};
use super::{Loaded, RANGES_FILE_NAME, check_ranges_file, entry_line, load_yaml};
use crate::{Finding, Outcome, RepoRoot};

/// `cargo xtask yaml-data validate` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// Path to `CLASSIC Data/databases/`.
    #[arg(long, value_name = "DIR")]
    pub databases_dir: PathBuf,
    /// Path to client-schema-ranges.yaml (defaults to
    /// <databases-dir>/client-schema-ranges.yaml).
    #[arg(long, value_name = "FILE")]
    pub schema_ranges: Option<PathBuf>,
}

/// Validates the ranges file and every `*.yaml` file in the databases
/// directory, collecting every finding.
///
/// Per file, in order: it parses as one YAML mapping; every mapping that has
/// both `placement` and `bucket` gives them the same trimmed, lowercased
/// value; the root has a quoted `schema_version` the client parses. A file
/// with no other finding must be listed in the ranges file, and every listed
/// name must exist.
///
/// # Errors
///
/// When the databases directory or the ranges file is missing, or the
/// directory holds no `*.yaml` file.
pub(crate) fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    let dir = &args.databases_dir;
    if !dir.is_dir() {
        bail!("{} is not a directory", dir.display());
    }
    let ranges_path = args
        .schema_ranges
        .unwrap_or_else(|| dir.join(RANGES_FILE_NAME));
    if !ranges_path.is_file() {
        bail!(
            "client-schema-ranges file {} is missing",
            ranges_path.display()
        );
    }
    let ranges_name = ranges_path
        .file_name()
        .map_or_else(String::new, |name| name.to_string_lossy().into_owned());

    let ranges = check_ranges_file(root, &ranges_path);
    let mut findings = ranges.findings;
    let listed: BTreeSet<&str> = ranges.listed_names.iter().map(String::as_str).collect();

    let yaml_files = yaml_files(dir)?;
    if yaml_files.is_empty() {
        bail!("{} contains no *.yaml files", dir.display());
    }
    let ranges_identity = std::fs::canonicalize(&ranges_path).ok();
    let mut seen = BTreeSet::new();
    for path in &yaml_files {
        // The ranges file has no schema_version; it was checked above.
        if ranges_identity.is_some() && std::fs::canonicalize(path).ok() == ranges_identity {
            continue;
        }
        let mut file_findings = validate_file(root, path);
        let name = path
            .file_name()
            .map_or_else(String::new, |name| name.to_string_lossy().into_owned());
        if listed.contains(name.as_str()) {
            seen.insert(name);
        } else if file_findings.is_empty() {
            // Every *.yaml in the directory is uploaded, so an unlisted file
            // would ship with no published schema range.
            file_findings.push(Finding {
                path: root.relative(path),
                line: 1,
                rule: "unlisted-shippable-yaml",
                message: format!("shippable YAML not listed in {ranges_name}"),
            });
        }
        findings.extend(file_findings);
    }

    let ranges_text = std::fs::read_to_string(&ranges_path).unwrap_or_default();
    for name in listed.iter().filter(|name| !seen.contains(**name)) {
        findings.push(Finding {
            path: root.relative(&ranges_path),
            line: entry_line(&ranges_text, name),
            rule: "missing-shippable-yaml",
            message: format!(
                "{name} listed in {ranges_name} but not found in {}",
                dir.display()
            ),
        });
    }

    let count = findings.len();
    Ok(Outcome::from_findings(
        findings,
        format!("validated {} shippable YAML files", seen.len()),
        format!("yaml-data validate: {count} finding(s)"),
    ))
}

/// The `*.yaml` files directly inside `dir`, sorted.
fn yaml_files(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    for entry in std::fs::read_dir(dir).with_context(|| format!("reading {}", dir.display()))? {
        let path = entry
            .with_context(|| format!("reading {}", dir.display()))?
            .path();
        let is_yaml = path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.ends_with(".yaml"));
        if is_yaml && path.is_file() {
            files.push(path);
        }
    }
    files.sort();
    Ok(files)
}

/// Every finding for one shippable YAML file.
fn validate_file(root: &RepoRoot, path: &Path) -> Vec<Finding> {
    let (text, document) = match load_yaml(root, path) {
        Loaded::Document { text, document } => (text, document),
        Loaded::Unparseable(finding) => return vec![finding],
    };
    let finding = |line, rule, message| Finding {
        path: root.relative(path),
        line,
        rule,
        message,
    };
    if !matches!(document, Yaml::Hash(_)) {
        return vec![finding(
            1,
            "root-not-mapping",
            "root document is not a mapping".to_owned(),
        )];
    }

    let mut findings = Vec::new();
    for (placement, bucket) in placement_bucket_disagreements(&document) {
        findings.push(finding(
            1,
            "placement-bucket-mismatch",
            format!(
                "action declares placement={} and bucket={}; both keys must resolve to the same value",
                python_repr(placement),
                python_repr(bucket)
            ),
        ));
    }

    let schema_line = text
        .lines()
        .position(|line| line.starts_with("schema_version:"))
        .map_or(1, |index| index + 1);
    match &document["schema_version"] {
        Yaml::BadValue => findings.push(finding(
            1,
            "missing-schema-version",
            "missing root-level schema_version".to_owned(),
        )),
        Yaml::String(value) => {
            if parse_schema_version(value).is_none() {
                findings.push(finding(
                    schema_line,
                    "malformed-schema-version",
                    format!(
                        "schema_version {} is not a MAJOR.MINOR schema version",
                        quoted(value)
                    ),
                ));
            }
        }
        other => findings.push(finding(
            schema_line,
            "schema-version-not-string",
            format!(
                "schema_version must be a quoted string, got {}",
                describe(other)
            ),
        )),
    }
    findings
}

/// Every `(placement, bucket)` pair, from any mapping nested anywhere in
/// `node`, whose values disagree.
///
/// Runtime rule parsers read `placement` and fall back to `bucket`, so an
/// action carrying both with different values would render to different
/// Autoscan Report sections depending on client version. Strings compare
/// trimmed and lowercased (as the parsers match them); other values compare
/// as-is, so a malformed value never equals a valid one.
fn placement_bucket_disagreements(node: &Yaml) -> Vec<(&Yaml, &Yaml)> {
    let mut found = Vec::new();
    match node {
        Yaml::Hash(map) => {
            let placement = map.get(&Yaml::String("placement".to_owned()));
            let bucket = map.get(&Yaml::String("bucket".to_owned()));
            if let (Some(placement), Some(bucket)) = (placement, bucket)
                && normalized(placement) != normalized(bucket)
            {
                found.push((placement, bucket));
            }
            for value in map.values() {
                found.extend(placement_bucket_disagreements(value));
            }
        }
        Yaml::Array(items) => {
            for item in items {
                found.extend(placement_bucket_disagreements(item));
            }
        }
        _ => {}
    }
    found
}

/// A placement/bucket value as the runtime parsers compare it.
fn normalized(value: &Yaml) -> Yaml {
    match value {
        Yaml::String(text) => Yaml::String(text.trim().to_lowercase()),
        other => other.clone(),
    }
}

/// Renders a YAML value the way the retired Python tool's `repr` did, so the
/// `placement='…'` wording in logs is unchanged.
fn python_repr(value: &Yaml) -> String {
    match value {
        Yaml::String(text) => quoted(text),
        Yaml::Real(text) => text.clone(),
        Yaml::Integer(number) => number.to_string(),
        Yaml::Boolean(true) => "True".to_owned(),
        Yaml::Boolean(false) => "False".to_owned(),
        Yaml::Null => "None".to_owned(),
        other => describe(other),
    }
}
