//! `cargo xtask app-notification dry-run`: rehearse the side-effect-free
//! parts of `.github/workflows/publish-app-notification.yml` locally, so a
//! maintainer can check an `app-notification-v<SEMVER>` tag, the generated
//! manifest bytes, Pages staging and the gate order without pushing a
//! throwaway tag or touching GitHub Releases.
//!
//! The steps run in-process (the retired tool spawned each helper script)
//! against a localhost server that stands in for both the release asset URL
//! and GitHub Pages. The only subprocess left is the read-only `git` lookup
//! of the tag's publication time, which mirrors the workflow's own step.
//! `--simulate-release-asset-mismatch` and `--simulate-pages-mismatch` stage
//! stale bytes so the matching gate can be seen to fail.

use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::Arc;
use std::thread::JoinHandle;
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result, anyhow, bail};

use super::validate::{check_source, check_workflow_tag};
use super::{manifest, smoke_pages, verify_asset};
use crate::publish::utc_timestamp;
use crate::{Finding, Outcome, RepoRoot};

/// Default source, relative to the repository root.
const DEFAULT_SOURCE: &str = "CLASSIC Data/app-notification.yaml";
/// The staged manifest, relative to the work directory.
pub const STAGED_MANIFEST: &str = "staging/manifest.json";
/// The staged rolling Pages manifest, relative to the work directory.
pub const PAGES_LATEST: &str = "gh-pages/app-notification/manifest-latest.json";
/// The staged release-asset tree, relative to the work directory; the asset
/// is `<RELEASE_ASSETS>/<tag>/manifest.json`.
pub const RELEASE_ASSETS: &str = "releases/download";
/// Name prefix of the preserved temporary work directory.
const TEMP_PREFIX: &str = "classic-app-notification-dry-run-";

/// What the mismatch simulations stage instead of the generated manifest.
const STALE_MANIFEST: &[u8] = b"{\n  \"manifest_version\": \"1.0\",\n  \"release_tag\": \"v0.0.0\",\n  \"latest_version\": \"0.0.0\",\n  \"published_at\": \"1970-01-01T00:00:00Z\"\n}\n";

/// `cargo xtask app-notification dry-run` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// Tag that would trigger the workflow, e.g. app-notification-v9.2.0.
    #[arg(long)]
    pub workflow_tag: String,
    /// Path to app-notification.yaml (default: "CLASSIC Data/app-notification.yaml"
    /// under the repository root).
    #[arg(long, value_name = "FILE")]
    pub source: Option<PathBuf>,
    /// RFC 3339 timestamp to use when the source has published_at: null.
    /// Defaults to the local tag timestamp when present, otherwise current UTC.
    #[arg(long)]
    pub published_at: Option<String>,
    /// Require the workflow tag to exist locally so timestamp resolution
    /// mirrors CI exactly.
    #[arg(long)]
    pub require_existing_tag: bool,
    /// Directory for dry-run outputs. Defaults to a preserved temp directory.
    #[arg(long, value_name = "DIR")]
    pub work_dir: Option<PathBuf>,
    /// Retry budget for the local release and Pages probes.
    #[arg(long, default_value_t = 5)]
    pub timeout_seconds: u64,
    /// Stage stale release-asset bytes so the release probe fails before Pages staging.
    #[arg(long)]
    pub simulate_release_asset_mismatch: bool,
    /// Stage stale Pages bytes so the Pages smoke test fails before final visibility.
    #[arg(long)]
    pub simulate_pages_mismatch: bool,
}

/// Runs the nine dry-run stages, reporting each as `[n/9] …` (plus what it
/// staged and each passing gate's `OK:` line) through `progress`.
///
/// The tag is validated before the source is read, and nothing is written
/// until both pass. A failing gate returns that gate's `Fail` outcome; the
/// work directory is kept either way so its contents can be inspected.
///
/// # Errors
///
/// When `--require-existing-tag` is set and the tag has no local timestamp,
/// or when the work directory, its files or the local server cannot be
/// created.
pub(crate) fn run(root: &RepoRoot, args: Args, progress: &mut dyn FnMut(&str)) -> Result<Outcome> {
    let tag = args.workflow_tag.as_str();
    let source = std::path::absolute(
        args.source
            .clone()
            .unwrap_or_else(|| root.join(DEFAULT_SOURCE)),
    )
    .context("resolving --source")?;

    progress("[1/9] Validate app-notification workflow tag");
    let findings = check_workflow_tag(tag);
    if !findings.is_empty() {
        return Ok(failed(findings));
    }
    progress(&format!("OK: {tag} passes app-notification tag validation"));

    progress("[2/9] Validate app-notification source");
    let findings = check_source(root, &source);
    if !findings.is_empty() {
        return Ok(failed(findings));
    }
    progress(&format!(
        "OK: {} passes app-notification validation",
        source.display()
    ));

    progress("[3/9] Resolve tag publication timestamp");
    let (published_at, timestamp_source) = resolve_published_at(
        root,
        tag,
        args.published_at.as_deref(),
        args.require_existing_tag,
    )?;
    progress(&format!("published_at={published_at} ({timestamp_source})"));

    let work = prepare_work_dir(args.work_dir.as_deref())?;
    let staged = under(&work, STAGED_MANIFEST);

    progress("[4/9] Generate manifest.json");
    let generated = manifest::run(
        root,
        manifest::Args {
            source: source.clone(),
            output: staged.clone(),
            published_at: Some(published_at),
        },
    )?;
    if !passed(&generated, progress) {
        return Ok(generated);
    }
    progress(&format!("staged manifest: {}", staged.display()));

    let server = LocalServer::serve(work.clone())?;

    progress("[5/9] Stage local release asset");
    let asset = under(&work, RELEASE_ASSETS).join(tag).join("manifest.json");
    stage(&staged, &[&asset], args.simulate_release_asset_mismatch)?;
    progress(&format!("staged release asset: {}", asset.display()));

    progress("[6/9] Verify local release asset with existing probe");
    let verified = verify_asset::run(
        root,
        verify_asset::Args {
            url: format!(
                "{}/{RELEASE_ASSETS}/{}/manifest.json",
                server.base,
                quote(tag)
            ),
            expected_body_path: Some(staged.clone()),
            timeout_seconds: args.timeout_seconds,
            poll_interval_seconds: 1,
        },
        progress,
    )?;
    if !passed(&verified, progress) {
        return Ok(verified);
    }

    progress("[7/9] Stage local gh-pages manifests");
    let latest = under(&work, PAGES_LATEST);
    let tagged = under(&work, "gh-pages/app-notification").join(format!("manifest-{tag}.json"));
    stage(&staged, &[&latest, &tagged], args.simulate_pages_mismatch)?;
    progress(&format!("staged Pages latest: {}", latest.display()));
    progress(&format!("staged Pages tagged: {}", tagged.display()));

    progress("[8/9] Smoke-test local Pages manifest with reused helper");
    let smoked = smoke_pages::run(
        root,
        smoke_pages::Args {
            owner: None,
            repo: None,
            expected_body_path: staged,
            timeout_seconds: args.timeout_seconds,
            poll_interval_seconds: 1,
            pages_path: "app-notification/manifest-latest.json".to_owned(),
            base_url: Some(format!("{}/gh-pages", server.base)),
        },
        progress,
    )?;
    if !passed(&smoked, progress) {
        return Ok(smoked);
    }
    drop(server);

    progress("[9/9] Dry run complete; live workflow would clear prerelease flag now");
    Ok(Outcome::Pass {
        summary: format!(
            "dry run complete; outputs preserved under: {}",
            work.display()
        ),
        report: None,
    })
}

/// A `Fail` outcome for a dry-run validation stage.
fn failed(findings: Vec<Finding>) -> Outcome {
    let count = findings.len();
    Outcome::from_findings(
        findings,
        String::new(),
        format!("app-notification dry-run: {count} finding(s)"),
    )
}

/// Reports a passing stage's `OK:` line; `false` when the stage failed.
fn passed(outcome: &Outcome, progress: &mut dyn FnMut(&str)) -> bool {
    match outcome {
        Outcome::Pass { summary, .. } => {
            progress(&format!("OK: {summary}"));
            true
        }
        Outcome::Fail { .. } => false,
    }
}

/// The `published_at` fallback and where it came from, in the workflow's
/// order: the explicit value, the annotated tag's tagger date, the tagged
/// commit's committer date, then (unless `require_existing_tag`) the current
/// UTC second. The `git` lookups run read-only in the repository root; a
/// missing tag or a missing `git` both mean "no local timestamp".
///
/// # Errors
///
/// When `require_existing_tag` is set and no local timestamp exists.
fn resolve_published_at(
    root: &RepoRoot,
    tag: &str,
    explicit: Option<&str>,
    require_existing_tag: bool,
) -> Result<(String, String)> {
    if let Some(explicit) = explicit.filter(|value| !value.is_empty()) {
        return Ok((explicit.to_owned(), "--published-at argument".to_owned()));
    }
    let tag_ref = format!("refs/tags/{tag}");
    if let Some(tagger) = git_stdout(
        root,
        &[
            "for-each-ref",
            "--format=%(taggerdate:iso-strict)",
            &tag_ref,
        ],
    ) {
        return Ok((tagger, format!("local annotated tag {tag}")));
    }
    if let Some(committer) = git_stdout(root, &["log", "-1", "--format=%cI", tag]) {
        return Ok((committer, format!("local lightweight tag/commit {tag}")));
    }
    if require_existing_tag {
        bail!(
            "workflow tag does not exist locally, so no workflow timestamp could be resolved. \
             Pass --published-at or omit --require-existing-tag."
        );
    }
    Ok((
        utc_timestamp(SystemTime::now()),
        "current UTC time (tag does not exist locally)".to_owned(),
    ))
}

/// Trimmed stdout of `git <args>` in the repository root, or `None` when git
/// is missing, fails, or prints nothing.
fn git_stdout(root: &RepoRoot, args: &[&str]) -> Option<String> {
    let output = Command::new("git")
        .current_dir(root.path())
        .args(args)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    (!text.is_empty()).then_some(text)
}

/// Creates the work directory (`--work-dir`, or a new preserved temp
/// directory) and returns its resolved path.
fn prepare_work_dir(path: Option<&Path>) -> Result<PathBuf> {
    let dir = match path {
        Some(path) => {
            std::fs::create_dir_all(path)
                .with_context(|| format!("creating {}", path.display()))?;
            path.to_path_buf()
        }
        None => new_temp_dir()?,
    };
    let resolved = dir
        .canonicalize()
        .with_context(|| format!("resolving {}", dir.display()))?;
    Ok(strip_verbatim(resolved))
}

/// Creates `<temp>/classic-app-notification-dry-run-<unique>`. It is not
/// removed afterwards: the dry run's outputs are for the maintainer to read.
fn new_temp_dir() -> Result<PathBuf> {
    let base = std::env::temp_dir();
    let pid = std::process::id();
    for attempt in 0..100_u32 {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0, |elapsed| elapsed.subsec_nanos());
        let dir = base.join(format!("{TEMP_PREFIX}{pid}-{nanos:09}-{attempt}"));
        match std::fs::create_dir(&dir) {
            Ok(()) => return Ok(dir),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
                // Name collision with an earlier dry run: retry with the next
                // attempt number (and a fresh timestamp).
            }
            Err(error) => {
                return Err(error).with_context(|| format!("creating {}", dir.display()));
            }
        }
    }
    bail!(
        "could not create a unique {TEMP_PREFIX}* directory under {}",
        base.display()
    )
}

/// Drops Windows' `\\?\` verbatim prefix from a canonical drive path, so the
/// reported path is the familiar `C:\…` form. Other paths are kept.
fn strip_verbatim(path: PathBuf) -> PathBuf {
    let text = path.to_string_lossy();
    match text.strip_prefix(r"\\?\") {
        Some(rest) if rest.as_bytes().get(1) == Some(&b':') => PathBuf::from(rest),
        _ => path,
    }
}

/// `work` joined with the `/`-separated `relative`, one component at a time,
/// so reported paths use the platform's separator throughout.
fn under(work: &Path, relative: &str) -> PathBuf {
    relative
        .split('/')
        .fold(work.to_path_buf(), |path, part| path.join(part))
}

/// Writes each target as a copy of `staged`, or as the stale manifest when
/// `stale` is set, creating parent directories.
fn stage(staged: &Path, targets: &[&Path], stale: bool) -> Result<()> {
    for target in targets {
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("creating {}", parent.display()))?;
        }
        if stale {
            std::fs::write(target, STALE_MANIFEST)
                .with_context(|| format!("writing {}", target.display()))?;
        } else {
            std::fs::copy(staged, target)
                .with_context(|| format!("copying {} to {}", staged.display(), target.display()))?;
        }
    }
    Ok(())
}

/// Percent-encodes `text` like Python's `urllib.parse.quote(text, safe="")`.
fn quote(text: &str) -> String {
    text.bytes()
        .map(|byte| {
            if byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'-' | b'~') {
                char::from(byte).to_string()
            } else {
                format!("%{byte:02X}")
            }
        })
        .collect()
}

/// A localhost static file server over the work directory; it stands in for
/// both `releases/download/…` and the gh-pages root. Stopped when dropped.
struct LocalServer {
    /// `http://127.0.0.1:<port>`, no trailing slash.
    base: String,
    server: Arc<tiny_http::Server>,
    worker: Option<JoinHandle<()>>,
}

impl LocalServer {
    /// Starts serving `root` on `127.0.0.1:<free port>` from one background
    /// thread (the probes request one file at a time).
    fn serve(root: PathBuf) -> Result<Self> {
        let server = Arc::new(
            tiny_http::Server::http("127.0.0.1:0")
                .map_err(|error| anyhow!("starting the local server: {error}"))?,
        );
        let address = server
            .server_addr()
            .to_ip()
            .context("the local server has no IP address")?;
        let worker = {
            let server = Arc::clone(&server);
            std::thread::spawn(move || {
                for request in server.incoming_requests() {
                    let response = match local_file(&root, request.url())
                        .and_then(|path| std::fs::read(path).ok())
                    {
                        Some(body) => tiny_http::Response::from_data(body),
                        None => tiny_http::Response::from_data(Vec::new()).with_status_code(404),
                    };
                    // A probe that hung up has already reported its own error.
                    let _ = request.respond(response);
                }
            })
        };
        Ok(Self {
            base: format!("http://{address}"),
            server,
            worker: Some(worker),
        })
    }
}

impl Drop for LocalServer {
    fn drop(&mut self) {
        self.server.unblock();
        if let Some(worker) = self.worker.take() {
            // The worker only serves files; a panic there has nothing to report.
            let _ = worker.join();
        }
    }
}

/// The file under `root` that the request path `url` names: query and
/// fragment dropped, percent-escapes decoded, and any segment that could
/// leave `root` (`..`, `.`, a drive or a backslash) refused.
fn local_file(root: &Path, url: &str) -> Option<PathBuf> {
    let path = url.split(['?', '#']).next().unwrap_or_default();
    let decoded = String::from_utf8(percent_decode(path)?).ok()?;
    let mut file = root.to_path_buf();
    for segment in decoded.split('/').filter(|segment| !segment.is_empty()) {
        if matches!(segment, "." | "..") || segment.contains(['\\', ':']) {
            return None;
        }
        file.push(segment);
    }
    file.is_file().then_some(file)
}

/// Decodes `%XX` escapes; `None` on a malformed escape.
fn percent_decode(text: &str) -> Option<Vec<u8>> {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' {
            let hex = std::str::from_utf8(bytes.get(index + 1..index + 3)?).ok()?;
            out.push(u8::from_str_radix(hex, 16).ok()?);
            index += 3;
        } else {
            out.push(bytes[index]);
            index += 1;
        }
    }
    Some(out)
}

#[cfg(test)]
#[path = "dry_run_tests.rs"]
mod tests;
