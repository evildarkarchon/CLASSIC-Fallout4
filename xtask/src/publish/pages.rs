//! The strict-body GitHub Pages smoke test shared by `yaml-data smoke-pages`
//! and `app-notification smoke-pages`: after the gh-pages push, poll the
//! Pages manifest until it serves exactly the staged `manifest.json` bytes.
//!
//! Pages deploys are eventually consistent. Comparing only `release_tag` can
//! pass against the previous payload on a same-tag republish (or, for
//! app-notification, a notification-only republish), so the whole body's
//! SHA-256 must match. Live runs poll
//! `https://<owner>.github.io/<repo>/<pages-path>`; a base URL points the
//! same check at another root, such as a local server.

use std::path::Path;
use std::time::Duration;

use anyhow::{Context, Result};

use super::probe::{self, Polled, Request, Schedule};
use crate::{Finding, Outcome, RepoRoot};

/// Per-request socket timeout (fixed, as in the retired tool).
const SOCKET_TIMEOUT: Duration = Duration::from_secs(15);

/// One smoke test: where to poll, what to expect, and for how long.
#[derive(Debug, Clone, Copy)]
pub(crate) struct Smoke<'a> {
    /// The publish family, for the failure summary (`yaml-data`, …).
    pub family: &'a str,
    /// The `<owner>` segment of the live Pages URL.
    pub owner: Option<&'a str>,
    /// The `<repo>` segment of the live Pages URL.
    pub repo: Option<&'a str>,
    /// Path under the Pages root.
    pub pages_path: &'a str,
    /// Overrides the Pages root.
    pub base_url: Option<&'a str>,
    /// The staged bytes the response must equal.
    pub expected_body_path: &'a Path,
    /// Total budget for retrying.
    pub timeout_seconds: u64,
    /// Seconds between polls.
    pub poll_interval_seconds: u64,
}

/// The URL to poll: `<base-url>/<pages-path>` when a base URL is given,
/// otherwise `https://<owner>.github.io/<repo>/<pages-path>`. Slashes at the
/// join are collapsed. `None` when neither a base URL nor both owner and repo
/// are available.
pub(crate) fn pages_url(
    owner: Option<&str>,
    repo: Option<&str>,
    pages_path: &str,
    base_url: Option<&str>,
) -> Option<String> {
    let path = pages_path.trim_start_matches('/');
    match (base_url.filter(|base| !base.is_empty()), owner, repo) {
        (Some(base), _, _) => Some(format!("{}/{path}", base.trim_end_matches('/'))),
        (None, Some(owner), Some(repo)) if !owner.is_empty() && !repo.is_empty() => {
            Some(format!("https://{owner}.github.io/{repo}/{path}"))
        }
        _ => None,
    }
}

/// Polls the Pages URL until its body hashes to the staged manifest's SHA-256.
///
/// `progress` first gets a `strict-body smoke test: expecting …` line, then a
/// `retrying: …` line before each retry. Any 2xx body counts as fetched;
/// other statuses and transport errors count as `fetch-failed`. A timeout is
/// a `pages-not-serving` finding against the expected body path.
///
/// # Errors
///
/// When the URL cannot be built or the expected body cannot be read.
pub(crate) fn smoke(
    root: &RepoRoot,
    smoke: &Smoke<'_>,
    progress: &mut dyn FnMut(&str),
) -> Result<Outcome> {
    let url = pages_url(smoke.owner, smoke.repo, smoke.pages_path, smoke.base_url)
        .context("--owner and --repo are required unless --base-url is provided")?;
    let staged = std::fs::read(smoke.expected_body_path)
        .with_context(|| format!("reading {}", smoke.expected_body_path.display()))?;
    let expected = probe::sha256_hex(&staged);
    progress(&format!(
        "strict-body smoke test: expecting sha256={expected} ({} bytes from {})",
        staged.len(),
        smoke.expected_body_path.display()
    ));

    let polled = probe::poll(
        Schedule {
            timeout: Duration::from_secs(smoke.timeout_seconds),
            interval: Duration::from_secs(smoke.poll_interval_seconds),
        },
        || {
            let response = probe::fetch(&Request {
                url: &url,
                headers: &[
                    ("Accept", "application/json"),
                    ("Cache-Control", "no-cache"),
                ],
                user_agent: None,
                socket_timeout: SOCKET_TIMEOUT,
            });
            match response {
                Ok(response) if (200..300).contains(&response.status) => {
                    let digest = probe::sha256_hex(&response.body);
                    if digest == expected {
                        Ok(digest)
                    } else {
                        Err(format!("sha256={digest}"))
                    }
                }
                _ => Err("fetch-failed".to_owned()),
            }
        },
        |attempt, last_seen, remaining| {
            progress(&format!(
                "retrying: attempt {attempt}, remote {last_seen}, expected sha256={expected}, \
                 {remaining}s remaining"
            ));
        },
    );

    Ok(match polled {
        Polled::Ready { value, attempt } => Outcome::Pass {
            summary: format!("{url} serves staged manifest (sha256={value}, attempt {attempt})"),
        },
        Polled::TimedOut { last, .. } => Outcome::from_findings(
            vec![Finding {
                path: root.relative(smoke.expected_body_path),
                line: 1,
                rule: "pages-not-serving",
                message: format!(
                    "{url} did not serve expected bytes (sha256={expected}) within {}s (last saw {last})",
                    smoke.timeout_seconds
                ),
            }],
            String::new(),
            format!(
                "{} smoke-pages: the Pages manifest does not match the staged manifest",
                smoke.family
            ),
        ),
    })
}

#[cfg(test)]
#[path = "pages_tests.rs"]
mod tests;
