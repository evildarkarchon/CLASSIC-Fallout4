//! `cargo xtask app-notification smoke-pages`: after the gh-pages push, poll
//! the Pages manifest until it serves exactly the staged `manifest.json`
//! bytes.
//!
//! The notification channel allows notification-only republishes that keep
//! the same binary `release_tag` while changing `min_supported_version` or
//! `display`. A `release_tag` comparison would pass against the previous
//! Pages payload, and the final "Clear prerelease flag" step would then make
//! the new release visible to the Releases fallback while Pages-first clients
//! still read the old one. So the whole body's SHA-256 must match. The check
//! is `publish::pages`, shared with `yaml-data smoke-pages`; only the
//! `--pages-path` default differs.

use std::path::PathBuf;

use anyhow::Result;

use crate::publish::pages::{self, Smoke};
use crate::{Outcome, RepoRoot};

/// `cargo xtask app-notification smoke-pages` arguments.
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
    #[arg(long, default_value = "app-notification/manifest-latest.json")]
    pub pages_path: String,
    /// Override the Pages root URL (for example a localhost server). When
    /// omitted, --owner/--repo build the live GitHub Pages URL.
    #[arg(long, value_name = "URL")]
    pub base_url: Option<String>,
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
    pages::smoke(
        root,
        &Smoke {
            family: "app-notification",
            owner: args.owner.as_deref(),
            repo: args.repo.as_deref(),
            pages_path: &args.pages_path,
            base_url: args.base_url.as_deref(),
            expected_body_path: &args.expected_body_path,
            timeout_seconds: args.timeout_seconds,
            poll_interval_seconds: args.poll_interval_seconds,
        },
        progress,
    )
}
