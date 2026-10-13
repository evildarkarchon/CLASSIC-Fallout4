//! `cargo xtask yaml-data verify-assets`: prove the promoted release serves
//! this run's staged bytes to an anonymous client before it is made
//! discoverable.
//!
//! Reachability alone is not enough: a same-tag delete-and-rerun reuses the
//! `releases/download/<tag>/<name>` URLs, and GitHub's CDN can keep serving
//! the previous run's bytes for a while. So the release `manifest.json` asset
//! and every `files[].download_url` are fetched in full (no `Range`, no
//! credentials even when a token is in the environment) and each body's
//! SHA-256 is compared with what was staged. Any mismatch counts as "not
//! ready yet", and every asset is re-swept until all match or the budget runs
//! out.

use std::path::PathBuf;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use serde_json::Value;

use super::client_rules::quoted;
use crate::publish::probe::{self, Polled, Request, Schedule};
use crate::{Finding, Outcome, RepoRoot, digest};

/// Sent with every probe so the requests are identifiable in server logs.
const USER_AGENT: &str = "classic-publish-yaml-data/verify-assets";

/// `cargo xtask yaml-data verify-assets` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// Path to the generated manifest.json.
    #[arg(long, value_name = "FILE")]
    pub manifest: PathBuf,
    /// Total retry budget across all URLs.
    #[arg(long, default_value_t = 120)]
    pub timeout_seconds: u64,
    /// Wait between full-sweep retries.
    #[arg(long, default_value_t = 8)]
    pub poll_interval_seconds: u64,
    /// Per-request socket timeout.
    #[arg(long, default_value_t = 15)]
    pub socket_timeout_seconds: u64,
}

/// One release asset that must serve exact staged bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Asset {
    /// Asset name, for diagnostics.
    pub name: String,
    /// Anonymous download URL.
    pub url: String,
    /// Expected lowercase hex SHA-256 of the body.
    pub sha256: String,
}

/// An asset that did not serve its staged bytes on the latest sweep.
struct NotReady<'a> {
    asset: &'a Asset,
    diagnostic: String,
}

/// Polls every asset named by the manifest until all serve their staged bytes.
///
/// Before each retry, `progress` gets a `retrying: …` line followed by one
/// `  - <name>: <diagnostic> (<url>)` line per asset not yet ready.
///
/// # Errors
///
/// When the manifest cannot be read or is malformed.
pub(crate) fn run(root: &RepoRoot, args: Args, progress: &mut dyn FnMut(&str)) -> Result<Outcome> {
    let bytes = std::fs::read(&args.manifest)
        .with_context(|| format!("reading {}", args.manifest.display()))?;
    let assets = manifest_assets(&args.manifest.display().to_string(), &bytes)?;
    let socket_timeout = Duration::from_secs(args.socket_timeout_seconds);
    let total = assets.len();

    let polled = probe::poll(
        Schedule {
            timeout: Duration::from_secs(args.timeout_seconds),
            interval: Duration::from_secs(args.poll_interval_seconds),
        },
        || {
            // Sweep every asset each attempt so one offender on an N-file
            // manifest is named, not hidden behind the first failure.
            let not_ready: Vec<NotReady<'_>> = assets
                .iter()
                .filter_map(|asset| {
                    probe_asset(asset, socket_timeout)
                        .err()
                        .map(|diagnostic| NotReady { asset, diagnostic })
                })
                .collect();
            if not_ready.is_empty() {
                Ok(())
            } else {
                Err(not_ready)
            }
        },
        |attempt, not_ready, remaining| {
            progress(&format!(
                "retrying: attempt {attempt}, {}/{total} asset(s) not ready, {remaining}s remaining",
                not_ready.len()
            ));
            for item in not_ready {
                progress(&format!(
                    "  - {}: {} ({})",
                    item.asset.name, item.diagnostic, item.asset.url
                ));
            }
        },
    );

    Ok(match polled {
        Polled::Ready { attempt, .. } => Outcome::Pass {
            summary: format!(
                "all {total} asset URL(s) serve manifest bytes anonymously (attempt {attempt})"
            ),
            report: None,
        },
        Polled::TimedOut { last, .. } => {
            let failed = last.len();
            let findings = last
                .into_iter()
                .map(|item| {
                    Finding::file(
                        root.relative(&args.manifest),
                        "asset-not-serving",
                        format!(
                            "{}: {} ({})",
                            item.asset.name, item.diagnostic, item.asset.url
                        ),
                    )
                })
                .collect();
            Outcome::from_findings(
                findings,
                String::new(),
                format!(
                    "{failed} of {total} asset URL(s) still not serving expected bytes after {}s",
                    args.timeout_seconds
                ),
            )
        }
    })
}

/// One anonymous GET of `asset`; `Err` carries the diagnostic.
fn probe_asset(asset: &Asset, socket_timeout: Duration) -> Result<(), String> {
    let response = probe::fetch(&Request {
        url: &asset.url,
        headers: &[("Accept", "*/*")],
        user_agent: Some(USER_AGENT),
        socket_timeout,
    })
    .map_err(|error| format!("network error: {error}"))?;
    if response.status != 200 {
        return Err(format!("HTTP {}", response.status));
    }
    let actual = digest::sha256_hex(&response.body);
    if actual != asset.sha256 {
        return Err(format!(
            "SHA-256 mismatch: expected {}, got {actual} \
             (CDN likely still serving the previous same-tag asset)",
            asset.sha256
        ));
    }
    Ok(())
}

/// Every asset a manifest's release must serve: each `files[]` entry, then
/// the release's own `manifest.json` (next to the first file's URL, expected
/// to hash to `manifest_bytes`). `label` names the manifest in errors.
///
/// Each `sha256` is trimmed, must be 64 hex digits, and is lowercased.
///
/// # Errors
///
/// When the manifest is not a JSON object with a non-empty `files` array of
/// objects carrying string `name`, `download_url` and `sha256`, or when no
/// `manifest.json` URL can be derived from the first `download_url`.
pub(crate) fn manifest_assets(label: &str, manifest_bytes: &[u8]) -> Result<Vec<Asset>> {
    let document: Value = serde_json::from_slice(manifest_bytes)
        .with_context(|| format!("{label} is not valid JSON"))?;
    let Some(root) = document.as_object() else {
        bail!("{label} root is not a JSON object");
    };
    let files = match root.get("files").and_then(Value::as_array) {
        Some(files) if !files.is_empty() => files,
        _ => bail!("{label} has no non-empty 'files' array"),
    };
    let mut assets = Vec::with_capacity(files.len() + 1);
    for entry in files {
        let Some(fields) = entry.as_object() else {
            bail!("manifest entry is not a mapping: {entry}");
        };
        let string = |key: &str| fields.get(key).and_then(Value::as_str);
        let (Some(name), Some(url)) = (string("name"), string("download_url")) else {
            bail!("manifest entry missing string name/download_url: {entry}");
        };
        let Some(sha256) = string("sha256") else {
            bail!("manifest entry missing string sha256: {entry}");
        };
        assets.push(Asset {
            name: name.to_owned(),
            url: url.to_owned(),
            sha256: normalized_sha256(sha256)?,
        });
    }

    let first_url = &assets[0].url;
    let base = match first_url.rsplit_once('/') {
        Some((base, _)) if !base.is_empty() => base,
        _ => bail!(
            "cannot derive manifest.json release asset URL from download_url: {}",
            quoted(first_url)
        ),
    };
    assets.push(Asset {
        name: "manifest.json".to_owned(),
        url: format!("{base}/manifest.json"),
        sha256: digest::sha256_hex(manifest_bytes),
    });
    Ok(assets)
}

/// A manifest `sha256` value, trimmed and lowercased.
fn normalized_sha256(raw: &str) -> Result<String> {
    let trimmed = raw.trim();
    if trimmed.len() != 64 || !trimmed.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        bail!(
            "manifest entry sha256 must be a 64-character hex digest (got {})",
            quoted(raw)
        );
    }
    Ok(trimmed.to_ascii_lowercase())
}

#[cfg(test)]
#[path = "verify_assets_tests.rs"]
mod tests;
