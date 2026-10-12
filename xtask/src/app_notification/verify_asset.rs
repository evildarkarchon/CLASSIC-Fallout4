//! `cargo xtask app-notification verify-asset`: prove the promoted release's
//! single asset, `manifest.json`, is anonymously reachable before the
//! release becomes discoverable.
//!
//! Reachability alone is not enough. The workflow supports delete-and-rerun
//! on the same tag, which reuses `releases/download/<tag>/manifest.json`, and
//! GitHub's CDN can keep serving the previous recreation's bytes. A
//! reachability-only probe would pass while Releases-fallback clients later
//! read the stale asset, splitting them from Pages-first clients. With
//! `--expected-body-path`, the fetched body's SHA-256 must equal the staged
//! manifest's, and a mismatch counts as "not ready yet".

use std::path::PathBuf;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use serde_json::Value;

use crate::publish::probe::{self, Polled, Request, Schedule};
use crate::{Finding, Outcome, RepoRoot};

/// Sent with every probe so the requests are identifiable in server logs.
const USER_AGENT: &str = "classic-app-notification-publish-probe";

/// Per-request socket timeout (fixed, as in the retired tool).
const SOCKET_TIMEOUT: Duration = Duration::from_secs(15);

/// `cargo xtask app-notification verify-asset` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// URL of the release asset manifest.json (HTTPS in CI, localhost for dry
    /// runs).
    #[arg(long)]
    pub url: String,
    /// Staged manifest.json bytes. When given, success also requires the
    /// fetched body's SHA-256 to match this file's, closing the same-tag
    /// stale-CDN window.
    #[arg(long, value_name = "FILE")]
    pub expected_body_path: Option<PathBuf>,
    /// Total retry budget in seconds.
    #[arg(long, default_value_t = 120)]
    pub timeout_seconds: u64,
    /// Seconds between retries.
    #[arg(long, default_value_t = 5)]
    pub poll_interval_seconds: u64,
}

/// Polls the asset until one probe succeeds or the budget runs out.
///
/// With an expected body, `progress` first gets an `expecting body SHA-256 …`
/// line; it then gets a `retrying: …` line before each retry. A timeout is a
/// finding against the expected body path (or, without one, the URL).
///
/// # Errors
///
/// When `--expected-body-path` is not a regular file or cannot be read.
pub(crate) fn run(root: &RepoRoot, args: Args, progress: &mut dyn FnMut(&str)) -> Result<Outcome> {
    let expected = match &args.expected_body_path {
        Some(path) => {
            if !path.is_file() {
                bail!(
                    "--expected-body-path `{}` does not exist or is not a regular file",
                    path.display()
                );
            }
            let bytes =
                std::fs::read(path).with_context(|| format!("reading {}", path.display()))?;
            let digest = probe::sha256_hex(&bytes);
            progress(&format!(
                "expecting body SHA-256 {digest} (computed from {})",
                path.display()
            ));
            Some(digest)
        }
        None => None,
    };

    let polled = probe::poll(
        Schedule {
            timeout: Duration::from_secs(args.timeout_seconds),
            interval: Duration::from_secs(args.poll_interval_seconds),
        },
        || probe_once(&args.url, expected.as_deref()),
        |attempt, error, remaining| {
            progress(&format!(
                "retrying: attempt {attempt}: {error}; {remaining}s remaining"
            ));
        },
    );

    Ok(match polled {
        Polled::Ready { attempt, .. } => Outcome::Pass {
            summary: format!(
                "{} is anonymously reachable (attempt {attempt}){}",
                args.url,
                if expected.is_some() {
                    " (body matches staged manifest)"
                } else {
                    ""
                }
            ),
        },
        Polled::TimedOut { last, .. } => Outcome::from_findings(
            vec![Finding {
                path: args
                    .expected_body_path
                    .as_deref()
                    .map_or_else(|| args.url.clone(), |path| root.relative(path)),
                line: 1,
                rule: "asset-not-reachable",
                message: format!(
                    "{} did not become reachable within {}s (last error: {last})",
                    args.url, args.timeout_seconds
                ),
            }],
            String::new(),
            "app-notification verify-asset: the release asset does not serve the staged manifest"
                .to_owned(),
        ),
    })
}

/// One anonymous GET; `Err` carries the diagnostic, checked in the retired
/// tool's order: transport, status, JSON, `release_tag`, then the digest.
pub(crate) fn probe_once(url: &str, expected_sha256: Option<&str>) -> Result<(), String> {
    let response = probe::fetch(&Request {
        url,
        headers: &[("Accept", "application/json")],
        user_agent: Some(USER_AGENT),
        socket_timeout: SOCKET_TIMEOUT,
    })
    .map_err(|error| format!("transport error: {error}"))?;
    if response.status != 200 {
        return Err(format!("unexpected status {}", response.status));
    }
    let document: Value = serde_json::from_slice(&response.body)
        .map_err(|error| format!("body is not JSON: {error}"))?;
    let has_tag = document
        .get("release_tag")
        .and_then(Value::as_str)
        .is_some_and(|tag| !tag.trim().is_empty());
    if !has_tag {
        return Err("manifest is missing a non-empty release_tag".to_owned());
    }
    if let Some(expected) = expected_sha256 {
        let actual = probe::sha256_hex(&response.body);
        if actual != expected {
            return Err(format!(
                "body SHA-256 mismatch: expected {expected}, got {actual} \
                 (CDN likely still serving the previous same-tag asset)"
            ));
        }
    }
    Ok(())
}
