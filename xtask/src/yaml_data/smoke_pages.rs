//! `cargo xtask yaml-data smoke-pages`: after the gh-pages push, poll the
//! Pages manifest until it serves exactly the staged `manifest.json` bytes.
//!
//! Pages deploys are eventually consistent. Comparing only `release_tag` can
//! pass against the previous payload on a same-tag republish, so the whole
//! body's SHA-256 must match (the retired `--tag` mode is gone). Live runs
//! poll `https://<owner>.github.io/<repo>/<pages-path>`; `--base-url` points
//! the same check at another root, such as a local test server.

use std::path::PathBuf;
use std::time::Duration;

use anyhow::{Context, Result};

use crate::publish::probe::{self, Polled, Request, Schedule};
use crate::{Finding, Outcome, RepoRoot};

/// Per-request socket timeout (fixed, as in the retired tool).
const SOCKET_TIMEOUT: Duration = Duration::from_secs(15);

/// `cargo xtask yaml-data smoke-pages` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// The "<owner>" segment of the repo. Required unless --base-url is provided.
    #[arg(long, required_unless_present = "base_url")]
    pub owner: Option<String>,
    /// The "<repo>" segment (no owner prefix). Required unless --base-url is provided.
    #[arg(long, required_unless_present = "base_url")]
    pub repo: Option<String>,
    /// Require the response bytes to equal the bytes at this path (SHA-256 compared).
    #[arg(long, value_name = "FILE")]
    pub expected_body_path: PathBuf,
    /// Total budget for retrying.
    #[arg(long, default_value_t = 180)]
    pub timeout_seconds: u64,
    /// Seconds between polls.
    #[arg(long, default_value_t = 10)]
    pub poll_interval_seconds: u64,
    /// Path under the Pages root.
    #[arg(long, default_value = "yaml-data/manifest-latest.json")]
    pub pages_path: String,
    /// Override the Pages root URL (for example a localhost server). When
    /// omitted, --owner/--repo build the live GitHub Pages URL.
    #[arg(long, value_name = "URL")]
    pub base_url: Option<String>,
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
/// other statuses and transport errors count as `fetch-failed`.
///
/// # Errors
///
/// When the URL cannot be built or the expected body cannot be read.
pub(crate) fn run(root: &RepoRoot, args: Args, progress: &mut dyn FnMut(&str)) -> Result<Outcome> {
    let url = pages_url(
        args.owner.as_deref(),
        args.repo.as_deref(),
        &args.pages_path,
        args.base_url.as_deref(),
    )
    .context("--owner and --repo are required unless --base-url is provided")?;
    let staged = std::fs::read(&args.expected_body_path)
        .with_context(|| format!("reading {}", args.expected_body_path.display()))?;
    let expected = probe::sha256_hex(&staged);
    progress(&format!(
        "strict-body smoke test: expecting sha256={expected} ({} bytes from {})",
        staged.len(),
        args.expected_body_path.display()
    ));

    let polled = probe::poll(
        Schedule {
            timeout: Duration::from_secs(args.timeout_seconds),
            interval: Duration::from_secs(args.poll_interval_seconds),
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
                path: root.relative(&args.expected_body_path),
                line: 1,
                rule: "pages-not-serving",
                message: format!(
                    "{url} did not serve expected bytes (sha256={expected}) within {}s (last saw {last})",
                    args.timeout_seconds
                ),
            }],
            String::new(),
            "yaml-data smoke-pages: the Pages manifest does not match the staged manifest"
                .to_owned(),
        ),
    })
}

#[cfg(test)]
#[path = "smoke_pages_tests.rs"]
mod tests;
