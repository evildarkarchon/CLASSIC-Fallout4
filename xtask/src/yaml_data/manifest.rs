//! `cargo xtask yaml-data manifest`: stage the release assets for a
//! `yaml-data-v*` publish.
//!
//! For every `client-schema-ranges.yaml` entry, in file order, the source file
//! is copied to `<staging>/<name>` and a `<staging>/<name>.sha256` sidecar is
//! written as `<lowercase hex>\n`. Then `<staging>/manifest.json` is written.
//!
//! `manifest.json` is byte-compatible with the retired Python tool's
//! `json.dump(manifest, indent=2)` plus a trailing newline: keys in a fixed
//! order, two-space indent, `,` and `: ` separators, LF line endings, and
//! non-ASCII escaped as lowercase `\uXXXX` (surrogate pairs above the BMP),
//! because Python's `ensure_ascii` defaults to on. Every `download_url` is
//! `https://github.com/<repo>/releases/download/<tag>/<name>` with the name
//! percent-encoded like Python's `urllib.parse.quote(name, safe="")`; the
//! client rejects any other shape.

use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

use anyhow::{Context, Result};
use serde::Serialize;
use yaml_rust2::Yaml;

use super::{Loaded, RANGES_FILE_NAME, check_ranges_file, entry_line, load_yaml};
use crate::digest::sha256_hex;
use crate::publish::utc_timestamp;
use crate::{Finding, Outcome, RepoRoot};

/// The `manifest_version` this tool writes.
const MANIFEST_VERSION: u32 = 1;

/// `cargo xtask yaml-data manifest` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// Release tag, e.g. yaml-data-v2026.04.17.
    #[arg(long)]
    pub tag: String,
    /// "<owner>/<repo>" (github.repository).
    #[arg(long)]
    pub repo: String,
    /// Path to `CLASSIC Data/databases/`.
    #[arg(long, value_name = "DIR")]
    pub databases_dir: PathBuf,
    /// Defaults to <databases-dir>/client-schema-ranges.yaml.
    #[arg(long, value_name = "FILE")]
    pub schema_ranges: Option<PathBuf>,
    /// Output directory to populate with release assets.
    #[arg(long, value_name = "DIR")]
    pub staging: PathBuf,
    /// Fixed `published_at` for deterministic tests; the CLI always uses the
    /// current UTC time.
    #[arg(skip)]
    pub published_at: Option<String>,
}

/// `manifest.json`, with fields in output order.
#[derive(Debug, Serialize)]
struct Manifest {
    manifest_version: u32,
    release_tag: String,
    published_at: String,
    files: Vec<ManifestFile>,
    signatures: Vec<()>,
}

/// One `files[]` entry, with fields in output order.
#[derive(Debug, Serialize)]
struct ManifestFile {
    name: String,
    schema_version: String,
    sha256: String,
    size_bytes: u64,
    min_client_schema: String,
    max_client_schema: String,
    download_url: String,
}

/// Stages every listed file with its sidecar, then writes `manifest.json`.
///
/// The ranges file is re-checked first (all findings collected), so a direct
/// run cannot publish a range the client would refuse; nothing is staged when
/// it has findings. A listed file that is missing, or whose staged copy has no
/// string root `schema_version`, is a finding and `manifest.json` is not
/// written.
///
/// # Errors
///
/// When the staging directory or a staged file cannot be written.
pub(crate) fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    let ranges_path = args
        .schema_ranges
        .clone()
        .unwrap_or_else(|| args.databases_dir.join(RANGES_FILE_NAME));
    let ranges = check_ranges_file(root, &ranges_path);
    if !ranges.findings.is_empty() {
        return Ok(failed(ranges.findings));
    }
    std::fs::create_dir_all(&args.staging)
        .with_context(|| format!("creating {}", args.staging.display()))?;
    let ranges_text = std::fs::read_to_string(&ranges_path).unwrap_or_default();

    let mut findings = Vec::new();
    let mut files = Vec::new();
    for entry in ranges.entries {
        let source = args.databases_dir.join(&entry.name);
        if !source.is_file() {
            findings.push(Finding::new(
                root.relative(&ranges_path),
                entry_line(&ranges_text, &entry.name),
                "missing-shippable-source",
                format!("shippable source missing: {}", source.display()),
            ));
            continue;
        }
        let staged = args.staging.join(&entry.name);
        std::fs::copy(&source, &staged)
            .with_context(|| format!("copying {} to {}", source.display(), staged.display()))?;
        let bytes =
            std::fs::read(&staged).with_context(|| format!("reading {}", staged.display()))?;
        let digest = sha256_hex(&bytes);
        let sidecar = sidecar_path(&staged);
        std::fs::write(&sidecar, format!("{digest}\n"))
            .with_context(|| format!("writing {}", sidecar.display()))?;

        let Some(schema_version) = staged_schema_version(root, &staged) else {
            findings.push(Finding::file(
                root.relative(&staged),
                "missing-schema-version",
                "has no string schema_version (run `cargo xtask yaml-data validate` first)"
                    .to_owned(),
            ));
            continue;
        };
        files.push(ManifestFile {
            download_url: download_url(&args.repo, &args.tag, &entry.name),
            name: entry.name,
            schema_version,
            sha256: digest,
            size_bytes: bytes.len() as u64,
            min_client_schema: entry.min_client_schema,
            max_client_schema: entry.max_client_schema,
        });
    }
    if !findings.is_empty() {
        return Ok(failed(findings));
    }

    let manifest = Manifest {
        manifest_version: MANIFEST_VERSION,
        release_tag: args.tag,
        published_at: args
            .published_at
            .unwrap_or_else(|| utc_timestamp(SystemTime::now())),
        signatures: Vec::new(),
        files,
    };
    let manifest_path = args.staging.join("manifest.json");
    std::fs::write(&manifest_path, manifest_bytes(&manifest)?)
        .with_context(|| format!("writing {}", manifest_path.display()))?;

    Ok(Outcome::Pass {
        summary: format!(
            "staged {} files at {} and wrote {}",
            manifest.files.len(),
            args.staging.display(),
            manifest_path.display()
        ),
        report: None,
    })
}

/// A `Fail` outcome for manifest generation.
fn failed(findings: Vec<Finding>) -> Outcome {
    let count = findings.len();
    Outcome::from_findings(
        findings,
        String::new(),
        format!("yaml-data manifest: {count} finding(s); nothing published"),
    )
}

/// `<file>.sha256` next to `staged`.
fn sidecar_path(staged: &Path) -> PathBuf {
    let mut name = staged.as_os_str().to_owned();
    name.push(".sha256");
    PathBuf::from(name)
}

/// The staged copy's root `schema_version` string, if it has one.
fn staged_schema_version(root: &RepoRoot, staged: &Path) -> Option<String> {
    match load_yaml(root, staged) {
        Loaded::Document { document, .. } => match &document["schema_version"] {
            Yaml::String(value) => Some(value.clone()),
            _ => None,
        },
        Loaded::Unparseable(_) => None,
    }
}

/// The canonical release-asset URL for `asset_name`. Only the asset name is
/// encoded; `repo` and `tag` are used as given.
pub(crate) fn download_url(repo: &str, tag: &str, asset_name: &str) -> String {
    format!(
        "https://github.com/{repo}/releases/download/{tag}/{}",
        quote(asset_name)
    )
}

/// Percent-encodes `text` like Python's `urllib.parse.quote(text, safe="")`:
/// every UTF-8 byte except `A-Z a-z 0-9 _ . - ~` becomes `%XX` (uppercase
/// hex), so a space is `%20`, never `+`.
fn quote(text: &str) -> String {
    let mut encoded = String::with_capacity(text.len());
    for byte in text.bytes() {
        if byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'-' | b'~') {
            encoded.push(char::from(byte));
        } else {
            // Writing to a String cannot fail.
            let _ = write!(encoded, "%{byte:02X}");
        }
    }
    encoded
}

/// Serializes `manifest` exactly as Python's `json.dump(indent=2)` followed by
/// `"\n"` does.
fn manifest_bytes(manifest: &Manifest) -> Result<Vec<u8>> {
    let pretty = serde_json::to_string_pretty(manifest).context("serializing manifest.json")?;
    let mut text = ensure_ascii(&pretty);
    text.push('\n');
    Ok(text.into_bytes())
}

/// Escapes every character outside printable ASCII (`0x7F` and above) as
/// lowercase `\uXXXX`, using a surrogate pair above the BMP, as Python's
/// `ensure_ascii` does.
///
/// Applied to already-serialized JSON: `serde_json` has escaped quotes,
/// backslashes and control characters, and non-ASCII can only occur inside
/// strings, so escaping it here keeps the JSON valid and equal in value.
fn ensure_ascii(json: &str) -> String {
    let mut out = String::with_capacity(json.len());
    for ch in json.chars() {
        if u32::from(ch) < 0x7f {
            out.push(ch);
        } else {
            let mut units = [0u16; 2];
            for unit in ch.encode_utf16(&mut units) {
                // Writing to a String cannot fail.
                let _ = write!(out, "\\u{unit:04x}");
            }
        }
    }
    out
}

#[cfg(test)]
#[path = "manifest_tests.rs"]
mod tests;
